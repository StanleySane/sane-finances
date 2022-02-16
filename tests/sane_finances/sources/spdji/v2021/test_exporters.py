#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import decimal
import unittest

from sane_finances.sources.base import CheckApiActualityError, ParseError, InstrumentExporterFactory
from sane_finances.sources.spdji.v2021.exporters import (
    SpdjDynamicEnumTypeManager, SpdjDownloadParameterValuesStorage, SpdjStringDataDownloader,
    SpdjApiActualityChecker, SpdjExporterFactory)
from sane_finances.sources.spdji.v2021.meta import (
    SpdjIndexesInfoDownloadParameters, SpdjIndexHistoryDownloadParameters,
    IndexMetaData, IndexFinderFilter, IndexFinderFilterGroup,
    IndexLevel, Currency, ReturnType)

from .common import CommonTestCases
from .fakes import (
    FakeDownloader, FakeSpdjMetaJsonParser, FakeSpdjInfoJsonParser,
    FakeSpdjIndexFinderFiltersParser, FakeSpdjHistoryJsonParser, FakeSpdjStringDataDownloader)


class TestSpdjDynamicEnumTypeManager(unittest.TestCase):

    def setUp(self) -> None:
        self.manager = SpdjDynamicEnumTypeManager()

    def test_is_dynamic_enum_type_Success(self):
        all_types = self.manager.get_all_managed_types()

        for dynamic_enum_type in all_types:
            self.assertTrue(self.manager.is_dynamic_enum_type(dynamic_enum_type))

    def test_is_dynamic_enum_type_FalseWithWrongType(self):
        # noinspection PyTypeChecker
        self.assertFalse(self.manager.is_dynamic_enum_type(None))

    def test_get_dynamic_enum_key_Success(self):
        instance = ReturnType.safe_create(return_type_code='CODE', return_type_name='NAME')

        self.assertEqual(self.manager.get_dynamic_enum_key(instance), instance.return_type_code)

    def test_get_dynamic_enum_key_NoneWithWrongType(self):
        self.assertIsNone(self.manager.get_dynamic_enum_key(None))


class TestSpdjDownloadParameterValuesStorage(unittest.TestCase):

    def setUp(self):
        self.expected_key_value = 'ID'
        group = IndexFinderFilterGroup.safe_create(name='GROUP_NAME', label='Group Label')
        self.fake_index_meta_data = IndexMetaData(
            currencies=(Currency.safe_create(currency_code=self.expected_key_value),),
            return_types=(ReturnType.safe_create(return_type_code=self.expected_key_value, return_type_name='PRICE'),),
            index_finder_filters=()
        )
        self.fake_index_finder_filters = (
            IndexFinderFilter.safe_create(
                group=group,
                label='Label 1',
                value=self.expected_key_value),
            IndexFinderFilter.safe_create(
                group=group,
                label='Label 2',
                value=self.expected_key_value + '2'))

        self.downloader = FakeDownloader(None)
        self.meta_json_parser = FakeSpdjMetaJsonParser(self.fake_index_meta_data)
        self.index_finder_filters_parser = FakeSpdjIndexFinderFiltersParser(
            self.fake_index_finder_filters)

        self.storage = SpdjDownloadParameterValuesStorage(
            self.downloader,
            self.meta_json_parser,
            self.index_finder_filters_parser)

    def test_reload_Success(self):
        self.storage.reload()

        self.assertGreaterEqual(len(self.downloader.download_string_results), 1)
        self.assertTrue(all(result.is_correct
                            for result
                            in self.downloader.download_string_results))

    def test_reload_LastDownloadStringResultIsNotCorrectWhenMetaError(self):
        self.meta_json_parser.parse_exception = ParseError('Error')

        with self.assertRaises(Exception):
            self.storage.reload()

        self.assertGreaterEqual(len(self.downloader.download_string_results), 1)
        self.assertIs(self.downloader.download_string_results[-1].is_correct, False)

    def test_reload_LastDownloadStringResultIsNotCorrectWhenIndexFinderError(self):
        self.index_finder_filters_parser.parse_exception = ParseError('Error')

        with self.assertRaises(Exception):
            self.storage.reload()

        self.assertGreaterEqual(len(self.downloader.download_string_results), 1)
        self.assertIs(self.downloader.download_string_results[-1].is_correct, False)

    def test_get_dynamic_enum_value_by_key_Success(self):
        all_types = self.storage.get_all_managed_types()
        for dynamic_enum_type in all_types:
            value = self.storage.get_dynamic_enum_value_by_key(dynamic_enum_type, self.expected_key_value)
            self.assertIsNotNone(value)

            value = self.storage.get_dynamic_enum_value_by_key(dynamic_enum_type, 'UNKNOWN_KEY')
            self.assertIsNone(value)

        # noinspection PyTypeChecker
        value = self.storage.get_dynamic_enum_value_by_key(None, self.expected_key_value)
        self.assertIsNone(value)

    def test_get_dynamic_enum_value_by_choice_Success(self):
        all_types = self.storage.get_all_managed_types()
        for dynamic_enum_type in all_types:
            value = self.storage.get_dynamic_enum_value_by_choice(dynamic_enum_type, self.expected_key_value)
            self.assertIsNotNone(value)

            value = self.storage.get_dynamic_enum_value_by_choice(dynamic_enum_type, 'UNKNOWN_KEY')
            self.assertIsNone(value)

        # noinspection PyTypeChecker
        value = self.storage.get_dynamic_enum_value_by_choice(None, self.expected_key_value)
        self.assertIsNone(value)

    def test_get_all_parameter_values_for_Success(self):
        all_types = self.storage.get_all_managed_types()
        for dynamic_enum_type in all_types:
            values = list(self.storage.get_all_parameter_values_for(dynamic_enum_type))
            self.assertGreaterEqual(len(values), 1)

        # noinspection PyTypeChecker
        values = self.storage.get_all_parameter_values_for(None)
        self.assertIsNone(values)

    def test_get_parameter_type_choices_Success(self):
        all_types = self.storage.get_all_managed_types()
        for dynamic_enum_type in all_types:
            choices = self.storage.get_parameter_type_choices(dynamic_enum_type)
            self.assertGreaterEqual(len(choices), 1)

        # noinspection PyTypeChecker
        choices = self.storage.get_parameter_type_choices(None)
        self.assertIsNone(choices)


class TestSpdjStringDataDownloader(unittest.TestCase):

    def setUp(self):
        self.fake_data = 'data'

        self.expected_key_value = 'ID'
        self.fake_index_meta_data = IndexMetaData(
            currencies=(Currency.safe_create(currency_code=self.expected_key_value),),
            return_types=(ReturnType.safe_create(return_type_code=self.expected_key_value, return_type_name='PRICE'),),
            index_finder_filters=(IndexFinderFilter.safe_create(
                group=IndexFinderFilterGroup.safe_create(name='GROUP_NAME', label='Group Label'),
                label='Label',
                value=self.expected_key_value),)
        )

        self.string_data_downloader = SpdjStringDataDownloader(FakeDownloader(self.fake_data))

        self.history_download_params = SpdjIndexHistoryDownloadParameters(
            index_id='WHATEVER',
            currency=self.fake_index_meta_data.currencies[0],
            return_type=self.fake_index_meta_data.return_types[0])

    def test_download_instrument_history_string_Success(self):
        moment_from = datetime.datetime(2010, 1, 1, 12)  # has hours
        moment_to = moment_from + datetime.timedelta(days=1)

        result = self.string_data_downloader.download_instrument_history_string(
            self.history_download_params,
            moment_from,
            moment_to)

        self.assertEqual(result.downloaded_string, self.fake_data)

    def test_download_index_history_string_Success(self):
        result = self.string_data_downloader.download_index_history_string(
            index_id='WHATEVER',
            currency=self.fake_index_meta_data.currencies[0],
            return_type=self.fake_index_meta_data.return_types[0])

        self.assertEqual(result.downloaded_string, self.fake_data)

    def test_download_index_history_string_SuccessWithNoneParams(self):
        result = self.string_data_downloader.download_index_history_string(
            index_id='WHATEVER',
            currency=None,
            return_type=None)

        self.assertEqual(result.downloaded_string, self.fake_data)

    def test_paginate_download_instruments_info_parameters_Success(self):
        params = SpdjIndexesInfoDownloadParameters.safe_create(
            index_finder_filter=None,
            page_number=1)
        test_steps = 10  # number of first pages to test

        self.assertGreaterEqual(test_steps, 2)

        current_step = 1
        current_page_number = 1  # start from one
        for paginated_params in self.string_data_downloader.paginate_download_instruments_info_parameters(params):
            self.assertEqual(paginated_params.page_number, current_page_number)

            current_page_number += 1
            current_step += 1
            if current_step > test_steps:
                # limit pages for test purpose because pagination in this exporter is infinite by design
                break

    def test_download_instruments_info_string_Success(self):
        params = SpdjIndexesInfoDownloadParameters.safe_create(
            index_finder_filter=None,
            page_number=1)

        result = self.string_data_downloader.download_instruments_info_string(params)

        self.assertEqual(result.downloaded_string, self.fake_data)

    def test_download_indexes_info_string_Success(self):
        result = self.string_data_downloader.download_index_info_string(
            page_number=1,
            index_finder_filter=self.fake_index_meta_data.index_finder_filters[0])

        self.assertEqual(result.downloaded_string, self.fake_data)


class TestSpdjApiActualityChecker(unittest.TestCase):

    def setUp(self):
        self.index_info_parser = FakeSpdjInfoJsonParser([])

        self.success_history_data = [IndexLevel(
            index_id='ID',
            effective_date=datetime.datetime.utcnow(),
            index_value=decimal.Decimal(42))]
        self.history_parser = FakeSpdjHistoryJsonParser(self.success_history_data)
        self.string_data_downloader = FakeSpdjStringDataDownloader(None, None)

    def get_checker(self) -> SpdjApiActualityChecker:
        return SpdjApiActualityChecker(
            self.string_data_downloader,
            self.index_info_parser,
            self.history_parser)

    def test_check_Success(self):
        checker = self.get_checker()
        checker.check()

        # check that there is no incorrectly downloaded strings
        self.assertGreaterEqual(len(self.string_data_downloader.download_instruments_info_string_results), 1)
        self.assertFalse(any(result.is_correct is False
                             for result
                             in self.string_data_downloader.download_instruments_info_string_results))
        self.assertGreaterEqual(len(self.string_data_downloader.download_instrument_history_string_results), 1)
        self.assertFalse(any(result.is_correct is False
                             for result
                             in self.string_data_downloader.download_instrument_history_string_results))

    def test_check_RaiseWhenInfoParseError(self):
        # corrupt data
        self.index_info_parser.parse_exception = ParseError('Error')
        checker = self.get_checker()

        with self.assertRaises(CheckApiActualityError):
            checker.check()

        self.assertGreaterEqual(len(self.string_data_downloader.download_instruments_info_string_results), 1)
        self.assertIs(self.string_data_downloader.download_instruments_info_string_results[-1].is_correct, False)

    def test_check_RaiseWhenInfoUnknownError(self):
        # corrupt data
        self.index_info_parser.parse_exception = Exception('Error')
        checker = self.get_checker()

        with self.assertRaises(Exception):
            checker.check()

        self.assertGreaterEqual(len(self.string_data_downloader.download_instruments_info_string_results), 1)
        self.assertIs(self.string_data_downloader.download_instruments_info_string_results[-1].is_correct, False)

    def test_check_RaisesWhenHistoryParseError(self):
        # corrupt data
        self.history_parser.parse_exception = ParseError('Error')
        checker = self.get_checker()

        with self.assertRaises(CheckApiActualityError):
            checker.check()

        self.assertGreaterEqual(len(self.string_data_downloader.download_instrument_history_string_results), 1)
        self.assertIs(self.string_data_downloader.download_instrument_history_string_results[-1].is_correct, False)

    def test_check_RaiseWhenHistoryUnknownError(self):
        # corrupt data
        self.history_parser.parse_exception = Exception('Error')
        checker = self.get_checker()

        with self.assertRaises(Exception):
            checker.check()

        self.assertGreaterEqual(len(self.string_data_downloader.download_instrument_history_string_results), 1)
        self.assertIs(self.string_data_downloader.download_instrument_history_string_results[-1].is_correct, False)

    def test_check_RaiseWhenNoHistory(self):
        # corrupt data
        self.history_parser.fake_data = []  # No data
        checker = self.get_checker()

        with self.assertRaisesRegex(CheckApiActualityError, 'Not found history'):
            checker.check()

        self.assertGreaterEqual(len(self.string_data_downloader.download_instrument_history_string_results), 1)
        self.assertIs(self.string_data_downloader.download_instrument_history_string_results[-1].is_correct, False)


class TestSpdjExporterFactory(CommonTestCases.CommonInstrumentExporterFactoryTests):

    def get_exporter_factory(self) -> InstrumentExporterFactory:
        return SpdjExporterFactory()

    def is_dynamic_enum_type_manager_singleton(self):
        return True

    def is_download_parameters_factory_singleton(self):
        return True
