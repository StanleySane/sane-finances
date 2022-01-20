#!/usr/bin/python
# -*- coding: utf-8 -*-
import collections
import dataclasses
import datetime
import decimal
import enum
import unittest
import typing

from sane_finances.inspection.analyzers import (
    FULL_PATH_DELIMITER, get_attr_by_path, get_all_builtins, get_full_path, get_by_full_path,
    is_namedtuple, is_namedtuple_class,
    InstanceBuilderArgFactory, InstanceBuilder, FlattenedAnnotatedInstanceAnalyzer,
    InstanceFlattener, InstanceFactoryDataConverter)
from sane_finances.annotations import Description, Volatile, LEGACY_ANNOTATIONS
from sane_finances.sources.inspection import InstrumentInfoParameter

if LEGACY_ANNOTATIONS:
    from sane_finances.annotations import Annotated
else:
    from typing import Annotated

from .fakes import FakeDownloadParameterValuesStorage
from . import fakes


@dataclasses.dataclass
class DynamicEnumType:
    enum_id: int
    enum_value: str


class SomeEnum(enum.Enum):
    ONE = 'one'
    TWO = 'two'


class SubNestedNative:
    value: str
    date: Annotated[datetime.date, 'Sample of complex annotation']
    moment: datetime.datetime
    enum_val: SomeEnum
    number: decimal.Decimal
    lst: typing.List[str]  # sample of generic alias
    dct: typing.Dict

    def __init__(
            self,
            value: str,
            date: datetime.date,
            moment: datetime.datetime,
            enum_val: SomeEnum,
            number: decimal.Decimal,
            lst: typing.List[str],
            dct: typing.Dict):
        if not isinstance(value, str):
            raise TypeError("'value' is not str")
        if not isinstance(date, datetime.date):
            raise TypeError("'date' is not date")
        if not isinstance(moment, datetime.datetime):
            raise TypeError("'moment' is not datetime")
        if not isinstance(enum_val, SomeEnum):
            raise TypeError("'enum_val' is not SomeEnum")
        if not isinstance(number, decimal.Decimal):
            raise TypeError("'number' is not Decimal")
        if not isinstance(lst, list):
            raise TypeError("'lst' is not list")
        if not isinstance(dct, dict):
            raise TypeError("'dct' is not dict")

        self.value = value
        self.date = date
        self.moment = moment
        self.enum_val = enum_val
        self.number = number
        self.lst = lst
        self.dct = dct

    def __eq__(self, other):
        if isinstance(other, SubNestedNative):
            return (self.value == other.value
                    and self.date == other.date
                    and self.moment == other.moment
                    and self.enum_val == other.enum_val
                    and self.number == other.number
                    and self.lst == other.lst
                    and self.dct == other.dct)
        return False


class SubNestedNamedTuple(typing.NamedTuple):
    value: str
    date: datetime.date
    moment: datetime.datetime
    enum_val: SomeEnum
    number: decimal.Decimal
    lst: typing.List[str]
    dct: typing.Dict


@dataclasses.dataclass
class SubNestedDataclass:
    value: str
    date: datetime.date
    moment: datetime.datetime
    enum_val: SomeEnum
    number: decimal.Decimal
    lst: typing.List[str]
    dct: typing.Dict


class NestedNative:
    sub_nested1: SubNestedNative
    sub_nested2: SubNestedNative
    dynamic_enum: DynamicEnumType
    not_nested: str

    def __init__(
            self,
            sub_nested1: SubNestedNative,
            sub_nested2: SubNestedNative,
            dynamic_enum: DynamicEnumType,
            not_nested: str):
        self.sub_nested1 = sub_nested1
        self.sub_nested2 = sub_nested2
        self.dynamic_enum = dynamic_enum
        self.not_nested = not_nested

    def __eq__(self, other):
        if isinstance(other, NestedNative):
            return (self.sub_nested1 == other.sub_nested1
                    and self.sub_nested2 == other.sub_nested2
                    and self.dynamic_enum == other.dynamic_enum
                    and self.not_nested == other.not_nested)
        return False


class NestedNamedTuple(typing.NamedTuple):
    sub_nested1: SubNestedNamedTuple
    sub_nested2: SubNestedNative
    dynamic_enum: DynamicEnumType
    not_nested: str


@dataclasses.dataclass
class NestedDataclass:
    sub_nested1: SubNestedNamedTuple
    sub_nested2: SubNestedDataclass
    dynamic_enum: DynamicEnumType
    not_nested: str


class RootNative:
    nested1: NestedNative
    nested2: NestedNative
    not_nested: str

    def __init__(self, nested1: NestedNative, nested2: NestedNative, not_nested: str):
        self.nested1 = nested1
        self.nested2 = nested2
        self.not_nested = not_nested

    def __eq__(self, other):
        if isinstance(other, RootNative):
            return (self.nested1 == other.nested1
                    and self.nested2 == other.nested2
                    and self.not_nested == other.not_nested)
        return False


class RootNamedTuple(typing.NamedTuple):
    nested1: NestedNamedTuple
    nested2: NestedNative
    not_nested: str


@dataclasses.dataclass
class RootDataclass:
    nested1: NestedNamedTuple
    nested2: NestedDataclass
    not_nested: str


class CommonTestCaseMixin:

    def get_flattened_data(
            self,
            src: typing.Dict[str, typing.Any],
            dst: typing.Dict[str, typing.Any],
            prefix: str = None):

        for name, attr_value in src.items():
            current_prefix = name if prefix is None else prefix + '_' + name
            if isinstance(attr_value, dict) and name != 'dct':
                self.get_flattened_data(attr_value, dst, current_prefix)
            else:
                assert current_prefix not in dst

                if isinstance(attr_value, enum.Enum):
                    attr_value = attr_value.value

                dst[current_prefix] = attr_value

    # noinspection PyAttributeOutsideInit
    def create_common_data(self):
        date1 = datetime.date(1900, 12, 31)
        moment1 = datetime.datetime.combine(date1, datetime.time.max)
        date2 = datetime.date(2000, 12, 31)
        moment2 = datetime.datetime.combine(date2, datetime.time.max)
        number1 = decimal.Decimal('42.42')
        number2 = number1 * 42

        kwargs1 = {'date': date1, 'moment': moment1, 'enum_val': SomeEnum.ONE, 'number': number1, 'lst': [], 'dct': {}}
        kwargs2 = {'date': date2, 'moment': moment2, 'enum_val': SomeEnum.TWO, 'number': number2, 'lst': [], 'dct': {}}
        kwargs_a = dict(**kwargs1, value='a')
        kwargs_b = dict(**kwargs2, value='b')
        kwargs_d = dict(**kwargs1, value='d')
        kwargs_e = dict(**kwargs2, value='e')

        self.build_data: typing.Dict[str, typing.Any] = {
            'nested1': {'sub_nested1': kwargs_a,
                        'sub_nested2': kwargs_b,
                        'dynamic_enum': 1,
                        'not_nested': 'c'},
            'nested2': {'sub_nested1': kwargs_d,
                        'sub_nested2': kwargs_e,
                        'dynamic_enum': 2,
                        'not_nested': 'f'},
            'not_nested': 'g'
        }

        self.flattened_data = {}
        self.get_flattened_data(self.build_data, self.flattened_data)
        self.flattened_attrs_names = set(self.flattened_data.keys())

        dynamic_enum_values = {1: DynamicEnumType(1, 'd1'), 2: DynamicEnumType(2, 'd2')}
        dynamic_enum_types = {DynamicEnumType: tuple((v.enum_id, str(v.enum_id), v)
                                                     for v
                                                     in dynamic_enum_values.values())}

        self.param_values_storage = FakeDownloadParameterValuesStorage(dynamic_enum_types)

        self.args_factories = collections.OrderedDict({
            DynamicEnumType: InstanceBuilderArgFactory.simple(lambda t, v: dynamic_enum_values[v])})

        self.native_instance = RootNative(
            nested1=NestedNative(
                sub_nested1=SubNestedNative(**kwargs_a),
                sub_nested2=SubNestedNative(**kwargs_b),
                dynamic_enum=DynamicEnumType(1, 'd1'),
                not_nested='c'),
            nested2=NestedNative(
                sub_nested1=SubNestedNative(**kwargs_d),
                sub_nested2=SubNestedNative(**kwargs_e),
                dynamic_enum=DynamicEnumType(2, 'd2'),
                not_nested='f'),
            not_nested='g')

        self.named_tuple_instance = RootNamedTuple(
            nested1=NestedNamedTuple(
                sub_nested1=SubNestedNamedTuple(**kwargs_a),
                sub_nested2=SubNestedNative(**kwargs_b),
                dynamic_enum=DynamicEnumType(1, 'd1'),
                not_nested='c'),
            nested2=NestedNative(
                sub_nested1=SubNestedNative(**kwargs_d),
                sub_nested2=SubNestedNative(**kwargs_e),
                dynamic_enum=DynamicEnumType(2, 'd2'),
                not_nested='f'),
            not_nested='g')

        self.dataclass_instance = RootDataclass(
            nested1=NestedNamedTuple(
                sub_nested1=SubNestedNamedTuple(**kwargs_a),
                sub_nested2=SubNestedNative(**kwargs_b),
                dynamic_enum=DynamicEnumType(1, 'd1'),
                not_nested='c'),
            nested2=NestedDataclass(
                sub_nested1=SubNestedNamedTuple(**kwargs_d),
                sub_nested2=SubNestedDataclass(**kwargs_e),
                dynamic_enum=DynamicEnumType(2, 'd2'),
                not_nested='f'),
            not_nested='g')


class TestModuleFunctions(unittest.TestCase, CommonTestCaseMixin):

    def setUp(self) -> None:
        self.create_common_data()

    def test_get_attr_by_path_Success(self):
        expected_result = self.native_instance.nested1.sub_nested1.value

        result = get_attr_by_path(self.native_instance, ('nested1', 'sub_nested1', 'value'))

        self.assertEqual(expected_result, result)

    def test_get_all_builtins_Success(self):
        all_builtins = get_all_builtins()

        self.assertTrue(str in all_builtins)

        all_builtins = get_all_builtins()

        self.assertTrue(int in all_builtins)

    def test_get_full_path_Success(self):
        class_to_test = RootNative
        expected_result = __name__ + FULL_PATH_DELIMITER + class_to_test.__name__
        full_path = get_full_path(class_to_test)

        self.assertEqual(expected_result, full_path)

    def test_get_full_path_RaiseWithWrongObject(self):
        with self.assertRaisesRegex(ValueError, "has no attribute '__module__'"):
            _ = get_full_path(42)

        # Only modules have no attribute __qualname__
        # but so no attribute __module__ therefore add it explicitly (for code coverage purposes only)
        fakes.__module__ = 'fakes'
        with self.assertRaisesRegex(ValueError, "has no attribute '__qualname__'"):
            _ = get_full_path(fakes)

    def test_get_by_full_path_Success(self):
        expected_class = RootNative
        full_path = __name__ + FULL_PATH_DELIMITER + expected_class.__name__
        result = get_by_full_path(full_path)

        self.assertIs(result, expected_class)

        full_path = 'WRONG_MODULE' + FULL_PATH_DELIMITER + expected_class.__name__
        result = get_by_full_path(full_path)

        self.assertIsNone(result)

    def test_is_namedtuple_Success(self):
        self.assertTrue(is_namedtuple(self.named_tuple_instance))
        self.assertFalse(is_namedtuple(self.native_instance))
        self.assertFalse(is_namedtuple(self.dataclass_instance))

    def test_is_namedtuple_class_Success(self):
        self.assertTrue(is_namedtuple_class(RootNamedTuple))
        self.assertFalse(is_namedtuple_class(RootNative))
        self.assertFalse(is_namedtuple_class(RootDataclass))


class TestInstanceBuilderArgFactory(unittest.TestCase):

    def test_simple_Success(self):
        simple_arg_factory = InstanceBuilderArgFactory.simple(lambda t, v: v)

        self.assertTrue(simple_arg_factory.is_simple)
        self.assertFalse(simple_arg_factory.is_complex)

    def test_complex_Success(self):
        complex_arg_factory = InstanceBuilderArgFactory.complex(RootNative)

        self.assertTrue(complex_arg_factory.is_complex)
        self.assertFalse(complex_arg_factory.is_simple)

    def test_RaiseWhenWrongArguments(self):
        with self.assertRaises(ValueError):
            _ = InstanceBuilderArgFactory(simple_converter=lambda t, v: v, complex_factory=RootNative)

        with self.assertRaises(ValueError):
            _ = InstanceBuilderArgFactory(simple_converter=None, complex_factory=None)

        with self.assertRaises(ValueError):
            # noinspection PyTypeChecker
            _ = InstanceBuilderArgFactory.simple(None)

        with self.assertRaises(ValueError):
            # noinspection PyTypeChecker
            _ = InstanceBuilderArgFactory.complex(None)


class TestInstanceBuilder(unittest.TestCase, CommonTestCaseMixin):

    def setUp(self) -> None:
        self.create_common_data()

    def test_build_instance_SuccessWithArgsFactories(self):
        # test using args_factories argument
        for root_factory, expected_instance in ((RootNative, self.native_instance),
                                                (RootNamedTuple, self.named_tuple_instance),
                                                (RootDataclass, self.dataclass_instance)):
            builder = InstanceBuilder(root_factory, args_factories=self.args_factories)
            instance = builder.build_instance(self.build_data)

            self.assertEqual(instance, expected_instance)

    def test_build_instance_SuccessWithComplexArgsFactories(self):
        # test using args_factories argument
        args_factories = collections.OrderedDict(self.args_factories)

        # in spite of the fact that SubNestedNative successfully treated by default algorithm
        # here we explicitly register it as a complex type, just for testing purposes
        args_factories[SubNestedNative] = InstanceBuilderArgFactory.complex(SubNestedNative)

        for root_factory, expected_instance in ((RootNative, self.native_instance),
                                                (RootNamedTuple, self.named_tuple_instance),
                                                (RootDataclass, self.dataclass_instance)):
            builder = InstanceBuilder(root_factory, args_factories=args_factories)
            instance = builder.build_instance(self.build_data)

            self.assertEqual(instance, expected_instance)

    def test_build_instance_SuccessWithFullDynamicEnumValues(self):
        modified_build_data = self.build_data.copy()
        self.assertEqual(modified_build_data['nested1']['dynamic_enum'], 1)
        # replace key of dynamic enum with its full typed value
        modified_build_data['nested1']['dynamic_enum'] = DynamicEnumType(1, 'd1')

        for root_factory, expected_instance in ((RootNative, self.native_instance),
                                                (RootNamedTuple, self.named_tuple_instance),
                                                (RootDataclass, self.dataclass_instance)):
            builder = InstanceBuilder(root_factory, parameter_values_storage=self.param_values_storage)
            instance = builder.build_instance(modified_build_data)

            self.assertEqual(instance, expected_instance)

    def test_build_instance_SuccessWithUnknownDynamicEnumValues(self):
        modified_build_data = self.build_data.copy()
        self.assertEqual(modified_build_data['nested2']['dynamic_enum'], 2)
        # replace key of dynamic enum with some unknown value
        unknown_value = 'UNKNOWN'
        modified_build_data['nested2']['dynamic_enum'] = unknown_value

        # Here we assume that InstanceBuilder successfully builds target instances with unknown dynamic enum values
        # just passing such values to instance factory.
        # The factory decides whether verify such value (and raise exception) or not.
        # Here we know that our factories does not verify dynamic enum values and not raises in such cases.
        # Otherwise, we would rewrite this test case and use self.assertRaises instead of self.assertEqual.

        self.native_instance.nested2.dynamic_enum = unknown_value
        self.named_tuple_instance.nested2.dynamic_enum = unknown_value
        self.dataclass_instance.nested2.dynamic_enum = unknown_value

        for root_factory, expected_instance in ((RootNative, self.native_instance),
                                                (RootNamedTuple, self.named_tuple_instance),
                                                (RootDataclass, self.dataclass_instance)):
            builder = InstanceBuilder(root_factory, parameter_values_storage=self.param_values_storage)
            instance = builder.build_instance(modified_build_data)

            self.assertEqual(instance, expected_instance)

    def test_build_instance_SuccessWithParameterValuesStorage(self):
        # test using parameter_values_storage argument
        for root_factory, expected_instance in ((RootNative, self.native_instance),
                                                (RootNamedTuple, self.named_tuple_instance),
                                                (RootDataclass, self.dataclass_instance)):
            builder = InstanceBuilder(root_factory, parameter_values_storage=self.param_values_storage)
            instance = builder.build_instance(self.build_data)

            self.assertEqual(instance, expected_instance)

    def test_build_instance_SuccessWithVariableArguments(self):
        class GoodClass:
            value: int

            # noinspection PyUnusedLocal
            def __init__(self, value: int, *args, **kwargs):
                self.value = value

            def __eq__(self, other):
                if isinstance(other, GoodClass):
                    return self.value == other.value
                return False

        expected_instance = GoodClass(42)
        builder = InstanceBuilder(GoodClass)
        instance = builder.build_instance({'value': expected_instance.value})

        self.assertEqual(instance, expected_instance)

    def test_RaiseForWrongFactory(self):
        with self.assertRaisesRegex(TypeError, 'is not callable'):
            # noinspection PyTypeChecker
            _ = InstanceBuilder(None)

        with self.assertRaisesRegex(TypeError, 'is not callable'):
            # noinspection PyTypeChecker
            _ = InstanceBuilder(42)

    def test_RaiseForNotAnnotatedAttribute(self):
        class BadClass:
            # 'value' not annotated on class level
            def __init__(self, value: str):  # even if annotated in factory
                self.value = value

        with self.assertRaisesRegex(ValueError, 'is not annotated'):
            _ = InstanceBuilder(BadClass)

    def test_RaiseForBadAnnotatedAttribute(self):
        class BadClass:
            # 'value' IS annotated on class level
            # but with annotation that can't be used as factory, i.e. not callable
            value: 42

            def __init__(self, value):
                self.value = value

        with self.assertRaisesRegex(ValueError, 'is not callable'):
            _ = InstanceBuilder(BadClass)

    def test_build_instance_RaiseForUnknownAttr(self):
        unknown_attr_name = 'unknown'
        wrong_build_data = self.build_data.copy()
        wrong_build_data[unknown_attr_name] = 42

        for root_factory in (RootNative, RootNamedTuple, RootDataclass):
            builder = InstanceBuilder(root_factory, args_factories=self.args_factories)

            with self.assertRaisesRegex(ValueError, 'Not found.*' + unknown_attr_name):
                _ = builder.build_instance(wrong_build_data)

    def test_build_instance_RaiseForWrongAttrType(self):
        wrong_build_data = self.build_data.copy()
        # change dictionary representation for complex type to something else
        wrong_build_data['nested1'] = 42

        for root_factory in (RootNative, RootNamedTuple, RootDataclass):
            builder = InstanceBuilder(root_factory, args_factories=self.args_factories)

            with self.assertRaisesRegex(ValueError, 'dict expected'):
                _ = builder.build_instance(wrong_build_data)


class TestFlattenedAnnotatedInstanceAnalyzer(unittest.TestCase, CommonTestCaseMixin):

    def setUp(self) -> None:
        self.create_common_data()

    def test_get_flattened_attrs_info_Success(self):
        for root_data_class in (RootNative, RootNamedTuple, RootDataclass):
            analyzer = FlattenedAnnotatedInstanceAnalyzer(
                root_data_class,
                dynamic_enum_type_manager=self.param_values_storage)
            flattened_attrs_info = analyzer.get_flattened_attrs_info()
            flattened_attrs_names = set(flattened_attrs_info.keys())

            self.assertEqual(flattened_attrs_names, self.flattened_attrs_names)

    def test_dynamic_enum_types_Success(self):
        for root_data_class in (RootNative, RootNamedTuple, RootDataclass):
            expected_dynamic_enum_types = tuple(self.param_values_storage.get_all_managed_types())
            analyzer = FlattenedAnnotatedInstanceAnalyzer(
                root_data_class,
                dynamic_enum_type_manager=self.param_values_storage)
            dynamic_enum_types = tuple(analyzer.dynamic_enum_types)

            self.assertSequenceEqual(dynamic_enum_types, expected_dynamic_enum_types)

        # when no dynamic enum type manager result is empty
        analyzer = FlattenedAnnotatedInstanceAnalyzer(str)
        dynamic_enum_types = tuple(analyzer.dynamic_enum_types)

        self.assertSequenceEqual(dynamic_enum_types, ())

    def test_get_flattened_attrs_info_WithNoHintsReturnEmpty(self):
        class NoHints:
            def __int__(self, val):
                self.val = val

        analyzer = FlattenedAnnotatedInstanceAnalyzer(NoHints)
        flattened_attrs_info = analyzer.get_flattened_attrs_info()

        self.assertEqual(flattened_attrs_info, {})

    def test_get_flattened_attrs_info_SuccessWithSpecialAnnotation(self):
        expected_description = "Description"

        class SpecialAnnotations:
            attr: Annotated[int,
                            Description(description=expected_description),
                            Volatile(generator=lambda ctx: 42),
                            InstrumentInfoParameter()]

        analyzer = FlattenedAnnotatedInstanceAnalyzer(SpecialAnnotations)
        flattened_attrs_info = analyzer.get_flattened_attrs_info()

        self.assertTrue('attr' in flattened_attrs_info)

        attr_info = flattened_attrs_info['attr']

        self.assertIsNone(attr_info.parent_info)
        self.assertEqual(attr_info.path_from_root, ('attr',))
        self.assertIs(attr_info.origin_annotated_type, int)
        self.assertIsNotNone(attr_info.description_annotation)
        self.assertEqual(attr_info.description_annotation.description, expected_description)
        self.assertIsNotNone(attr_info.volatile_annotation)
        self.assertIsNotNone(attr_info.instrument_info_parameter_annotation)
        self.assertIs(attr_info.has_default, False)
        self.assertTrue(attr_info.is_immutable)

    def test_get_flattened_attrs_info_SuccessDuplicatedAttrNamesWithIndex(self):
        class SomeClass:
            attr: int

        class RootClass:
            some_attr: int
            some: SomeClass

        analyzer = FlattenedAnnotatedInstanceAnalyzer(RootClass)
        flattened_attrs_info = analyzer.get_flattened_attrs_info()

        self.assertEqual(len(flattened_attrs_info), 2)
        self.assertTrue('some_attr' in flattened_attrs_info)
        self.assertTrue('some_attr_2' in flattened_attrs_info)

    def test_RaiseWhenDuplicatedAttrNames(self):
        class SomeClass:
            attr: int

        class RootClass:
            some_attr: int
            some_attr_2: int
            some: SomeClass

        with self.assertRaisesRegex(ValueError, 'Field name.*?duplicated'):
            # allow only one step of adding suffix: _2
            # suffix _3 not allowed
            _ = FlattenedAnnotatedInstanceAnalyzer(RootClass, max_flattened_attr_name_suffix_index=2)

    def test_RaiseWhenWrongRoot(self):
        with self.assertRaisesRegex(TypeError, 'is not class'):
            _ = FlattenedAnnotatedInstanceAnalyzer(None)


class TestInstanceFlattener(unittest.TestCase, CommonTestCaseMixin):

    def setUp(self) -> None:
        self.create_common_data()

    def test_get_flattened_data_from_Success(self):
        for root_data_class, instance in ((RootNative, self.native_instance),
                                          (RootNamedTuple, self.named_tuple_instance),
                                          (RootDataclass, self.dataclass_instance)):
            # assume that FlattenedAnnotatedInstanceAnalyzer is absolutely correct and fully tested
            analyzer = FlattenedAnnotatedInstanceAnalyzer(
                root_data_class,
                dynamic_enum_type_manager=self.param_values_storage)
            flattener = InstanceFlattener(
                flattened_instance_analyzer=analyzer,
                dynamic_enum_type_manager=self.param_values_storage)

            flattened_data = flattener.get_flattened_data_from(instance)

            self.assertEqual(flattened_data, self.flattened_data)

            # for None return empty
            flattened_data = flattener.get_flattened_data_from(None)

            self.assertEqual(flattened_data, {})

    def test_get_flattened_data_from_SuccessWithVolatile(self):
        annotated_value = 42

        @dataclasses.dataclass
        class SomeClass:
            attr: Annotated[int, Volatile(generator=lambda ctx: 0, stub_value=annotated_value)]

        # assume that FlattenedAnnotatedInstanceAnalyzer is absolutely correct and fully tested
        analyzer = FlattenedAnnotatedInstanceAnalyzer(SomeClass)
        flattener = InstanceFlattener(flattened_instance_analyzer=analyzer)
        actual_value = -1
        instance = SomeClass(attr=actual_value)

        flattened_data = flattener.get_flattened_data_from(instance)

        self.assertEqual({'attr': annotated_value}, flattened_data)

        flattened_data = flattener.get_flattened_data_from(instance, stub_volatile=False)

        self.assertEqual({'attr': actual_value}, flattened_data)

    def test_get_flattened_data_from_SuccessWithDefault(self):
        default_value = 42

        @dataclasses.dataclass
        class SomeClass:
            attr: int = default_value

        # assume that FlattenedAnnotatedInstanceAnalyzer is absolutely correct and fully tested
        analyzer = FlattenedAnnotatedInstanceAnalyzer(SomeClass)
        flattener = InstanceFlattener(flattened_instance_analyzer=analyzer)
        actual_value = -1
        instance = SomeClass(attr=actual_value)
        flattened_data = flattener.get_flattened_data_from(instance)

        self.assertEqual({'attr': default_value}, flattened_data)

        flattened_data = flattener.get_flattened_data_from(instance, stub_volatile=False)

        self.assertEqual({'attr': actual_value}, flattened_data)

    def test_get_flattened_data_from_RaiseWhenWringInstance(self):
        for root_data_class, wrong_instance in ((RootNative, 42),
                                                (RootNamedTuple, 42),
                                                (RootDataclass, 42)):
            # assume that FlattenedAnnotatedInstanceAnalyzer is absolutely correct and fully tested
            analyzer = FlattenedAnnotatedInstanceAnalyzer(
                root_data_class,
                dynamic_enum_type_manager=self.param_values_storage)
            flattener = InstanceFlattener(
                flattened_instance_analyzer=analyzer,
                dynamic_enum_type_manager=self.param_values_storage)

            with self.assertRaisesRegex(ValueError, 'is not instance of'):
                _ = flattener.get_flattened_data_from(wrong_instance)


class TestInstanceFactoryDataConverter(unittest.TestCase, CommonTestCaseMixin):

    def setUp(self) -> None:
        self.create_common_data()

    def test_get_instance_factory_data_Success(self):
        for root_data_class, expected_instance in ((RootNative, self.native_instance),
                                                   (RootNamedTuple, self.named_tuple_instance),
                                                   (RootDataclass, self.dataclass_instance)):
            # assume that FlattenedAnnotatedInstanceAnalyzer and InstanceBuilder are absolutely correct and fully tested
            analyzer = FlattenedAnnotatedInstanceAnalyzer(
                root_data_class,
                dynamic_enum_type_manager=self.param_values_storage)
            builder = InstanceBuilder(root_data_class, parameter_values_storage=self.param_values_storage)

            converter = InstanceFactoryDataConverter(flattened_instance_analyzer=analyzer)
            factory_data = converter.get_instance_factory_data(self.flattened_data)

            instance = builder.build_instance(factory_data)

            self.assertEqual(expected_instance, instance)

    def test_get_instance_factory_data_SuccessWithVolatile(self):
        generated_value = 42
        actual_value = -1
        self.assertNotEqual(actual_value, generated_value)

        @dataclasses.dataclass
        class NestedClass:
            attr: Annotated[int, Volatile(generator=lambda ctx: generated_value, stub_value=0)]

        @dataclasses.dataclass
        class SomeClass:
            nested: NestedClass

        flattened_data = {'nested_attr': actual_value}
        expected_factory_data_generated = {'nested': {'attr': generated_value}}
        expected_factory_data_not_generated = {'nested': {'attr': actual_value}}

        self.assertNotEqual(expected_factory_data_generated, expected_factory_data_not_generated)

        # assume that FlattenedAnnotatedInstanceAnalyzer is absolutely correct and fully tested
        analyzer = FlattenedAnnotatedInstanceAnalyzer(SomeClass)
        converter = InstanceFactoryDataConverter(flattened_instance_analyzer=analyzer)

        factory_data = converter.get_instance_factory_data(flattened_data, generate_volatiles=True)
        self.assertEqual(expected_factory_data_generated, factory_data)

        factory_data = converter.get_instance_factory_data(flattened_data, generate_volatiles=False)
        self.assertEqual(expected_factory_data_not_generated, factory_data)

    def test_get_instance_factory_data_RaiseWithUnknownAttrName(self):
        class SomeClass:
            attr: int

        wrong_flattened_data = {'WRONG_ATTR': 42}

        # assume that FlattenedAnnotatedInstanceAnalyzer is absolutely correct and fully tested
        analyzer = FlattenedAnnotatedInstanceAnalyzer(SomeClass)
        converter = InstanceFactoryDataConverter(flattened_instance_analyzer=analyzer)

        with self.assertRaisesRegex(ValueError, 'Not found'):
            _ = converter.get_instance_factory_data(wrong_flattened_data)

    def test_get_instance_factory_data_RaiseWithBadAttrInfo(self):
        class SomeClass:
            attr: int

        flattened_data = {'attr': 42}

        # assume that FlattenedAnnotatedInstanceAnalyzer is absolutely correct and fully tested
        analyzer = FlattenedAnnotatedInstanceAnalyzer(SomeClass)
        # spoil info data
        analyzer._flattened_attrs_info['attr'] = analyzer._flattened_attrs_info['attr']._replace(path_from_root=())

        converter = InstanceFactoryDataConverter(flattened_instance_analyzer=analyzer)

        with self.assertRaisesRegex(ValueError, 'Path is empty'):
            _ = converter.get_instance_factory_data(flattened_data)

    def test_get_instance_factory_data_RaiseWithDuplicatedAttrInfo(self):
        class SomeClass:
            attr1: int
            attr2: int

        flattened_data = {'attr1': 42, 'attr2': 42}

        # assume that FlattenedAnnotatedInstanceAnalyzer is absolutely correct and fully tested
        analyzer = FlattenedAnnotatedInstanceAnalyzer(SomeClass)
        # spoil info data
        for attr_name in ('attr1', 'attr2'):
            analyzer._flattened_attrs_info[attr_name] = \
                analyzer._flattened_attrs_info[attr_name]._replace(path_from_root=('attr',))

        converter = InstanceFactoryDataConverter(flattened_instance_analyzer=analyzer)

        with self.assertRaisesRegex(ValueError, 'Possible duplication'):
            _ = converter.get_instance_factory_data(flattened_data)
