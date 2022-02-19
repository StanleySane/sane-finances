#!/usr/bin/python
# -*- coding: utf-8 -*-
import dataclasses
import datetime
import decimal
import enum
import inspect
import typing
import unittest

from sane_finances.inspection import analyzers
from sane_finances.annotations import LEGACY_ANNOTATIONS
from sane_finances.sources.base import (
    InstrumentExporterFactory, DownloadParametersFactory, InstrumentHistoryDownloadParameters,
    DownloadParameterValuesStorage)
from sane_finances.sources.generic import get_all_instrument_exporters
from ..communication.fakes import FakeDownloader

if LEGACY_ANNOTATIONS:
    from sane_finances.annotations import get_type_hints, get_args, get_origin
else:
    from typing import get_type_hints, get_args, get_origin


class CommonTestCases:  # hide test cases from unittest discovery

    class CommonDownloadParametersFactoryTests(unittest.TestCase):

        def get_download_parameters_factory(self) -> DownloadParametersFactory:
            raise NotImplementedError

        def get_generate_history_download_parameters_from_expected_result_with_none(self) \
                -> InstrumentHistoryDownloadParameters:
            raise NotImplementedError

        def get_download_parameter_values_storage(self) -> DownloadParameterValuesStorage:
            raise NotImplementedError

        def test_download_history_parameters_class_Success(self):
            factory = self.get_download_parameters_factory()

            self.assertTrue(inspect.isclass(factory.download_history_parameters_class))

        def test_download_history_parameters_class_IsAnalyzable(self):
            factory = self.get_download_parameters_factory()
            download_parameter_values_storage = self.get_download_parameter_values_storage()

            _ = analyzers.FlattenedAnnotatedInstanceAnalyzer(
                factory.download_history_parameters_class,
                download_parameter_values_storage,
                '')

        def test_download_history_parameters_factory_Success(self):
            factory = self.get_download_parameters_factory()

            self.assertTrue(callable(factory.download_history_parameters_factory))

        def test_download_history_parameters_factory_IsAnalyzable(self):
            factory = self.get_download_parameters_factory()
            download_parameter_values_storage = self.get_download_parameter_values_storage()

            _ = analyzers.InstanceBuilder(
                factory.download_history_parameters_factory,
                download_parameter_values_storage)

        def test_download_info_parameters_class_Success(self):
            factory = self.get_download_parameters_factory()

            self.assertTrue(inspect.isclass(factory.download_info_parameters_class))

        def test_download_info_parameters_class_IsAnalyzable(self):
            factory = self.get_download_parameters_factory()
            download_parameter_values_storage = self.get_download_parameter_values_storage()

            _ = analyzers.FlattenedAnnotatedInstanceAnalyzer(
                factory.download_info_parameters_class,
                download_parameter_values_storage,
                '')

        def test_download_info_parameters_factory_Success(self):
            factory = self.get_download_parameters_factory()

            self.assertTrue(callable(factory.download_info_parameters_factory))

        def test_download_info_parameters_factory_IsAnalyzable(self):
            factory = self.get_download_parameters_factory()
            download_parameter_values_storage = self.get_download_parameter_values_storage()

            _ = analyzers.InstanceBuilder(
                factory.download_info_parameters_factory,
                download_parameter_values_storage)

        def test_generate_history_download_parameters_from_SuccessWithNone(self):
            factory = self.get_download_parameters_factory()
            expected_result = self.get_generate_history_download_parameters_from_expected_result_with_none()

            result = factory.generate_history_download_parameters_from(None, None, None)

            self.assertEqual(result, expected_result)

    class CommonInstrumentExporterFactoryTests(unittest.TestCase):

        def get_exporter_factory(self) -> InstrumentExporterFactory:
            raise NotImplementedError

        def is_dynamic_enum_type_manager_singleton(self):
            raise NotImplementedError

        def is_download_parameters_factory_singleton(self):
            raise NotImplementedError

        def test_create_history_values_exporter_Success(self):
            factory = self.get_exporter_factory()
            result = factory.create_history_values_exporter(FakeDownloader(None))

            self.assertIsNotNone(result)

        def test_create_info_exporter_Success(self):
            factory = self.get_exporter_factory()
            result = factory.create_info_exporter(FakeDownloader(None))

            self.assertIsNotNone(result)

        def test_create_download_parameter_values_storage_Success(self):
            factory = self.get_exporter_factory()
            result = factory.create_download_parameter_values_storage(FakeDownloader(None))

            self.assertIsNotNone(result)

        def test_create_api_actuality_checker_Success(self):
            factory = self.get_exporter_factory()
            result = factory.create_api_actuality_checker(FakeDownloader(None))

            self.assertIsNotNone(result)

        def test_dynamic_enum_type_manager_Success(self):
            factory = self.get_exporter_factory()
            result = factory.dynamic_enum_type_manager

            self.assertIsNotNone(result)

            if self.is_dynamic_enum_type_manager_singleton():
                new_result = factory.dynamic_enum_type_manager

                self.assertIs(new_result, result)

        def test_download_parameters_factory_Success(self):
            factory = self.get_exporter_factory()
            result = factory.download_parameters_factory

            self.assertIsNotNone(result)

            if self.is_download_parameters_factory_singleton():
                new_result = factory.download_parameters_factory

                self.assertIs(new_result, result)

    class CommonSourceRegisterTests(unittest.TestCase):

        def get_source_instrument_exporter_factory(self) -> typing.Type:
            raise NotImplementedError

        def test_settings(self):
            source_instrument_exporter_factory = self.get_source_instrument_exporter_factory()

            self.assertTrue(inspect.isclass(source_instrument_exporter_factory))
            self.assertTrue(issubclass(source_instrument_exporter_factory, InstrumentExporterFactory))

        def test_source_register(self):
            # at first read all available exporters
            all_exporters = get_all_instrument_exporters()

            # and only after that import testing source factory
            source_instrument_exporter_factory = self.get_source_instrument_exporter_factory()

            testing_factories = [
                registry
                for registry
                in all_exporters
                if isinstance(registry.factory, source_instrument_exporter_factory)
            ]

            self.assertEqual(len(testing_factories), 1)

    class CommonStrAndReprTests(unittest.TestCase):

        def get_testing_module(self):
            raise NotImplementedError

        def test_settings(self):
            testing_module = self.get_testing_module()

            self.assertTrue(inspect.ismodule(testing_module))

        def _get_type_value(self, _type: typing.Type):
            if inspect.isclass(_type) and issubclass(_type, enum.Enum):
                # for enum get first available value
                return list(_type)[0]

            kwargs = {}

            all_builtins = analyzers.get_all_builtins()
            special_values = {
                datetime.date: datetime.date.today(),
                datetime.datetime: datetime.datetime.utcnow(),
                decimal.Decimal: decimal.Decimal(42),
                type(None): None
            }

            type_hints = get_type_hints(_type)
            sig = inspect.signature(_type)
            for param in sig.parameters.values():
                is_named = param.kind not in (inspect.Parameter.VAR_KEYWORD, inspect.Parameter.VAR_POSITIONAL)
                if not is_named or param.default is not param.empty:
                    # pass not required params
                    continue

                param_annotation = type_hints.get(param.name, None)
                if param_annotation is None:
                    # suppose it permits None
                    kwargs[param.name] = None
                    continue

                origin = get_origin(param_annotation)
                if origin is not None:
                    if origin is typing.Union:
                        # indirectly find out that param_annotation is typing.Optional
                        union_args = get_args(param_annotation)
                        if type(None) in union_args:
                            param_annotation = type(None)
                        else:
                            param_annotation = union_args[0]
                    else:
                        param_annotation = origin

                self.assertTrue(callable(param_annotation))

                if param_annotation in all_builtins:
                    param_value = param_annotation()

                elif param_annotation in special_values:
                    param_value = special_values[param_annotation]

                else:
                    # something complex
                    param_value = self._get_type_value(param_annotation)

                kwargs[param.name] = param_value

            instance = _type(**kwargs)
            return instance

        def _test_class(self, _class: typing.Type):
            instance_value = self._get_type_value(_class)

            self.assertIsInstance(str(instance_value), str)
            self.assertIsInstance(repr(instance_value), str)

        def test_str_and_repr_methods(self):
            testing_module = self.get_testing_module()
            for module_attr_name in dir(testing_module):
                module_obj = getattr(testing_module, module_attr_name)
                if (not inspect.isclass(module_obj) or
                        module_obj.__module__ != testing_module.__name__ or
                        (not dataclasses.is_dataclass(module_obj) and
                         not issubclass(module_obj, enum.Enum) and
                         not (issubclass(module_obj, tuple) and hasattr(module_obj, '_asdict')))):
                    continue

                self._test_class(module_obj)
