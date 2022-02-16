#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import decimal
import unittest

from sane_finances.sources.base import CheckApiActualityError, InstrumentExporterFactory, ParseError
from sane_finances.sources.msci.v1.exporters import (
    MsciStringDataDownloader, MsciApiActualityChecker, MsciIndexExporterFactory,
    MsciIndexDownloadParameterValuesStorage)
from sane_finances.sources.msci.v1.meta import (
    IndexValue, IndexInfo, Markets, Styles, Sizes, Scopes, Context, IndexLevels, Currencies,
    MsciIndexesInfoDownloadParameters, MsciIndexHistoryDownloadParameters)
from .common import CommonTestCases
from .fakes import (
    FakeDownloader, FakeIndexInfoParser, FakeMsciHistoryXmlParser, FakeMsciStringDataDownloader)


class TestMsciStringDataDownloader(unittest.TestCase):
    
    def setUp(self):
        # fake downloaders
        self.fake_data = 'data'
        
        downloader = FakeDownloader(self.fake_data)
        
        self.string_data_downloader = MsciStringDataDownloader(downloader)

    @staticmethod
    def generate_history_download_parameters(date_from: datetime.date, date_to: datetime.date):
        index_id = '100'
        context = Context(style=Styles.NONE, size=Sizes.REGIONAL_STANDARD, scope=Scopes.REGIONAL)
        index_level = IndexLevels.PRICE
        currency = Currencies.USD
        parameters = MsciIndexHistoryDownloadParameters.safe_create(
            index_id=index_id,
            context=context,
            index_level=index_level,
            currency=currency,
            date_from=date_from,
            date_to=date_to
        )
        return parameters

    def test_adjust_download_instrument_history_parameters_Success(self):
        moment_from = datetime.datetime(2010, 1, 1)
        moment_to = moment_from + datetime.timedelta(days=365)
        parameters = self.generate_history_download_parameters(moment_from.date(), moment_to.date())

        params, moment_from, moment_to = self.string_data_downloader.adjust_download_instrument_history_parameters(
            parameters=parameters,
            moment_from=moment_from,
            moment_to=moment_to)

        self.assertLessEqual(moment_from, moment_to)
        self.assertIsNotNone(params)

        # disalign dates with parameters
        moment_from -= datetime.timedelta(days=30)
        moment_to += datetime.timedelta(days=30)

        params, moment_from, moment_to = self.string_data_downloader.adjust_download_instrument_history_parameters(
            parameters=parameters,
            moment_from=moment_from,
            moment_to=moment_to)

        self.assertLessEqual(moment_from, moment_to)
        self.assertIsNotNone(params)

        # disalign dates with parameters
        moment_from += datetime.timedelta(days=60)
        moment_to += datetime.timedelta(days=60)

        params, moment_from, moment_to = self.string_data_downloader.adjust_download_instrument_history_parameters(
            parameters=parameters,
            moment_from=moment_from,
            moment_to=moment_to)

        self.assertLessEqual(moment_from, moment_to)
        self.assertIsNotNone(params)

    def test_paginate_download_instrument_history_parameters_LongAgoSuccess(self):
        # long ago
        moment_from = datetime.datetime(1955, 1, 1)
        moment_to = moment_from + datetime.timedelta(days=365)
        parameters = self.generate_history_download_parameters(moment_from.date(), moment_to.date())

        paginated_parameters_tuples = \
            self.string_data_downloader.paginate_download_instrument_history_parameters(
                parameters,
                moment_from,
                moment_to)
        paginated_parameters_tuples = list(paginated_parameters_tuples)  # materialize generator

        self.assertEqual(len(paginated_parameters_tuples), 1)  # don't split

    def test_paginate_download_instrument_history_parameters_TodaySuccess(self):
        # today
        moment_from = datetime.datetime.now()
        moment_to = moment_from + datetime.timedelta(days=365)
        parameters = self.generate_history_download_parameters(moment_from.date(), moment_to.date())

        paginated_parameters_tuples = \
            self.string_data_downloader.paginate_download_instrument_history_parameters(
                parameters,
                moment_from,
                moment_to)
        paginated_parameters_tuples = list(paginated_parameters_tuples)  # materialize generator

        self.assertEqual(len(paginated_parameters_tuples), 1)  # don't split

    def test_paginate_download_instrument_history_parameters_FiveYearsInsideIntervalSuccess(self):
        # 5 years ago inside interval
        moment_from = datetime.datetime.now() - datetime.timedelta(days=365*10)
        moment_to = datetime.datetime.now()
        parameters = self.generate_history_download_parameters(moment_from.date(), moment_to.date())

        paginated_parameters_tuples = \
            self.string_data_downloader.paginate_download_instrument_history_parameters(
                parameters,
                moment_from,
                moment_to)
        paginated_parameters_tuples = list(paginated_parameters_tuples)  # materialize generator

        self.assertEqual(len(paginated_parameters_tuples), 2)  # interval was split
        (first_params, _, _), (second_params, _, _) = paginated_parameters_tuples
        self.assertLessEqual(first_params.date_from, first_params.date_to)
        self.assertLessEqual(second_params.date_from, second_params.date_to)

        # even if parameters was disaligned
        long_ago = datetime.date(1945, 1, 1)
        parameters = self.generate_history_download_parameters(long_ago, long_ago)

        paginated_parameters_tuples = \
            self.string_data_downloader.paginate_download_instrument_history_parameters(
                parameters,
                moment_from,
                moment_to)
        paginated_parameters_tuples = list(paginated_parameters_tuples)  # materialize generator

        self.assertEqual(len(paginated_parameters_tuples), 2)  # interval was split
        (first_params, _, _), (second_params, _, _) = paginated_parameters_tuples
        self.assertLessEqual(first_params.date_from, first_params.date_to)
        self.assertLessEqual(second_params.date_from, second_params.date_to)

        today = datetime.date.today()
        parameters = self.generate_history_download_parameters(today, today)

        paginated_parameters_tuples = \
            self.string_data_downloader.paginate_download_instrument_history_parameters(
                parameters,
                moment_from,
                moment_to)
        paginated_parameters_tuples = list(paginated_parameters_tuples)  # materialize generator

        self.assertEqual(len(paginated_parameters_tuples), 2)  # interval was split
        (first_params, _, _), (second_params, _, _) = paginated_parameters_tuples
        self.assertLessEqual(first_params.date_from, first_params.date_to)
        self.assertLessEqual(second_params.date_from, second_params.date_to)

    def test_paginate_download_instrument_history_parameters_OneDayDontSplit(self):
        # one day don't split
        moment_from = moment_to = datetime.datetime.now()
        parameters = self.generate_history_download_parameters(moment_from.date(), moment_to.date())

        paginated_parameters_tuples = \
            self.string_data_downloader.paginate_download_instrument_history_parameters(
                parameters,
                moment_from,
                moment_to)
        paginated_parameters_tuples = list(paginated_parameters_tuples)  # materialize generator

        self.assertEqual(len(paginated_parameters_tuples), 1)  # exactly one

    def test_download_index_history_string_Success(self):
        date_from = datetime.date(2010, 1, 1)
        date_to = date_from + datetime.timedelta(days=365)
        parameters = self.generate_history_download_parameters(date_from, date_to)
        index_id = parameters.index_id
        context = parameters.context
        index_level = parameters.index_level
        currency = parameters.currency

        result = self.string_data_downloader.download_index_history_string(
            index_id,
            context,
            index_level,
            currency,
            date_from,
            date_to)
        
        self.assertEqual(result.downloaded_string, self.fake_data)

    def test_download_instrument_history_string_Success(self):
        moment_from = datetime.datetime(2010, 1, 1)  # no hours
        moment_to = moment_from + datetime.timedelta(days=365)
        parameters = self.generate_history_download_parameters(moment_from.date(), moment_to.date())

        result = self.string_data_downloader.download_instrument_history_string(parameters, moment_from, moment_to)

        self.assertEqual(result.downloaded_string, self.fake_data)

        moment_from = datetime.datetime(2010, 1, 1, 12)  # has hours
        moment_to = moment_from + datetime.timedelta(days=365)
        parameters = self.generate_history_download_parameters(moment_from.date(), moment_to.date())

        result = self.string_data_downloader.download_instrument_history_string(parameters, moment_from, moment_to)

        self.assertEqual(result.downloaded_string, self.fake_data)

    def test_download_indexes_info_string_Success(self):
        market = Markets.REGIONAL_ALL_COUNTRY
        context = Context(style=Styles.NONE, size=Sizes.REGIONAL_STANDARD, scope=Scopes.REGIONAL)
        
        result = self.string_data_downloader.download_indexes_info_string(market, context)
        
        self.assertEqual(result.downloaded_string, self.fake_data)

    def test_download_instruments_info_string_Success(self):
        market = Markets.REGIONAL_ALL_COUNTRY
        context = Context(style=Styles.NONE, size=Sizes.REGIONAL_STANDARD, scope=Scopes.REGIONAL)
        parameters = MsciIndexesInfoDownloadParameters.safe_create(market=market, context=context)

        result = self.string_data_downloader.download_instruments_info_string(parameters)

        self.assertEqual(result.downloaded_string, self.fake_data)


class TestMsciAPIActualityChecker(unittest.TestCase):
    
    def setUp(self):
        # fakes
        self.fake_info_str_data = 'info'
        self.fake_history_str_data = 'history'
        
        self.success_history_parsed_item = \
            IndexValue(
                date=MsciApiActualityChecker._expectedFirstDate,
                value=MsciApiActualityChecker._expectedFirstValue,
                index_name=MsciApiActualityChecker._expectedIndexName,
                style=MsciApiActualityChecker._expectedIndexContext.style,
                size=MsciApiActualityChecker._expectedIndexContext.size
            )
        self.success_info_parsed_item = IndexInfo(index_id='FAKE_ID', name='FAKE_NAME')
        
        self.fake_string_data_downloader = FakeMsciStringDataDownloader(
            self.fake_info_str_data,
            self.fake_history_str_data)
    
    def test_check_Success(self):
        history_parser = FakeMsciHistoryXmlParser([self.success_history_parsed_item])
        info_parser = FakeIndexInfoParser([self.success_info_parsed_item])
        
        checker = MsciApiActualityChecker(self.fake_string_data_downloader, history_parser, info_parser)
        
        checker.check()

        # check that there is no incorrectly downloaded strings
        self.assertGreaterEqual(len(self.fake_string_data_downloader.download_instruments_info_string_results), 1)
        self.assertFalse(any(result.is_correct is False
                             for result
                             in self.fake_string_data_downloader.download_instruments_info_string_results))
        self.assertGreaterEqual(len(self.fake_string_data_downloader.download_instrument_history_string_results), 1)
        self.assertFalse(any(result.is_correct is False
                             for result
                             in self.fake_string_data_downloader.download_instrument_history_string_results))

    def test_check_raisesWhenInfoParseError(self):
        history_parser = FakeMsciHistoryXmlParser([self.success_history_parsed_item])
        info_parser = FakeIndexInfoParser([self.success_info_parsed_item])
        info_parser.parse_exception = ParseError('Error')

        checker = MsciApiActualityChecker(self.fake_string_data_downloader, history_parser, info_parser)

        with self.assertRaises(Exception):
            checker.check()

        self.assertGreaterEqual(len(self.fake_string_data_downloader.download_instruments_info_string_results), 1)
        self.assertIs(self.fake_string_data_downloader.download_instruments_info_string_results[-1].is_correct, False)

    def test_check_raisesWhenInfoUnknownError(self):
        history_parser = FakeMsciHistoryXmlParser([self.success_history_parsed_item])
        info_parser = FakeIndexInfoParser([self.success_info_parsed_item])
        info_parser.parse_exception = Exception('Error')

        checker = MsciApiActualityChecker(self.fake_string_data_downloader, history_parser, info_parser)

        with self.assertRaises(Exception):
            checker.check()

        self.assertGreaterEqual(len(self.fake_string_data_downloader.download_instruments_info_string_results), 1)
        self.assertIs(self.fake_string_data_downloader.download_instruments_info_string_results[-1].is_correct, False)

    def test_check_raisesWhenNoInfo(self):
        history_parser = FakeMsciHistoryXmlParser([self.success_history_parsed_item])
        info_parser = FakeIndexInfoParser([])  # No data
        
        checker = MsciApiActualityChecker(self.fake_string_data_downloader, history_parser, info_parser)
        
        with self.assertRaises(CheckApiActualityError):
            checker.check()

        self.assertGreaterEqual(len(self.fake_string_data_downloader.download_instruments_info_string_results), 1)
        self.assertIs(self.fake_string_data_downloader.download_instruments_info_string_results[-1].is_correct, False)

    def test_check_raisesWhenHistoryParseError(self):
        history_parser = FakeMsciHistoryXmlParser([self.success_history_parsed_item])
        history_parser.parse_exception = ParseError('Error')
        info_parser = FakeIndexInfoParser([self.success_info_parsed_item])

        checker = MsciApiActualityChecker(self.fake_string_data_downloader, history_parser, info_parser)

        with self.assertRaises(Exception):
            checker.check()

        self.assertGreaterEqual(len(self.fake_string_data_downloader.download_instrument_history_string_results), 1)
        self.assertIs(self.fake_string_data_downloader.download_instrument_history_string_results[-1].is_correct, False)

    def test_check_raisesWhenHistoryUnknownError(self):
        history_parser = FakeMsciHistoryXmlParser([self.success_history_parsed_item])
        history_parser.parse_exception = Exception('Error')
        info_parser = FakeIndexInfoParser([self.success_info_parsed_item])

        checker = MsciApiActualityChecker(self.fake_string_data_downloader, history_parser, info_parser)

        with self.assertRaises(Exception):
            checker.check()

        self.assertGreaterEqual(len(self.fake_string_data_downloader.download_instrument_history_string_results), 1)
        self.assertIs(self.fake_string_data_downloader.download_instrument_history_string_results[-1].is_correct, False)

    def test_check_raisesWhenWrongIndexName(self):
        # corrupt data
        self.success_history_parsed_item.index_name = 'WRONG'
        
        history_parser = FakeMsciHistoryXmlParser([self.success_history_parsed_item])
        info_parser = FakeIndexInfoParser([self.success_info_parsed_item])
        
        checker = MsciApiActualityChecker(self.fake_string_data_downloader, history_parser, info_parser)
        
        with self.assertRaises(CheckApiActualityError):
            checker.check()
    
    def test_check_raisesWhenWrongIndexSize(self):
        # corrupt data
        self.success_history_parsed_item.size = None
        
        history_parser = FakeMsciHistoryXmlParser([self.success_history_parsed_item])
        info_parser = FakeIndexInfoParser([self.success_info_parsed_item])
        
        checker = MsciApiActualityChecker(self.fake_string_data_downloader, history_parser, info_parser)
        
        with self.assertRaises(CheckApiActualityError):
            checker.check()
    
    def test_check_raisesWhenWrongIndexStyle(self):
        # corrupt data
        self.success_history_parsed_item.style = None
        
        history_parser = FakeMsciHistoryXmlParser([self.success_history_parsed_item])
        info_parser = FakeIndexInfoParser([self.success_info_parsed_item])
        
        checker = MsciApiActualityChecker(self.fake_string_data_downloader, history_parser, info_parser)
        
        with self.assertRaises(CheckApiActualityError):
            checker.check()
    
    def test_check_raisesWhenWrongFirstDate(self):
        # corrupt data
        self.success_history_parsed_item.date = datetime.date.max
        
        history_parser = FakeMsciHistoryXmlParser([self.success_history_parsed_item])
        info_parser = FakeIndexInfoParser([self.success_info_parsed_item])
        
        checker = MsciApiActualityChecker(self.fake_string_data_downloader, history_parser, info_parser)
        
        with self.assertRaises(CheckApiActualityError):
            checker.check()
    
    def test_check_raisesWhenWrongFirstValue(self):
        # corrupt data
        self.success_history_parsed_item.value = decimal.Decimal(-1)
        
        history_parser = FakeMsciHistoryXmlParser([self.success_history_parsed_item])
        info_parser = FakeIndexInfoParser([self.success_info_parsed_item])
        
        checker = MsciApiActualityChecker(self.fake_string_data_downloader, history_parser, info_parser)
        
        with self.assertRaises(CheckApiActualityError):
            checker.check()


class TestMsciIndexDownloadParameterValuesStorage(unittest.TestCase):

    def setUp(self):
        self.storage = MsciIndexDownloadParameterValuesStorage()

    def test_is_dynamic_enum_type_AlwaysFalse(self):
        self.assertFalse(self.storage.is_dynamic_enum_type(Markets))
        self.assertFalse(self.storage.is_dynamic_enum_type(Sizes))
        self.assertFalse(self.storage.is_dynamic_enum_type(IndexLevels))
        # noinspection PyTypeChecker
        self.assertFalse(self.storage.is_dynamic_enum_type(None))

    def test_get_dynamic_enum_key_AlwaysNone(self):
        self.assertIsNone(self.storage.get_dynamic_enum_key(Markets.REGIONAL_ALL_COUNTRY))
        self.assertFalse(self.storage.get_dynamic_enum_key(Sizes.REGIONAL_STANDARD))
        self.assertFalse(self.storage.get_dynamic_enum_key(IndexLevels.PRICE))

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

        choices = self.storage.get_parameter_type_choices(Styles)

        self.assertIsNone(choices)


class TestMsciIndexExporterFactory(CommonTestCases.CommonInstrumentExporterFactoryTests):

    def get_exporter_factory(self) -> InstrumentExporterFactory:
        return MsciIndexExporterFactory()

    def is_dynamic_enum_type_manager_singleton(self):
        return True

    def is_download_parameters_factory_singleton(self):
        return True
