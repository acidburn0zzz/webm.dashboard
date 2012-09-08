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
from google.appengine.ext import db
from google.appengine.api import oauth
from google.appengine.api import users

# Standard libraries
import datetime
import hashlib
from django.utils import simplejson as json
import pickle
import StringIO
import urllib
import logging
import re

# App libraries
from drilldown import drilldown
from cache import cache_result, CachedDataView
import curve_compare
import model
import util
import urllib

GERRIT_LINK_HTML=("<a target='_blank' href=\"https://gerrit.chromium.org/gerrit/"
                  "#q,%s,n,z\">%s</a>")
GERRIT_LINK_PATTERN="(I[a-f0-9]{40})"
OAUTH_SCOPE = 'https://www.googleapis.com/auth/userinfo.email'

# We give metrics their own handler for convenience
class ImportMetricHandler(webapp.RequestHandler):
    def post(self):
        assert util.development() or oauth.is_current_user_admin()
        data = StringIO.StringIO(self.request.get("data"))
        for line in data:
            data = json.loads(line)

            # We first load the fileset into the database
            # For use later, we also add a list of filenames in the fileset
            m = model.Metric(key_name=data["name"],
                             display_name=data["display name"],
                             distortion=data["distortion"],
                             yaxis=data.get("yaxis", None))
            m.put()
        model.metrics().invalidate()

class ImportFileSetHandler(webapp.RequestHandler):
    def post(self):
        assert util.development() or oauth.is_current_user_admin()
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
        model.filesets().invalidate()
        model.files().invalidate()

class ImportCodecMetricHandler(webapp.RequestHandler):
    def put_metric_index(self, parent, metrics, files):
        assert util.development() or oauth.is_current_user_admin()
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

    metric_data = model.metrics()[metric]
    result=[]
    for cm in db.get(keys):
        for run in cm.data[filename]:
            this_run_data = []

            if metric_data.distortion:
                this_run_data.append(run["Bitrate"])
                this_run_data.append(run["target_bitrate"])

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

    metric_data = model.metrics()[metric]
    results_by_file = {}
    for cm in db.get(keys):
        for filename, runs in cm.data.iteritems():
            if filename not in files:
                continue
            result = results_by_file.get(filename, [])
            for run in runs:
                this_run_data = []

                if metric_data.distortion:
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

def fetch_time_series(metric, config, files, commit):
    branch = commit[1:]
    q = model.CodecMetricTimeSeries.all()
    q = q.filter('metric =', metric)
    q = q.filter('config_name =', config)
    q = q.filter('branch =', branch)
    result = {}
    for data in q:
        if data.file_or_set_name in files:
            result[data.file_or_set_name] = zip(
                [(x.year, x.month - 1, x.day, x.hour, x.minute, x.second)
                    for x in data.times],
                data.commits,
                [(x-1.0)*100.0 for x in data.values])
    return result

class CodecMetricHandler(webapp.RequestHandler):
    def get(self, metric, config, filename, commit):
        """Fetches the requested metric data as JSON"""
        if not metric or not config or not filename or not commit:
            self.error(404)
            return

        filename = urllib.unquote(filename)
        commit = urllib.unquote(commit)

        if commit[0] == "~":
            result = {'yaxis': "Percent Improvement",
                      'data': fetch_time_series(metric, config, filename,
                                                commit)[filename],
                     }
        else:
            result = {'yaxis': model.metrics()[metric].yaxis,
                      'data': fetch_codec_metric(metric, config, filename,
                                                 commit),
                      }

        # Return the result
        if result['data']:
            self.response.headers['Content-Type'] = 'application/json'
            self.response.out.write(pretty_json(result))
        else:
            self.error(404)

@cache_result()
def find_baseline(metric, config, filename, commits):
    def find_first_parent(commit, data, candidates):
        while True:
            parents = data[commit].parents
            if not parents:
               # root node
               return None
            commit = parents[0]
            if commit in candidates:
                return commit

    # Removes some errors when no commits are selected
    if len(commits) == 0:
        return None

    candidates = drilldown.query(metric, config, filename, commits)[3]
    commit_data = model.commits()
    commits = util.field_list(commits)
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


def rd_improvement(base_data, data):
    return curve_compare.DataBetter(base_data, data) * 100

def mean_improvement(base_data, data):
    def sum0(vals):
        return sum([x[0] for x in vals])

    base_mean = sum0(base_data) / len(base_data)
    mean = sum0(data) / len(data)
    return (mean / base_mean - 1) * 100

def calculate_improvement(m, cfg, fs, cm, base_data, composite_fn):
    '''Calculates the average improvement given the set up and the parent
    commit, caching the result'''

    data = fetch_metric_for_fileset(m, cfg, fs, cm)
    result = {}
    sum_overall = 0
    count_overall = 0
    for f in fs:
        if f not in base_data or f not in data:
            continue
        composite = composite_fn(base_data[f], data[f])
        sum_overall += composite
        count_overall += 1
        result[f] = composite
    if result:
        return sum_overall / count_overall, result
    return None, result

class AverageImprovementHandler(webapp.RequestHandler):
    def get_adhoc_improvement(self, metrics, configs, filenames, commits):
        """Calculates the requested composite metrics and outputs as JSON"""
        # Find the baseline based on the raw URL variables
        parent = find_baseline(metrics, configs, filenames, commits)
        # We format the end of the table with extra info
        if parent:
            parent_str = parent[:9]
        else:
            parent_str = "None found"

        result = []

        metrics = util.field_list(metrics)
        configs = util.field_list(configs)
        filenames = util.filename_list(filenames)
        commits = util.field_list(commits)

        # Fix for the case that a commit in commits has no parent
        # In this case we choose the oldest commit as the parent, ie the one
        # without a parent.
        if not parent:
            parent = commits[-1]

        metrics_cache = model.metrics()
        for m in metrics:
            if metrics_cache[m].distortion:
                improvement = rd_improvement
            else:
                improvement = mean_improvement

            for cfg in configs:
                baseline_data = fetch_metric_for_fileset(m, cfg, filenames,
                                                         parent)
                for cm in commits:
                    col = [] # Each m, cfg, cm combination will be a column in
                             # the table
                    average, results = calculate_improvement(
                        m, cfg, filenames, cm, baseline_data, improvement)
                    for f, composite in results.iteritems():
                        col.append([f, composite])

                    # Build the column name
                    col_name = []
                    if len(metrics) > 1:
                        col_name.append(m)
                    if len(configs) > 1:
                        col_name.append(cfg)
                    if len(col_name) == 0 or len(commits) > 1:
                        col_name.append(cm[:9])
                    col_name = "/".join(col_name)

                    col.append(['OVERALL: (' + parent_str + ')', average])
                    result.append({'col': col_name,
                                   'data': col})
        # return the results
        result = {'baseline': parent,
                  'data': result,
                  'commits': ','.join(commits)
                  }
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(pretty_json(result))

    def get_time_series(self, metrics, configs, filenames, commits):
        metrics = util.field_list(metrics)
        configs = util.field_list(configs)
        filesets = util.field_list(filenames)
        branches = util.field_list(commits)
        result = []
        for m in metrics:
            for c in configs:
                for f in filesets:
                    for b in branches:
                        # Get all the data for all files in the set
                        files_and_set = util.filename_list(f)
                        files_and_set.append(f)
                        data = fetch_time_series(m, c, files_and_set, b)

                        # Remove unnecessary commit info
                        formatted_data = {}
                        for key in data:
                            data_list = data[key]
                            formatted_data_list = []
                            for e in data_list:
                                formatted_data_list.append([e[0], e[2]])
                            formatted_data[key] = formatted_data_list
                        data = formatted_data

                        # Build the column name
                        col_name = []
                        if len(metrics) > 1:
                            col_name.append(m)
                        if len(configs) > 1:
                            col_name.append(c)
                        if len(filesets) > 1:
                            col_name.append(f)
                        if len(col_name) == 0 or len(branches) > 1:
                            col_name.append(b[1:])
                        col_name = "/".join(col_name)

                        # Build the rows for this column
                        col = []
                        for filename, filedata in data.iteritems():
                            improvement = filedata[-1][1]
                            col.append([filename, improvement])

                        result.append({'col': col_name,
                                       'data': col})

        # return the results
        result = {'data': result,
                  'commits': ','.join(branches)
                  }
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(pretty_json(result))

    def get(self, metrics, configs, filenames, commits):
        if urllib.unquote(commits)[0] == "~":
            self.get_time_series(metrics, configs, filenames, commits)
        else:
            self.get_adhoc_improvement(metrics, configs, filenames, commits)


class MainHandler(webapp.RequestHandler):
    def get(self):
        devel = util.development()

        values = {
            "user": users.get_current_user(),
            "login_url": users.create_login_url("/"),
            "logout_url": users.create_logout_url("/")
        }
        if devel:
            values["development"] = True

        self.response.out.write(template.render("home.html", values))


class ExploreHandler(webapp.RequestHandler):
    def get(self):
        devel = util.development()

        values = {
            "user": users.get_current_user(),
            "login_url": users.create_login_url("/"),
            "logout_url": users.create_logout_url("/")
        }
        if devel:
            values["development"] = True

        self.response.out.write(template.render("index.html", values))


class SharedMainHandler(webapp.RequestHandler):
    '''This Handler provides a way of linking to specific dashboard views for
    sharing with others.'''
    def get(self, metrics, configs, filesets, commits, filenames, opentrees):
        # Note that we also must keep track of which trees are open
        devel = util.development()

        values = {
            "metrics": urllib.unquote(metrics),
            "configs": urllib.unquote(configs),
            "filesets": urllib.unquote(filesets),
            "commits": urllib.unquote(commits),
            "filenames": urllib.unquote(filenames),
            "opentrees": urllib.unquote(opentrees),
            "user": users.get_current_user(),
            "login_url": users.create_login_url("/"),
            "logout_url": users.create_logout_url("/")
        }
        if devel:
            values["development"] = True

        self.response.out.write(template.render("index.html", values))

class ChartHandler(webapp.RequestHandler):
    def get(self):
        self.response.out.write(template.render("graph.html", {}))


@cache_result()
def build_history(commit, visited=set()):
    to_visit = [commit]
    history = []
    commit_cache = model.commits()
    while(to_visit):
        commit = to_visit.pop(0)
        if commit not in visited:
            visited.add(commit)
            history.insert(0, commit)
            commit = commit_cache[commit]
            to_visit.extend(commit.parents)
    return history


@cache_result()
def initial_visited(c1):
    visited=set()
    commit_cache = model.commits()
    while c1:
        c1 = commit_cache[c1]
        visited.update(c1.parents)
        if c1.parents:
            c1 = c1.parents[0]
        else:
            break
    return visited


class CommitInfoHandler(webapp.RequestHandler):
    '''This hander is used to get all the information regarding a set of
    commits and their baseline commit.'''
    def get(self, commits, baseline):
        def gerrit_link(m):
            return GERRIT_LINK_HTML%(m.group(0), m.group(0))

        if baseline == '':
            # we will handle this case specially
            baseline = False

        commits = util.field_list(commits)

        # Look up the commit data for these commits
        selected_commits = {}
        commit_cache = model.commits()
        for commit in commits:
            if commit not in selected_commits:
                selected_commits[commit] = commit_cache[commit]

        # Sort in topological order
        commits = sorted(selected_commits.keys(),
                         key=lambda x: selected_commits[x].depth, reverse=True)

        visited = initial_visited(commits[-1])
        history = build_history(commits[0], visited)
        history.reverse()

        formatted = []
        for commit in history:
            commit_data = commit_cache[commit]
            message = commit_data.message.split("\n")
            nonempty_lines = sum(map(bool, message))
            data = {'commit': commit_data.key().name()[:9],
                    'author': commit_data.author,
                    'subject': message[0],
                    'body': message[1:],
                    'date': commit_data.author_time}
            formatted.append(data)

        # We also get the baseline
        if baseline:
            commit_data = commit_cache[baseline]
            message = commit_data.message.split("\n")
            nonempty_lines = sum(map(bool, message))
            baseline = {'commit': commit_data.key().name()[:9],
                        'author': commit_data.author,
                        'subject': message[0],
                        'body': message[1:],
                        'date': commit_data.author_time}

        html = template.render("commitinfo.html", {"commits": formatted, 'baseline':baseline})
        html = re.sub(GERRIT_LINK_PATTERN, gerrit_link, html)
        self.response.out.write(html)

@cache_result()
def fetch_config_info(metric, config, filename, commit):
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

    metric_data = model.metrics()[metric]
    result=[]
    for cm in db.get(keys): # cm = codec metric

        # we get the runtime and config flags
        config_flags = cm.config_flags
        runtime_flags = cm.runtime_flags
        commit = cm.commit

        result.append((commit, config_flags, runtime_flags))

    # Sanity checks - we only want one runtime configuration
    assert len(result) == 1

    # We go ahead and return the tuple
    result = result[0]
    return result

class ConfigInfoHandler(webapp.RequestHandler):
    '''This hander is used to get all the information regarding the config
    required to reproduce a data point'''
    def get(self, metric, config, filename, commit, bitrate):

        config_info = fetch_config_info(metric, config, filename, commit)
        commit, config_flags, runtime_flags = config_info

        if bitrate != '':
            bitrate = float(bitrate)

            # Now we replace the string ${target_bitrate} in runtime_flags
            i = runtime_flags.find('${target_bitrate}')
            runtime_flags = runtime_flags[:i] + str(bitrate)

        # We see if this commit is in gerrit
        commit_data = model.commits()[commit]
        if commit_data.gerrit_url is not None:
            commit_url = commit_data.gerrit_url
            commit_ref = commit_data.gerrit_patchset_ref
            commit_in_gerrit = True
            commit = {'commitid': commit,
                      'commit_in_gerrit': True,
                      'commit_url': commit_data.gerrit_url,
                      'commit_ref': commit_data.gerrit_patchset_ref}
        else:
            commit = {'commitid': commit,
                      'commit_in_gerrit': False}

        response = {'commit': commit,
                    'config_flags': config_flags,
                    'runtime_flags': runtime_flags}

        html = template.render("configinfo.html", response)
        self.response.out.write(html)

class HistoryHandler(webapp.RequestHandler):
    def get(self, commits):
        def gerrit_link(m):
            return GERRIT_LINK_HTML%(m.group(0), m.group(0))

        def commit_group(commits, rollup):
            return {'commits': commits, 'count': len(commits),
                    'rollup': rollup, 'id': commits[0]['commit']}

        commits = util.field_list(commits)
        # Don't print history for the whole branch
        for commit in commits:
            if commit[0] == '~':
                return

        # Find the oldest commit
        visited = set(commits[:1])
        for commit in commits:
            if commit in visited:
                visited = initial_visited(commit)

        history = [build_history(c, set(visited)) for c in commits]
        #self.response.out.write("\n".join(map(str, history)))

        history = sorted(history, key=lambda x:len(x))
        collapsed_history = history[0]
        collapsed_history_set = set(collapsed_history)
        for h in history[1:]:
            for c in h:
                if c not in collapsed_history_set:
                    collapsed_history_set.add(c)
                    collapsed_history.append(c)

        formatted = []
        rollup = []
        commit_cache = model.commits()
        for commit in collapsed_history:
            commit_data = commit_cache[commit]
            message = commit_data.message.split("\n")
            nonempty_lines = sum(map(bool, message))
            data = {'commit': commit_data.key().name()[:9],
                    'author': commit_data.author,
                    'subject': message[0],
                    'body': message[1:],
                    'selected': False,
                    'expandable': nonempty_lines > 1}
            if commit in commits:
                if rollup:
                    formatted.append(commit_group(rollup, rollup=True))
                    rollup = []
                data['selected'] = True
                formatted.append(commit_group([data], rollup=False))
            else:
                rollup.append(data)

        html = template.render("history.html", {"commit_groups": formatted})
        html = re.sub(GERRIT_LINK_PATTERN, gerrit_link, html)
        self.response.out.write(html)

def main():
    application = webapp.WSGIApplication([
        ('/', MainHandler),
        ('/explore', ExploreHandler),
        ('/import-metrics', ImportMetricHandler),
        ('/import-filesets', ImportFileSetHandler),
        ('/import-codec-metrics', ImportCodecMetricHandler),
        (r'/history/(.*)', HistoryHandler),
        (r'/commit-info/(.*)/(.*)', CommitInfoHandler),
        (r'/config-info/(.*)/(.*)/(.*)/(.*)/(.*)', ConfigInfoHandler),
        (r'/metric-data/(.*)/(.*)/(.*)/(.*)', CodecMetricHandler),
        (r'/average-improvement/(.*)/(.*)/(.*)/(.*)', AverageImprovementHandler),
        ('/explore/(.*)/(.*)/(.*)/(.*)/(.*)/(.*)', SharedMainHandler),
        ('/graph', ChartHandler)
    ], debug=True)
    webapp_util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
