from __future__ import division, absolute_import, print_function, unicode_literals

from keyword import kwlist
import re
import tokenize
from contextlib import contextmanager

import six

try:
    from pathlib import Path
    PATHLIB_LOADED = True
except ImportError:
    PATHLIB_LOADED = False
    Path = None


class JacquardParseError(IOError):
    pass


class JacquardSpecificationError(AttributeError):
    pass


class JacquardTypeError(ValueError):
    pass


class JacquardValue(object):
    """Wraps the value of a Jacquard attribute to facilitate type-checking and pretty error messages."""

    def __init__(self, value, name, owner=None):
        self.value = value
        self._name = str(name)
        self._owner = owner

    def __str__(self): return str(self.value)

    def __repr__(self): return "JacquardValue(%r)" % self.value

    @property
    def namespace(self):
        """Dot-separated name of this jacquard value"""
        if self._owner is not None:
            return self._owner.namespace + '.' + self._name
        return self._name

    def as_type(self, type_):
        """Attempts to cast the value to a specified type.

        Args:
            type_ (type): The type (e.g. int, float, etc.) to try to cast

        Returns:
            The value cast as type

        Raises:
            JacquardTypeError: if the casting could not be performed.
        """

        try:
            return type_(self.value)
        except (ValueError, TypeError):

            message = "Attribute <{}> = '{}' could not be converted to {}".format(
                self.namespace, self.value, type_
            )
            raise JacquardTypeError(message)

    def as_bool(self):
        """Resolves the value to bool

        Raises:
            JacquardTypeError: If the value cannot be resolved to bool
        """
        return self.as_type(bool)

    def as_int(self):
        """Resolves the value to int

        Raises:
            JacquardTypeError: If the value cannot be resolved to int
        """
        return self.as_type(int)

    def as_float(self):
        """Resolves the value to float

        Raises:
            JacquardTypeError: If the value cannot be resolved to float
        """
        return self.as_type(float)

    def as_str(self):
        """Resolves the value to str

        Raises:
            JacquardTypeError: If the value cannot be resolved to str
        """
        return self.as_type(str)

    def as_list(self, sub_type=None):
        """Resolves the value to a list.

        Args:
            sub_type (type): Optional. Specifies the expected contiguous (uniform) type of the list to convert to.

        Returns:
            list: The value, as a list
        """
        if sub_type is None:
            return self.as_type(list)

        return [
            item.as_type(sub_type)
            for item in self.as_type(list)
        ]

    if PATHLIB_LOADED:
        def as_path(self, parent=None, check_exist=False):
            """Resolves the value to Path type (available only when using Python 3)

            Args:
                parent: Optional parent folder if this is a relative path
                check_exist: Flag to check file existence

            Raises:
                JacquardTypeError: If the value cannot be resolved to Path
            """
            fp = Path(self.as_str()) if parent is None else (Path(parent) / Path(self.as_str()))
            if check_exist:
                if not fp.exists():
                    raise FileNotFoundError('File `%s` not found' % fp.as_posix())
            return fp

    def as_set(self, sub_type=None):
        """Converts the value to a set.

        Args:
            sub_type (type): Optional. Specifies the expected contiguous (uniform) type of the set to convert to.

        Returns:
            set: The value, as a set
        """
        if sub_type is None: return self.as_type(set)

        return {
            item.as_type(sub_type)
            for item in self.as_type(set)
        }

    def serialize(self):
        if isinstance(self.value, list):
            return [x.serialize() if hasattr(x, 'serialize') else x for x in self.value]
        return self.value


if six.PY3:
    def is_identifier(name):
        """Tests that the name is a valid Python variable name and does not collide with reserved keywords

        Args:
            name (str): Name to test

        Returns:
            bool: If the name is 'Pythonic'
        """

        return name.isidentifier() and name not in kwlist
else:
    def is_identifier(name):
        """Tests that the name is a valid Python variable name and does not collide with reserved keywords

        Args:
            name (str): Name to test

        Returns:
            bool: If the name is 'Pythonic'
        """

        return bool(re.match(tokenize.Name + '$', name)) and name not in kwlist


@contextmanager
def open_file(file_handle, **kwargs):
    """Context manager for opening files provided as several different types. Supports a file handler as a str, unicode,
    ``pathlib.Path``, or an already-opened handler.

    Args:
        file_handle (Union[str, unicode, Path, File]): The item to be opened or is already open.
        **kwargs: Keyword args passed to ``open()``. Usually mode='w'.

    Yields:
        File: The opened file handler. Automatically closed once out of context.
    """
    opened = False
    if isinstance(file_handle, six.string_types):
        f = open(file_handle, **kwargs)
        opened = True
    elif Path is not None and isinstance(file_handle, Path):
        f = file_handle.open(**kwargs)
        opened = True
    else:
        f = file_handle

    try:
        yield f
    finally:
        if opened:
            f.close()
