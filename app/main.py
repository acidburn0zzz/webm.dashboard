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

import datetime
import hashlib
import json
import pickle
import StringIO

from drilldown import drilldown

class Commit(db.Model):
    author = db.StringProperty()
    author_time = db.DateTimeProperty()
    committer = db.StringProperty()
    commit_time = db.DateTimeProperty()
    message = db.TextProperty()


class ImportCommitHandler(webapp.RequestHandler):
    def convert_time(self, time, zone):
        class GitTZInfo(datetime.tzinfo):
            def __init__(self, utcoffset):
                self.offset = utcoffset

            def dst(self, dt):
                return datetime.timedelta(0)

            def utcoffset(self, dt):
                return datetime.timedelta(seconds=self.offset)
        return datetime.datetime.fromtimestamp(time, GitTZInfo(zone))

    def load(self, data):
      author_time = self.convert_time(data["author_time"],
                                      data["author_timezone"])
      commit_time = self.convert_time(data["commit_time"],
                                      data["commit_timezone"])
      c = Commit(key_name=data["id"],
                 author=data["author"],
                 author_time=author_time,
                 committer=data["committer"],
                 commit_time=commit_time,
                 message=data["message"])
      c.put()

    def post(self):
        data = StringIO.StringIO(self.request.get("data"))
        for line in data:
            self.load(json.loads(line))


class DictProperty(db.Property):
  data_type = dict

  def get_value_for_datastore(self, model_instance):
    value = super(DictProperty, self).get_value_for_datastore(model_instance)
    return db.Blob(pickle.dumps(value))

  def make_value_from_datastore(self, value):
    if value is None:
      return dict()
    return pickle.loads(value)

  def default_value(self):
    if self.default is None:
      return dict()
    else:
      return super(DictProperty, self).default_value().copy()

  def validate(self, value):
    if not isinstance(value, dict):
      raise db.BadValueError('Property %s needs to be convertible '
                             'to a dict instance (%s) of class dict' % (self.name, value))
    return super(DictProperty, self).validate(value)

  def empty(self, value):
    return value is None


class CodecMetric(db.Model):
    commit = db.StringProperty()
    config_flags = db.StringProperty()
    runtime_flags = db.StringProperty()
    config_name = db.StringProperty()
    data = DictProperty()


class CodecMetricIndex(db.Model):
    # parent = CodecMetric
    commit = db.StringProperty()
    config_name = db.StringProperty()
    files = db.StringListProperty()
    metrics = db.StringListProperty()


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
            CodecMetricIndex(key_name=h.hexdigest(),
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
            m = CodecMetric(key_name=key,
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

def pretty_json(x):
    return json.dumps(x, indent=2, sort_keys=True)

class CodecMetricHandler(webapp.RequestHandler):
    def get(self, metric, config, filename, commit):
        """Fetches the requested metric data as JSON"""

        indexes = CodecMetricIndex.all(keys_only = True)
        indexes = indexes.filter('metrics =', metric)
        indexes = indexes.filter('config_name =', config)
        indexes = indexes.filter('files =', filename)
        indexes = indexes.filter('commit =', commit)
        keys = [k.parent() for k in indexes]

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
        #
        # TODO(jkoleszar): do we always want to sort? or do it on the client?
        result = sorted(result, key=lambda x:x[0])

        # Return the result
        if result:
            self.response.headers['Content-Type'] = 'application/json'
            self.response.out.write(pretty_json(result))
        else:
            self.error(404)

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
        ('/import-commits', ImportCommitHandler),
        ('/import-codec-metrics', ImportCodecMetricHandler),
        (r'/metric-data/(.*)/(.*)/(.*)/(.*)', CodecMetricHandler),
        ('/graph', ChartHandler)
    ], debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
