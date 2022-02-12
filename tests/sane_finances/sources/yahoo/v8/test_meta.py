#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import decimal
import unittest

from sane_finances.sources.base import (
    InstrumentValue, InstrumentInfo, DownloadParametersFactory, InstrumentHistoryDownloadParameters)
from sane_finances.sources.yahoo.v8.meta import (
    InstrumentQuoteValue, InstrumentQuoteInfo,
    YahooInstrumentInfoDownloadParameters, YahooInstrumentHistoryDownloadParameters, YahooDownloadParametersFactory)
from .common import CommonTestCases


class TestIndexValue(unittest.TestCase):

    def test_instrument_value_Success(self):
        quote_value = InstrumentQuoteValue(
            symbol='SYMBOL',
            timestamp=datetime.datetime(2000, 12, 31, 12, tzinfo=datetime.timezone.utc),
            close=decimal.Decimal(42))
        expected_instrument_value = InstrumentValue(
            value=quote_value.close,
            moment=quote_value.timestamp.astimezone(datetime.timezone.utc))

        instrument_value = quote_value.get_instrument_value(datetime.timezone.utc)

        self.assertEqual(expected_instrument_value, instrument_value)

    def test_raiseWrongTimestamp(self):
        with self.assertRaises(TypeError):
            # noinspection PyTypeChecker
            _ = InstrumentQuoteValue(
                symbol='SYMBOL',
                timestamp=None,
                close=decimal.Decimal(42))


class TestInstrumentQuoteInfo(unittest.TestCase):

    def test_instrument_value_Success(self):
        quote_info = InstrumentQuoteInfo(
            symbol='SYMBOL',
            exchange='NYSE',
            short_name='SHORT NAME',
            long_name=None,
            type_disp=None,
            exchange_disp=None,
            is_yahoo_finance=True)
        expected_instrument_info = InstrumentInfo(code=quote_info.symbol, name=quote_info.short_name)

        instrument_info = quote_info.instrument_info

        self.assertEqual(expected_instrument_info, instrument_info)


class TestYahooInstrumentInfoDownloadParameters(unittest.TestCase):

    def test_safe_create_Success(self):
        self.assertIsInstance(
            YahooInstrumentInfoDownloadParameters.safe_create(search_string='TEST'),
            YahooInstrumentInfoDownloadParameters)


class TestYahooInstrumentHistoryDownloadParameters(unittest.TestCase):

    def test_safe_create_Success(self):
        self.assertIsInstance(
            YahooInstrumentHistoryDownloadParameters.safe_create(symbol='SYMBOL'),
            YahooInstrumentHistoryDownloadParameters)

    def test_clone_with_instrument_info_parameters_Success(self):
        params = YahooInstrumentHistoryDownloadParameters.safe_create(symbol='SYMBOL')
        expected_result = params

        result = params.clone_with_instrument_info_parameters(None, None)

        self.assertEqual(expected_result, result)


class TestYahooDownloadParametersFactory(CommonTestCases.CommonDownloadParametersFactoryTests):

    def get_download_parameters_factory(self) -> DownloadParametersFactory:
        return YahooDownloadParametersFactory()

    def get_generate_history_download_parameters_from_expected_result_with_none(self) \
            -> InstrumentHistoryDownloadParameters:
        # noinspection PyTypeChecker
        expected_result = YahooInstrumentHistoryDownloadParameters(symbol=None)
        return expected_result
