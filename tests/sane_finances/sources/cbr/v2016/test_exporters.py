#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import decimal
import unittest

from sane_finances.sources.base import CheckApiActualityError, InstrumentExporterFactory, ParseError
from sane_finances.sources.cbr.v2016.exporters import CbrStringDataDownloader, CbrApiActualityChecker, \
    CbrCurrencyRatesExporterFactory, CbrCurrencyDownloadParameterValuesStorage
from sane_finances.sources.cbr.v2016.meta import (
    RateFrequencies, CurrencyInfo, CurrencyRateValue,
    CbrCurrenciesInfoDownloadParameters, CbrCurrencyHistoryDownloadParameters)
from .common import CommonTestCases
from .fakes import (
    FakeDownloader, FakeCbrCurrencyInfoParser,
    FakeCbrCurrencyHistoryXmlParser, FakeCbrStringDataDownloader)


class TestMsciStringDataDownloader(unittest.TestCase):

    def setUp(self):
        # fake downloaders
        self.fake_data = 'data'

        downloader = FakeDownloader(self.fake_data)

        self.string_data_downloader = CbrStringDataDownloader(downloader)

    def test_download_currency_history_string(self):
        currency_id = 'USD'
        date_from = datetime.date(2010, 1, 1)
        date_to = date_from + datetime.timedelta(days=365*10)

        result = self.string_data_downloader.download_currency_history_string(
            currency_id,
            date_from,
            date_to)

        self.assertEqual(result.downloaded_string, self.fake_data)

    def test_download_instrument_history_string(self):
        currency_id = 'USD'
        moment_from = datetime.datetime(2010, 1, 1)  # no hours
        moment_to = moment_from + datetime.timedelta(days=365*10)
        parameters = CbrCurrencyHistoryDownloadParameters.safe_create(currency_id=currency_id)

        result = self.string_data_downloader.download_instrument_history_string(parameters, moment_from, moment_to)

        self.assertEqual(result.downloaded_string, self.fake_data)

        moment_from = datetime.datetime(2010, 1, 1, 12)  # has hours
        moment_to = moment_from + datetime.timedelta(days=365*10)
        parameters = CbrCurrencyHistoryDownloadParameters.safe_create(currency_id=currency_id)

        result = self.string_data_downloader.download_instrument_history_string(parameters, moment_from, moment_to)

        self.assertEqual(result.downloaded_string, self.fake_data)

    def test_download_currencies_info_string(self):
        rate_frequency = RateFrequencies.DAILY

        result = self.string_data_downloader.download_currencies_info_string(rate_frequency)

        self.assertSequenceEqual(result.downloaded_string, self.fake_data)

    def test_download_instruments_info_string(self):
        rate_frequency = RateFrequencies.DAILY
        parameters = CbrCurrenciesInfoDownloadParameters.safe_create(rate_frequency=rate_frequency)

        result = self.string_data_downloader.download_instruments_info_string(parameters)

        self.assertSequenceEqual(result.downloaded_string, self.fake_data)


class TestCbrAPIActualityChecker(unittest.TestCase):

    def setUp(self):
        # fakes
        self.fake_info_str_data = 'info'
        self.fake_history_str_data = 'history'

        self.success_history_parsed_item = \
            CurrencyRateValue(
                date=CbrApiActualityChecker._expectedFirstDate,
                value=CbrApiActualityChecker._expectedFirstValue,
                nominal=CbrApiActualityChecker._expectedFirstNominal,
                currency_id=CbrApiActualityChecker._currencyToCheck
            )
        self.success_info_parsed_item = CurrencyInfo(
            currency_id='FAKE_ID',
            name='FAKE_NAME',
            eng_name='FAKE_ENG_NAME',
            nominal=1,
            parent_code='FAKE_PARENT_CODE')

        self.fake_string_data_downloader = FakeCbrStringDataDownloader(
            self.fake_info_str_data,
            self.fake_history_str_data)

    def test_check_Success(self):
        history_parser = FakeCbrCurrencyHistoryXmlParser([self.success_history_parsed_item])
        info_parser = FakeCbrCurrencyInfoParser([self.success_info_parsed_item])
        checker = CbrApiActualityChecker(self.fake_string_data_downloader, history_parser, info_parser)

        checker.check()

    def test_check_raisesWhenInfoParseError(self):
        # corrupt data
        history_parser = FakeCbrCurrencyHistoryXmlParser([self.success_history_parsed_item])
        info_parser = FakeCbrCurrencyInfoParser([self.success_info_parsed_item])
        info_parser.parse_exception = ParseError('Error')
        checker = CbrApiActualityChecker(self.fake_string_data_downloader, history_parser, info_parser)

        with self.assertRaises(CheckApiActualityError):
            checker.check()

        self.assertGreaterEqual(len(self.fake_string_data_downloader.download_instruments_info_string_results), 1)
        self.assertIs(self.fake_string_data_downloader.download_instruments_info_string_results[-1].is_correct, False)

    def test_check_raisesWhenInfoUnknownError(self):
        # corrupt data
        history_parser = FakeCbrCurrencyHistoryXmlParser([self.success_history_parsed_item])
        info_parser = FakeCbrCurrencyInfoParser([self.success_info_parsed_item])
        info_parser.parse_exception = Exception('Error')
        checker = CbrApiActualityChecker(self.fake_string_data_downloader, history_parser, info_parser)

        with self.assertRaises(Exception):
            checker.check()

        self.assertGreaterEqual(len(self.fake_string_data_downloader.download_instruments_info_string_results), 1)
        self.assertIs(self.fake_string_data_downloader.download_instruments_info_string_results[-1].is_correct, False)

    def test_check_raisesWhenNoInfo(self):
        history_parser = FakeCbrCurrencyHistoryXmlParser([self.success_history_parsed_item])
        info_parser = FakeCbrCurrencyInfoParser([])  # No data

        checker = CbrApiActualityChecker(self.fake_string_data_downloader, history_parser, info_parser)

        with self.assertRaises(CheckApiActualityError):
            checker.check()

    def test_check_raisesWhenHistoryParseError(self):
        # corrupt data
        history_parser = FakeCbrCurrencyHistoryXmlParser([self.success_history_parsed_item])
        history_parser.parse_exception = ParseError('Error')
        info_parser = FakeCbrCurrencyInfoParser([self.success_info_parsed_item])
        checker = CbrApiActualityChecker(self.fake_string_data_downloader, history_parser, info_parser)

        with self.assertRaises(CheckApiActualityError):
            checker.check()

        self.assertGreaterEqual(len(self.fake_string_data_downloader.download_instrument_history_string_results), 1)
        self.assertIs(self.fake_string_data_downloader.download_instrument_history_string_results[-1].is_correct, False)

    def test_check_raisesWhenHistoryUnknownError(self):
        # corrupt data
        history_parser = FakeCbrCurrencyHistoryXmlParser([self.success_history_parsed_item])
        history_parser.parse_exception = Exception('Error')
        info_parser = FakeCbrCurrencyInfoParser([self.success_info_parsed_item])
        checker = CbrApiActualityChecker(self.fake_string_data_downloader, history_parser, info_parser)

        with self.assertRaises(Exception):
            checker.check()

        self.assertGreaterEqual(len(self.fake_string_data_downloader.download_instrument_history_string_results), 1)
        self.assertIs(self.fake_string_data_downloader.download_instrument_history_string_results[-1].is_correct, False)

    def test_check_raisesWhenWrongCurrencyId(self):
        # corrupt data
        self.success_history_parsed_item.currency_id = 'WRONG'

        history_parser = FakeCbrCurrencyHistoryXmlParser([self.success_history_parsed_item])
        info_parser = FakeCbrCurrencyInfoParser([self.success_info_parsed_item])

        checker = CbrApiActualityChecker(self.fake_string_data_downloader, history_parser, info_parser)

        with self.assertRaises(CheckApiActualityError):
            checker.check()

    def test_check_raisesWhenWrongNominal(self):
        # corrupt data
        self.success_history_parsed_item.nominal = -1

        history_parser = FakeCbrCurrencyHistoryXmlParser([self.success_history_parsed_item])
        info_parser = FakeCbrCurrencyInfoParser([self.success_info_parsed_item])

        checker = CbrApiActualityChecker(self.fake_string_data_downloader, history_parser, info_parser)

        with self.assertRaises(CheckApiActualityError):
            checker.check()

    def test_check_raisesWhenWrongFirstDate(self):
        # corrupt data
        self.success_history_parsed_item.date = datetime.date.max

        history_parser = FakeCbrCurrencyHistoryXmlParser([self.success_history_parsed_item])
        info_parser = FakeCbrCurrencyInfoParser([self.success_info_parsed_item])

        checker = CbrApiActualityChecker(self.fake_string_data_downloader, history_parser, info_parser)

        with self.assertRaises(CheckApiActualityError):
            checker.check()

    def test_check_raisesWhenWrongFirstValue(self):
        # corrupt data
        self.success_history_parsed_item.value = decimal.Decimal(-1)

        history_parser = FakeCbrCurrencyHistoryXmlParser([self.success_history_parsed_item])
        info_parser = FakeCbrCurrencyInfoParser([self.success_info_parsed_item])

        checker = CbrApiActualityChecker(self.fake_string_data_downloader, history_parser, info_parser)

        with self.assertRaises(CheckApiActualityError):
            checker.check()


class TestCbrCurrencyDownloadParameterValuesStorage(unittest.TestCase):

    def setUp(self):
        self.storage = CbrCurrencyDownloadParameterValuesStorage()

    def test_is_dynamic_enum_type_AlwaysFalse(self):
        self.assertFalse(self.storage.is_dynamic_enum_type(RateFrequencies))
        # noinspection PyTypeChecker
        self.assertFalse(self.storage.is_dynamic_enum_type(None))

    def test_get_dynamic_enum_key_AlwaysNone(self):
        self.assertIsNone(self.storage.get_dynamic_enum_key(RateFrequencies.DAILY))

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


class TestCbrCurrencyRatesExporterFactory(CommonTestCases.CommonInstrumentExporterFactoryTests):

    def get_exporter_factory(self) -> InstrumentExporterFactory:
        return CbrCurrencyRatesExporterFactory()

    def is_dynamic_enum_type_manager_singleton(self):
        return True

    def is_download_parameters_factory_singleton(self):
        return True
