#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import decimal
import unittest

from sane_finances.sources.base import CheckApiActualityError, ParseError, InstrumentExporterFactory
from sane_finances.sources.lbma.v2021.exporters import (
    LbmaDownloadParameterValuesStorage,
    LbmaStringDataDownloader, LbmaApiActualityChecker, LbmaExporterFactory)
from sane_finances.sources.lbma.v2021.meta import (
    PreciousMetalPrice, Currencies, HistoryFieldNames, PreciousMetals,
    LbmaPreciousMetalInfoDownloadParameters, LbmaPreciousMetalHistoryDownloadParameters)

from .common import CommonTestCases
from .fakes import (
    FakeDownloader, FakeLbmaHistoryJsonParser, FakeLbmaStringDataDownloader)


class TestLbmaDownloadParameterValuesStorage(unittest.TestCase):

    def setUp(self):
        self.storage = LbmaDownloadParameterValuesStorage()

    def test_is_dynamic_enum_type_AlwaysFalse(self):
        self.assertFalse(self.storage.is_dynamic_enum_type(HistoryFieldNames))
        self.assertFalse(self.storage.is_dynamic_enum_type(Currencies))
        self.assertFalse(self.storage.is_dynamic_enum_type(PreciousMetals))
        # noinspection PyTypeChecker
        self.assertFalse(self.storage.is_dynamic_enum_type(None))

    def test_get_dynamic_enum_key_AlwaysNone(self):
        self.assertIsNone(self.storage.get_dynamic_enum_key(HistoryFieldNames.VALUE))
        self.assertIsNone(self.storage.get_dynamic_enum_key(Currencies.USD))
        self.assertIsNone(self.storage.get_dynamic_enum_key(PreciousMetals.GOLD_AM))

    def test_get_all_managed_types_AlwaysEmpty(self):
        self.assertSequenceEqual(list(self.storage.get_all_managed_types()), [])


class TestLbmaStringDataDownloader(unittest.TestCase):

    def setUp(self):
        self.fake_data = 'data'
        self.string_data_downloader = LbmaStringDataDownloader(FakeDownloader(self.fake_data))

        self.history_download_params = LbmaPreciousMetalHistoryDownloadParameters(
            metal=PreciousMetals.GOLD_AM,
            currency=Currencies.USD)

    def test_download_instrument_history_string_Success(self):
        moment_from = datetime.datetime(2010, 1, 1)
        moment_to = moment_from + datetime.timedelta(days=1)

        result = self.string_data_downloader.download_instrument_history_string(
            self.history_download_params,
            moment_from,
            moment_to)

        self.assertEqual(result.downloaded_string, self.fake_data)

    def test_download_instruments_info_string_Success(self):
        params = LbmaPreciousMetalInfoDownloadParameters()

        _ = self.string_data_downloader.download_instruments_info_string(params)


class TestLbmaApiActualityChecker(unittest.TestCase):

    def setUp(self):
        self.success_history_data = [
            PreciousMetalPrice(
                date=datetime.date.today(),
                value=decimal.Decimal(42)),
            PreciousMetalPrice(
                date=LbmaApiActualityChecker._date_to_check,
                value=LbmaApiActualityChecker._expected_value)
        ]
        self.history_parser = FakeLbmaHistoryJsonParser(self.success_history_data)

        self.string_data_downloader = FakeLbmaStringDataDownloader(None, None)

    def get_checker(self) -> LbmaApiActualityChecker:
        return LbmaApiActualityChecker(
            self.string_data_downloader,
            self.history_parser)

    def test_check_Success(self):
        checker = self.get_checker()
        checker.check()

        # check that there is no incorrectly downloaded strings
        self.assertGreaterEqual(len(self.string_data_downloader.download_instruments_info_string_results), 0)
        self.assertGreaterEqual(len(self.string_data_downloader.download_instrument_history_string_results), 1)
        self.assertFalse(any(result.is_correct is False
                             for result
                             in self.string_data_downloader.download_instrument_history_string_results))

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


class TestLbmaExporterFactory(CommonTestCases.CommonInstrumentExporterFactoryTests):

    def get_exporter_factory(self) -> InstrumentExporterFactory:
        return LbmaExporterFactory()

    def is_dynamic_enum_type_manager_singleton(self):
        return True

    def is_download_parameters_factory_singleton(self):
        return True
