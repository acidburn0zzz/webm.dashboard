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
from google.appengine.api import urlfetch
from google.appengine.api import memcache

import datetime
from django.utils import simplejson as json
import logging
import StringIO

import model

GERRIT_SERVER_URL="https://gerrit.chromium.org/gerrit"
GERRIT_PROJECT_QUERY="project:webm/libvpx"

class Gerrit(object):
    def __init__(self, url=GERRIT_SERVER_URL):
        self._url = url
        self._sort_key = None
        self._changes = {}
        self._patches = {}
        self._once = False

    def _load(self, data):
        if "id" in data:
            key = data["id"]
            self._changes[key] = data
            for p in data["patchSets"]:
                p["Change-Id"] = key
                self._patches[p["revision"]] = p
            del self._changes[key]["patchSets"]

    def _poll(self):
        # Build query URL
        query_url = self._url + "/query?patch-sets=true&q="
        query=[GERRIT_PROJECT_QUERY]
        if self._sort_key:
            query.append("sortkey_after:" + self._sort_key)
        query_url += "+".join(query)

        # Fetch
        response = urlfetch.fetch(query_url)
        if response.status_code != 200:
            logging.info("Failed to fetch %s (%s)"%(
                query_url, response.status_code))
            return

        again = False
        for line in response.content.split("\n"):
            if not line:
                continue

            logging.debug("gerrit: parse %r"%line)
            data = json.loads(line)
            if not again and "sortKey" in data:
                self._sort_key = data["sortKey"]
                again = True
            self._load(data)

        return again

    def _poll_once(self):
        if not self._once:
            self.poll()

    def __contains__(self, item):
        self._poll_once()
        return item in self._changes or item in self._patches

    def __getitem__(self, item):
        self._poll_once()
        if item in self._changes:
            return self._changes[item]
        if item in self._patches:
            return self._patches[item]
        logging.info("%r not in gerrit"%item)
        return None

    def poll(self):
        self._once = True
        while self._poll():
            pass

# singleton
gerrit = Gerrit()

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

      # See if this patch is known to gerrit
      gerrit_data = {}
      patchset = gerrit[data["id"]]
      if patchset:
          change_id = patchset["Change-Id"]
          change = gerrit[change_id]
          gerrit_data["gerrit_change_id"] = change_id
          gerrit_data["gerrit_change_num"] = int(change["number"])
          gerrit_data["gerrit_url"] = change["url"]
          gerrit_data["gerrit_branch"] = change["branch"]
          gerrit_data["gerrit_patchset_num"] = int(patchset["number"])
          gerrit_data["gerrit_patchset_ref"] = patchset["ref"]

      c = model.Commit(key_name=data["id"],
                       author=data["author"],
                       author_time=author_time,
                       committer=data["committer"],
                       commit_time=commit_time,
                       message=data["message"],
                       parents=data["parents"],
                       **gerrit_data)
      c.put()

    def post(self):
        gerrit.poll()
        data = StringIO.StringIO(self.request.get("data"))
        for line in data:
            self.load(json.loads(line))
        memcache.flush_all()
        model.reset_commit_cache()


def main():
    application = webapp.WSGIApplication([
        ('/gerrit/import-commits', ImportCommitHandler),
    ], debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
