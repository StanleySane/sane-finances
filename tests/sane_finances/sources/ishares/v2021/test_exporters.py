#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import decimal
import unittest

from sane_finances.sources.base import CheckApiActualityError, ParseError, InstrumentExporterFactory
from sane_finances.sources.ishares.v2021.exporters import (
    ISharesDownloadParameterValuesStorage, ISharesStringDataDownloader, ISharesApiActualityChecker,
    ISharesExporterFactory)
from sane_finances.sources.ishares.v2021.meta import (
    InfoFieldNames, PerformanceValue, ISharesInstrumentInfoDownloadParameters,
    ISharesInstrumentHistoryDownloadParameters, ProductInfo)

from .common import CommonTestCases
from .fakes import (
    FakeDownloader, FakeISharesInfoJsonParser, FakeISharesHistoryHtmlParser, FakeISharesStringDataDownloader)


class TestISharesDownloadParameterValuesStorage(unittest.TestCase):

    def setUp(self):
        self.storage = ISharesDownloadParameterValuesStorage()

    def test_is_dynamic_enum_type_AlwaysFalse(self):
        self.assertFalse(self.storage.is_dynamic_enum_type(InfoFieldNames))
        # noinspection PyTypeChecker
        self.assertFalse(self.storage.is_dynamic_enum_type(None))

    def test_get_dynamic_enum_key_AlwaysNone(self):
        self.assertIsNone(self.storage.get_dynamic_enum_key(InfoFieldNames.FUND_NAME))

    def test_get_all_managed_types_AlwaysEmpty(self):
        self.assertSequenceEqual(list(self.storage.get_all_managed_types()), [])


class TestISharesStringDataDownloader(unittest.TestCase):

    def setUp(self):
        self.fake_data = 'data'
        self.string_data_downloader = ISharesStringDataDownloader(FakeDownloader(self.fake_data))

        self.history_download_params = ISharesInstrumentHistoryDownloadParameters(product_page_url='URL')

    def test_download_instrument_history_string_Success(self):
        moment_from = datetime.datetime(2010, 1, 1)
        moment_to = moment_from + datetime.timedelta(days=1)

        result = self.string_data_downloader.download_instrument_history_string(
            self.history_download_params,
            moment_from,
            moment_to)

        self.assertEqual(result.downloaded_string, self.fake_data)

    def test_download_instruments_info_string_Success(self):
        params = ISharesInstrumentInfoDownloadParameters()

        result = self.string_data_downloader.download_instruments_info_string(params)

        self.assertEqual(result.downloaded_string, self.fake_data)


class TestISharesApiActualityChecker(unittest.TestCase):

    def setUp(self):
        self.success_info_data = [
            ProductInfo(
                local_exchange_ticker=ISharesApiActualityChecker._ticker_to_check,
                isin='ISIN',
                fund_name='FUND_NAME',
                inception_date=datetime.date.today(),
                product_page_url='URL'),
            ProductInfo(
                local_exchange_ticker='TICKER',
                isin='ISIN',
                fund_name='FUND_NAME',
                inception_date=datetime.date.today(),
                product_page_url='URL')
        ]
        self.info_parser = FakeISharesInfoJsonParser(self.success_info_data)

        self.success_history_data = [
            PerformanceValue(
                date=datetime.date.today(),
                value=decimal.Decimal(42)),
            PerformanceValue(
                date=ISharesApiActualityChecker._expected_performance_date,
                value=ISharesApiActualityChecker._expected_value)
        ]
        self.history_parser = FakeISharesHistoryHtmlParser(self.success_history_data)

        self.string_data_downloader = FakeISharesStringDataDownloader(None, None)

    def get_checker(self) -> ISharesApiActualityChecker:
        return ISharesApiActualityChecker(
            self.string_data_downloader,
            self.info_parser,
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
        self.info_parser.parse_exception = ParseError('Error')
        checker = self.get_checker()

        with self.assertRaises(CheckApiActualityError):
            checker.check()

        self.assertGreaterEqual(len(self.string_data_downloader.download_instruments_info_string_results), 1)
        self.assertIs(self.string_data_downloader.download_instruments_info_string_results[-1].is_correct, False)

    def test_check_RaiseWhenInfoUnknownError(self):
        # corrupt data
        self.info_parser.parse_exception = Exception('Error')
        checker = self.get_checker()

        with self.assertRaises(Exception):
            checker.check()

        self.assertGreaterEqual(len(self.string_data_downloader.download_instruments_info_string_results), 1)
        self.assertIs(self.string_data_downloader.download_instruments_info_string_results[-1].is_correct, False)

    def test_check_RaiseWhenNoInfo(self):
        # corrupt data
        self.info_parser.fake_data = []  # No data
        checker = self.get_checker()

        with self.assertRaisesRegex(CheckApiActualityError, 'Not found instrument'):
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

        with self.assertRaisesRegex(CheckApiActualityError, 'Not found expected history value'):
            checker.check()

        self.assertGreaterEqual(len(self.string_data_downloader.download_instrument_history_string_results), 1)
        self.assertIs(self.string_data_downloader.download_instrument_history_string_results[-1].is_correct, False)


class TestISharesExporterFactory(CommonTestCases.CommonInstrumentExporterFactoryTests):

    def get_exporter_factory(self) -> InstrumentExporterFactory:
        return ISharesExporterFactory()

    def is_dynamic_enum_type_manager_singleton(self):
        return True

    def is_download_parameters_factory_singleton(self):
        return True
