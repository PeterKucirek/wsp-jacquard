from __future__ import division, absolute_import, print_function, unicode_literals

import json
import os
from collections import OrderedDict
import re

from six import iteritems, StringIO

from .api import (JacquardParseError, JacquardSpecificationError, JacquardTypeError, JacquardValue, is_identifier, 
                  open_file)


class Jacquard(object):
    """Represents a model configuration, usually stored in JSON format with the order of items preserved and comments
    (beginning with '//') stripped out. Keys in the JSON file which conform to Python variable names (e.g.
    "my_attribute" but not "My Attribute") become *attributes* of the Jacquard object (e.g. instance.my_attribute).

    Value attributes (e.g. ``value`` in ``{"key": value}``) are stored as JacquardValue objects to facilitate type
    conversion and checking. So to access the raw value, write "instance.my_attribute.value" or, to convert it to a
    specified type, write ``instance.my_attribute.as_bool()``.

    This all facilitates "pretty" error message generation, to provide the end-user with as much information about the
    source of an error as these are common when specifying a model.

    A `Jacquard` can be constructed from three static methods:

    - ``from_file()`` to construct from a JSON file on-disk
    - ``from_string()`` to construct from a JSON-formatted string in-memory
    - ``from_dict()`` to construct from a dictionary in-memory

    Note:
        - Jacquard implements ``__contains__`` for testing if a name is 'in' the set of attributes.
    """

    def __init__(self, jqd_dict, name=None, parent=None, file_=None):
        self._contents = {}
        self._name = name
        self._parent = parent
        self._file = file_

        for key, original_value in iteritems(jqd_dict):
            if isinstance(original_value, dict):
                value = Jacquard(original_value, name=key, parent=self, file_=file_)
            elif isinstance(original_value, (list, set)):
                value_list = []
                for (i, item) in enumerate(original_value):
                    if isinstance(item, dict):
                        value_list.append(Jacquard(item, name=key + "[%s]" % i, parent=self, file_=file_))
                    else:
                        value_list.append(JacquardValue(item, key + "[%s]" % i, owner=self))
                value = JacquardValue(value_list, key, owner=self)
            elif original_value is None:
                value = None
            else:
                value = JacquardValue(original_value, key, owner=self)

            if is_identifier(key):
                try:
                    setattr(self, key, value)
                except AttributeError:
                    print("WARNING: Jacquard key '%s' conflicts with reserved properties" % key)
            self._contents[key] = value

    @property
    def name(self):
        """Short name of each part of the jacquard. For non-root Jacquards, this will be the name of the attribute used
        to access this Jacquard from the parent."""
        return self._name

    @property
    def parent(self):
        """Pointer to the parent of non-root Jacquard."""
        return self._parent

    @property
    def namespace(self):
        """The dot-separated namespace of this part of the full Jacquard."""
        name = self._name if self._name is not None else '<unnamed>'
        if self._parent is None:
            return name
        return '.'.join([self._parent.namespace, name])

    def __str__(self):
        if self._parent is None:
            return "Jacquard @%s" % self._file

        return "Jacquard(%s) @%s" % (self.namespace, self._file)

    def __getattr__(self, item):
        raise JacquardSpecificationError("Item '%s' is missing from jacquard <%s>" % (item, self.namespace))

    def __contains__(self, item): return item in self._contents

    def __getitem__(self, item):
        if item not in self:
            raise JacquardSpecificationError("Item '%s' is missing from jacquard <%s>" % (item, self.namespace))
        return self._contents[item]

    def as_dict(self, value_type=None):
        """Converts this entry to a primitive dictionary, using specified types for the keys and values.

        Args:
            value_type (type, optional): Defaults to ``None``. The type to which the values will be cast, or None to
                ignore casting.

        Returns:
            dict: A dictionary containing the entry's keys and values
        """

        if value_type is None:
            return self._contents.copy()

        def any_type(value): return value

        if value_type is None: value_type = any_type

        retval = OrderedDict()
        for key, val in iteritems(self._contents):
            try:
                val = val.as_type(value_type)
            except ValueError:
                message = "Value <{}.{}> = '{}' could not be converted to {}".format(
                    self.namespace, key, val, value_type
                )
                raise JacquardTypeError(message)
            retval[key] = val
        return retval

    def serialize(self):
        """Recursively converts the Jacquard back to primitive dictionaries"""
        child_dict = OrderedDict()
        for attr, item in iteritems(self._contents):
            if isinstance(item, Jacquard):
                child_dict[attr] = item.serialize()
            elif isinstance(item, list):
                child_dict[attr] = [x.serialize() if isinstance(x, Jacquard) else x for x in item]
            else:
                child_dict[attr] = item
        return child_dict

    def to_file(self, fp):
        """Writes the Jacquard to a JSON file.

        Args:
            fp (str): File path to the output files
        """
        dict_ = self.serialize()
        with open_file(fp, mode='w') as writer:
            json.dump(dict_, writer, indent=2)

    @classmethod
    def from_file(cls, fp):
        """Reads a Jacquard from a JSON file. Comments beginning with '//' are ignored.

        Args:
            fp (str): The path to the JSON file

        Returns:
            Jacquard: The Jacquard object representing the JSON file.

        Raises:
            JacquardParseError: if there's a problem parsing the JSON file
        """
        with open_file(fp, mode='r') as reader:
            try:
                dict_ = json.loads(cls._parse_comments(reader), object_pairs_hook=OrderedDict)
            except ValueError as ve:
                # If there's an error reading the JSON file, re-raise it as a JacquardParseError for clarity
                raise JacquardParseError(str(ve))

            root_name = os.path.splitext(os.path.basename(fp))[0]
            return Jacquard(dict_, name=root_name, file_=fp)

    @classmethod
    def from_string(cls, s, file_name='<from_str>', root_name='<root>'):
        """Reads a Jacquard from a JSON file as a string. Comments beginning with '//' are ignored.

        Args:
            s (str): The string containing the Jacquard data, in JSON format.
            file_name (str): Optional 'file' name for display purposes.
            root_name (str): Optional root name for display purposes.

        Returns:
            Jacquard:
                The Jacquard object representing the JSON file.

        Raises:
            JacquardParseError: if there's a problem parsing the JSON file
        """
        sio = StringIO(s)
        try:
            dict_ = json.loads(cls._parse_comments(sio), object_pairs_hook=OrderedDict)
        except ValueError as ve:
            raise JacquardParseError(str(ve))

        return Jacquard(dict_, name=root_name, file_=file_name)

    @staticmethod
    def from_dict(dict_, file_name='<from_dict>', root_name='<root>'):
        """Converts a raw dictionary to a Jacquard object.

        Args:
            dict_ (dict): The dictionary to create a Jacquard from
            file_name:
            root_name:

        Returns:
            Jacquard
        """
        return Jacquard(dict_, name=root_name, file_=file_name)

    @staticmethod
    def _parse_comments(reader):
        """Removes comments beginning with '//' from the stream"""
        regex = r'\s*(#|\/{2}).*$'
        regex_inline = r'(:?(?:\s)*([A-Za-z\d\.{}]*)|((?<=\").*\"),?)(?:\s)*(((#|(\/{2})).*)|)$'

        pipe = []
        for line in reader:
            if re.search(regex, line):
                if re.search(r'^' + regex, line, re.IGNORECASE): continue
                elif re.search(regex_inline, line):
                    pipe.append(re.sub(regex_inline, r'\1', line))
            else:
                pipe.append(line)
        return "\n".join(pipe)
