# -*- coding: utf-8 -*-

"""
Module entry point: call get_store() to instanciate a KittyStore
implementation.

Copyright (C) 2012 Aurelien Bompard
Author: Aurelien Bompard <abompard@fedoraproject.org>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or (at
your option) any later version.
See http://www.gnu.org/copyleft/gpl.html  for the full text of the
license.
"""

from __future__ import absolute_import, print_function, unicode_literals

__all__ = ("get_store", "create_store", "MessageNotFound",
           "SchemaUpgradeNeeded")

from kittystore.search import SearchEngine
from kittystore.caching import register_events


def _check_settings(settings):
    required_keys = ("KITTYSTORE_URL", "KITTYSTORE_SEARCH_INDEX",
                     "MAILMAN_REST_SERVER", "MAILMAN_API_USER",
                     "MAILMAN_API_PASS")
    for req_key in required_keys:
        try:
            getattr(settings, req_key)
        except AttributeError:
            raise AttributeError("The settings file is missing the \"%s\" key" % req_key)
    if settings.KITTYSTORE_URL.startswith("mongo://"):
        raise NotImplementedError

def _get_search_index(settings):
    search_index_path = settings.KITTYSTORE_SEARCH_INDEX
    if search_index_path is None:
        return None
    return SearchEngine(search_index_path)

def get_store(settings, debug=None, auto_create=False):
    """Factory for a KittyStore subclass"""
    _check_settings(settings)
    if debug is None:
        debug = getattr(settings, "KITTYSTORE_DEBUG", False)

    search_index = _get_search_index(settings)

    if getattr(settings, "KITTYSTORE_USE_STORM", False):
        from kittystore.storm import get_storm_store
        store = get_storm_store(settings, search_index, debug, auto_create)
    else:
        from kittystore.sa import get_sa_store
        store = get_sa_store(settings, search_index, debug, auto_create)

    if search_index is not None and search_index.needs_upgrade():
        if auto_create:
            search_index.upgrade(store)
        else:
            store.close()
            raise SchemaUpgradeNeeded()

    register_events()

    return store


def create_store(settings, debug=None):
    """Factory for a KittyStore subclass"""
    _check_settings(settings)
    if debug is None:
        debug = getattr(settings, "KITTYSTORE_DEBUG", False)

    search_index = _get_search_index(settings)
    if getattr(settings, "KITTYSTORE_USE_STORM", False):
        from kittystore.storm import get_storm_store, create_storm_db
        version = create_storm_db(settings, debug)
        store = get_storm_store(settings, search_index, debug)
    else:
        from kittystore.sa import create_sa_db, get_sa_store
        version = create_sa_db(settings, debug)
        store = get_sa_store(settings, search_index, debug)
    if search_index is not None and search_index.needs_upgrade():
        search_index.upgrade(store)
    return store, version


class SchemaUpgradeNeeded(Exception):
    """Raised when there are pending patches"""


class MessageNotFound(Exception):
    pass
