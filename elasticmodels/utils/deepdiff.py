# utils/deepdiff.py
# author: andrew young
# email: ayoung@thewulf.org
from __future__ import print_function

import difflib
import datetime
from sys import version

py3 = version[0] == '3'

if py3:
    from builtins import int
    basestring = str
    numbers = (int, float, complex, datetime.datetime)
    from itertools import zip_longest
else:
    numbers = (int, float, long, complex, datetime.datetime)
    from itertools import izip_longest as zip_longest

from collections import Iterable


class ListItemRemovedOrAdded(object):
    pass


class DeepDiff(dict):
    def __init__(self, t1, t2, ignore_order=False):

        self.ignore_order = ignore_order

        self.update({
            "type_changes": [],
            "dic_item_added": [],
            "dic_item_removed": [],
            "values_changed": [],
            "unprocessed": [],
            "iterable_item_added": [],
            "iterable_item_removed": [],
            "attribute_added": [],
            "attribute_removed": [],
            "set_item_removed": [],
            "set_item_added": []
        })

        self.__diff(t1, t2, parents_ids=frozenset({id(t1)}))

        if not py3:
            self.items = self.iteritems

        empty_keys = [k for k, v in self.items() if not v]
        for k in empty_keys:
            del self[k]

    @staticmethod
    def __gettype(obj):
        ''' python 3 returns <class 'something'> instead of <type 'something'>.
        For backward compatibility, we replace class with type.
        '''
        return str(type(obj)).replace('class', 'type')

    def __diff_obj(self, t1, t2, parent, parents_ids=frozenset({})):
        ''' difference of 2 objects
        '''
        try:
            t1 = t1.__dict__
            t2 = t2.__dict__
        except AttributeError:
            try:
                t1 = {i: getattr(t1, i) for i in t1.__slots__}
                t2 = {i: getattr(t2, i) for i in t2.__slots__}
            except AttributeError:
                self['unprocessed'].append("%s: %s and %s" % (parent, t1, t2))
                return

        self.__diff_dict(t1, t2, parent, parents_ids, print_as_attribute=True)

    def __diff_dict(self, t1, t2, parent, parents_ids=frozenset({}),
            print_as_attribute=False):
        ''' difference of 2 dictionaries
        '''
        if print_as_attribute:
            item_added_key = "attribute_added"
            item_removed_key = "attribute_removed"
            parent_text = "%s.%s"
        else:
            item_added_key = "dic_item_added"
            item_removed_key = "dic_item_removed"
            parent_text = "%s[%s]"

        t1_keys, t2_keys = [
            set(d.keys()) for d in (t1, t2)
        ]

        t_keys_intersect = t2_keys.intersection(t1_keys)

        t_keys_added = t2_keys - t_keys_intersect
        t_keys_removed = t1_keys - t_keys_intersect

        if t_keys_added:
            if print_as_attribute:
                self[item_added_key].append("%s.%s" % (parent, ','.join(t_keys_added)))
            else:
                self[item_added_key].append("%s%s" % (parent, list(t_keys_added)))

        if t_keys_removed:
            if print_as_attribute:
                self[item_removed_key].append("%s%s" %
                    (parent, ','.join(t_keys_removed)))
            else:
                self[item_removed_key].append("%s%s" % (parent, list(t_keys_removed)))

        self.__diff_common_children(t1, t2, t_keys_intersect, print_as_attribute,
                parents_ids, parent, parent_text)

    def __diff_common_children(self, t1, t2, t_keys_intersect, print_as_attribute,
            parents_ids, parent, parent_text):
        ''' difference between common attributes of objects or values of common keys of
        dictionaries
        '''
        for item_key in t_keys_intersect:
            if not print_as_attribute and isinstance(item_key, (basestring, bytes)):
                item_key_str = "'%s'" % item_key
            else:
                item_key_str = item_key

            t1_child = t1[item_key]
            t2_child = t2[item_key]

            item_id = id(t1_child)

            if parents_ids and item_id in parents_ids:
                continue

            parents_added = set(parents_ids)
            parents_added.add(item_id)
            parents_added = frozenset(parents_added)

            self.__diff(t1_child, t2_child, parent=parent_text % (parent, item_key_str),
                parents_ids=parents_added)

    def __diff_set(self, t1, t2, parent="root"):
        ''' difference of sets
        '''
        items_added = list(t2 - t1)
        items_removed = list(t1 - t2)

        if items_removed:
            self["set_item_removed"].append("%s: %s" % (parent, items_removed))

        if items_added:
            self["set_item_added"].append("%s: %s" % (parent, items_added))

    def __diff_iterable(self, t1, t2, parent="root", parents_ids=frozenset({})):
        ''' difference of iterables except dictionaries, sets and strings.
        '''
        items_removed = []
        items_added = []

        for i, (x, y) in enumerate(zip_longest(t1, t2,
            fillvalue=ListItemRemovedOrAdded)):

            if y is ListItemRemovedOrAdded:
                items_removed.append(x)
            elif x is ListItemRemovedOrAdded:
                items_added.append(y)
            else:
                self.__diff(x, y, "%s[%s]" % (parent, i), parents_ids)

        if items_removed:
            self["iterable_item_removed"].append("%s: %s" % (parent, items_removed))

        if items_added:
            self["iterable_item_added"].append("%s: %s" % (parent, items_added))

    def __diff_str(self, t1, t2, parent):
        ''' compares strings
        '''
        if '\n' in t1 or '\n' in t2:
            diff = difflib.unified_diff(t1.splitlines(), t2.splitlines(), lineterm='')
            diff = list(diff)
            if diff:
                diff = '\n'.join(diff)
                self["values_changed"].append("%s:\n%s" % (parent, diff))
        elif t1 != t2:
            self["values_changed"].append("%s: '%s' ===> '%s'" % (parent, t1, t2))

    def __diff_tuple(self, t1, t2, parent, parents_ids):
        # Checking to see if it has _fields. Which probably means it is a named tuple.
        try:
            t1._fields
        # It must be a normal tuple
        except:
            self.__diff_iterable(t1, t2, parent, parents_ids)
        # We assume it is a namedtuple then
        else:
            self.__diff_obj(t1, t2, parent, parents_ids)

    def __diff(self, t1, t2, parent="root", parents_ids=frozenset({})):
        ''' The main diff method
        '''
        if t1 is t2:
            return

        if type(t1) != type(t2):
            self["type_changes"].append("%s: %s=%s ===> %s=%s" %
                (parent, t1, self.__gettype(t1), t2, self.__gettype(t2)))

        elif isinstance(t1, (basestring, bytes)):
            self.__diff_str(t1, t2, parent)

        elif isinstance(t1, numbers):
            if t1 != t2:
                self["values_changed"].append("%s: %s ===> %s" % (parent, t1, t2))

        elif isinstance(t1, dict):
            self.__diff_dict(t1, t2, parent, parents_ids)

        elif isinstance(t1, tuple):
            self.__diff_tuple(t1, t2, parent, parents_ids)

        elif isinstance(t1, (set, frozenset)):
            self.__diff_set(t1, t2, parent=parent)

        elif isinstance(t1, Iterable):
            if self.ignore_order:
                try:
                    t1 = set(t1)
                    t2 = set(t2)
                # When we can't make a set since the iterable has unhashable items
                except TypeError:
                    self.__diff_iterable(t1, t2, parent, parents_ids)
                else:
                    self.__diff_set(t1, t2, parent=parent)
            else:
                self.__diff_iterable(t1, t2, parent, parents_ids)

        else:
            self.__diff_obj(t1, t2, parent, parents_ids)

        return

    @property
    def changes(self):
        ''' This is for backward compatibility with previous versions of DeepDiff.
        You don't need this anymore since you can access the result dictionary of
        changes directly from DeepDiff now:

        DeepDiff(t1,t2) == DeepDiff(t1, t2).changes
        '''
        return self

