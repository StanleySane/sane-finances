#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import decimal
import unittest

from sane_finances.sources.base import CheckApiActualityError, ParseError, InstrumentExporterFactory
from sane_finances.sources.bloomberg.v2021.exporters import (
    BloombergDownloadParameterValuesStorage, BloombergStringDataDownloader, BloombergApiActualityChecker,
    BloombergExporterFactory)
from sane_finances.sources.bloomberg.v2021.meta import (
    Timeframes, Intervals, HistoryFieldNames, InfoFieldNames,
    BloombergInfoDownloadParameters, BloombergHistoryDownloadParameters, InstrumentPrice)

from .common import CommonTestCases
from .fakes import (
    FakeDownloader, FakeBloombergStringDataDownloader,
    FakeBloombergHistoryJsonParser, FakeBloombergInfoJsonParser)


class TestBloombergDownloadParameterValuesStorage(unittest.TestCase):

    def setUp(self):
        self.storage = BloombergDownloadParameterValuesStorage()

    def test_is_dynamic_enum_type_AlwaysFalse(self):
        self.assertFalse(self.storage.is_dynamic_enum_type(HistoryFieldNames))
        self.assertFalse(self.storage.is_dynamic_enum_type(InfoFieldNames))
        self.assertFalse(self.storage.is_dynamic_enum_type(Timeframes))
        self.assertFalse(self.storage.is_dynamic_enum_type(Intervals))
        # noinspection PyTypeChecker
        self.assertFalse(self.storage.is_dynamic_enum_type(None))

    def test_get_dynamic_enum_key_AlwaysNone(self):
        self.assertIsNone(self.storage.get_dynamic_enum_key(HistoryFieldNames.VALUE))
        self.assertIsNone(self.storage.get_dynamic_enum_key(InfoFieldNames.NAME))
        self.assertIsNone(self.storage.get_dynamic_enum_key(Timeframes.FIVE_YEARS))
        self.assertIsNone(self.storage.get_dynamic_enum_key(Intervals.DAILY))

    def test_get_all_managed_types_AlwaysEmpty(self):
        self.assertSequenceEqual(list(self.storage.get_all_managed_types()), [])

    def test_get_parameter_type_choices_Success(self):
        all_types = self.storage._special_handlers.keys()
        for dynamic_enum_type in all_types:
            choices = self.storage.get_parameter_type_choices(dynamic_enum_type)

            self.assertGreaterEqual(len(choices), 1)

        # noinspection PyTypeChecker
        choices = self.storage.get_parameter_type_choices(None)
        self.assertIsNone(choices)

        choices = self.storage.get_parameter_type_choices(object)
        self.assertIsNone(choices)


class TestBloombergStringDataDownloader(unittest.TestCase):

    def setUp(self):
        self.fake_data = 'data'

        self.string_data_downloader = BloombergStringDataDownloader(FakeDownloader(self.fake_data))

        self.history_download_params = BloombergHistoryDownloadParameters(
            ticker='TICKER',
            timeframe=Timeframes.FIVE_YEARS,
            interval=Intervals.DAILY)

    def test_download_instrument_history_string_Success(self):
        moment_from = datetime.datetime(2010, 1, 1)
        moment_to = moment_from + datetime.timedelta(days=1)

        result = self.string_data_downloader.download_instrument_history_string(
            self.history_download_params,
            moment_from,
            moment_to)

        self.assertEqual(result.downloaded_string, self.fake_data)

    def test_download_index_history_string_Success(self):
        result = self.string_data_downloader.download_history_string(
            ticker='TICKER',
            timeframe=Timeframes.FIVE_YEARS,
            interval=Intervals.DAILY)

        self.assertEqual(result.downloaded_string, self.fake_data)

    def test_download_instruments_info_string_Success(self):
        params = BloombergInfoDownloadParameters.safe_create(search_string='')

        result = self.string_data_downloader.download_instruments_info_string(params)

        self.assertEqual(result.downloaded_string, self.fake_data)

    def test_download_indexes_info_string_Success(self):
        result = self.string_data_downloader.download_info_string(search_string='')

        self.assertEqual(result.downloaded_string, self.fake_data)


class TestBloombergApiActualityChecker(unittest.TestCase):

    def setUp(self):
        self.index_info_parser = FakeBloombergInfoJsonParser([])

        self.success_history_data = [InstrumentPrice(
            ticker='TICKER',
            price_date=datetime.date.today(),
            price_value=decimal.Decimal(42))]
        self.history_parser = FakeBloombergHistoryJsonParser(self.success_history_data)
        self.string_data_downloader = FakeBloombergStringDataDownloader(None, None)

    def get_checker(self) -> BloombergApiActualityChecker:
        return BloombergApiActualityChecker(
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


class TestBloombergExporterFactory(CommonTestCases.CommonInstrumentExporterFactoryTests):

    def get_exporter_factory(self) -> InstrumentExporterFactory:
        return BloombergExporterFactory()

    def is_dynamic_enum_type_manager_singleton(self):
        return True

    def is_download_parameters_factory_singleton(self):
        return True
