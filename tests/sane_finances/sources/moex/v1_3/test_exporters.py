#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import datetime
import decimal

from sane_finances.sources.base import CheckApiActualityError, ParseError, InstrumentExporterFactory, SourceError
from sane_finances.sources.moex.v1_3.exporters import (
    MoexDynamicEnumTypeManager, MoexDownloadParameterValuesStorage,
    MoexStringDataDownloader, MoexApiActualityChecker, MoexIndexExporterFactory_v1_3)
from sane_finances.sources.moex.v1_3.meta import (
    MoexSecuritiesInfoDownloadParameters,
    MoexSecurityHistoryDownloadParameters, TradeEngine, Market, Board, GlobalIndexData, SecurityInfo, SecurityValue)

from .fakes import (
    FakeDownloader, FakeMoexStringDataDownloader, FakeMoexDownloadParameterValuesStorage, FakeMoexHistoryJsonParser,
    FakeMoexGlobalIndexJsonParser, FakeMoexSecurityInfoJsonParser)
from .common import CommonTestCases


class TestMoexDynamicEnumTypeManager(unittest.TestCase):

    def test_is_dynamic_enum_type_Success(self):
        manager = MoexDynamicEnumTypeManager()
        all_types = manager.get_all_managed_types()

        for dynamic_enum_type in all_types:
            self.assertTrue(manager.is_dynamic_enum_type(dynamic_enum_type))

    def test_is_dynamic_enum_type_FalseWithWrongType(self):
        manager = MoexDynamicEnumTypeManager()

        # noinspection PyTypeChecker
        self.assertFalse(manager.is_dynamic_enum_type(None))

    def test_get_dynamic_enum_key_Success(self):
        manager = MoexDynamicEnumTypeManager()
        engine = TradeEngine(identity=42, name='NAME', title='TITLE')

        self.assertEqual(manager.get_dynamic_enum_key(engine), engine.identity)

    def test_get_dynamic_enum_key_NoneWithWrongType(self):
        manager = MoexDynamicEnumTypeManager()

        self.assertIsNone(manager.get_dynamic_enum_key(None))


class TestMoexDownloadParameterValuesStorage(unittest.TestCase):

    def setUp(self):
        engine = TradeEngine(
            identity=42,
            name='stock',
            title='Фондовый рынок и рынок депозитов')
        market = Market(
            identity=42,
            trade_engine=engine,
            name='shares',
            title='Рынок акций',
            marketplace='MXSE')
        board = Board(
            identity=42,
            trade_engine=engine,
            market=market,
            boardid='TQTF',
            title='Т+: ETF - безадрес.',
            is_traded=True,
            has_candles=True,
            is_primary=True)
        self.global_index_data = GlobalIndexData(
            trade_engines=(engine, engine),
            markets=(market, market),
            boards=(board, board))

        self.downloader = FakeDownloader(None)
        self.global_index_json_parser = FakeMoexGlobalIndexJsonParser(self.global_index_data)
        self.storage = MoexDownloadParameterValuesStorage(
            self.downloader,
            self.global_index_json_parser)

    def test_reload_Success(self):
        self.storage.reload()

        self.assertGreaterEqual(len(self.downloader.download_string_results), 1)
        self.assertTrue(all(result.is_correct
                            for result
                            in self.downloader.download_string_results))

    def test_reload_LastDownloadStringResultIsNotCorrectWhenParseError(self):
        self.global_index_json_parser.parse_exception = ParseError('Error')

        with self.assertRaises(Exception):
            self.storage.reload()

        self.assertGreaterEqual(len(self.downloader.download_string_results), 1)
        self.assertIs(self.downloader.download_string_results[-1].is_correct, False)

    def test_reload_LastDownloadStringResultIsNotCorrectWhenUnknownError(self):
        self.global_index_json_parser.parse_exception = Exception('Error')

        with self.assertRaises(Exception):
            self.storage.reload()

        self.assertGreaterEqual(len(self.downloader.download_string_results), 1)
        self.assertIs(self.downloader.download_string_results[-1].is_correct, False)

    def test_get_dynamic_enum_value_by_key_Success(self):
        all_types = self.storage.get_all_managed_types()
        for dynamic_enum_type in all_types:
            value = self.storage.get_dynamic_enum_value_by_key(dynamic_enum_type, 42)
            wrong_value = self.storage.get_dynamic_enum_value_by_key(dynamic_enum_type, -1)

            self.assertIsNotNone(value)
            self.assertIsNone(wrong_value)

        # noinspection PyTypeChecker
        value = self.storage.get_dynamic_enum_value_by_key(None, 42)

        self.assertIsNone(value)

    def test_get_dynamic_enum_value_by_choice_Success(self):
        all_types = self.storage.get_all_managed_types()
        for dynamic_enum_type in all_types:
            value = self.storage.get_dynamic_enum_value_by_choice(dynamic_enum_type, '42')
            wrong_value = self.storage.get_dynamic_enum_value_by_choice(dynamic_enum_type, '-1')

            self.assertIsNotNone(value)
            self.assertIsNone(wrong_value)

        # noinspection PyTypeChecker
        value = self.storage.get_dynamic_enum_value_by_choice(None, '42')

        self.assertIsNone(value)

    def test_get_dynamic_enum_value_by_choice_RaiseWhenWrongChoice(self):
        all_types = self.storage.get_all_managed_types()
        for dynamic_enum_type in all_types:
            with self.assertRaises(SourceError):
                _ = self.storage.get_dynamic_enum_value_by_choice(dynamic_enum_type, 'WRONG')

    def test_get_all_parameter_values_for_Success(self):
        all_types = self.storage.get_all_managed_types()
        for dynamic_enum_type in all_types:
            value = self.storage.get_all_parameter_values_for(dynamic_enum_type)

            self.assertIsNotNone(value)

        # noinspection PyTypeChecker
        value = self.storage.get_all_parameter_values_for(None)

        self.assertIsNone(value)

    def test_get_parameter_type_choices_Success(self):
        all_types = self.storage.get_all_managed_types()
        for dynamic_enum_type in all_types:
            choices = self.storage.get_parameter_type_choices(dynamic_enum_type)

            self.assertIsNotNone(choices)

        # noinspection PyTypeChecker
        choices = self.storage.get_parameter_type_choices(None)

        self.assertIsNone(choices)


class TestMoexStringDataDownloader(unittest.TestCase):

    def setUp(self):
        self.fake_data = 'data'

        self.engine = TradeEngine(
            identity=42,
            name='stock',
            title='Фондовый рынок и рынок депозитов')
        self.market = Market(
            identity=42,
            trade_engine=self.engine,
            name='shares',
            title='Рынок акций',
            marketplace='MXSE')
        self.board = Board(
            identity=42,
            trade_engine=self.engine,
            market=self.market,
            boardid='TQTF',
            title='Т+: ETF - безадрес.',
            is_traded=True,
            has_candles=True,
            is_primary=True)

        self.string_data_downloader = MoexStringDataDownloader(FakeDownloader(self.fake_data))
        self.history_download_params = MoexSecurityHistoryDownloadParameters(board=self.board, sec_id='SECID', start=0)

    def test_paginate_download_instrument_history_parameters_Success(self):
        params = MoexSecurityHistoryDownloadParameters(self.board, sec_id='SEC ID', start=0)
        moment_from = datetime.datetime(2010, 1, 1)
        moment_to = moment_from + datetime.timedelta(days=1)
        test_steps = 10  # number of first pages to test

        self.assertGreaterEqual(test_steps, 2)

        current_step = 1
        current_start = 0  # start from zero
        for paginated_params, paginated_moment_from, paginated_moment_to in \
                self.string_data_downloader.paginate_download_instrument_history_parameters(
                    params, moment_from, moment_to):
            self.assertEqual(paginated_moment_from, moment_from)
            self.assertEqual(paginated_moment_to, moment_to)
            self.assertEqual(paginated_params.board, params.board)
            self.assertEqual(paginated_params.sec_id, params.sec_id)
            self.assertEqual(paginated_params.start, current_start)

            current_start += self.string_data_downloader.limit.value
            current_step += 1
            if current_step > test_steps:
                # limit pages for test purpose because pagination in this exporter is infinite by design
                break

    def test_download_instrument_history_string_Success(self):
        moment_from = datetime.datetime(2010, 1, 1, 12)  # has hours
        moment_to = moment_from + datetime.timedelta(days=1)

        result = self.string_data_downloader.download_instrument_history_string(
            self.history_download_params,
            moment_from,
            moment_to)

        self.assertEqual(result.downloaded_string, self.fake_data)

        moment_from = datetime.datetime(2010, 1, 1)  # no hours
        moment_to = moment_from + datetime.timedelta(days=1)

        result = self.string_data_downloader.download_instrument_history_string(
            self.history_download_params,
            moment_from,
            moment_to)

        self.assertEqual(result.downloaded_string, self.fake_data)

    def test_download_security_history_string_Success(self):
        date_from = datetime.date(2010, 1, 1)
        date_to = date_from + datetime.timedelta(days=1)

        result = self.string_data_downloader.download_security_history_string(
            self.history_download_params.board,
            self.history_download_params.sec_id,
            self.history_download_params.start,
            date_from,
            date_to)

        self.assertEqual(result.downloaded_string, self.fake_data)

    def test_download_instruments_info_string_Success(self):
        params = MoexSecuritiesInfoDownloadParameters.safe_create(board=self.board)

        result = self.string_data_downloader.download_instruments_info_string(params)

        self.assertEqual(result.downloaded_string, self.fake_data)

    def test_download_securities_info_string_Success(self):
        result = self.string_data_downloader.download_securities_info_string(self.board)

        self.assertEqual(result.downloaded_string, self.fake_data)


class TestMoexApiActualityChecker(unittest.TestCase):

    def setUp(self):
        self.engine = TradeEngine(
            identity=42,
            name=MoexApiActualityChecker._trade_engine_name_to_test,
            title='Фондовый рынок и рынок депозитов')
        self.market = Market(
            identity=42,
            trade_engine=self.engine,
            name=MoexApiActualityChecker._market_name_to_test,
            title='Рынок акций',
            marketplace='MXSE')
        self.board = Board(
            identity=42,
            trade_engine=self.engine,
            market=self.market,
            boardid=MoexApiActualityChecker._boardid_to_test,
            title='Т+: ETF - безадрес.',
            is_traded=True,
            has_candles=True,
            is_primary=True)
        self.global_index_data = GlobalIndexData(
            trade_engines=(self.engine,),
            markets=(self.market,),
            boards=(self.board,))

        self.success_info_data = [SecurityInfo(
            sec_id='SEC ID',
            board=self.board,
            short_name='SHORT NAME')
        ]
        self.index_info_parser = FakeMoexSecurityInfoJsonParser(self.success_info_data)

        self.success_history_data = [SecurityValue(
            trade_date=MoexApiActualityChecker._history_date_to_test,
            close=MoexApiActualityChecker._expected_close_value)
        ]
        self.history_parser = FakeMoexHistoryJsonParser(self.success_history_data)

        self.string_data_downloader = FakeMoexStringDataDownloader(None, None)

    def get_checker(self):
        return MoexApiActualityChecker(
            FakeMoexDownloadParameterValuesStorage(self.global_index_data),
            self.string_data_downloader,
            self.index_info_parser,
            self.history_parser)

    def test_check_Success(self):
        checker = self.get_checker()
        checker.check()

        # check that there is no incorrect downloaded strings
        self.assertGreaterEqual(len(self.string_data_downloader.download_instruments_info_string_results), 1)
        self.assertFalse(any(result.is_correct is False
                             for result
                             in self.string_data_downloader.download_instruments_info_string_results))
        self.assertGreaterEqual(len(self.string_data_downloader.download_instrument_history_string_results), 1)
        self.assertFalse(any(result.is_correct is False
                             for result
                             in self.string_data_downloader.download_instrument_history_string_results))

    def test_check_SuccessWithUnknownBoard(self):
        unknown_board = Board(
            identity=42,
            trade_engine=TradeEngine(identity=42, name='UNKNOWN NAME', title='UNKNOWN TITLE'),
            market=self.market,
            boardid=MoexApiActualityChecker._boardid_to_test,
            title='Т+: ETF - безадрес.',
            is_traded=True,
            has_candles=True,
            is_primary=True)
        self.global_index_data = self.global_index_data._replace(boards=(unknown_board,))
        checker = self.get_checker()

        checker.check()

        # check that there is no incorrect downloaded strings
        self.assertGreaterEqual(len(self.string_data_downloader.download_instruments_info_string_results), 1)
        self.assertFalse(any(result.is_correct is False
                             for result
                             in self.string_data_downloader.download_instruments_info_string_results))
        self.assertGreaterEqual(len(self.string_data_downloader.download_instrument_history_string_results), 1)
        self.assertFalse(any(result.is_correct is False
                             for result
                             in self.string_data_downloader.download_instrument_history_string_results))

    def test_check_raisesWhenNoBoards(self):
        # corrupt data
        self.global_index_data = self.global_index_data._replace(boards=())
        checker = self.get_checker()

        with self.assertRaises(CheckApiActualityError):
            checker.check()

    def test_check_raisesWhenNotFoundTargetBoard(self):
        # corrupt data
        unknown_board = Board(
            identity=42,
            trade_engine=self.engine,
            market=self.market,
            boardid='UNKNOWN BOARDID',
            title='Т+: ETF - безадрес.',
            is_traded=True,
            has_candles=True,
            is_primary=True)
        self.global_index_data = self.global_index_data._replace(boards=(unknown_board,))
        checker = self.get_checker()

        with self.assertRaises(CheckApiActualityError):
            checker.check()

        self.assertGreaterEqual(len(self.string_data_downloader.download_instruments_info_string_results), 1)
        self.assertIs(self.string_data_downloader.download_instruments_info_string_results[-1].is_correct, False)

    def test_check_raisesWhenInfoParseError(self):
        # corrupt data
        self.index_info_parser.parse_exception = ParseError('Error')
        checker = self.get_checker()

        with self.assertRaises(CheckApiActualityError):
            checker.check()

        self.assertGreaterEqual(len(self.string_data_downloader.download_instruments_info_string_results), 1)
        self.assertIs(self.string_data_downloader.download_instruments_info_string_results[-1].is_correct, False)

    def test_check_raisesWhenInfoUnknownError(self):
        # corrupt data
        self.index_info_parser.parse_exception = Exception('Error')
        checker = self.get_checker()

        with self.assertRaises(Exception):
            checker.check()

        self.assertGreaterEqual(len(self.string_data_downloader.download_instruments_info_string_results), 1)
        self.assertIs(self.string_data_downloader.download_instruments_info_string_results[-1].is_correct, False)

    def test_check_raisesWhenHistoryParseError(self):
        # corrupt data
        self.history_parser.parse_exception = ParseError('Error')
        checker = self.get_checker()

        with self.assertRaises(CheckApiActualityError):
            checker.check()

        self.assertGreaterEqual(len(self.string_data_downloader.download_instrument_history_string_results), 1)
        self.assertIs(self.string_data_downloader.download_instrument_history_string_results[-1].is_correct, False)

    def test_check_raisesWhenHistoryUnknownError(self):
        # corrupt data
        self.history_parser.parse_exception = Exception('Error')
        checker = self.get_checker()

        with self.assertRaises(Exception):
            checker.check()

        self.assertGreaterEqual(len(self.string_data_downloader.download_instrument_history_string_results), 1)
        self.assertIs(self.string_data_downloader.download_instrument_history_string_results[-1].is_correct, False)

    def test_check_raisesWhenNoHistory(self):
        # corrupt data
        self.history_parser.fake_data = []  # No data
        checker = self.get_checker()

        with self.assertRaises(CheckApiActualityError):
            checker.check()

        self.assertGreaterEqual(len(self.string_data_downloader.download_instrument_history_string_results), 1)
        self.assertIs(self.string_data_downloader.download_instrument_history_string_results[-1].is_correct, False)

    def test_check_raisesWhenWrongFirstDate(self):
        # corrupt data
        self.success_history_data[0].trade_date = datetime.date.max
        checker = self.get_checker()

        with self.assertRaises(CheckApiActualityError):
            checker.check()

        self.assertGreaterEqual(len(self.string_data_downloader.download_instrument_history_string_results), 1)
        self.assertIs(self.string_data_downloader.download_instrument_history_string_results[-1].is_correct, False)

    def test_check_raisesWhenWrongFirstValue(self):
        # corrupt data
        self.success_history_data[0].close = decimal.Decimal(-1)
        checker = self.get_checker()

        with self.assertRaises(CheckApiActualityError):
            checker.check()

        self.assertGreaterEqual(len(self.string_data_downloader.download_instrument_history_string_results), 1)
        self.assertIs(self.string_data_downloader.download_instrument_history_string_results[-1].is_correct, False)


# noinspection PyPep8Naming
class TestMoexIndexExporterFactory_v1_3(CommonTestCases.CommonIndexExporterFactoryTests):

    def get_exporter_factory(self) -> InstrumentExporterFactory:
        return MoexIndexExporterFactory_v1_3()

    def is_dynamic_enum_type_manager_singleton(self):
        return True

    def is_download_parameters_factory_singleton(self):
        return True
