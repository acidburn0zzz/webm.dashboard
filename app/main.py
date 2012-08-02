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
from google.appengine.api import memcache

# Standard libraries
import datetime
import hashlib
import json
import pickle
import StringIO
import urllib
import logging

# App libraries
from drilldown import drilldown
from cache import cache_result, CachedDataView
import curve_compare
import model

# We give metrics their own handler for convenience
class ImportMetricHandler(webapp.RequestHandler):
    def post(self):
        data = StringIO.StringIO(self.request.get("data"))
        for line in data:
            data = json.loads(line)

            # We first load the fileset into the database
            # For use later, we also add a list of filenames in the fileset
            m = model.Metric(key_name=data["name"],
                             display_name=data["display name"],
                             distortion=data["distortion"])
            m.put()
        memcache.flush_all()

class ImportFileSetHandler(webapp.RequestHandler):
    def post(self):
        files_added = {}
        data = StringIO.StringIO(self.request.get("data"))
        for line in data:
            data = json.loads(line)

            # We first load the fileset into the database
            # For use later, we also add a list of filenames in the fileset
            f = model.FileSet(key_name=data["name"],
                              display_name=data["name"],
                              files=data["setfiles"])
            f.put()

            for filename in data["setfiles"]:
                if filename not in files_added:
                    files_added[filename] = [data["name"]]
                else:
                    files_added[filename].append(data["name"])

        # We now update the database with the elements in files_added
        for filename in files_added:
            # TODO: Is there a better way of assigning display names?
            split_index = filename.rfind("_")
            model.File(key_name=filename,
                       display_name=filename[:split_index],
                       file_sets=files_added[filename]).put()
        memcache.flush_all()

class ImportCodecMetricHandler(webapp.RequestHandler):
    def put_metric_index(self, parent, metrics, files):
        if metrics and files:
            metric_list = list(metrics)
            file_list = list(files)

            h = hashlib.sha1()
            h.update(parent.key().name())
            h.update(parent.commit)
            h.update(parent.config_name)
            map(h.update, metric_list)
            map(h.update, file_list)
            model.CodecMetricIndex(key_name=h.hexdigest(),
                                   parent=parent,
                                   commit=parent.commit,
                                   config_name=parent.config_name,
                                   metrics=metric_list,
                                   files=file_list).put()

    def update_drilldown(self, parent, metrics, files):
        # TODO(jkoleszar): if drilldown is moved to a backend, maybe post this
        # through a task queue.
        commit = set([parent.commit])
        config = set([parent.config_name])
        drilldown.insert(metrics, set(config), files, set(commit))

    def post(self):
        for line in StringIO.StringIO(self.request.get("data")):
            # Key off a hash of the input line to make the import idempotent
            key = hashlib.sha1(line).hexdigest()

            # Deserialize data, populating optional fields
            data = {"config_flags": None,
                    "runtime_flags": None
                   }
            data.update(json.loads(line))

            # Put the data
            m = model.CodecMetric(key_name=key,
                                  commit=data["commit"],
                                  config_flags=data["config_flags"],
                                  runtime_flags=data["runtime_flags"],
                                  config_name=data["config"],
                                  data=data["data"])
            m.put()

            # Build indexes
            metrics = set()
            files = set()
            for filename, metric_entries in data["data"].iteritems():
                for metric_entry in metric_entries:
                    this_metrics = set(metric_entry.keys())
                    if this_metrics != metrics:
                        self.put_metric_index(m, metrics, files)
                        self.update_drilldown(m, metrics, files)
                        metrics = this_metrics
                        files = set()
                    files.add(filename)
            self.put_metric_index(m, metrics, files)
            self.update_drilldown(m, metrics, files)
        drilldown.save()
        memcache.flush_all()

def pretty_json(x):
    return json.dumps(x, indent=2, sort_keys=True)


@cache_result()
def fetch_codec_metric(metric, config, filename, commit):
    '''This function fetches the data for a given metric, config, filename,
    commit tuple. This functionality is used multiple places, such as
    CodecMetricHandler and AverageImprovementHandler.'''
    indexes = model.CodecMetricIndex.all(keys_only = True)
    indexes = indexes.filter('metrics =', metric)
    indexes = indexes.filter('config_name =', config)
    indexes = indexes.filter('files =', filename)
    indexes = indexes.filter('commit =', commit)
    keys = [k.parent() for k in indexes]

    if len(keys) == 0:
        return None

    result=[]
    for cm in db.get(keys):
        for run in cm.data[filename]:
            this_run_data = []

            # TODO(jkoleszar): How do we handle this properly?
            if "Bitrate" in run:
                this_run_data.append(run["Bitrate"])

            this_run_data.append(run[metric])
            result.append(this_run_data)

    # Sanity checks
    for r in result[1:]:
        assert len(r) == len(result[0])

    # Result is a list of lists. Sort by the first element of the nested
    # list.
    result = sorted(result, key=lambda x:x[0])
    return result

@cache_result()
def fetch_metric_for_fileset(metric, config, files, commit):
    """This function is a bulk version of fetch_codec_metric()"""
    indexes = model.CodecMetricIndex.all(keys_only = True)
    indexes = indexes.filter('metrics =', metric)
    indexes = indexes.filter('config_name =', config)
    indexes = indexes.filter('commit =', commit)
    keys = [k.parent() for k in indexes]

    if len(keys) == 0:
        return None

    results_by_file = {}
    for cm in db.get(keys):
        for filename, runs in cm.data.iteritems():
            if filename not in files:
                continue
            result = results_by_file.get(filename, [])
            for run in runs:
                this_run_data = []

                # TODO(jkoleszar): How do we handle this properly?
                if "Bitrate" in run:
                    this_run_data.append(run["Bitrate"])

                this_run_data.append(run[metric])
                result.append(this_run_data)
            results_by_file[filename] = result

    # Sanity checks
    for filename, result in results_by_file.iteritems():
        for r in result[1:]:
            assert len(r) == len(result[0])

        # Result is a list of lists. Sort by the first element of the nested
        # list.
        results_by_file[filename] = sorted(result, key=lambda x:x[0])
    return results_by_file

class CodecMetricHandler(webapp.RequestHandler):
    def get(self, metric, config, filename, commit):
        """Fetches the requested metric data as JSON"""

        result = fetch_codec_metric(metric, config, filename, commit)

        # Return the result
        if result:
            self.response.headers['Content-Type'] = 'application/json'
            self.response.out.write(pretty_json(result))
        else:
            self.error(404)

@cache_result()
def find_baseline(metric, config, filename, commits):
    def field_list(field):
        '''Returns the field as a list of strings.'''
        result = urllib.unquote(field).split(",")
        if len(result[0]) == 0:
            return None
        return result

    def find_first_parent(commit, data, candidates):
        while True:
            parents = data[commit].parents
            if not parents:
               # root node
               return None
            commit = parents[0]
            if commit in candidates:
                return commit

    candidates = drilldown.query(metric, config, filename, commits)[3]
    commit_data = model.CommitCache()
    commits = field_list(commits)
    parentage = {}
    for commit in commits:
        parentage[commit] = []

    root_nodes_seen = 0
    while root_nodes_seen < len(commits):
        for commit1 in commits:
            parents = parentage[commit1]
            if parents:
                this_commit = parents[-1]
            else:
                this_commit = commit1

            # already hit the root for this commit?
            if this_commit is None:
               continue

            parent = find_first_parent(this_commit, commit_data, candidates)
            parents.append(parent)
            if parent is None:
                root_nodes_seen += 1
                continue

            n = 0
            for commit2 in commits:
                if parent in parentage[commit2]:
                    n += 1

            if n == len(commits):
                # parent is found in all lineages
                return parent
    return None


def calculate_average_improvement(m, cfg, fs, cm, base_data):
    '''Calculates the average improvement given the set up and the parent
    commit, caching the result'''

    data = fetch_metric_for_fileset(m, cfg, fs, cm)
    result = {}
    sum_overall = 0
    count_overall = 0
    for f in fs:
        composite = curve_compare.DataBetter(base_data[f], data[f])
        composite *= 100 # Make it a percent
        sum_overall += composite
        count_overall += 1
        result[f] = composite
    if result:
        return sum_overall / count_overall, result
    return None, result


@cache_result()
def get_files_from_fileset(fileset, fs_cache):
    '''Returns a list of files in a given fileset.'''
    fsdata = fs_cache[fileset]
    return fsdata.files[:]

class AverageImprovementHandler(webapp.RequestHandler):
    def get(self, metrics, configs, filenames, commits):
        """Calculates the requested composite metrics and outputs as JSON"""
        def split_field(field):
            if field:
                for f in urllib.unquote(field).split(","):
                    yield f

        def field_list(field):
            '''Returns the field as a list of strings.'''
            result = urllib.unquote(field).split(",")
            if len(result[0]) == 0:
                return []
            return result

        # Find the baseline based on the raw URL variables
        parent = find_baseline(metrics, configs, filenames, commits)
        # We format the end of the table with extra info
        if parent:
            parent_str = parent[:9]
        else:
            parent_str = "None found"


        # We expect to get filesets instead
        fs_modded = []
        for f in urllib.unquote(filenames).split(","):
            if f is not None and f != "" and f[0] == "~":
                fs_modded.append(f[1:])
        fileset_cache = model.FileSetCache(fs_modded)

        fsets = set([])
        for fs in urllib.unquote(filenames).split(","):
            if fs != '':
                fsets.update(get_files_from_fileset(fs[1:], fileset_cache))
        filenames = fsets

        result = []
        commit_cache = model.CommitCache()

        for m in split_field(metrics):
            for cfg in split_field(configs):
                baseline_data = fetch_metric_for_fileset(m, cfg, filenames,
                                                         parent)
                commit_list = field_list(commits)
                for cm in commit_list:
                    cmdata = commit_cache[cm]
                    col = [] # Each m, cfg, cm combination will be a column in
                             # the table
                    sum_overall = 0
                    count_overall = 0
                    average, results = calculate_average_improvement(
                        m, cfg, filenames, cm, baseline_data)
                    for f, composite in results.iteritems():
                        col.append([f, composite])

                    col.append(['OVERALL: (' + parent_str + ')', average])
                    result.append({'col': m+ "/" + cfg + "/" + cm[:9],
                                   'data': col})
        # return the results
        self.response.out.write(pretty_json(result))

class MainHandler(webapp.RequestHandler):
    def get(self):
        values = {} # This is the dictionary of template values passed to html
        self.response.out.write(template.render("index.html", values))

class ChartHandler(webapp.RequestHandler):
    def get(self):
        self.response.out.write(template.render("graph.html", {}))

def main():
    application = webapp.WSGIApplication([
        ('/', MainHandler),
        ('/import-metrics', ImportMetricHandler),
        ('/import-filesets', ImportFileSetHandler),
        ('/import-codec-metrics', ImportCodecMetricHandler),
        (r'/metric-data/(.*)/(.*)/(.*)/(.*)', CodecMetricHandler),
        (r'/average-improvement/(.*)/(.*)/(.*)/(.*)', AverageImprovementHandler),
        ('/graph', ChartHandler)
    ], debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
