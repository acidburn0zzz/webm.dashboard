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
from google.appengine.ext.webapp import util as webapp_util
from google.appengine.api import users

from drilldown import drilldown
from cache import cache_result, CachedDataView
import model
import util
import main
import drilldown
import logging

# A global variable to determine how important a test run is (percent improvement)
THRESHOLD_HIGH = 1.0
THRESHOLD_LOW = 0.1


class CommitQueryHandler(webapp.RequestHandler):
    def get(self):
        self.response.out.write(template.render("commit_viewer.html", {}))

@cache_result()
def get_adhoc_improvement(metrics, config, filenames, commit):
    # Mostly copied from main.py with some notable changes
    response = []

    # Find the baseline based on the raw URL variables
    parent = main.find_baseline(",".join(metrics), config,
                                ",".join(filenames), commit)
    result = []

    for m in metrics:
        if model.metrics()[m].distortion:
            improvement = main.rd_improvement
        else:
            improvement = main.mean_improvement

        if parent:
            baseline_data = main.fetch_metric_for_fileset(
                m, config, filenames, parent)
            average, results = main.calculate_improvement(
                m, config, filenames, commit, baseline_data, improvement)
        else:
            results = dict([f, 0.0] for f in filenames)

        for f, composite in results.iteritems():
            response.append({'metric': m, 'config': config, 'baseline': parent,
                             'filename': f, 'value': composite})
    return response

class CommitDisplayHandler(webapp.RequestHandler):
    def get(self, commit, optThreshold):

        # TODO: will the threshold ever be adjustable?
        if not optThreshold:
            threshold = THRESHOLD_HIGH  # Go back to default if none given
        else:
            threshold = float(optThreshold)

        # We start by seeing if its a valid commit
        indexes = model.CodecMetricIndex.all(keys_only = True)
        indexes = indexes.filter('commit =', commit)
        keys = [k.parent() for k in indexes]
        if len(keys) == 0:
            self.error(404)
            return

        commit_data = model.commits()[commit]
        message = commit_data.message.split("\n")
        nonempty_lines = sum(map(bool, message))
        commit = {'commit': commit_data.key().name()[:9],
                 'commitid': commit_data.key().name(),
                 'author': commit_data.author,
                 'subject': message[0],
                 'body': message[1:],
                 'date': commit_data.author_time,
                 'branches': commit_data.branches}
        commitid = commit_data.key().name()

        # We need (metric, config, fileset) tuples
        resps = []
        query = model.CodecMetricIndex.all()
        query = query.filter('commit =', commitid)
        for item in query:
            resps.extend(get_adhoc_improvement(item.metrics, item.config_name,
                                               item.files, commitid))

        # Now that we have our responses, we can format them by seeing if
        # the value crosses our threshold
        formatted_resps = []
        for row in resps:
            if row['metric'] == 'Time(us)' or row['metric'] == 'Bitrate' or row['metric'] == 'target_bitrate':
                continue
            if row['filename'][0] == '~':
                continue

            if not row['baseline']:
                row['class'] = 'unknown'
            elif abs(row['value']) > THRESHOLD_HIGH:
                if row['value'] > 0:
                    row['class'] = 'good major'
                else:
                    row['class'] = 'bad major'

            elif abs(row['value']) > THRESHOLD_LOW:
                if row['value'] > 0:
                    row['class'] = 'good minor'
                else:
                    row['class'] = 'bad minor'

            else: # We are right in the middle
              row['class'] = "unchanged"

            # This is a bit messy, but it works (mixing django and
            # javascript doesn't work like you would hope)
            if row['baseline']:
                row['clickcommand'] = str("javascript: ChartFillerCaller(" + "\'" +
                                      row['metric'].encode('ascii', 'ignore') + "," +
                                      row['config'].encode('ascii', 'ignore') + "," +
                                      row['filename'].encode('ascii', 'ignore') + ',' +
                                      commit['commitid'].encode('ascii', 'ignore') + "," +
                                      row['baseline'].encode('ascii', 'ignore') + "\'"+ ')')
            formatted_resps.append(row)

        # TODO: How do we want to sort this?
        resp_rows = {}
        for resp in formatted_resps:
            key = (resp['metric'], resp['config'])
            row = resp_rows.setdefault(key, [])
            row.append(resp)
        formatted_resps=[]
        for key in sorted(resp_rows.keys()):
            formatted_resps.append({
                'metric': key[0],
                'config': key[1],
                'runs': sorted(resp_rows[key], key=lambda x: x['filename']),
                })

        html = template.render("commit_view.html", {'commit': commit,
                                                    'runs': formatted_resps,
                                                    'threshold': threshold})
        self.response.out.write(html)

def main_func():
    application = webapp.WSGIApplication([
        ('/commit_viewer/', CommitQueryHandler),
        ('/commit_viewer/(.*)/(.*)', CommitDisplayHandler),
    ], debug=True)
    webapp_util.run_wsgi_app(application)

if __name__ == '__main__':
    main_func()
