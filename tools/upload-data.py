#!/usr/bin/env python
##  Copyright (c) 2012 The WebM project authors. All Rights Reserved.
##
##  Use of this source code is governed by a BSD-style license
##  that can be found in the LICENSE file in the root of the source
##  tree. An additional intellectual property rights grant can be found
##  in the file PATENTS.  All contributing project authors may
##  be found in the AUTHORS file in the root of the source tree.
##
import json
import os
from optparse import OptionParser
import sys
import urllib
import urllib2

COMMIT_UPLOAD_URL="/gerrit/import-commits"
FILESET_UPLOAD_URL="/import-filesets"
METRICS_UPLOAD_URL="/import-metrics"
DATA_UPLOAD_URL="/import-codec-metrics"
DASHBOARD_HOST="localhost:8080"

# https://developers.google.com/accounts/docs/OAuth2InstalledApp
CLIENT_ID = '143135962842.apps.googleusercontent.com'
CLIENT_SECRET = 'kEBk6qXuvUEE7j1JM0TsjXTT'
CALLBACK_URI = 'urn:ietf:wg:oauth:2.0:oob'
AUTH_URL='https://accounts.google.com/o/oauth2/auth'
TOKEN_URL='https://accounts.google.com/o/oauth2/token'

def parse_jsonfile(f):
  return json.loads(open(f, "r").read())

def fetch_auth_token():
  while True:
    try:
      # Auth request
      params = {'response_type': 'code',
                'client_id': '143135962842.apps.googleusercontent.com',
                'redirect_uri': CALLBACK_URI,
                'scope': 'https://www.googleapis.com/auth/userinfo.email',
               }
      url = '%s?%s'%(AUTH_URL, urllib.urlencode(params))
      print "Please visit the following URL in your browser:"
      print url
      oauth_verifier = raw_input('What is the Access Code? ')

      # Get authorization token
      params = {'code': oauth_verifier,
                'client_id': CLIENT_ID,
                'client_secret': CLIENT_SECRET,
                'redirect_uri': CALLBACK_URI,
                'grant_type' : 'authorization_code',
                }
      response = urllib2.urlopen(TOKEN_URL, urllib.urlencode(params))
      authorization = json.loads(response.read())
      return authorization
    except urllib2.HTTPError:
      print "Authorization failed. Try again."

def save_auth_token(token, filename):
  fd = os.open(filename, os.O_CREAT | os.O_WRONLY, 0600)
  with os.fdopen(fd, 'w') as outfile:
    record = {'refresh_token': token['refresh_token']}
    outfile.write(json.dumps(record))

def fetch_refresh_token():
  dotfile = os.path.join(os.path.expanduser("~"), '.webm-dashboard')
  try:
    data = parse_jsonfile(dotfile)
  except:
    auth = fetch_auth_token()
    save_auth_token(auth, dotfile)
    data = parse_jsonfile(dotfile)
  return data['refresh_token']

def fetch_access_token():
  # Send refresh request
  params = {'refresh_token': fetch_refresh_token(),
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'grant_type': 'refresh_token',
            }
  response = urllib2.urlopen(TOKEN_URL, urllib.urlencode(params))
  token = json.loads(response.read())
  return token['access_token']

def upload(secure, host, path, filehandle):
  protocol = {True: 'https', False: 'http'}[secure]
  url = '%s://%s%s'%(protocol, host, path)
  form = {'data': filehandle.read()}
  data = urllib.urlencode(form)
  headers = {'Authorization': 'Bearer %s'%fetch_access_token()}
  request = urllib2.Request(url, data, headers)
  response = urllib2.urlopen(request)

def main(argv=None):
  if argv is None:
    argv = sys.argv

  parser = OptionParser(usage="Usage: %prog <options> file ...")
  parser.add_option("", "--commit", help="Upload commit data",
                    action="store_const", const=COMMIT_UPLOAD_URL, dest="url")
  parser.add_option("", "--fileset", help="Upload fileset data",
                    action="store_const", const=FILESET_UPLOAD_URL, dest="url")
  parser.add_option("", "--metric-metadata", help="Upload metric metadata",
                    action="store_const", const=METRICS_UPLOAD_URL, dest="url")
  parser.add_option("", "--data", help="Upload run metrics",
                    action="store_const", const=DATA_UPLOAD_URL, dest="url")
  parser.add_option("-s", "--secure", help="Use https", action="store_true",
                    default=False, dest="secure")
  parser.add_option("-H", "--host", help="Hostname",
                    default=DASHBOARD_HOST, dest="host")
  opts, args = parser.parse_args()

  if not opts.url:
    parser.print_help()
    return 1

  for filename in args:
    if filename == "-":
      upload(opts.secure, opts.host, opts.url, sys.stdin)
    else:
      upload(opts.secure, opts.host, opts.url, open(filename))

if __name__ == "__main__":
  sys.exit(main())
