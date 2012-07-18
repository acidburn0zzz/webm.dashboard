#!/usr/bin/env python
##  Copyright (c) 2012 The WebM project authors. All Rights Reserved.
##
##  Use of this source code is governed by a BSD-style license
##  that can be found in the LICENSE file in the root of the source
##  tree. An additional intellectual property rights grant can be found
##  in the file PATENTS.  All contributing project authors may
##  be found in the AUTHORS file in the root of the source tree.
##

## This file contains our necessary database definitions

from google.appengine.ext import db

import pickle

class File(db.Model):
    # key_name is the filename
    display_name = db.StringProperty()
    file_sets = db.StringListProperty()

class FileSet(db.Model):
    # key_name is the file set name
    display_name = db.StringProperty()

class Commit(db.Model):
    author = db.StringProperty()
    author_time = db.DateTimeProperty()
    committer = db.StringProperty()
    commit_time = db.DateTimeProperty()
    message = db.TextProperty()
    branches = db.StringListProperty()


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
