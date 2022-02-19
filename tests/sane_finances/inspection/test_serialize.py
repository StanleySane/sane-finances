#!/usr/bin/python
# -*- coding: utf-8 -*-
import dataclasses
import datetime
import decimal
import enum
import unittest
import typing
import json

from sane_finances.inspection.analyzers import InstanceAttributeInfo
from sane_finances.inspection.serialize import (
    FlattenedJSONEncoder, FlattenedJSONDecoder, FlattenedDataJsonSerializer)

from .fakes import FakeDownloadParameterValuesStorage, FakeFlattenedInstanceAnalyzer


@dataclasses.dataclass
class DynamicEnumType:
    enum_id: int
    enum_value: str


class TestFlattenedJSONEncoder(unittest.TestCase):

    def setUp(self) -> None:
        self.encoder = FlattenedJSONEncoder
        self.separators = (',', ':')  # override separators with no spaces for testing purposes

    def test_encode_Success(self):
        class SomeEnum(enum.Enum):
            ONE = 'one'
            TWO = 'two'

        @dataclasses.dataclass
        class SomeDataclass:
            value: int

        class SomeNamedTuple(typing.NamedTuple):
            value: int

        for flattened_data, expected_json_str in (
                (None, 'null'),
                (42, '42'),
                ('42', '"42"'),
                ([42], '[42]'),
                (SomeEnum.ONE, f'"{SomeEnum.ONE.value}"'),
                (datetime.date(1900, 12, 31), '"1900-12-31"'),
                (decimal.Decimal(42), '42.0'),
                ({}, '{}'),
                ({'value': 42}, '{"value":42}'),
                (SomeDataclass(value=42), '{"value":42}'),
                (SomeNamedTuple(value=42), '{"value":42}'),
        ):
            json_str_data = json.dumps(
                flattened_data,
                cls=self.encoder,
                separators=self.separators)

            self.assertEqual(expected_json_str, json_str_data)

    def test_encode_SuccessWithSpecialEncoders(self):

        dynamic_enum_value = DynamicEnumType(42, 'd42')

        for flattened_data, expected_json_str in (
                (dynamic_enum_value, str(dynamic_enum_value.enum_id)),
        ):
            json_str_data = json.dumps(
                flattened_data,
                cls=self.encoder,
                separators=self.separators,
                special_encoders={DynamicEnumType: lambda v: v.enum_id})

            self.assertEqual(expected_json_str, json_str_data)

    def test_encode_RaiseWithUnknownType(self):
        class SomeUnknownClass:
            pass

        with self.assertRaises(TypeError):
            _ = json.dumps(SomeUnknownClass(), cls=self.encoder)


class TestFlattenedJSONDecoder(unittest.TestCase):

    def setUp(self) -> None:
        self.decoder = FlattenedJSONDecoder
        self.decoders = {'value': lambda v: v}

    def test_decode_Success(self):
        for expected_flattened_data, json_str in (
                ({}, '{}'),
                ({'value': 42}, '{"value":42}'),
        ):
            flattened_data = json.loads(
                json_str,
                cls=self.decoder,
                decoders=self.decoders)

            self.assertEqual(expected_flattened_data, flattened_data)

    def test_decode_RaiseWithNotDict(self):
        with self.assertRaises(ValueError):
            _ = json.loads(
                '42',
                cls=self.decoder,
                decoders=self.decoders)

    def test_get_default_type_decoder_Success(self):
        class SomeUnknownClass:
            pass

        self.assertIsNotNone(self.decoder.get_default_type_decoder(datetime.date))
        self.assertIsNone(self.decoder.get_default_type_decoder(SomeUnknownClass))


class TestFlattenedDataJsonSerializer(unittest.TestCase):

    def setUp(self) -> None:
        int_attr_info = InstanceAttributeInfo(
            parent_info=None,
            path_from_root=(),
            origin_annotated_type=int,
            description_annotation=None,
            volatile_annotation=None,
            instrument_info_parameter_annotation=None,
            has_default=False,
            default_value=None,
            is_immutable=False
        )
        date_attr_info = InstanceAttributeInfo(
            parent_info=None,
            path_from_root=(),
            origin_annotated_type=datetime.date,
            description_annotation=None,
            volatile_annotation=None,
            instrument_info_parameter_annotation=None,
            has_default=False,
            default_value=None,
            is_immutable=False
        )
        dyn_enum_attr_info = InstanceAttributeInfo(
            parent_info=None,
            path_from_root=(),
            origin_annotated_type=DynamicEnumType,
            description_annotation=None,
            volatile_annotation=None,
            instrument_info_parameter_annotation=None,
            has_default=False,
            default_value=None,
            is_immutable=False
        )

        flattened_instance_analyzer = FakeFlattenedInstanceAnalyzer(
            fake_root_data_class=type(None),
            fake_flattened_attrs_info={'int_value': int_attr_info,
                                       'date_value': date_attr_info,
                                       'dyn_enum_value': dyn_enum_attr_info},
            fake_dynamic_enum_types=(DynamicEnumType,)
        )

        self.dynamic_enum_value = DynamicEnumType(42, 'd42')
        parameter_values_storage = FakeDownloadParameterValuesStorage(
            fake_data={DynamicEnumType: ((42, '42', self.dynamic_enum_value),)}
        )

        self.serializer = FlattenedDataJsonSerializer(
            flattened_instance_analyzer=flattened_instance_analyzer,
            parameter_values_storage=parameter_values_storage)

    def test_serialize_flattened_data_Success(self):
        for flattened_data, expected_json_str in (
                ({}, '{}'),
                ({'int_value': 42}, '{"int_value":42}'),
                ({'date_value': datetime.date(1900, 12, 31)}, '{"date_value":"1900-12-31"}'),
                ({'dyn_enum_value': self.dynamic_enum_value}, '{"dyn_enum_value":42}'),
        ):
            json_str_data = self.serializer.serialize_flattened_data(flattened_data)

            self.assertEqual(expected_json_str, json_str_data)

    def test_deserialize_flattened_data_Success(self):
        for expected_flattened_data, json_str, decode_dynamic_enums in (
                ({}, '{}', True),
                ({'int_value': 42}, '{"int_value":42}', True),
                ({'date_value': datetime.date(1900, 12, 31)}, '{"date_value":"1900-12-31"}', True),
                ({'dyn_enum_value': self.dynamic_enum_value}, '{"dyn_enum_value":42}', True),
                ({'dyn_enum_value': 42}, '{"dyn_enum_value":42}', False),
        ):
            data = self.serializer.deserialize_flattened_data(json_str, decode_dynamic_enums)

            self.assertEqual(expected_flattened_data, data)
