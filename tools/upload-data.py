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
import urlparse
import oauth2 as oauth
import httplib2

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
REQUEST_TOKEN_URL='%s/_ah/OAuthGetRequestToken'
AUTHZ_TOKEN_URL='%s/_ah/OAuthAuthorizeToken'
ACCESS_TOKEN_URL='%s/_ah/OAuthGetAccessToken'
PROXY_INFO=httplib2.ProxyInfo.from_environment()

def parse_jsonfile(f):
  return json.loads(open(f, "r").read())

def fetch_request_token(consumer, host):
  oauth_client = oauth.Client(consumer, proxy_info=PROXY_INFO)
  resp, content = oauth_client.request(REQUEST_TOKEN_URL%host, "GET")
  if resp['status'] != '200':
    raise Exception("Invalid response %s." % resp['status'])
  return dict(urlparse.parse_qsl(content))

def fetch_authz_token(consumer, host):
  request_token = fetch_request_token(consumer, host)
  params = {'oauth_token': request_token['oauth_token']}
  url = '%s?%s'%(AUTHZ_TOKEN_URL%host, urllib.urlencode(params))
  print "Please visit the following URL in your browser:"
  print url
  oauth_verifier = raw_input('Press enter once verified...')
  return request_token

def fetch_access_token(consumer, host):
  request_token = fetch_authz_token(consumer, host)
  token = oauth.Token(request_token['oauth_token'],
                      request_token['oauth_token_secret'])
  client = oauth.Client(consumer, token, proxy_info=PROXY_INFO)
  resp, content = client.request(ACCESS_TOKEN_URL%host, "POST")
  if resp['status'] != '200':
    raise Exception("Invalid response %s." % resp['status'])
  return dict(urlparse.parse_qsl(content))

def save_access_token(token, filename):
  fd = os.open(filename, os.O_CREAT | os.O_WRONLY, 0600)
  with os.fdopen(fd, 'w') as outfile:
    outfile.write(json.dumps(token))

def load_or_fetch_access_token(consumer, host):
  dotfile = os.path.join(os.path.expanduser("~"), '.webm-dashboard')
  try:
    data = parse_jsonfile(dotfile)
  except:
    data = fetch_access_token(consumer, host)
    save_access_token(data, dotfile)
    data = parse_jsonfile(dotfile)
  return oauth.Token(data['oauth_token'], data['oauth_token_secret'])

def upload(secure, host, path, filehandle):
  protocol = {True: 'https', False: 'http'}[secure]
  url = '%s://%s%s'%(protocol, host, path)
  form = {'data': filehandle.read()}
  data = urllib.urlencode(form)
  consumer = oauth.Consumer(CLIENT_ID, CLIENT_SECRET)
  oauth_host = '%s://%s'%(protocol, host)
  token = load_or_fetch_access_token(consumer, oauth_host)
  client = oauth.Client(consumer, token, proxy_info=PROXY_INFO)
  resp, content = client.request(url, "POST", data)
  if resp['status'] != '200':
    print content
    raise Exception("Invalid response %s." % resp['status'])

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

  # Force https to prod
  secure = opts.secure or 'appspot' in opts.host

  for filename in args:
    if filename == "-":
      upload(opts.secure, opts.host, opts.url, sys.stdin)
    else:
      upload(opts.secure, opts.host, opts.url, open(filename))

if __name__ == "__main__":
  sys.exit(main())
