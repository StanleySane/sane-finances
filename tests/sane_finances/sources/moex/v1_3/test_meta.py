#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import decimal
import unittest

from sane_finances.sources.base import (
    InstrumentValue, InstrumentInfo, DownloadParametersFactory, InstrumentHistoryDownloadParameters)
from sane_finances.sources.moex.v1_3.meta import (
    Market, TradeEngine, Board,
    SecurityValue, SecurityInfo, MoexSecurityHistoryDownloadParameters, MoexSecuritiesInfoDownloadParameters,
    MoexDownloadParametersFactory)
from .common import CommonTestCases


class TestTradeEngine(unittest.TestCase):

    def test_safe_create_Success(self):
        _ = TradeEngine.safe_create(identity=42, name='NAME', title='TITLE')


class TestMarket(unittest.TestCase):

    def test_safe_create_Success(self):
        _ = Market.safe_create(
            identity=42,
            trade_engine=TradeEngine(identity=42, name='NAME', title='TITLE'),
            name='NAME',
            title='TITLE',
            marketplace='MARKETPLACE')

    def test_safe_create_raiseWrongEngine(self):
        with self.assertRaises(TypeError):
            # noinspection PyTypeChecker
            _ = Market.safe_create(
                identity=42,
                trade_engine=None,
                name='NAME',
                title='TITLE',
                marketplace='MARKETPLACE')


class TestBoard(unittest.TestCase):

    def setUp(self) -> None:
        self.engine = TradeEngine(identity=42, name='NAME', title='TITLE')
        self.market = Market(
            identity=42,
            trade_engine=self.engine,
            name='NAME',
            title='TITLE',
            marketplace='MARKETPLACE')

    def test_safe_create_Success(self):
        _ = Board.safe_create(
            identity=42,
            trade_engine=self.engine,
            market=self.market,
            boardid='BOARDID',
            title='TITLE',
            is_traded=True,
            has_candles=True,
            is_primary=True)

    def test_safe_create_raiseWrongEngine(self):
        with self.assertRaises(TypeError):
            # noinspection PyTypeChecker
            _ = Board.safe_create(
                identity=42,
                trade_engine=None,
                market=self.market,
                boardid='BOARDID',
                title='TITLE',
                is_traded=True,
                has_candles=True,
                is_primary=True)

    def test_safe_create_raiseWrongMarket(self):
        with self.assertRaises(TypeError):
            # noinspection PyTypeChecker
            _ = Board.safe_create(
                identity=42,
                trade_engine=self.engine,
                market=None,
                boardid='BOARDID',
                title='TITLE',
                is_traded=True,
                has_candles=True,
                is_primary=True)


class TestSecurityValue(unittest.TestCase):

    def test_instrument_value_Success(self):
        security_value = SecurityValue(
            trade_date=datetime.date(2000, 12, 31),
            close=decimal.Decimal(42))
        expected_instrument_value = InstrumentValue(
            value=security_value.close,
            moment=datetime.datetime.combine(security_value.trade_date,
                                             datetime.time.min,
                                             tzinfo=datetime.timezone.utc))

        instrument_value = security_value.get_instrument_value(datetime.timezone.utc)

        self.assertEqual(expected_instrument_value, instrument_value)

    def test_raiseWrongDate(self):
        with self.assertRaises(TypeError):
            # noinspection PyTypeChecker
            _ = SecurityValue(
                trade_date=None,
                close=decimal.Decimal(42))


class TestSecurityInfo(unittest.TestCase):

    def test_instrument_value_Success(self):
        engine = TradeEngine(identity=42, name='NAME', title='TITLE')
        market = Market(
            identity=42,
            trade_engine=engine,
            name='NAME',
            title='TITLE',
            marketplace='MARKETPLACE')

        board = Board.safe_create(
            identity=42,
            trade_engine=engine,
            market=market,
            boardid='BOARDID',
            title='TITLE',
            is_traded=True,
            has_candles=True,
            is_primary=True)

        security_info = SecurityInfo(
            sec_id='ID',
            board=board,
            short_name='SHORT NAME')
        expected_instrument_info = InstrumentInfo(code=security_info.sec_id, name=security_info.short_name)

        instrument_info = security_info.instrument_info

        self.assertEqual(expected_instrument_info, instrument_info)

    def test_instrument_value_RaiseWhenWrongBoard(self):
        with self.assertRaises(TypeError):
            # noinspection PyTypeChecker
            _ = SecurityInfo(
                sec_id='ID',
                board=None,
                short_name='SHORT NAME')


class TestMoexSecuritiesInfoDownloadParameters(unittest.TestCase):

    def test_safe_create_Success(self):
        engine = TradeEngine(identity=42, name='NAME', title='TITLE')
        market = Market(
            identity=42,
            trade_engine=engine,
            name='NAME',
            title='TITLE',
            marketplace='MARKETPLACE')

        board = Board.safe_create(
            identity=42,
            trade_engine=engine,
            market=market,
            boardid='BOARDID',
            title='TITLE',
            is_traded=True,
            has_candles=True,
            is_primary=True)

        _ = MoexSecuritiesInfoDownloadParameters.safe_create(board=board)

    def test_safe_create_raiseWrongBoard(self):
        with self.assertRaises(TypeError):
            # noinspection PyTypeChecker
            _ = MoexSecuritiesInfoDownloadParameters.safe_create(board=None)


class TestMoexSecurityHistoryDownloadParameters(unittest.TestCase):

    def setUp(self) -> None:
        engine = TradeEngine(identity=42, name='NAME', title='TITLE')
        market = Market(
            identity=42,
            trade_engine=engine,
            name='NAME',
            title='TITLE',
            marketplace='MARKETPLACE')

        self.board = Board.safe_create(
            identity=42,
            trade_engine=engine,
            market=market,
            boardid='BOARDID',
            title='TITLE',
            is_traded=True,
            has_candles=True,
            is_primary=True)

    def test_safe_create_Success(self):
        _ = MoexSecurityHistoryDownloadParameters.safe_create(
            board=self.board,
            sec_id='ID',
            start=0)

    def test_safe_create_raiseWrongBoard(self):
        with self.assertRaises(TypeError):
            # noinspection PyTypeChecker
            _ = MoexSecurityHistoryDownloadParameters.safe_create(
                board=None,
                sec_id='ID',
                start=0)

    def test_clone_with_instrument_info_parameters_Success(self):
        params = MoexSecurityHistoryDownloadParameters.safe_create(
            board=self.board,
            sec_id='ID',
            start=0)
        expected_result = params

        result = params.clone_with_instrument_info_parameters(None, None)

        self.assertEqual(expected_result, result)


class TestMoexDownloadParametersFactory(CommonTestCases.CommonDownloadParametersFactoryTests):

    def get_download_parameters_factory(self) -> DownloadParametersFactory:
        return MoexDownloadParametersFactory()

    def get_generate_history_download_parameters_from_expected_result_with_none(self) \
            -> InstrumentHistoryDownloadParameters:
        # noinspection PyTypeChecker
        expected_result = MoexSecurityHistoryDownloadParameters(board=None, sec_id=None, start=0)
        return expected_result
