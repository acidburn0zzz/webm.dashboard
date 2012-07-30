#!/usr/bin/env python
##  Copyright (c) 2012 The WebM project authors. All Rights Reserved.
##
##  Use of this source code is governed by a BSD-style license
##  that can be found in the LICENSE file in the root of the source
##  tree. An additional intellectual property rights grant can be found
##  in the file PATENTS.  All contributing project authors may
##  be found in the AUTHORS file in the root of the source tree.
##

# Setup django to silence deprecation warning for 0.96
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from google.appengine.dist import use_library
use_library('django', '1.2')

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp import util
from google.appengine.ext import db

import json
import re
import urllib
import time

# Here is everything we need to format the output for the UI
from cache import CachedDataView, cache_result
from google.appengine.api import memcache
from model import FileCache, CommitCache, MetricCache, FileSetCache

class DrilldownCommitCache(CachedDataView):
    def begin_getitem(self, commit):
        key = db.Key.from_path('Commit', commit)
        return db.get_async(key)

    def getitem(self, commit, rpc):
        commitdata = rpc.get_result()

        subject = commitdata.message.split("\n")[0]
        changeid = re.search(r'Change-Id: ([I0-9a-f]+)', commitdata.message)
        if changeid:
            subject = "%s: %s"%(changeid.group(1)[:9], subject)
        commitdata = {"displayname" : "Patch Set: (" + commit[:8] +")",
                     "commitSet" : subject,
                     "parents" : commitdata.parents,
                     "date" : commitdata.commit_time,
                     "author" : commitdata.author }
        return commitdata

@cache_result()
def metric_tree_formatter(metric_cache):
    # We only display a metric if it has a display name
    # A display name of "" means we have something like bitrate or time
    formatted = []
    for metricname, metricdata in metric_cache:
        if metricdata.display_name != "":
            formatted.append({"data":metricdata.display_name,
                              "attr":{"id": metricname}})
    return formatted

@cache_result()
def file_tree_formatter(file_cache):
    filesets = {}
    for filename, filedata in file_cache:
        for fileset in filedata.file_sets:
            if fileset in filesets:
                filesets[fileset].append({"attr": {"id": filename},
                                          "data":filedata.display_name})
            else:
                filesets[fileset] = [{"attr": {"id": filename},
                                      "data":filedata.display_name}]
    formatted = []
    for fileset in filesets:
        #formatted.append({"data":fileset, "children":filesets[fileset],
        #                  "attr": {"id": "@" + fileset}})
        formatted.append({"data":fileset,
                          "attr": {"id": "~" + fileset}})
    return formatted

@cache_result()
def commit_tree_formatter(commit_cache):
    commitSets = {}
    for patch, patchdata in commit_cache:
        commitDescription = patchdata["commitSet"]

        prettydate = "%s" %(patchdata["date"])

        # We convert the time also to ms for comparison (in sorting)
        ms = time.mktime(patchdata["date"].utctimetuple())
        ms += getattr(patchdata["date"], 'microseconds', 0) / 1000
        date = int(ms)

        if commitDescription in commitSets:
            commitSets[commitDescription].append({"attr": {"id": patch,
                                                           "date" : date,
                                                           "prettydate" : prettydate,
                                                           "author" : patchdata["author"]},
                                                  "data":patchdata["displayname"]})
        else:
            commitSets[commitDescription] = [{"attr": {"id": patch,
                                                        "date" : date,
                                                        "prettydate" : prettydate,
                                                        "author" : patchdata["author"]},
                                              "data":patchdata["displayname"]}]
    formatted = []
    n = 0
    for commitDescription in commitSets:
        date = commitSets[commitDescription][0]["attr"]["date"]
        prettydate = commitSets[commitDescription][0]["attr"]["prettydate"]
        formatted.append({"data":commitDescription,
                          "children":commitSets[commitDescription],
                          "attr": {"id": "_c" + str(n),
                                   "date" : date,
                                   "author" : "See patch",
                                   "prettydate" : prettydate }})
        n += 1
    return formatted

def tree_formatter(query_result):
    #memcache.flush_all(); # For debugging

    # When recieved from drilldown, these are all sets
    metrics = query_result[0]
    configs = query_result[1]
    files = query_result[2]
    commits = query_result[3]

    # The metric tree
    metrics = metric_tree_formatter(MetricCache(metrics))

    # Handle the file tree
    files = file_tree_formatter(FileCache(files))

    # Handle the commit tree
    commits = commit_tree_formatter(DrilldownCommitCache(commits))

    formatted = []
    for config in configs:
        formatted.append({"data":config, "attr":{"id": config}})
    configs = formatted

    formatted_result = [metrics, configs, files, commits]
    return formatted_result


# ------------------------------------------------------------------------------
class DrilldownMatrixEntry(db.Model):
    """A non-sparse 4-dimensional matrix (DME)

    Each row in this table represents a number of queries which can be answered
    from the available metric data.
    """

    metrics = db.StringListProperty()
    configs = db.StringListProperty()
    files   = db.StringListProperty()
    commits = db.StringListProperty()


class DrilldownMatrixEntryProxy(object):
    """Object that allows in-memory manipulations of DME

    Allows operations like merges without a round trip through the datastore.
    """
    def __init__(self, metric, config, files, commits):
        """Construct a DME not (yet) backed by a datastore entity"""
        self._data = [metric, config, files, commits]
        self._entity = None

    @classmethod
    def from_entity(klass, entity):
        """Construct a DME backed by a datastore entity"""
        self = klass(set(entity.metrics), set(entity.configs),
                     set(entity.files), set(entity.commits))
        self._entity = entity
        return self

    def save_async(self, parent):
        """Persist a DME to the datastore

        The root must be specified as the parent so that the store can
        happen as part of an asynchronous transaction.
        """
        if not self._entity:
            self._entity = DrilldownMatrixEntry(parent=parent)
        self._entity.metrics = list(self._data[0])
        self._entity.configs = list(self._data[1])
        self._entity.files   = list(self._data[2])
        self._entity.commits = list(self._data[3])
        db.put_async(self._entity)

    def merge(self, new_entry):
        """Merge another DME into this one

        If the non-sparsity constraint can be met by taking the union of
        the two DMEs, combine them into one.

        Returns True if a merge took place, False otherwise.
        """
        subsets = 0
        for field_idx in range(4):
            if self.field_issubset(new_entry, field_idx):
                subsets += 1

        if subsets == 4:
            return True

        if subsets == 3:
            # return the union of the two entries
            for field_idx in range(4):
                self._data[field_idx] = self.field_union(new_entry, field_idx)
            return True

        # Unmergeable.
        return False

    def field_issubset(self, new_entry, field):
        """Is the new entity a subset of this one for a given field?"""
        return new_entry._data[field].issubset(self._data[field])

    def field_union(self, new_entry, field):
        """The union of the new entity and this one"""
        return new_entry._data[field].union(self._data[field])


class DrilldownMatrix(object):
    """An in-memory proxy for a list of DrilldownMatrixEntry

    Maintains a copy of the DrilldownMatrixEntry table for performing various
    set membership queries.
    """
    def __init__(self):
        self._entries = []
        self._root_entity = None

    def entries(self):
        """Get the current list of entries, loading if necessary"""
        if not self._entries:
            # Get root
            self._root_entity = DrilldownMatrixEntry.get_by_key_name("root")
            if not self._root_entity:
                self._root_entity = DrilldownMatrixEntry(key_name="root").put()

            for e in DrilldownMatrixEntry.all():
                if e != self._root_entity:
                    proxy = DrilldownMatrixEntryProxy.from_entity(e)
                    self._entries.append(proxy)
        return self._entries

    def insert(self, metric, config, files, commits):
        """Insert a new entry into the matrix

        Merge the current entry with an existing one if possible.
        """
        if metric and config and files and commits:
            new_entry = DrilldownMatrixEntryProxy(metric, config, files,
                                                  commits)
            size = len(metric) * len(config) * len(files) * len(commits)

            # Try to merge the whole entry as a group
            for entry in self.entries():
                if entry.merge(new_entry):
                     return

            # If that fails, take the cross product and add each
            if size > 1:
                for m in metric:
                    for cf in config:
                        for f in files:
                            for cm in commits:
                                self.insert(set([m]), set([cf]),
                                            set([f]), set([cm]))
                return

            # Otherwise, add a new entry
            self.entries().append(new_entry)

    def save(self):
        """Persist the list to the datastore"""
        def save_all_entries():
            for e in self.entries():
                e.save_async(self._root_entity)
        db.run_in_transaction(save_all_entries)

    def reset(self):
        """Reinitialize the object, forcing the data to be refetched"""
        self.__init__()

    def query_(self, metric=None, config=None, filename=None, commit=None):
        """Returns a subset of the matrix matching the given parameters"""
        def match_only(entry, params, field):
            """Does the entry match on only a single field"""
            if params[field]:
                return params[field] in entry._data[field]
            # No constraint given on this field, so it matches.
            return True

        def match_all_but(entry, params, exclude_field):
            """Does the entry matches all but one field"""
            for idx in range(4):
                if idx == exclude_field:
                    continue
                if not match_only(entry, params, idx):
                    return False
            return True

        params = (metric, config, filename, commit)
        result = [set(), set(), set(), set()]
        found = [not bool(x) for x in params]
        for e in self.entries():
            for idx in range(4):
                if params[idx] and match_only(e, params, idx):
                    found[idx] = True
                if match_all_but(e, params, idx):
                    result[idx] = result[idx].union(e._data[idx])

        # If there were no matches for a given field, don't return anything.
        # This shouldn't happen if the queries are limited to the results
        # returned by previous invokations of this function.
        for idx in range(4):
            if not found[idx]:
                result[idx] = set()

        # TODO(jkoleszar): need to format this jstree friendly
        return result

    def query(self, metric, config, filename, commit):
        def split_field(field):
            if field:
                for f in urllib.unquote(field).split(","):
                    yield f
            else:
                yield None

        fs_modded = []
        for f in urllib.unquote(filename).split(","):
            if f is not None and f != "" and f[0] == "~":
                fs_modded.append(f[1:])
        fs_cache = FileSetCache(fs_modded)

        result = None
        for m in split_field(metric):
            for cfg in split_field(config):
                for f in split_field(filename):
                    if f is not None and f[0] == '~' :
                        # We have a fileset instead of a file
                        # We replace any filesets with filenames
                        fsdata = fs_cache[f[1:]]

                        for fname in fsdata.files:
                            for cm in split_field(commit):
                                if not result:
                                    result = self.query_(m,cfg,fname,cm)
                                else:
                                    r = self.query_(m,cfg,fname,cm)
                                    for idx in range(4):
                                        result[idx] = result[idx].intersection(r[idx])

                    else: # Do we ever have a file, not fileset?
                        for cm in split_field(commit):
                            if not result:
                                result = self.query_(m,cfg,f,cm)
                            else:
                                r = self.query_(m,cfg,f,cm)
                                for idx in range(4):
                                    result[idx] = result[idx].intersection(r[idx])
        return result

drilldown = DrilldownMatrix()

class DrilldownQueryHandler(webapp.RequestHandler):
    def get(self, metric, config, filename, commit):
        result = drilldown.query(metric, config, filename, commit)

        # Here is our formatting
        result = tree_formatter(result)
        #self.response.out.write(json.dumps(map(list, result)))
        self.response.out.write(json.dumps(result))

class DrilldownResetHandler(webapp.RequestHandler):
    def get(self):
        memcache.flush_all()
        drilldown.reset()

def main():
    application = webapp.WSGIApplication([
        (r'/drilldown/(.*)/(.*)/(.*)/(.*)', DrilldownQueryHandler),
        ('/drilldown/reset', DrilldownResetHandler),
    ], debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
