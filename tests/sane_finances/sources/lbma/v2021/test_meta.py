#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import decimal
import unittest

from sane_finances.sources.base import (
    InstrumentValue, DownloadParametersFactory, InstrumentHistoryDownloadParameters,
    DownloadParameterValuesStorage, InstrumentInfo)
from sane_finances.sources.lbma.v2021.meta import (
    PreciousMetalPrice, PreciousMetalInfo, Currencies, PreciousMetals,
    LbmaDownloadParametersFactory, LbmaPreciousMetalInfoDownloadParameters, LbmaPreciousMetalHistoryDownloadParameters)
from .common import CommonTestCases
from .fakes import FakeLbmaDownloadParameterValuesStorage


class TestPreciousMetalPrice(unittest.TestCase):

    def test_instrument_value_Success(self):
        metal_price = PreciousMetalPrice(
            date=datetime.date(2000, 12, 31),
            value=decimal.Decimal(42))
        expected_instrument_value = InstrumentValue(
            value=metal_price.value,
            moment=datetime.datetime.combine(metal_price.date, datetime.time.min, datetime.timezone.utc))

        instrument_value = metal_price.get_instrument_value(datetime.timezone.utc)

        self.assertEqual(expected_instrument_value, instrument_value)

    def test_RaiseWrongDate(self):
        with self.assertRaisesRegex(TypeError, "'date'"):
            # noinspection PyTypeChecker
            _ = PreciousMetalPrice(
                date=None,
                value=decimal.Decimal(42))


class TestPreciousMetalInfo(unittest.TestCase):

    def test_instrument_value_Success(self):
        metal_info = PreciousMetalInfo(metal=PreciousMetals.GOLD_AM)
        expected_instrument_info = InstrumentInfo(code=metal_info.metal.value, name=metal_info.metal.description)

        instrument_info = metal_info.instrument_info

        self.assertEqual(expected_instrument_info, instrument_info)


class TestLbmaPreciousMetalInfoDownloadParameters(unittest.TestCase):

    def test_safe_create_Success(self):
        self.assertIsInstance(
            LbmaPreciousMetalInfoDownloadParameters.safe_create(),
            LbmaPreciousMetalInfoDownloadParameters)


class TestLbmaPreciousMetalHistoryDownloadParameters(unittest.TestCase):

    def test_safe_create_Success(self):
        self.assertIsInstance(
            LbmaPreciousMetalHistoryDownloadParameters.safe_create(
                metal=PreciousMetals.GOLD_AM,
                currency=Currencies.USD),
            LbmaPreciousMetalHistoryDownloadParameters)

    def test_clone_with_instrument_info_parameters_Success(self):
        params = LbmaPreciousMetalHistoryDownloadParameters.safe_create(
                metal=PreciousMetals.GOLD_AM,
                currency=Currencies.USD)
        expected_result = params

        result = params.clone_with_instrument_info_parameters(None, None)

        self.assertEqual(expected_result, result)

    def test_RaiseWrongMetal(self):
        with self.assertRaisesRegex(TypeError, "'metal'"):
            # noinspection PyTypeChecker
            _ = LbmaPreciousMetalHistoryDownloadParameters.safe_create(
                metal=None,
                currency=Currencies.USD)

    def test_RaiseWrongCurrency(self):
        with self.assertRaisesRegex(TypeError, "'currency'"):
            # noinspection PyTypeChecker
            _ = LbmaPreciousMetalHistoryDownloadParameters.safe_create(
                metal=PreciousMetals.GOLD_AM,
                currency=None)


class TestLbmaDownloadParametersFactory(CommonTestCases.CommonDownloadParametersFactoryTests):

    def get_download_parameters_factory(self) -> DownloadParametersFactory:
        return LbmaDownloadParametersFactory()

    def get_generate_history_download_parameters_from_expected_result_with_none(self) \
            -> InstrumentHistoryDownloadParameters:
        # noinspection PyTypeChecker
        expected_result = LbmaPreciousMetalHistoryDownloadParameters(metal=None, currency=None)
        return expected_result

    def get_download_parameter_values_storage(self) -> DownloadParameterValuesStorage:
        return FakeLbmaDownloadParameterValuesStorage()


class TestMetaStrAndRepr(CommonTestCases.CommonStrAndReprTests):

    def get_testing_module(self):
        from sane_finances.sources.lbma.v2021 import meta
        return meta
