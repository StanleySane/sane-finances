#!/usr/bin/python
# -*- coding: utf-8 -*-

import inspect
import typing
import unittest

from sane_finances.sources.base import (
    InstrumentExporterFactory, DownloadParametersFactory, InstrumentHistoryDownloadParameters)
from sane_finances.sources.generic import get_all_instrument_exporters
from ..communication.fakes import FakeDownloader


class CommonTestCases:  # hide test cases from unittest discovery

    class CommonDownloadParametersFactoryTests(unittest.TestCase):

        def get_download_parameters_factory(self) -> DownloadParametersFactory:
            raise NotImplementedError

        def get_generate_history_download_parameters_from_expected_result_with_none(self) \
                -> InstrumentHistoryDownloadParameters:
            raise NotImplementedError

        def test_download_history_parameters_class_Success(self):
            factory = self.get_download_parameters_factory()

            self.assertTrue(inspect.isclass(factory.download_history_parameters_class))

        def test_download_history_parameters_factory_Success(self):
            factory = self.get_download_parameters_factory()

            self.assertTrue(callable(factory.download_history_parameters_factory))

        def test_download_info_parameters_class_Success(self):
            factory = self.get_download_parameters_factory()

            self.assertTrue(inspect.isclass(factory.download_info_parameters_class))

        def test_download_info_parameters_factory_Success(self):
            factory = self.get_download_parameters_factory()

            self.assertTrue(callable(factory.download_info_parameters_factory))

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
