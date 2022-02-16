#!/usr/bin/python
# -*- coding: utf-8 -*-

""" Analyzers and utilities for instances and classes annotated structure.

Every source has its own structure of download parameters: attributes, their types, etc.
This module helps to deal with such structure in unified way: analyze, parse, convert to/from dictionary, etc.
"""
import abc
import builtins
import collections
import datetime
import decimal
import enum
import importlib
import inspect
import itertools
import logging
import typing

from ..annotations import Description, Volatile, LEGACY_ANNOTATIONS
from ..sources.base import DownloadParameterValuesStorage, DynamicEnumTypeManager
from ..sources.inspection import InstrumentInfoParameter

if LEGACY_ANNOTATIONS:  # pragma: no cover
    from ..annotations import get_type_hints, get_args, get_origin
else:  # pragma: no cover
    from typing import get_type_hints, get_args, get_origin

logging.getLogger().addHandler(logging.NullHandler())

T = typing.TypeVar('T')  # pylint: disable=invalid-name

FULL_PATH_DELIMITER = ','


def get_attr_by_path(src: typing.Any, parts: typing.Iterable[str]) -> typing.Any:
    """ Get instance attribute value by path.

    Acts like ``getattr`` builtin function but instead of attribute name takes chain of names.
    E.g.::

        class Nested:
            val: str

        class A:
            nested: Nested

        n = Nested()
        n.val = 'Hello'
        a = A()
        a.nested = n
        print(get_attr_by_path(a, ['nested', 'val']))  # prints 'Hello'

    :param src: Instance.
    :param parts: Sequence of attributes names.
    :return: Attribute value.
    """
    value = src
    for part in parts:
        value = getattr(value, part)
    return value


def get_all_builtins() -> typing.Tuple:
    """ Get all builtins.

    :return: Tuple of all available builtin instances (classes, functions, instances, etc.)
    """
    if get_all_builtins.all_builtins is None:
        get_all_builtins.all_builtins = tuple(v for n, v in inspect.getmembers(builtins)
                                              if n not in ('copyright', '_', 'credits'))
    return get_all_builtins.all_builtins


get_all_builtins.all_builtins = None


def get_full_path(obj: typing.Any) -> str:
    """ Get full path os some object in form 'module_name,qualified_name'
    appropriate for ``get_by_full_path`` function.

    Such full path can be used as fully qualified or absolute path for object import,
    class for instance.

    :param obj: Object to inspect.
    :return: String that represents full path of object.
    """
    if not hasattr(obj, '__module__'):
        raise ValueError(f"Can't get full path because {obj!r} has no attribute '__module__'")
    if not hasattr(obj, '__qualname__'):
        raise ValueError(f"Can't get full path because {obj!r} has no attribute '__qualname__'")

    module_name, obj_qual_name = obj.__module__, obj.__qualname__
    return module_name + FULL_PATH_DELIMITER + obj_qual_name


def get_by_full_path(full_path: str) -> typing.Any:
    """ Get value by fully qualified name.

    :param full_path: Full path (fully qualified name) in form 'module_name,qualified_name'
    :return: Value of fully qualified object or ``None`` if module 'module_name' not found.
    """
    module_name, obj_qual_name = full_path.split(FULL_PATH_DELIMITER)
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError:
        return None
    return get_attr_by_path(module, obj_qual_name.split('.'))


def is_namedtuple(obj):
    """ Check that object is named tuple.

    :param obj: Object to check.
    :return: ``True`` if `obj` is named tuple. Otherwise, ``False``.
    """
    return isinstance(obj, tuple) and hasattr(obj, '_asdict')


def is_namedtuple_class(cls):
    """Check that class is named tuple.

    :param cls: Class to check.
    :return: ``True`` if `cls` is named tuple class. Otherwise, ``False``.
    """
    return issubclass(cls, tuple) and hasattr(cls, '_asdict')


class InstanceBuilderArgFactory:
    """ Container for ``InstanceBuilder`` settings.
    """

    def __init__(self,
                 simple_converter: typing.Optional[typing.Callable[[typing.Type, typing.Any], typing.Any]] = None,
                 complex_factory: typing.Optional[typing.Callable[..., typing.Any]] = None):
        """ Initialize instance.

        Do not use this ``__init__`` to instantiate container.
        Use ``simple`` or ``complex`` class methods instead.

        :param simple_converter: Callable takes target type (class) and value to convert. Returns converted value.
        :param complex_factory: Any callable that must be analyzed as nested instance builder.
        """

        if simple_converter is None and complex_factory is None:
            raise ValueError("All converters are ``None``")
        if simple_converter is not None and complex_factory is not None:
            raise ValueError("All converters are not ``None``. Only one accepted.")

        self.simple_converter = simple_converter
        self.complex_factory = complex_factory

    @property
    def is_simple(self):
        """ Whether this container is for simple converter.
        """
        return self.simple_converter is not None

    @property
    def is_complex(self):
        """ Whether this container is for complex instance.
        """
        return self.complex_factory is not None

    @classmethod
    def simple(
            cls,
            simple_converter: typing.Callable[[typing.Type, typing.Any], typing.Any]) -> 'InstanceBuilderArgFactory':
        """ Create new instance of simple converter container.

        :param simple_converter: Callable takes target type (class) and value to convert. Returns converted value.
        :return: New instance of container.
        """
        if simple_converter is None:
            raise ValueError("'simple_converter' is None")

        return cls(simple_converter, None)

    @classmethod
    def complex(cls, complex_factory: typing.Callable[..., typing.Any]) -> 'InstanceBuilderArgFactory':
        """ Create new instance of complex instance container.

        :param complex_factory: Any callable that must be analyzed as nested instance builder.
        :return: New instance of container.
        """
        if complex_factory is None:
            raise ValueError("'complex_converter' is None")

        return cls(None, complex_factory)


def _enum_converter(enum_type, value_to_convert):
    return enum_type(value_to_convert)


class InstanceBuilder:
    """ Creates new instances of some class from its dictionary representation.

    E.g.::

        class Nested:
            val: str

        class A:
            nested: Nested

        builder = InstanceBuilder(A)
        a = builder.build_instance({'nested':{'val':'Hello'}})
        assert isinstance(a, A)

    For dataclasses and named tuples every factory must have the same arguments names as fields names.
    Example::

        @dataclasses.dataclass
        class Wrong:
            attr_name: str
            def __init__(self, name: str): # argument name doesn't match attribute name
                self.attr_name = name

        @dataclasses.dataclass
        class Correct:
            attr_name: str
            def __init__(self, attr_name: str): # argument name do match attribute name
                self.attr_name = attr_name

    To correctly build instance of ``Wrong`` class we need to create alternative factory
    and use it instead of ``Wrong`` class itself::

        def factory_for_wrong(attr_name: str): # argument name do match attribute name
            return Wrong(attr_name)

    In such case we have to use ``builder = InstanceBuilder(factory_for_wrong)``
    instead of ``builder = InstanceBuilder(Wrong)``.

    """
    # order is important: last item wins.
    # thus base classes have to locate at the beginning,
    # more specialized classes (subclasses) have to locate at the ending.
    # otherwise, base class will always be used.
    args_factories: typing.OrderedDict[typing.Any, typing.Optional[InstanceBuilderArgFactory]]

    default_args_factories: typing.OrderedDict[typing.Any, typing.Optional[InstanceBuilderArgFactory]] = \
        collections.OrderedDict({
            datetime.date: InstanceBuilderArgFactory.simple(lambda t, v: v),
            datetime.datetime: InstanceBuilderArgFactory.simple(lambda t, v: v),
            enum.Enum: InstanceBuilderArgFactory.simple(_enum_converter),
            decimal.Decimal: InstanceBuilderArgFactory.simple(lambda t, v: v),
        })

    class _FactoriesDict(dict):
        def __init__(self, factory: typing.Callable[..., typing.Any], *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.factory = factory

    def __init__(
            self,
            root_factory: typing.Callable[..., T],
            parameter_values_storage: DownloadParameterValuesStorage = None,
            args_factories: typing.OrderedDict[typing.Any, typing.Optional[InstanceBuilderArgFactory]] = None):
        """ Initialize builder.

        :param root_factory: Factory to create instance.
          Usually some callable factory function or instance class itself (i.e. __init__ method).
        :param parameter_values_storage: Storage for managing dynamic enum types.
          Or ``None`` if no dynamic enum type available.
        :param args_factories: Additional factories for special or unknown types.
          Or ``None`` if not needed.
        """
        if not callable(root_factory):
            raise TypeError("'root_factory' is not callable")

        self.parameter_values_storage = parameter_values_storage

        initial_args_factories = tuple((k, v) for k, v in self.default_args_factories.items())

        if parameter_values_storage is not None:
            initial_args_factories = initial_args_factories + (
                tuple((dynamic_enum_type, InstanceBuilderArgFactory.simple(self._dynamic_enum_converter))
                      for dynamic_enum_type
                      in parameter_values_storage.get_all_managed_types()))

        # preserve order of user defined factories,
        # but default factories not overridden by user stays at the beginning,
        # thus if we want to change order of factories then we need explicitly override them.
        self.args_factories = (
            collections.OrderedDict(initial_args_factories)
            if args_factories is None
            else collections.OrderedDict(itertools.chain(
                ((k, v) for k, v in initial_args_factories if k not in args_factories),
                args_factories.items()))
        )

        self._factories_dict = self._build_factory(root_factory)

    def _dynamic_enum_converter(self, dynamic_enum_type, value_to_convert):
        if isinstance(value_to_convert, dynamic_enum_type):
            # already converted, maybe by deserializer
            return value_to_convert

        dynamic_enum_value = self.parameter_values_storage.get_dynamic_enum_value_by_key(
            dynamic_enum_type,
            value_to_convert)

        if dynamic_enum_value is not None:
            return dynamic_enum_value

        # can't convert - return original value
        return value_to_convert

    def build_instance(self, data: typing.Dict[str, typing.Any]) -> T:
        """ Create new instance from dictionary `data`.

        :param data: Dictionary representation of instance value.
        :return: New instance.
        """
        return self._build_instance(data, self._factories_dict)

    def _build_instance(self, data: typing.Dict[str, typing.Any], factories_dict) -> typing.Any:
        factories_dict: InstanceBuilder._FactoriesDict

        kwargs = {}
        for attr_name, attr_value in data.items():
            if attr_name not in factories_dict:
                raise ValueError(f"Not found factory for attribute {attr_name!r}")

            factories_dict_item = factories_dict[attr_name]
            if isinstance(factories_dict_item, InstanceBuilder._FactoriesDict):
                if not isinstance(attr_value, dict):
                    raise ValueError(f"The type of attribute {attr_name!r} is {type(attr_value)}. dict expected.")

                attr_value = self._build_instance(attr_value, factories_dict_item)

            else:
                attr_type, attr_value_factory = factories_dict_item
                attr_value = attr_value_factory(attr_type, attr_value)

            kwargs[attr_name] = attr_value

        return factories_dict.factory(**kwargs)

    def _build_factory(self, factory: typing.Callable[..., typing.Any]) -> 'InstanceBuilder._FactoriesDict':
        factories_dict = InstanceBuilder._FactoriesDict(factory)

        all_builtins = get_all_builtins()
        type_hints = get_type_hints(factory)
        sig = inspect.signature(factory)
        for param in sig.parameters.values():
            is_named = param.kind not in (inspect.Parameter.VAR_KEYWORD, inspect.Parameter.VAR_POSITIONAL)
            if is_named:
                if param.name not in type_hints:
                    raise ValueError(f"Parameter {param.name!r} of factory {factory!r} is not annotated")
                param_annotation = type_hints[param.name]

                origin = get_origin(param_annotation)
                if origin is not None:
                    if origin is typing.Union and param.default is None:
                        # indirectly find out that param_annotation is typing.Optional
                        param_annotation = param.annotation
                    else:
                        param_annotation = origin

                attr_type: typing.Any  # to fix https://youtrack.jetbrains.com/issue/PY-42287
                last_matched_factory = collections.deque(
                    (param_factory
                     for attr_type, param_factory
                     in self.args_factories.items()
                     if (issubclass(param_annotation, attr_type)
                         if inspect.isclass(param_annotation) and inspect.isclass(attr_type)
                         else param_annotation == attr_type)
                     ),
                    maxlen=1)

                if last_matched_factory:
                    param_factory = last_matched_factory.pop()

                    if param_factory.is_simple:
                        param_factory = param_annotation, param_factory.simple_converter

                    else:
                        assert param_factory.is_complex
                        param_factory = self._build_factory(param_factory.complex_factory)

                else:
                    if not callable(param_annotation):
                        raise ValueError(f"Annotation of parameter {param.name!r} of factory {factory!r} "
                                         f"is not callable: {param.annotation!r}")

                    if param_annotation in all_builtins:
                        param_factory = param_annotation, lambda t, v: t(v)

                    else:
                        # something complex
                        param_factory = self._build_factory(param_annotation)

                factories_dict[param.name] = param_factory

        return factories_dict


class InstanceAttributeInfo(typing.NamedTuple):
    """ Container for some instance attributes info got from ``FlattenedInstanceAnalyzer``.
    """
    parent_info: typing.Optional['InstanceAttributeInfo']
    path_from_root: typing.Tuple[str, ...]
    origin_annotated_type: typing.Any
    description_annotation: typing.Optional[Description]
    volatile_annotation: typing.Optional[Volatile]
    instrument_info_parameter_annotation: typing.Optional[InstrumentInfoParameter]
    has_default: bool
    default_value: typing.Any
    is_immutable: bool  # marked as absolutely dependent on another instance. can't change its value by itself.


class FlattenedInstanceAnalyzer(abc.ABC):
    """ Parse class (type) attributes annotations, including nested instances,
    and manage them as flattened data.
    """

    @abc.abstractmethod
    def get_flattened_attrs_info(self) -> typing.Dict[str, InstanceAttributeInfo]:
        """ Get info about all attributes of target class.

        :return: Dictionary in form {flattened_attribute_name: ``InstanceAttributeInfo``}.
        """
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def dynamic_enum_types(self) -> typing.Iterable[typing.Type]:
        """ All managed dynamic enum types.
        """
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def root_data_class(self) -> typing.Type[T]:
        """ Class to analyze.
        """
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def primitive_types(self) -> typing.Tuple[typing.Type, ...]:
        """ List of supported primitive types.
        """
        raise NotImplementedError


class FlattenedAnnotatedInstanceAnalyzer(FlattenedInstanceAnalyzer):
    """ Parse class (type) attributes annotations, including nested instances,
    and manage them as flattened data.
    """
    default_max_flattened_attr_name_suffix_index = 100

    # order is important: last item wins.
    # thus base classes have to locate at the beginning,
    # more specialized classes (subclasses) have to locate at the ending.
    # otherwise, base class will always be used.
    _primitive_types = (str, int, bool, float, list, set, dict,
                        decimal.Decimal, datetime.date, datetime.datetime, enum.Enum)

    def __init__(
            self,
            root_data_class: typing.Type[T],
            dynamic_enum_type_manager: DynamicEnumTypeManager = None,
            flattened_attr_name_prefix: str = None,
            max_flattened_attr_name_suffix_index: int = None):
        """ Initialize analyzer.

        :param root_data_class: Class to analyze.
        :param dynamic_enum_type_manager: Manager for dynamic enum types.
        :param flattened_attr_name_prefix: Prefix for flattened attribute names in resultant dictionary.
        :param max_flattened_attr_name_suffix_index: Max value of index added (as suffix)
            to flattened attribute name if it duplicated.
        """
        assert tuple not in self._primitive_types, "Named tuples treated as complex types"

        if not inspect.isclass(root_data_class):
            raise TypeError(f"{root_data_class!r} is not class")

        self._root_data_class = root_data_class
        self.dynamic_enum_type_manager = dynamic_enum_type_manager
        self.max_flattened_attr_name_suffix_index = (
            self.default_max_flattened_attr_name_suffix_index
            if max_flattened_attr_name_suffix_index is None
            else max_flattened_attr_name_suffix_index)

        self._flattened_attrs_info: typing.Dict[str, InstanceAttributeInfo] = {}

        self._analyze_data_class(root_data_class, flattened_attr_name_prefix)

    def get_flattened_attrs_info(self) -> typing.Dict[str, InstanceAttributeInfo]:
        return self._flattened_attrs_info

    @property
    def dynamic_enum_types(self) -> typing.Iterable[typing.Type]:
        if self.dynamic_enum_type_manager is None:
            return ()

        return self.dynamic_enum_type_manager.get_all_managed_types()

    @property
    def root_data_class(self) -> typing.Type[T]:
        return self._root_data_class

    @property
    def primitive_types(self) -> typing.Tuple[typing.Type, ...]:
        return self._primitive_types

    @staticmethod
    def _has_default_getter(_type: typing.Type[T], attr_name: str):
        if is_namedtuple_class(_type):
            # noinspection PyProtectedMember
            attr_defaults: typing.Dict = _type._field_defaults
            return attr_name in attr_defaults
        return hasattr(_type, attr_name)

    @staticmethod
    def _default_value_getter(_type: typing.Type[T], attr_name: str):
        if is_namedtuple_class(_type):
            # noinspection PyProtectedMember
            attr_defaults: typing.Dict = _type._field_defaults
            return attr_defaults.get(attr_name, None)
        return getattr(_type, attr_name, None)

    def _analyze_data_class(
            self,
            _type: typing.Type[T],
            flattened_attr_name_prefix: str = None,
            parent_info: InstanceAttributeInfo = None):

        hints = get_type_hints(_type)
        if not hints:
            return

        descriptions: typing.Dict[str, Description] = {}
        volatiles: typing.Dict[str, Volatile] = {}
        instrument_info_parameters: typing.Dict[str, InstrumentInfoParameter] = {}
        type_hints = get_type_hints(_type, include_extras=True)  # pylint: disable=unexpected-keyword-arg
        for attr_name, annotation in type_hints.items():
            for annotation_arg in get_args(annotation):
                if isinstance(annotation_arg, Description):
                    descriptions[attr_name] = annotation_arg
                elif isinstance(annotation_arg, Volatile):
                    volatiles[attr_name] = annotation_arg
                elif isinstance(annotation_arg, InstrumentInfoParameter):
                    instrument_info_parameters[attr_name] = annotation_arg

        for attr_name, annotation in hints.items():
            has_default = self._has_default_getter(_type, attr_name)
            default_value = self._default_value_getter(_type, attr_name)
            attr_is_immutable = bool((parent_info is not None and parent_info.is_immutable)
                                     or (attr_name in instrument_info_parameters))

            description = descriptions.get(attr_name, None)
            volatile = volatiles.get(attr_name, None)
            instrument_info_parameter = instrument_info_parameters.get(attr_name, None)
            path_from_root: typing.Tuple[str, ...] = (tuple(() if parent_info is None else parent_info.path_from_root)
                                                      + (attr_name,))

            if flattened_attr_name_prefix is None:
                flattened_attr_name = attr_name
            else:
                flattened_attr_name = f"{flattened_attr_name_prefix}_{attr_name}"

            if flattened_attr_name in self._flattened_attrs_info:
                # find the nearest vacant suffixed name
                for i in range(2, self.max_flattened_attr_name_suffix_index + 1):
                    new_form_field_name = f"{flattened_attr_name}_{i}"
                    if new_form_field_name not in self._flattened_attrs_info:
                        flattened_attr_name = new_form_field_name
                        break

            if flattened_attr_name in self._flattened_attrs_info:
                raise ValueError(f"Field name {flattened_attr_name!r} duplicated.")

            origin = get_origin(annotation)
            if origin is not None:
                if origin is typing.Union:
                    raise ValueError(
                        f"Attribute {attr_name!r} in {_type} "
                        f"has not available annotation typing.Union or typing.Optional")

                annotation = origin

            is_primitive_type = bool(tuple(
                primitive_type
                for primitive_type
                in self.primitive_types
                if (issubclass(annotation, primitive_type)
                    if inspect.isclass(annotation) and inspect.isclass(primitive_type)
                    else annotation == primitive_type)
            ))

            is_dynamic_enum = (self.dynamic_enum_type_manager is not None
                               and self.dynamic_enum_type_manager.is_dynamic_enum_type(annotation))

            attr_info = InstanceAttributeInfo(
                parent_info=parent_info,
                path_from_root=path_from_root,
                origin_annotated_type=annotation,
                description_annotation=description,
                volatile_annotation=volatile,
                instrument_info_parameter_annotation=instrument_info_parameter,
                has_default=has_default,
                default_value=default_value,
                is_immutable=attr_is_immutable
            )

            if is_primitive_type or is_dynamic_enum:
                self._flattened_attrs_info[flattened_attr_name] = attr_info

            else:
                self._analyze_data_class(annotation, flattened_attr_name, attr_info)


class InstanceFlattener:
    """ Create flattened dictionary representation of instance.

    E.g.::

        class Nested:
            val: str

        class A:
            nested: Nested

        n = Nested()
        n.val = 'Hello'
        a = A()
        a.nested = n

        flattener = InstanceFlattener(FlattenedInstanceAnalyzer(A))
        print(flattener.get_flattened_data_from(a)) # prints {'nested_val':'Hello'}

    It reverts ``InstanceFactoryDataConverter`` result.
    """

    def __init__(
            self,
            flattened_instance_analyzer: FlattenedInstanceAnalyzer,
            dynamic_enum_type_manager: DynamicEnumTypeManager = None):

        self.root_data_class = flattened_instance_analyzer.root_data_class
        self.dynamic_enum_type_manager = dynamic_enum_type_manager

        self._flattened_attrs_info = flattened_instance_analyzer.get_flattened_attrs_info()

    def get_flattened_data_from(self, instance: T, stub_volatile=True) -> typing.Dict[str, typing.Any]:
        """ Get flattened dictionary (one level) of data from instance.

        :param instance: Instance to flatten.
        :param stub_volatile: Whether substitute attribute values with their stubs.
        :return: Flattened dictionary in form {flattened_attribute_name: attribute_value}.
        """
        if instance is None:
            return {}

        if not isinstance(instance, self.root_data_class):
            raise ValueError(f"Value of {instance!r} is not instance of {self.root_data_class!r}")

        flattened_data = {}
        for flattened_attr_name, attr_info in self._flattened_attrs_info.items():

            attr_value = get_attr_by_path(instance, attr_info.path_from_root)

            if isinstance(attr_value, enum.Enum):
                attr_value = attr_value.value

            elif self.dynamic_enum_type_manager is not None:
                if self.dynamic_enum_type_manager.is_dynamic_enum_type(type(attr_value)):
                    attr_value = self.dynamic_enum_type_manager.get_dynamic_enum_key(attr_value)

            if stub_volatile:
                volatile = attr_info.volatile_annotation
                if volatile is not None:
                    attr_value = volatile.stub_value
                elif attr_info.has_default and attr_info.default_value:
                    attr_value = attr_info.default_value

            flattened_data[flattened_attr_name] = attr_value

        return flattened_data


class InstanceFactoryDataConverter:
    """ Converts flattened dictionary to "full-deep" dictionary that appropriate for instance builder.

    E.g.::

        class Nested:
            val: str

        class A:
            nested: Nested

        n = Nested()
        n.val = 'Hello'
        a = A()
        a.nested = n

        converter = InstanceFactoryDataConverter(FlattenedInstanceAnalyzer(A))
        print(converter.get_instance_factory_data({'nested_val':'Hello'})) # prints {'nested':{'val':'Hello'}}

    It reverts ``InstanceFlattener`` result.
    """

    def __init__(
            self,
            flattened_instance_analyzer: FlattenedInstanceAnalyzer):

        self._flattened_attrs_info = flattened_instance_analyzer.get_flattened_attrs_info()

    def get_instance_factory_data(
            self,
            flattened_data: typing.Dict[str, typing.Any],
            generate_volatiles: bool = True) -> typing.Dict[str, typing.Any]:
        """ Takes flattened data (as dictionary) and converts it to "full-deep" data
        enabled for instance creation via its factory.

        :param flattened_data: Flattened dictionary in form {flattened_attribute_name: attribute_value}.
        :param generate_volatiles: Whether generate volatile attributes with their current values.
        :return: Full-deep dictionary representation of instance.
        """
        return self._get_factory_data(flattened_data, generate_volatiles)

    def _get_factory_data(
            self,
            flattened_data: typing.Dict[str, typing.Any],
            generate_volatiles: bool) -> typing.Dict[str, typing.Any]:
        factory_data = {}
        volatiles: typing.List[typing.Tuple[str, typing.Dict[str, typing.Any], Volatile]] = []
        for flattened_attr_name, flattened_attr_value in flattened_data.items():
            if flattened_attr_name not in self._flattened_attrs_info:
                raise ValueError(f"Not found info for attribute {flattened_attr_name!r}")

            attr_info = self._flattened_attrs_info[flattened_attr_name]
            path = attr_info.path_from_root
            if not path:
                raise ValueError(f"Path is empty for attribute {flattened_attr_name!r}")

            volatile = attr_info.volatile_annotation

            dst_data = factory_data
            attr_name: str
            for attr_index, attr_name in reversed(list(enumerate(reversed(path)))):
                # for last attr in path (aka leaf) attr_index == 0
                if attr_index == 0 and attr_name in dst_data:
                    raise ValueError(f"Attribute {attr_name!r} already in data. Possible duplication.")

                if attr_index == 0:
                    dst_data[attr_name] = flattened_attr_value
                    if generate_volatiles and volatile is not None:
                        volatiles.append((attr_name, dst_data, volatile))

                else:
                    if attr_name in dst_data:
                        new_dst_data = dst_data[attr_name]
                        assert isinstance(new_dst_data, dict), (f"Internal error: factory data for {attr_name!r} "
                                                                f"in path {path!r} is not dict")
                    else:
                        dst_data[attr_name] = new_dst_data = {}

                    dst_data = new_dst_data

        if generate_volatiles:
            for attr_name, context, volatile in volatiles:
                context[attr_name] = volatile.generate(context)

        return factory_data
