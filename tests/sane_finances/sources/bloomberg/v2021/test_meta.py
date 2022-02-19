#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import decimal
import unittest

from sane_finances.sources.base import (
    InstrumentValue, InstrumentInfo, DownloadParametersFactory, InstrumentHistoryDownloadParameters,
    DownloadParameterValuesStorage)
from sane_finances.sources.bloomberg.v2021.meta import (
    Timeframes, Intervals, InstrumentPrice, BloombergInstrumentInfo,
    BloombergHistoryDownloadParameters, BloombergInfoDownloadParameters, BloombergDownloadParametersFactory)
from .common import CommonTestCases
from .fakes import FakeBloombergDownloadParameterValuesStorage


class TestInstrumentPrice(unittest.TestCase):

    def test_instrument_value_Success(self):
        price = InstrumentPrice(
            ticker='TICKER',
            price_date=datetime.date.today(),
            price_value=decimal.Decimal(42))
        expected_instrument_value = InstrumentValue(
            value=price.price_value,
            moment=datetime.datetime.combine(price.price_date, datetime.time.min, datetime.timezone.utc))

        instrument_value = price.get_instrument_value(datetime.timezone.utc)

        self.assertEqual(expected_instrument_value, instrument_value)

    def test_RaiseWrongDate(self):
        with self.assertRaisesRegex(TypeError, "'price_date'"):
            # noinspection PyTypeChecker
            _ = InstrumentPrice(
                ticker='TICKER',
                price_date=None,
                price_value=decimal.Decimal(42))


class TestBloombergInstrumentInfo(unittest.TestCase):

    def test_instrument_info_Success(self):
        index_info = BloombergInstrumentInfo(
            ticker_symbol='TICKER',
            name='NAME',
            country=None,
            resource_type=None,
            resource_id=None,
            security_type=None,
            url=None)
        expected_instrument_info = InstrumentInfo(code=index_info.ticker_symbol, name=index_info.name)

        instrument_info = index_info.instrument_info

        self.assertEqual(expected_instrument_info, instrument_info)


class TestBloombergInfoDownloadParameters(unittest.TestCase):

    def test_safe_create_Success(self):
        self.assertIsInstance(
            BloombergInfoDownloadParameters.safe_create(search_string=''),
            BloombergInfoDownloadParameters)


class TestBloombergHistoryDownloadParameters(unittest.TestCase):

    def test_safe_create_Success(self):
        self.assertIsInstance(
            BloombergHistoryDownloadParameters.safe_create(
                ticker='TICKER',
                timeframe=Timeframes.FIVE_YEARS,
                interval=Intervals.DAILY),
            BloombergHistoryDownloadParameters)

    def test_safe_create_RaiseWithWrongTimeframe(self):
        with self.assertRaisesRegex(TypeError, "'timeframe'"):
            # noinspection PyTypeChecker
            _ = BloombergHistoryDownloadParameters.safe_create(
                ticker='TICKER',
                timeframe=None,
                interval=Intervals.DAILY)

    def test_safe_create_RaiseWithWrongInterval(self):
        with self.assertRaisesRegex(TypeError, "'interval'"):
            # noinspection PyTypeChecker
            _ = BloombergHistoryDownloadParameters.safe_create(
                ticker='TICKER',
                timeframe=Timeframes.FIVE_YEARS,
                interval=None)

    def test_clone_with_instrument_info_parameters_Success(self):
        params = BloombergHistoryDownloadParameters.safe_create(
                ticker='TICKER',
                timeframe=Timeframes.FIVE_YEARS,
                interval=Intervals.DAILY)
        expected_result = params

        result = params.clone_with_instrument_info_parameters(None, None)

        self.assertEqual(expected_result, result)


class TestBloombergDownloadParametersFactory(CommonTestCases.CommonDownloadParametersFactoryTests):

    def get_download_parameters_factory(self) -> DownloadParametersFactory:
        return BloombergDownloadParametersFactory()

    def get_generate_history_download_parameters_from_expected_result_with_none(self) \
            -> InstrumentHistoryDownloadParameters:
        # noinspection PyTypeChecker
        expected_result = BloombergHistoryDownloadParameters(
                ticker=None,
                timeframe=None,
                interval=None)
        return expected_result

    def get_download_parameter_values_storage(self) -> DownloadParameterValuesStorage:
        return FakeBloombergDownloadParameterValuesStorage()


class TestMetaStrAndRepr(CommonTestCases.CommonStrAndReprTests):

    def get_testing_module(self):
        from sane_finances.sources.bloomberg.v2021 import meta
        return meta
