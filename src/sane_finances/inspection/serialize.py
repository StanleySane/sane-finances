#!/usr/bin/python
# -*- coding: utf-8 -*-

""" Serialisation utilities
"""
import abc
import collections
import dataclasses
import datetime
import decimal
import enum
import inspect
import json
import typing

from .analyzers import is_namedtuple, FlattenedInstanceAnalyzer
from ..sources.base import DownloadParameterValuesStorage


class FlattenedJSONEncoder(json.JSONEncoder):
    """ JSON encoder for one-level dictionaries.
    Flattened because not support nested dictionaries.

    Supports encoding of primitive types (int, str, float, etc.),
    but not supposed for using in such scenarios,
    because paired ``FlattenedJSONDecoder`` supports only dictionaries.

    Additionally, supports named tuples, dataclasses, enums, date, datetime and Decimal.
    """

    def __init__(
            self,
            *,
            skipkeys=False, ensure_ascii=True,
            check_circular=True, allow_nan=True, sort_keys=False,
            indent=None, separators=None, default=None,
            special_encoders: typing.Dict[typing.Type, typing.Callable[[typing.Any], typing.Any]] = None):
        """ Constructor for ``FlattenedJSONEncoder``, with sensible defaults.

        :param skipkeys: See ``json.JSONEncoder.__init__`` documentation
        :param ensure_ascii: See ``json.JSONEncoder.__init__`` documentation
        :param check_circular: See ``json.JSONEncoder.__init__`` documentation
        :param allow_nan: See ``json.JSONEncoder.__init__`` documentation
        :param sort_keys: See ``json.JSONEncoder.__init__`` documentation
        :param indent: See ``json.JSONEncoder.__init__`` documentation
        :param separators: See ``json.JSONEncoder.__init__`` documentation
        :param default: See ``json.JSONEncoder.__init__`` documentation
        :param special_encoders: Dictionary of encoders for special types
        in form of {<special type>, <encoder for such type>}.
        """

        super().__init__(
            skipkeys=skipkeys, ensure_ascii=ensure_ascii,
            check_circular=check_circular, allow_nan=allow_nan, sort_keys=sort_keys,
            indent=indent, separators=separators, default=default)

        self.special_encoders = special_encoders or {}

    def default(self, o: typing.Any) -> typing.Any:
        special_encoder = self.special_encoders.get(type(o))
        if special_encoder is not None:
            return special_encoder(o)

        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        if is_namedtuple(o):  # NamedTuple # pragma: no cover
            # unfortunately this not work because nested tuples treat as lists
            # we can fix it but need to reproduce all logic from 'iterencode' method (which is difficult)
            # that's why this encoder is flattened
            assert False, "Encoded object is named tuple. Should never fire."
            # noinspection PyProtectedMember,PyUnreachableCode
            return o._asdict()
        if isinstance(o, enum.Enum):
            return o.value
        if isinstance(o, (datetime.datetime, datetime.date)):
            return o.isoformat()
        if isinstance(o, decimal.Decimal):
            return float(o)

        # Let the base class default method raise the TypeError
        return super().default(o)

    def encode(self, o: typing.Any) -> str:
        if is_namedtuple(o):  # NamedTuple
            # if top level object is named tuple then we can consider it as dictionary
            # noinspection PyProtectedMember
            o = o._asdict()

        return super().encode(o)


class FlattenedJSONDecoder(json.JSONDecoder):
    """ Flat dict decoder. Supports only one level of dictionaries (i.e. nested dictionaries not decoded).
    """

    # order is important: last item wins.
    # thus base classes have to locate at the beginning,
    # more specialized classes (subclasses) have to locate at the ending.
    # otherwise, base class will always be used.
    default_type_decoders: typing.OrderedDict[typing.Any, typing.Callable[[typing.Any], typing.Any]] = \
        collections.OrderedDict({
            datetime.date: lambda v: None if v is None else datetime.date.fromisoformat(v),
            datetime.datetime: lambda v: None if v is None else datetime.datetime.fromisoformat(v),
            decimal.Decimal: lambda v: None if v is None else decimal.Decimal(repr(v) if isinstance(v, float) else v),
        })

    def __init__(
            self, *, object_hook=None, parse_float=None, parse_int=None, parse_constant=None,
            strict=True, object_pairs_hook=None,
            decoders: typing.Dict[str, typing.Callable[[typing.Any], typing.Any]] = None):
        """ Constructor for ``FlattenedJSONDecoder``, with sensible defaults.

        :param object_hook: See ``json.JSONDecoder.__init__`` documentation
        :param parse_float: See ``json.JSONDecoder.__init__`` documentation
        :param parse_int: See ``json.JSONDecoder.__init__`` documentation
        :param parse_constant: See ``json.JSONDecoder.__init__`` documentation
        :param strict: See ``json.JSONDecoder.__init__`` documentation
        :param object_pairs_hook: See ``json.JSONDecoder.__init__`` documentation
        :param decoders: Dictionary of decoders for special types
        in form of {<field name>, <decoder for such field>}.
        """

        self.decoders = decoders or {}

        super().__init__(
            object_hook=object_hook, parse_float=parse_float,
            parse_int=parse_int, parse_constant=parse_constant, strict=strict,
            object_pairs_hook=object_pairs_hook)

    @classmethod
    def get_default_type_decoder(
            cls: typing.Type['FlattenedJSONDecoder'],
            _type: typing.Any) -> typing.Optional[typing.Callable[[typing.Any], typing.Any]]:
        """ Get default decoder for some type (or derived).

        This method can be used for adjustment of decoders for types (or derived types)
        from internal default collection.

        :param _type: Type to decode.
        :return: Internal default decoder for type ``_type``, or ``None`` if type is unknown.
        """
        attr_type: typing.Any  # to fix https://youtrack.jetbrains.com/issue/PY-42287

        last_matched_decoder = collections.deque(
            (attr_decoder
             for attr_type, attr_decoder
             in cls.default_type_decoders.items()
             if (issubclass(_type, attr_type)
                 if inspect.isclass(_type) and inspect.isclass(attr_type)
                 else _type == attr_type)
             ),
            maxlen=1)

        if last_matched_decoder:
            attr_decoder = last_matched_decoder.pop()
            return attr_decoder

        return None

    def decode(self, s: str, **kwargs) -> typing.Dict[str, typing.Any]:  # pylint: disable=arguments-differ
        decoded = super().decode(s, **kwargs)

        if not isinstance(decoded, dict):
            raise ValueError(f"Can't decode object from {type(decoded)}. dict required.")

        decoded: typing.Dict[str, typing.Any]
        decoded = decoded.copy()

        for attr_name, attr_factory in self.decoders.items():
            if attr_name in decoded:
                decoded[attr_name] = attr_factory(decoded[attr_name])

        return decoded


class FlattenedDataSerializer(abc.ABC):
    """ Base class for flat dict serializer.

    Supports only one-level dictionaries.
    """

    @abc.abstractmethod
    def serialize_flattened_data(self, flattened_data: typing.Dict[str, typing.Any]) -> str:
        """ Get string representation of flattened data.

        :param flattened_data: One-level dictionary of data in form of {<field name>: <field value>}
        :return: String representation of data.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def deserialize_flattened_data(
            self,
            s: str,  # pylint: disable=invalid-name
            decode_dynamic_enums=True) -> typing.Dict[str, typing.Any]:
        """ Get dictionary representation of string data.

        Example::

            class DynEnum:
                enum_key: int
                enum_name: str

            d = FlattenedDataSerializer()

            data = d.deserialize_flattened_data('{"some_enum": 1}', decode_dynamic_enums=False)
            # data = {'some_enum': 1}

            data = d.deserialize_flattened_data('{"some_enum": 1}', decode_dynamic_enums=True)
            # data = {'some_enum': DynEnum(1)}

        :param s: String to deserialize.
        :param decode_dynamic_enums: ``True`` (default) if string representations of dynamic enums in ``s``
        must be converted to their enum types.
        Otherwise, deserialized values will be leaved in original representations (usually enum key value).
        See example above.
        :return: One-level dictionary of data in form of {<field name>: <field value>}
        """
        raise NotImplementedError


class FlattenedDataJsonSerializer(FlattenedDataSerializer):
    """ Flat dict serializer to/from JSON
    """
    separators = (',', ':')  # json separators with no spaces for more compact representation

    def __init__(
            self,
            flattened_instance_analyzer: FlattenedInstanceAnalyzer,
            parameter_values_storage: DownloadParameterValuesStorage,
            flattened_json_encoder: typing.Type[FlattenedJSONEncoder] = FlattenedJSONEncoder,
            flattened_json_decoder: typing.Type[FlattenedJSONDecoder] = FlattenedJSONDecoder):
        """ Constructor for ``FlattenedDataJsonSerializer``.

        :param flattened_instance_analyzer: Instance of ``FlattenedInstanceAnalyzer``
        :param parameter_values_storage: Instance of ``DownloadParameterValuesStorage``
        :param flattened_json_encoder: Appropriate ``JSONEncoder``
        :param flattened_json_decoder: Appropriate ``JSONDecoder``
        """
        self.flattened_json_encoder = flattened_json_encoder
        self.flattened_json_decoder = flattened_json_decoder

        self._prepare(flattened_instance_analyzer, parameter_values_storage)

    def _prepare(
            self,
            flattened_instance_analyzer: FlattenedInstanceAnalyzer,
            parameter_values_storage: DownloadParameterValuesStorage):

        self._flattened_data_decoders: typing.Dict[str, typing.Callable[[typing.Any], typing.Any]] = {}
        self._flattened_data_decoders_without_enums: typing.Dict[str, typing.Callable[[typing.Any], typing.Any]] = {}

        flattened_attrs_info = flattened_instance_analyzer.get_flattened_attrs_info()

        type_decoders: typing.OrderedDict[typing.Any, typing.Callable[[typing.Any], typing.Any]] = \
            collections.OrderedDict()
        for primitive_type in flattened_instance_analyzer.primitive_types:
            decoder = self.flattened_json_decoder.get_default_type_decoder(primitive_type)
            if decoder is not None:
                type_decoders[primitive_type] = decoder

        type_decoders_without_dynamic_enums = collections.OrderedDict(type_decoders)

        all_dynamic_enum_types: typing.Iterable[typing.Type] = flattened_instance_analyzer.dynamic_enum_types
        type_decoders.update({
            dynamic_enum_type: (
                lambda key, _enum_type=dynamic_enum_type, _parameter_values_storage=parameter_values_storage:
                _parameter_values_storage.get_dynamic_enum_value_by_key(_enum_type, key)
            )
            for dynamic_enum_type
            in all_dynamic_enum_types
        })

        self._dynamic_enum_encoders = {
            dynamic_enum_type: (
                lambda o, _parameter_values_storage=parameter_values_storage:
                _parameter_values_storage.get_dynamic_enum_key(o)
            )
            for dynamic_enum_type
            in all_dynamic_enum_types
        }

        for flattened_attr_name, attr_info in flattened_attrs_info.items():
            # find decoders for all attributes, include dynamic enums
            decoder = self._find_decoder(type_decoders, attr_info.origin_annotated_type)
            if decoder is not None:
                self._flattened_data_decoders[flattened_attr_name] = decoder

            # find decoders for attributes, exclude dynamic enums
            decoder = self._find_decoder(type_decoders_without_dynamic_enums, attr_info.origin_annotated_type)
            if decoder is not None:
                self._flattened_data_decoders_without_enums[flattened_attr_name] = decoder

    @staticmethod
    def _find_decoder(
            type_decoders: typing.OrderedDict[typing.Any, typing.Callable[[typing.Any], typing.Any]],
            attr_type: typing.Type):
        decodable_type: typing.Any  # to fix https://youtrack.jetbrains.com/issue/PY-42287

        last_matched_type = collections.deque(
            (decoder
             for decodable_type, decoder
             in type_decoders.items()
             if (issubclass(attr_type, decodable_type)
                 if inspect.isclass(attr_type) and inspect.isclass(decodable_type)
                 else attr_type == decodable_type)
             ),
            maxlen=1)

        if last_matched_type:
            decoder = last_matched_type.pop()
            return decoder

        return None

    def serialize_flattened_data(self, flattened_data: typing.Dict[str, typing.Any]) -> str:
        flattened_data = flattened_data.copy()
        # replace dynamic enum values with its keys
        flattened_data_pairs = tuple(flattened_data.items())
        for flattened_attr_name, flattened_attr_value in flattened_data_pairs:
            dynamic_enum_encoder = self._dynamic_enum_encoders.get(type(flattened_attr_value))
            if dynamic_enum_encoder is not None:
                flattened_data[flattened_attr_name] = dynamic_enum_encoder(flattened_attr_value)

        json_str_data = json.dumps(
            flattened_data,
            cls=self.flattened_json_encoder,
            separators=self.separators,
            special_encoders=self._dynamic_enum_encoders)

        return json_str_data

    def deserialize_flattened_data(self, s: str, decode_dynamic_enums=True) -> typing.Dict[str, typing.Any]:
        flattened_data: typing.Dict[str, typing.Any] = json.loads(
            s,
            cls=self.flattened_json_decoder,
            decoders=(self._flattened_data_decoders
                      if decode_dynamic_enums
                      else self._flattened_data_decoders_without_enums))

        return flattened_data
