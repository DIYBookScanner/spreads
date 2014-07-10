# -*- coding: utf-8 -*-

# Copyright (C) 2014 Johannes Baiter <johannes.baiter@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

""" Metadata class and utility function
"""

from __future__ import division, unicode_literals

from collections import MutableMapping

import isbnlib
from isbnlib import _goom as googlebooks
from spreads.vendor.bagit import BagInfo


def _format_isbnlib(isbnrecord):
    meta = {}
    for k, v in isbnrecord.items():
        # Ignore empty fields
        if not v:
            continue
        if k == 'Authors':
            meta['creator'] = v
        elif k == 'ISBN-13':
            meta['identifier'] = ["ISBN:{0}".format(v)]
        elif k == 'Year':
            meta['date'] = v
        elif k == 'Publisher':
            meta['publisher'] = [v]
        elif k == 'Language':
            meta['language'] = [v]
        else:
            meta[k.lower()] = v
    return meta


def get_isbn_suggestions(query):
    if isinstance(query, unicode):
        query = query.encode('utf-8')
    results = googlebooks.query(query)
    out_list = []
    for data in results:
        out_list.append(_format_isbnlib(data))
    return out_list


def get_isbn_metadata(isbn):
    try:
        rv = isbnlib.meta(isbn)
        if rv:
            return _format_isbnlib(rv)
    except isbnlib.NotValidISBNError:
        return None


class SchemaField(object):
    def __init__(self, key, description=None, multivalued=False):
        self.key = key
        self.multivalued = multivalued
        if not description:
            description = key.capitalize() + ("(s)" if multivalued else "")
        self.description = description

    def to_dict(self):
        return {
            'key': self.key,
            'description': self.description,
            'multivalued': self.multivalued,
        }

    def __repr__(self):
        return ("SchemaField(key={0}, description={1}, multivalued={2})"
                .format(self.key, self.description, self.multivalued))


class Metadata(MutableMapping):
    FILENAME = 'dcmeta.txt'
    SCHEMA = [
        SchemaField('title'),
        SchemaField('creator', multivalued=True),
        SchemaField('date'),
        SchemaField('publisher', multivalued=True),
        SchemaField('language', multivalued=True),
        SchemaField('extent', description="Extent/Number of pages"),
        SchemaField('identifier', multivalued=True),
    ]

    @classmethod
    def _schemafield_for_key(cls, key):
        try:
            return next(f for f in cls.SCHEMA if f.key == key)
        except StopIteration:
            raise KeyError("Could not find field '{0}' in schema".format(key))

    def __init__(self, base_path):
        self.filepath = base_path/self.FILENAME
        self._backingstore = BagInfo(unicode(self.filepath))

    def __getitem__(self, key):
        val = self._backingstore[key]
        schemafield = self._schemafield_for_key(key)
        if schemafield.multivalued and not type(val) in (tuple, list):
            val = [val]
        return val

    def __setitem__(self, key, value):
        self._schemafield_for_key(key)
        self._backingstore[key] = value

    def __delitem__(self, key):
        del self._backingstore[key]

    def __iter__(self):
        return iter(self._backingstore)

    def __len__(self):
        return len(self._backingstore)
