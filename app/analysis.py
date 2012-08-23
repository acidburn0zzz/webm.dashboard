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

import hashlib
from django.utils import simplejson as json

from curve_compare import DataBetter
from drilldown import drilldown
from mapreduce import base_handler
from mapreduce import mapreduce_pipeline
from mapreduce import operation as op
import model

from google.appengine.ext import webapp
from google.appengine.ext.webapp import util

def data_map(entry):
    metrics = model.MetricCache(
        [k.name() for k in model.Metric.all(keys_only=True)])

    data = entry.data
    for filename, runs in data.iteritems():
        for run in runs:
            for metric, params in metrics:
                if not params.display_name:
                    continue
                if metric in run:
                    if params.distortion:
                        yield (metric, filename, [run["Bitrate"], run[metric]])
                    else:
                        yield (metric, filename, [run[metric]])


def percent_improvement_map(entry):
    config = entry.config_name
    commit = entry.commit
    depth = model.commits()[commit].depth
    branches = ["master"]#model.commits()[commit].branches
    for metric, filename, values in data_map(entry):
        filesets = model.files()[filename].file_sets

        for branch in branches:
            k = (metric, config, filename, branch)
            v = (depth, commit, filename, values)
            yield (json.dumps(k), json.dumps(v))
            for fileset in filesets:
                k = (metric, config, "~"+fileset, branch)
                v = (depth, commit, filename, values)
                yield (json.dumps(k), json.dumps(v))


def percent_improvement_reduce(key, values):
    metrics = model.MetricCache(
        [k.name() for k in model.Metric.all(keys_only=True)])

    # deserialize and sort values
    (metric, config, fileset, branch) = json.loads(key)
    values = sorted(map(json.loads, values), key=lambda x: x[0])

    # unpack values to per commit/file lists
    commit_order = []
    by_commit = {}
    for v in values:
        (unused_depth, commit, filename, metric_data) = v
        if not commit_order or commit_order[-1] != commit:
            commit_order.append(commit)
        runs = by_commit.setdefault(commit, {}).setdefault(filename, [])
        runs.append(metric_data)

    # calculate improvement
    last_data = None
    abs_imp = 1.0
    result_t = []
    result_v = []
    for commit in commit_order:
        this_data = by_commit[commit]
        if last_data:
            last_files = set(last_data.keys())
            this_files = set(this_data.keys())
            imp = []

            for f in last_files.intersection(this_files):
                if metrics[metric].distortion:
                    data1 = sorted(last_data[f], key=lambda x: x[0])
                    data2 = sorted(this_data[f], key=lambda x: x[0])
                    imp.append(DataBetter(data1, data2))
                else:
                    data1 = [x[0] for x in last_data[f]]
                    data2 = [x[0] for x in this_data[f]]
                    data1 = sum(data1) / len(data1)
                    data2 = sum(data2) / len(data2)
                    imp.append(data2 / data1 - 1.0)

            if not imp:
                # Discontinuity
                abs_imp = 1.0
            else:
                avg_imp = sum(imp) / len(imp) + 1.0
                abs_imp *= avg_imp
        last_data = this_data
        result_t.append(model.commits()[commit].commit_time)
        result_v.append(abs_imp)

    h = hashlib.sha1()
    map(h.update, [metric, config, fileset, branch])
    ts = model.CodecMetricTimeSeries(key_name=h.hexdigest(),
                                     metric=metric,
                                     config_name=config,
                                     file_or_set_name=fileset,
                                     branch=branch,
                                     commits=commit_order,
                                     times=result_t,
                                     values=result_v)

    yield op.db.Put(ts)

    # Update the drilldown table
    branch = "~"+branch
    drilldown.insert(set([metric]), set([config]), set([fileset]),
                     set([branch]))
    drilldown.save()


class ImprovementAnalysisPipeline(base_handler.PipelineBase):
    def run(self):
        output = yield mapreduce_pipeline.MapreducePipeline(
            "percent_improvement",
            "analysis.percent_improvement_map",
            "analysis.percent_improvement_reduce",
            "mapreduce.input_readers.DatastoreInputReader",
            "mapreduce.output_writers.BlobstoreOutputWriter",
            mapper_params={
                "entity_kind": "model.CodecMetric",
            },
            reducer_params={
                "mime_type": "text/plain",
            },
            shards=16)


class StartHandler(webapp.RequestHandler):
  def get(self):
    pipeline = ImprovementAnalysisPipeline()
    pipeline.start()
    self.redirect(pipeline.base_path + "/status?root=" + pipeline.pipeline_id)

APP = webapp.WSGIApplication(
    [
        ("/analysis/start", StartHandler),
    ],
    debug=True)


def main():
  util.run_wsgi_app(APP)


if __name__ == "__main__":
  main()
