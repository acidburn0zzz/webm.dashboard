#!/usr/bin/env python
##  Copyright (c) 2012 The WebM project authors. All Rights Reserved.
##
##  Use of this source code is governed by a BSD-style license
##  that can be found in the LICENSE file in the root of the source
##  tree. An additional intellectual property rights grant can be found
##  in the file PATENTS.  All contributing project authors may
##  be found in the AUTHORS file in the root of the source tree.
##

from google.appengine.api import memcache

def cache_result(key=None):
    """Decorator to cache the result of the function"""
    def wrapper(fn):
        key2 = key # hmm... not sure why key isn't in-scope inside decorator?
        def decorator(*args, **kwargs):
            key = key2
            if not key:
                key = "/".join([fn.func_name, str(args), str(kwargs)])
            result = memcache.get(key)
            if result is None:
                result = fn(*args, **kwargs)
                memcache.set(key, result)
            return result
        return decorator
    return wrapper

class CachedDataView(object):
    """An abstract base class providing a memcache-backed view of a list
       of elements"""
    def __init__(self, keys):
        self._keys = list(keys)
        self._data_valid = False
        self.__data = None
        self._cache = memcache.Client()
        self._cache_rpc = memcache.create_rpc()
        self._cache_prefix = self.__class__.__name__
        self._cache.get_multi_async(self._keys, key_prefix=self._cache_prefix,
                                    rpc=self._cache_rpc)

    def _data(self):
        """Finalize the RPC, if required"""
        if not self._data_valid:
            self.__data = dict(zip(self._keys, [None for key in self._keys]))
            self.__data.update(self._cache_rpc.get_result())
            self._data_valid = True
        return self.__data

    def __iter__(self):
        """Return a key,value iterator for all items in the view, with
           early request and deferred response."""
        data = self._data()

        missing = []
        # Get a list of misses
        for key, value in data.iteritems():
            if value is None:
                missing.append(key)

        # Start the RPC to fill in the missing items
        missing_rpc = self.begin_getitems(missing)

        # Yield the items we do have first
        for key, value in data.iteritems():
            if value is not None:
                yield key, value

        missing_data = {}
        for key, value in self.getitems(self._keys, missing_rpc):
            data[key] = value
            missing_data[key] = value
            yield key, value

        # Add the missing data to the cache
        if missing_data:
            self._cache.set_multi(missing_data, key_prefix=self._cache_prefix)

    def __getitem__(self, key):
        """Get a single item from the cache"""
        data = self._data()
        if data[key] is None:
            value = {key: self.getitem(key, self.begin_getitem(key))}
            data.update(value)
            self._cache.set_multi(value, key_prefix=self._cache_prefix)
        return data[key]

    def begin_getitems(self, keys):
        """Called with a list of items that will be requested, so that the
           RPC(s) can be started early."""
        return dict(zip(keys, map(self.begin_getitem, keys)))

    def getitems(self, keys, rpc):
        """Finalize the outstanding RPCs started in begin_getitems()"""
        for key, deferred in rpc.iteritems():
            yield key, self.getitem(key, deferred)

    def begin_getitem(self, key):
        """Start the request for a single item"""
        return None

    def getitem(self, key, rpc=None):
        """Finalize the request for a single item"""
        return rpc.get_result()

    def __repr__(self):
        """Get a stable representation of the object, suitable for memcache"""
        return "%s(%s)"%(self.__class__.__name__, self._keys)
