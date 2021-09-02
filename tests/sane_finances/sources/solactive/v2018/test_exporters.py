#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import decimal
import unittest

from sane_finances.sources.base import ParseError, CheckApiActualityError, InstrumentExporterFactory
from sane_finances.sources.solactive.v2018.exporters import (
    SolactiveStringDataDownloader, SolactiveApiActualityChecker, SolactiveExporterFactory,
    SolactiveDownloadParameterValuesStorage)
from sane_finances.sources.solactive.v2018.meta import (
    IndexValue, SolactiveIndexHistoryDownloadParameters, SolactiveIndexesInfoDownloadParameters, IndexHistoryTypes,
    FileExtensions, FieldNames)
from .common import CommonTestCases
from .fakes import (
    FakeDownloader, FakeSolactiveStringDataDownloader, FakeSolactiveJsonParser)


class TestSolactiveStringDataDownloader(unittest.TestCase):
    
    def setUp(self):
        # fake downloaders
        self.fake_data = 'data'
        
        downloader = FakeDownloader(self.fake_data)
        
        self.string_data_downloader = SolactiveStringDataDownloader(downloader)

    def test_paginate_download_instrument_history_parameters(self):
        isin = 'SOME_ISIN'
        parameters = SolactiveIndexHistoryDownloadParameters.safe_create(isin=isin)
        moment_from, moment_to = datetime.datetime(2010, 1, 1), datetime.datetime(2020, 1, 1)

        paginated_parameters_tuples = \
            self.string_data_downloader.paginate_download_instrument_history_parameters(
                parameters,
                moment_from,
                moment_to)
        paginated_parameters_tuples = list(paginated_parameters_tuples)  # materialize generator

        self.assertTrue(len(paginated_parameters_tuples) >= 1)

    def test_download_instrument_history_string(self):
        isin = 'SOME_ISIN'
        parameters = SolactiveIndexHistoryDownloadParameters.safe_create(isin=isin)
        moment_from = moment_to = datetime.datetime(2000, 1, 1)

        result = self.string_data_downloader.download_instrument_history_string(parameters, moment_from, moment_to)

        self.assertEqual(result.downloaded_string, self.fake_data)

    def test_download_instruments_info_string(self):
        parameters = SolactiveIndexesInfoDownloadParameters.safe_create()

        result = self.string_data_downloader.download_instruments_info_string(parameters)

        self.assertEqual(result.downloaded_string, self.fake_data)

    def test_download_index_history_string(self):
        isin = 'SOME_ISIN'
        
        result = self.string_data_downloader.download_index_history_string(isin)
        
        self.assertEqual(result.downloaded_string, self.fake_data)
    
    def test_download_all_indexes_info_success(self):
        result = self.string_data_downloader.download_all_indexes_info_string()
        
        self.assertEqual(result.downloaded_string, self.fake_data)


class TestSolactiveAPIActualityChecker(unittest.TestCase):
    
    def setUp(self):
        # fakes
        self.success_json_parsed_item = \
            IndexValue(
                index_id=SolactiveApiActualityChecker.ActualityCheckISIN,
                # convert to datetime:
                moment=datetime.datetime.combine(SolactiveApiActualityChecker._expectedFirstMomentDate,
                                                 datetime.time.min),
                value=SolactiveApiActualityChecker._expectedFirstValue
            )
        
        self.fake_string_data_downloader = FakeSolactiveStringDataDownloader(None, None)
        self.json_parser = FakeSolactiveJsonParser([self.success_json_parsed_item])
        self.checker = SolactiveApiActualityChecker(self.fake_string_data_downloader, self.json_parser)

    def test_check_Success(self):
        checker = self.checker
        
        checker.check()

        # check that there is no incorrect downloaded strings
        self.assertGreaterEqual(len(self.fake_string_data_downloader.download_instrument_history_string_results), 1)
        self.assertFalse(any(result.is_correct is False
                             for result
                             in self.fake_string_data_downloader.download_instrument_history_string_results))

    def test_check_raisesWhenHistoryParseError(self):
        # corrupt data
        self.json_parser.parse_exception = ParseError('Error')
        checker = self.checker

        with self.assertRaises(CheckApiActualityError):
            checker.check()

        self.assertGreaterEqual(len(self.fake_string_data_downloader.download_instrument_history_string_results), 1)
        self.assertIs(self.fake_string_data_downloader.download_instrument_history_string_results[-1].is_correct, False)

    def test_check_raisesWhenHistoryUnknownError(self):
        # corrupt data
        self.json_parser.parse_exception = Exception('Error')
        checker = self.checker

        with self.assertRaises(Exception):
            checker.check()

        self.assertGreaterEqual(len(self.fake_string_data_downloader.download_instrument_history_string_results), 1)
        self.assertIs(self.fake_string_data_downloader.download_instrument_history_string_results[-1].is_correct, False)

    def test_check_raisesWhenWrongISIN(self):
        # corrupt data
        self.success_json_parsed_item.index_id = 'WRONG'
        checker = self.checker
        
        with self.assertRaises(CheckApiActualityError):
            checker.check()
    
    def test_check_raisesWhenWrongMoment(self):
        # corrupt data
        self.success_json_parsed_item.moment = datetime.datetime.max
        checker = self.checker
        
        with self.assertRaises(CheckApiActualityError):
            checker.check()
    
    def test_check_raisesWhenWrongValue(self):
        # corrupt data
        self.success_json_parsed_item.value = decimal.Decimal(-1)
        checker = self.checker
        
        with self.assertRaises(CheckApiActualityError):
            checker.check()


class TestSolactiveDownloadParameterValuesStorage(unittest.TestCase):

    def setUp(self):
        self.storage = SolactiveDownloadParameterValuesStorage()

    def test_is_dynamic_enum_type_AlwaysFalse(self):
        self.assertFalse(self.storage.is_dynamic_enum_type(IndexHistoryTypes))
        self.assertFalse(self.storage.is_dynamic_enum_type(FileExtensions))
        self.assertFalse(self.storage.is_dynamic_enum_type(FieldNames))
        # noinspection PyTypeChecker
        self.assertFalse(self.storage.is_dynamic_enum_type(None))

    def test_get_dynamic_enum_key_AlwaysNone(self):
        self.assertIsNone(self.storage.get_dynamic_enum_key(IndexHistoryTypes.MAX))
        self.assertFalse(self.storage.get_dynamic_enum_key(FileExtensions.JSON))
        self.assertFalse(self.storage.get_dynamic_enum_key(FieldNames.INDEX_ID))

    def test_get_all_managed_types_AlwaysEmpty(self):
        self.assertSequenceEqual(list(self.storage.get_all_managed_types()), [])


class TestMsciIndexExporterFactory(CommonTestCases.CommonIndexExporterFactoryTests):

    def get_exporter_factory(self) -> InstrumentExporterFactory:
        return SolactiveExporterFactory()

    def is_dynamic_enum_type_manager_singleton(self):
        return True

    def is_download_parameters_factory_singleton(self):
        return True
