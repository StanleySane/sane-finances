#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import unittest

from sane_finances.sources.base import ParseError, CheckApiActualityError, InstrumentExporterFactory
from sane_finances.sources.yahoo.v8.exporters import (
    YahooFinanceStringDataDownloader, YahooFinanceApiActualityChecker, YahooFinanceExporterFactory,
    YahooFinanceDownloadParameterValuesStorage)
from sane_finances.sources.yahoo.v8.meta import (
    YahooInstrumentHistoryDownloadParameters, YahooInstrumentInfoDownloadParameters,
    IntervalTypes, SearchInfoFieldNames, QuoteHistoryFieldNames)

from .common import CommonTestCases
from .fakes import FakeDownloader, FakeYahooFinanceStringDataDownloader, FakeYahooQuotesJsonParser


class TestYahooFinanceStringDataDownloader(unittest.TestCase):
    
    def setUp(self):
        # fake downloaders
        self.fake_data = 'data'
        
        downloader = FakeDownloader(self.fake_data)
        
        self.string_data_downloader = YahooFinanceStringDataDownloader(downloader)

    def test_download_instrument_history_string_Success(self):
        symbol = 'SOME_SYMBOL'
        parameters = YahooInstrumentHistoryDownloadParameters.safe_create(symbol=symbol)
        moment_from = moment_to = datetime.datetime(2000, 1, 1)

        result = self.string_data_downloader.download_instrument_history_string(parameters, moment_from, moment_to)

        self.assertEqual(result.downloaded_string, self.fake_data)

    def test_download_instruments_info_string_Success(self):
        parameters = YahooInstrumentInfoDownloadParameters.safe_create(search_string='s')

        result = self.string_data_downloader.download_instruments_info_string(parameters)

        self.assertEqual(result.downloaded_string, self.fake_data)

    def test_download_quotes_string_Success(self):
        symbol = 'SOME_SYMBOL'
        moment_from = datetime.datetime(2010, 1, 1)
        moment_to = moment_from + datetime.timedelta(days=365*10)

        result = self.string_data_downloader.download_quotes_string(symbol, moment_from, moment_to)
        
        self.assertEqual(result.downloaded_string, self.fake_data)
    
    def test_download_instruments_search_string_Success(self):
        result = self.string_data_downloader.download_instruments_search_string(search_string='s')
        
        self.assertEqual(result.downloaded_string, self.fake_data)


class TestYahooFinanceApiActualityChecker(unittest.TestCase):
    
    def setUp(self):
        # fakes
        self.fake_string_data_downloader = FakeYahooFinanceStringDataDownloader(None, None)
        self.fake_json_parser = FakeYahooQuotesJsonParser([])

        self.checker = YahooFinanceApiActualityChecker(self.fake_string_data_downloader, self.fake_json_parser)

    def test_check_Success(self):
        checker = self.checker
        
        checker.check()

        # check that there is no incorrectly downloaded strings
        self.assertGreaterEqual(len(self.fake_string_data_downloader.download_instrument_history_string_results), 1)
        self.assertFalse(any(result.is_correct is False
                             for result
                             in self.fake_string_data_downloader.download_instrument_history_string_results))

    def test_check_RaiseWhenHistoryParseError(self):
        # corrupt data
        self.fake_json_parser.parse_exception = ParseError('Error')
        checker = self.checker

        with self.assertRaises(CheckApiActualityError):
            checker.check()

        self.assertGreaterEqual(len(self.fake_string_data_downloader.download_instrument_history_string_results), 1)
        self.assertIs(self.fake_string_data_downloader.download_instrument_history_string_results[-1].is_correct, False)

    def test_check_RaiseWhenHistoryUnknownError(self):
        # corrupt data
        self.fake_json_parser.parse_exception = Exception('Error')
        checker = self.checker

        with self.assertRaises(Exception):
            checker.check()

        self.assertGreaterEqual(len(self.fake_string_data_downloader.download_instrument_history_string_results), 1)
        self.assertIs(self.fake_string_data_downloader.download_instrument_history_string_results[-1].is_correct, False)


class TestYahooFinanceDownloadParameterValuesStorage(unittest.TestCase):

    def setUp(self):
        self.storage = YahooFinanceDownloadParameterValuesStorage()

    def test_is_dynamic_enum_type_AlwaysFalse(self):
        self.assertFalse(self.storage.is_dynamic_enum_type(IntervalTypes))
        self.assertFalse(self.storage.is_dynamic_enum_type(SearchInfoFieldNames))
        self.assertFalse(self.storage.is_dynamic_enum_type(QuoteHistoryFieldNames))
        # noinspection PyTypeChecker
        self.assertFalse(self.storage.is_dynamic_enum_type(None))

    def test_get_dynamic_enum_key_AlwaysNone(self):
        self.assertIsNone(self.storage.get_dynamic_enum_key(IntervalTypes.ONE_DAY))
        self.assertFalse(self.storage.get_dynamic_enum_key(SearchInfoFieldNames.FINANCE))
        self.assertFalse(self.storage.get_dynamic_enum_key(QuoteHistoryFieldNames.QUOTE))

    def test_get_all_managed_types_AlwaysEmpty(self):
        self.assertSequenceEqual(list(self.storage.get_all_managed_types()), [])


class TestYahooFinanceExporterFactory(CommonTestCases.CommonInstrumentExporterFactoryTests):

    def get_exporter_factory(self) -> InstrumentExporterFactory:
        return YahooFinanceExporterFactory()

    def is_dynamic_enum_type_manager_singleton(self):
        return True

    def is_download_parameters_factory_singleton(self):
        return True
