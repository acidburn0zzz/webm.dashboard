#!/usr/bin/env python
##  Copyright (c) 2012 The WebM project authors. All Rights Reserved.
##
##  Use of this source code is governed by a BSD-style license
##  that can be found in the LICENSE file in the root of the source
##  tree. An additional intellectual property rights grant can be found
##  in the file PATENTS.  All contributing project authors may
##  be found in the AUTHORS file in the root of the source tree.
##

import os
import urllib

def field_list(field):
    '''Returns the field as a list of strings.'''
    result = urllib.unquote(field).split(",")
    if len(result[0]) == 0:
        return []
    return result

def filename_list(field):
    def generate(field):
        import model
        if field:
            for fs in urllib.unquote(field).split(","):
                if fs[0] == "~":
                    for f in model.filesets()[fs[1:]].files:
                        yield f
                else:
                    yield fs
    return [x for x in generate(field)]

def development():
    '''This function lets us determine if we are running on a local server or
    the live version.'''
    if os.environ['SERVER_SOFTWARE'].find('Development') == 0:
        return True
    else:
        return False
