from __future__ import annotations

import json
import os
import re
from collections import OrderedDict
from io import StringIO
from os import PathLike
from typing import Dict, Optional, Union
from warnings import warn

from .api import JacquardValue, is_identifier, open_file
from .exceptions import (JacquardParseError, JacquardSpecificationError,
                         JacquardTypeError)


class Jacquard:
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

    def __init__(self, jqd_dict: dict, *, name: str = None, parent: Jacquard = None, file_: Union[str, PathLike] = None):
        self._contents: Dict[str, Union[Jacquard, JacquardValue]] = {}
        self._name = name
        self._parent = parent
        self._file = str(file_)

        for key, original_value in jqd_dict.items():
            if isinstance(original_value, dict):
                value = Jacquard(original_value, name=key, parent=self, file_=file_)
            elif isinstance(original_value, (list, set)):
                value_list = []
                for (i, item) in enumerate(original_value):
                    if isinstance(item, dict):
                        value_list.append(Jacquard(item, name=f"{key}[{i}]", parent=self, file_=file_))
                    else:
                        value_list.append(JacquardValue(item, f"{key}[{i}]", owner=self))
                value = JacquardValue(value_list, key, owner=self)
            elif original_value is None:
                value = None
            else:
                value = JacquardValue(original_value, key, owner=self)

            if is_identifier(key):
                try:
                    setattr(self, key, value)
                except AttributeError:
                    warn(f'Jacquard key `{key}` conflicts with reserved properties')
            self._contents[key] = value

    @property
    def name(self) -> Optional[str]:
        """Short name of each part of the Jacquard. For non-root Jacquards, this will be the name of the attribute used
        to access this Jacquard from the parent."""
        return self._name

    @property
    def parent(self) -> Optional[Jacquard]:
        """Pointer to the parent of non-root Jacquard."""
        return self._parent

    @property
    def namespace(self) -> str:
        """The dot-separated namespace of this part of the full Jacquard."""
        name = self._name if self._name is not None else '<unnamed>'
        if self._parent is None:
            return name
        return '.'.join([self._parent.namespace, name])

    @property
    def file(self) -> str:
        """The source used for creation of the Jacquard instance."""
        return self._file

    def __repr__(self) -> str:
        if self._parent is None:
            return f"Jacquard @ {self._file}"
        return f"Jacquard({self.namespace}) @ {self._file}"

    def __str__(self) -> str:
        return f"Jacquard({self._name})"

    def __getattr__(self, item):
        raise JacquardSpecificationError(f"Item `{item}` is missing from Jacquard <{self.namespace}>")

    def __contains__(self, item):
        return item in self._contents

    def __getitem__(self, item):
        if item not in self:
            raise JacquardSpecificationError(f"Item `{item}` is missing from Jacquard <{self.namespace}>")
        return self._contents[item]

    def as_dict(self, *, value_type=None) -> OrderedDict:
        """Converts this entry to a primitive dictionary, using specified types for the keys and values.

        Args:
            value_type (type, optional): Defaults to ``None``. The type to which the values will be cast, or None to
                ignore casting.

        Returns:
            OrderedDict: A dictionary containing the entry's keys and values
        """

        if value_type is None:
            return self._contents.copy()

        def any_type(value):
            return value

        if value_type is None:
            value_type = any_type

        retval = OrderedDict()
        for key, val in self._contents.items():
            try:
                val = val.as_type(value_type)
            except ValueError:
                raise JacquardTypeError(f"Value <{self.namespace}.{key}> = '{val}' could not be converted to {value_type}")
            retval[key] = val
        return retval

    def serialize(self) -> OrderedDict:
        """Recursively converts the Jacquard back to primitive dictionaries"""
        child_dict = OrderedDict()
        for attr, item in self._contents.items():
            if isinstance(item, Jacquard):  # A nested Jacquard entry
                child_dict[attr] = item.serialize()
            elif isinstance(item, list):
                child_dict[attr] = [x.serialize() if isinstance(x, Jacquard) else x for x in item]
            elif isinstance(item, JacquardValue):  # A value saved as a JacquardValue
                child_dict[attr] = item.serialize()
            else:
                child_dict[attr] = item
        return child_dict

    def to_file(self, fp: Union[str, PathLike], *, sort_keys: bool = False):
        """Writes the Jacquard to a JSON file.

        Args:
            fp (str | PathLike): File path to the output files
            sort_keys (bool, optional): Defaults to ``True``.
        """
        dict_ = self.serialize()
        with open_file(fp, mode='w') as writer:
            json.dump(dict_, writer, indent=2, sort_keys=sort_keys)

    @classmethod
    def from_file(cls, fp: Union[str, PathLike]) -> Jacquard:
        """Reads a Jacquard from a JSON file. Comments beginning with '//' are ignored.

        Args:
            fp (str | PathLike): The path to the JSON file

        Returns:
            Jacquard: The Jacquard object representing the JSON file

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
    def from_string(cls, s: str, *, file_name: str = '<from_str>', root_name: str = '<root>') -> Jacquard:
        """Reads a Jacquard from a JSON string. Comments beginning with '//' are ignored.

        Args:
            s (str): The string containing the Jacquard data, in JSON format.
            file_name (str, optional): 'file' name for display purposes.
            root_name (str, optional): Root name for display purposes.

        Returns:
            Jacquard: The Jacquard object representing the JSON string

        Raises:
            JacquardParseError: if there's a problem parsing the JSON string
        """
        sio = StringIO(s)
        try:
            dict_ = json.loads(cls._parse_comments(sio), object_pairs_hook=OrderedDict)
        except ValueError as ve:
            raise JacquardParseError(str(ve))

        return Jacquard(dict_, name=root_name, file_=file_name)

    @staticmethod
    def from_dict(dict_: dict, *, file_name: str = '<from_dict>', root_name: str = '<root>') -> Jacquard:
        """Converts a raw dictionary to a Jacquard object.

        Args:
            dict_ (dict): The dictionary to create a Jacquard from
            file_name (str, optional): 'file' name for display purposes.
            root_name (str, optional): Root name for display purposes.

        Returns:
            Jacquard: The Jacquard object representing the dictionary object
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
                if re.search(r'^' + regex, line, re.IGNORECASE):
                    continue
                elif re.search(regex_inline, line):
                    pipe.append(re.sub(regex_inline, r'\1', line))
            else:
                pipe.append(line)
        return "\n".join(pipe)
