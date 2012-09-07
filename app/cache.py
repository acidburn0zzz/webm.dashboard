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
import logging

PREFETCH_LIMIT = 100

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

class LazyCachedDataView(object):
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

            # Get a list of misses
            self._missing = []
            for key, value in self.__data.iteritems():
                if value is None:
                    self._missing.append(key)

            logging.info("%s: initial memcache hit %d/%d items"%(
                self.__class__.__name__, len(self._keys) - len(self._missing),
                len(self._keys)))
            self._data_valid = True

        return self.__data

    def _begin_get_missing(self, items=None, limit=None):
        if items:
            missing = filter(lambda x: self._data()[x] == None, items)
            if limit is not None:
                limit = max(limit - len(missing), 0)
        else:
            missing = []

        last_missing = self._missing
        if limit is None:
            missing.extend(self._missing)
            self._missing = []
        elif limit > 0:
            missing.extend(self._missing[:limit])
            self._missing = self._missing[limit:]

        if items:
           for key in items:
               assert (key in missing) or (self._data()[key] is not None)

        if missing:
            logging.info("%s: fetching %d/%d missing items"%(
                         self.__class__.__name__, len(missing),
                         len(last_missing)))
            if len(missing) > len(last_missing):
                logging.info(("%s: some keys are being fetched that weren't "
                              "in _missing: %s")%(
                              self.__class__.__name__, missing))
            #assert len(missing) <= len(last_missing)

            # Start the RPC to fill in the missing items
            return self.begin_getitems(missing)
        return None


    def _get_missing(self, data, missing_rpc):
        missing_data = {}
        if missing_rpc:
            for key, value in self.getitems(self._keys, missing_rpc):
                data[key] = value
                missing_data[key] = value

            self._save(missing_data)
        return missing_data

    def _save(self, missing_data):
        # Add the missing data to the cache
        if missing_data:
            self._cache.set_multi(missing_data, key_prefix=self._cache_prefix)

    def __iter__(self):
        """Return a key,value iterator for all items in the view, with
           early request and deferred response."""
        data = self._data()

        # Start the RPC to fill in the missing items
        missing_rpc = self._begin_get_missing()

        # Yield the items we do have first
        for key, value in data.iteritems():
            if value is not None:
                yield key, value

        for key, value in self._get_missing(data, missing_rpc).iteritems():
            yield key, value

    def __getitem__(self, key):
        """Get a single item from the cache"""
        data = self._data()
        if data[key] is None:
            missing_rpc = self._begin_get_missing([key], PREFETCH_LIMIT)
            missing = self._get_missing(data, missing_rpc)
            assert key in missing.keys()
            assert missing[key] == data[key]
        else:
            missing_rpc = self._begin_get_missing(limit=PREFETCH_LIMIT)
            self._get_missing(data, missing_rpc)
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
        raise NotImplementedError

    def getitem(self, key, rpc=None):
        """Finalize the request for a single item"""
        return rpc.get_result()

    def __repr__(self):
        """Get a stable representation of the object, suitable for memcache"""
        return "%s(%s)"%(self.__class__.__name__, self._keys)

class CachedDataView(LazyCachedDataView):
    def __init__(self, keys):
        super(CachedDataView, self).__init__(keys)

        # Force a fetch of all missing items
        data = self._data()
        missing_rpc = self._begin_get_missing(limit=PREFETCH_LIMIT)
        self._get_missing(data, missing_rpc)

    def begin_getitems(self, keys):
        """Called with a list of items that will be requested, so that the
           RPC(s) can be started early."""
        raise NotImplementedError

    def getitems(self, keys, rpc):
        """Finalize the outstanding RPCs started in begin_getitems()"""
        for entity in rpc.get_result():
            if entity:
                yield entity.key().name(), entity

GLOBAL_CACHE_INVALIDATION_COUNTER = "__CachedDataViewInvalidation"

def GlobalDataView(view):
    class GlobalCachedDataView(object):
        _instance = None

        def __new__(cls, *args, **kwargs):
            if not cls._instance:
                cls._instance = super(GlobalCachedDataView, cls).__new__(
                                    cls, *args, **kwargs)
                cls._cache_class = view
                cls._cache = view(view.all_keys())
                cls._counter = None
                cls._key = (cls.__name__
                            + GLOBAL_CACHE_INVALIDATION_COUNTER)
            return cls._instance

        @classmethod
        def _refresh(cls):
            counter = memcache.get(cls._key)
            if not counter:
                memcache.incr(cls._key, initial_value=0)
                counter = memcache.get(cls._key)
            if not cls._cache or not counter or counter != cls._counter:
                logging.info("%s(%s): refresh"%(
                    cls.__name__, view.__name__))
                cls._counter = counter
                cls._cache = cls._cache_class(cls._cache_class.all_keys())

        @classmethod
        def invalidate(cls):
            logging.info("%s(%s): invalidate"%(
                cls.__name__, view.__name__))
            memcache.incr(cls._key, initial_value=0)

        def __iter__(self):
            self._refresh()
            return self.__class__._cache.__iter__()

        def __getitem__(self, item):
            return self.__class__._cache.__getitem__(item)

    return GlobalCachedDataView
