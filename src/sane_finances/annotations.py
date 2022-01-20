#!/usr/bin/python
# -*- coding: utf-8 -*-

""" Annotations for instance attributes, functions arguments, etc.
"""

import sys
import operator
import collections.abc
import logging
import typing

logging.getLogger().addHandler(logging.NullHandler())

T = typing.TypeVar('T')  # pylint: disable=invalid-name


@typing.runtime_checkable
class SupportsDescription(typing.Protocol):
    """ An ABC with description attribute of type string.

    Can be used with ``isinstance`` to check whether object contains such attribute.
    Supposed for using with custom enums in meta modules.
    """
    description: str


class Description:
    """ Description for attribute's or function argument's annotation

    ``description`` can be used for wide description.

    ``short_description`` can be used for short description, e.g. for label of input in HTML form.
    """
    description: str
    short_description: str = None

    def __init__(self, description: str, short_description: str = None):
        """ Initialize description.

        :param description: Description of attribute or argument.
        :param short_description: Short description (optional).
        """
        self.description = str(description)
        self.short_description = None if short_description is None else str(short_description)


class Volatile:
    """ Describes attribute or function argument which value even through not optional,
    but can be reevaluated each time when uses for instantiation or function calling.

    For example: some source demands interval [date_from; date_to] for download history data,
    but we need to download it every day. So we store this interval somewhere in configuration
    and mark date_to as ``Volatile`` with reevaluating as ``date.today()``
    every time we fetch parameters from configuration.
    Thus, interval widened every day without modifying configuration.

    ::

        class Params:
            isin: str
            date_from: datetime.date
            date_to: Annotated[datetime.date, Volatile(lambda ctx: datetime.date.today(), datetime.date.max)]
    """

    def __init__(self,
                 generator: typing.Callable[[typing.Dict[str, typing.Any]], T],
                 stub_value: T = None):
        """ Initialize volatile annotation.

        :param generator: Function for reevaluating;
                          takes context of instantiation or function calling (like ``kwargs``)
                          and returns new value of attribute.
        :param stub_value: Stub value for not optional attributes.
        """
        if not callable(generator):
            raise TypeError("generator is not callable")

        self.generator = generator
        self.stub_value = stub_value

    def generate(self, context: typing.Dict[str, typing.Any]) -> T:
        """ Generate actual value of attribute or function argument based on context.

        :param context: Context of instantiation or function calling (like ``kwargs``)
        :return: Actual value of volatile attribute.
        """
        return self.generator(context)


# Support legacy 3.8 version:
# Got from https://github.com/python/typing (typing_extensions module)

# After PEP 560, internal typing API was substantially reworked.
# This is especially important for Protocol class which uses internal APIs
# quite extensively.
PEP_560 = sys.version_info[:3] >= (3, 7, 0)

try:  # pragma: no cover
    # noinspection PyProtectedMember
    from typing import _tp_cache
except ImportError:  # pragma: no cover
    def _tp_cache(x):  # pylint: disable=invalid-name
        return x

LEGACY_ANNOTATIONS = True  # flag about legacy python version

# Python 3.9+ has PEP 593 (Annotated and modified get_type_hints)
if hasattr(typing, 'Annotated'):  # pragma: no cover

    Annotated = typing.Annotated
    get_type_hints = typing.get_type_hints

    # Not exported and not a public API, but needed for get_origin() and get_args()
    # to work.
    # noinspection PyUnresolvedReferences,PyProtectedMember
    _AnnotatedAlias = typing._AnnotatedAlias

    LEGACY_ANNOTATIONS = False

elif PEP_560:  # pragma: no cover

    # noinspection PyUnresolvedReferences,PyProtectedMember
    class _AnnotatedAlias(typing._GenericAlias, _root=True):
        """Runtime representation of an annotated type.
        At its core 'Annotated[t, dec1, dec2, ...]' is an alias for the type 't'
        with extra annotations. The alias behaves like a normal typing alias,
        instantiating is the same as instantiating the underlying type, binding
        it to types is also the same.
        """
        def __init__(self, origin, metadata):
            if isinstance(origin, _AnnotatedAlias):
                metadata = origin.__metadata__ + metadata
                origin = origin.__origin__
            super().__init__(origin, origin)
            self.__metadata__ = metadata

        def copy_with(self, params):
            assert len(params) == 1
            new_type = params[0]
            return _AnnotatedAlias(new_type, self.__metadata__)

        def __repr__(self):
            return "typing_extensions.Annotated[{}, {}]".format(
                typing._type_repr(self.__origin__),
                ", ".join(repr(a) for a in self.__metadata__)
            )

        def __reduce__(self):
            return operator.getitem, (
                Annotated, (self.__origin__,) + self.__metadata__
            )

        def __eq__(self, other):
            if not isinstance(other, _AnnotatedAlias):
                return NotImplemented
            if self.__origin__ != other.__origin__:
                return False
            return self.__metadata__ == other.__metadata__

        def __hash__(self):
            return hash((self.__origin__, self.__metadata__))

    class Annotated:
        """Add context specific metadata to a type.
        Example: Annotated[int, runtime_check.Unsigned] indicates to the
        hypothetical runtime_check module that this type is an unsigned int.
        Every other consumer of this type can ignore this metadata and treat
        this type as int.
        The first argument to Annotated must be a valid type (and will be in
        the __origin__ field), the remaining arguments are kept as a tuple in
        the __extra__ field.
        Details:
        - It's an error to call `Annotated` with less than two arguments.
        - Nested Annotated are flattened::
            Annotated[Annotated[T, Ann1, Ann2], Ann3] == Annotated[T, Ann1, Ann2, Ann3]
        - Instantiating an annotated type is equivalent to instantiating the
        underlying type::
            Annotated[C, Ann1](5) == C(5)
        - Annotated can be used as a generic type alias::
            Optimized = Annotated[T, runtime.Optimize()]
            Optimized[int] == Annotated[int, runtime.Optimize()]
            OptimizedList = Annotated[List[T], runtime.Optimize()]
            OptimizedList[int] == Annotated[List[int], runtime.Optimize()]
        """

        __slots__ = ()

        def __new__(cls, *args, **kwargs):
            raise TypeError("Type Annotated cannot be instantiated.")

        @_tp_cache
        def __class_getitem__(cls, params):
            if not isinstance(params, tuple) or len(params) < 2:
                raise TypeError("Annotated[...] should be used "
                                "with at least two arguments (a type and an "
                                "annotation).")
            msg = "Annotated[t, ...]: t must be a type."
            # noinspection PyUnresolvedReferences,PyProtectedMember
            origin = typing._type_check(params[0], msg)
            metadata = tuple(params[1:])
            return _AnnotatedAlias(origin, metadata)

        def __init_subclass__(cls, *args, **kwargs):
            raise TypeError(
                "Cannot subclass {}.Annotated".format(cls.__module__)
            )

    def _strip_annotations(t):  # pylint: disable=invalid-name
        """Strips the annotations from a given type.
        """
        if isinstance(t, _AnnotatedAlias):
            return _strip_annotations(t.__origin__)
        # noinspection PyUnresolvedReferences,PyProtectedMember
        if isinstance(t, typing._GenericAlias):
            stripped_args = tuple(_strip_annotations(a) for a in t.__args__)
            if stripped_args == t.__args__:
                return t
            res = t.copy_with(stripped_args)
            # noinspection PyProtectedMember
            res._special = t._special
            return res
        return t

    def get_type_hints(obj, globalns=None, localns=None, include_extras=False):
        """Return type hints for an object.
        This is often the same as obj.__annotations__, but it handles
        forward references encoded as string literals, adds Optional[t] if a
        default value equal to None is set and recursively replaces all
        'Annotated[T, ...]' with 'T' (unless 'include_extras=True').
        The argument may be a module, class, method, or function. The annotations
        are returned as a dictionary. For classes, annotations include also
        inherited members.
        TypeError is raised if the argument is not of a type that can contain
        annotations, and an empty dictionary is returned if no annotations are
        present.
        BEWARE -- the behavior of globalns and localns is counterintuitive
        (unless you are familiar with how eval() and exec() work).  The
        search order is locals first, then globals.
        - If no dict arguments are passed, an attempt is made to use the
          globals from obj (or the respective module's globals for classes),
          and these are also used as the locals.  If the object does not appear
          to have globals, an empty dictionary is used.
        - If one dict argument is passed, it is used for both globals and
          locals.
        - If two dict arguments are passed, they specify globals and
          locals, respectively.
        """
        hint = typing.get_type_hints(obj, globalns=globalns, localns=localns)
        if include_extras:
            return hint
        return {k: _strip_annotations(t) for k, t in hint.items()}

# Python 3.8 has get_origin() and get_args() but those implementations aren't
# Annotated-aware, so we can't use those, only Python 3.9 versions will do.
if sys.version_info[:2] >= (3, 9):  # pragma: no cover

    get_origin = typing.get_origin
    get_args = typing.get_args

elif PEP_560:  # pragma: no cover

    # noinspection PyUnresolvedReferences,PyProtectedMember
    from typing import _GenericAlias
    try:
        # 3.9+
        # noinspection PyProtectedMember
        from typing import _BaseGenericAlias
    except ImportError:
        _BaseGenericAlias = _GenericAlias
    try:
        # 3.9+
        from typing import GenericAlias
    except ImportError:
        GenericAlias = _GenericAlias


    def get_origin(tp):  # pylint: disable=invalid-name
        """Get the unsubscripted version of a type.

        This supports generic types, Callable, Tuple, Union, Literal, Final, ClassVar
        and Annotated. Return None for unsupported types. Examples::

            get_origin(Literal[42]) is Literal
            get_origin(int) is None
            get_origin(ClassVar[int]) is ClassVar
            get_origin(Generic) is Generic
            get_origin(Generic[T]) is Generic
            get_origin(Union[T, int]) is Union
            get_origin(List[Tuple[T, T]][int]) == list
        """
        if isinstance(tp, _AnnotatedAlias):
            return Annotated
        if isinstance(tp, (_BaseGenericAlias, GenericAlias)):
            return tp.__origin__
        if tp is typing.Generic:
            return typing.Generic
        return None


    def get_args(tp):  # pylint: disable=invalid-name
        """Get type arguments with all substitutions performed.

        For unions, basic simplifications used by Union constructor are performed.
        Examples::
            get_args(Dict[str, int]) == (str, int)
            get_args(int) == ()
            get_args(Union[int, Union[T, int], str][int]) == (int, str)
            get_args(Union[int, Tuple[T, int]][str]) == (int, Tuple[str, int])
            get_args(Callable[[], T][int]) == ([], int)
        """
        if isinstance(tp, _AnnotatedAlias):
            return (tp.__origin__,) + tp.__metadata__
        if isinstance(tp, (_GenericAlias, GenericAlias)):
            res = tp.__args__
            if tp.__origin__ is collections.abc.Callable and res[0] is not Ellipsis:
                res = (list(res[:-1]), res[-1])
            return res
        return ()
