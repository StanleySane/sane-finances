#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import decimal
import unittest

from sane_finances.sources.cbr.v2016.exporters import CbrCurrencyDownloadParameterValuesStorage
from sane_finances.sources.base import (
    InstrumentValue, InstrumentInfo, DownloadParametersFactory, InstrumentHistoryDownloadParameters,
    DownloadParameterValuesStorage)
from sane_finances.sources.cbr.v2016.meta import (
    RateFrequencies, CurrencyInfo, CurrencyRateValue,
    CbrCurrenciesInfoDownloadParameters, CbrCurrencyHistoryDownloadParameters, CbrDownloadParametersFactory)
from .common import CommonTestCases


class TestCurrencyRateValue(unittest.TestCase):

    def test_instrument_value_Success(self):
        index_value = CurrencyRateValue(
            date=datetime.date(2000, 12, 31),
            value=decimal.Decimal(42),
            nominal=42,
            currency_id='ID')
        expected_instrument_value = InstrumentValue(
            value=index_value.value / index_value.nominal,
            moment=datetime.datetime.combine(index_value.date, datetime.time.min, tzinfo=datetime.timezone.utc))

        instrument_value = index_value.get_instrument_value(datetime.timezone.utc)

        self.assertEqual(expected_instrument_value, instrument_value)

    def test_raiseWrongDate(self):
        with self.assertRaises(TypeError):
            # noinspection PyTypeChecker
            _ = CurrencyRateValue(
                date=None,
                value=decimal.Decimal(42),
                nominal=42,
                currency_id='ID')


class TestCurrencyInfo(unittest.TestCase):

    def test_instrument_value_Success(self):
        index_info = CurrencyInfo(
            currency_id='ID',
            name='NAME',
            eng_name='ENG NAME',
            nominal=42,
            parent_code='PARENT CODE')
        expected_instrument_info = InstrumentInfo(code=index_info.currency_id, name=index_info.name)

        instrument_info = index_info.instrument_info

        self.assertEqual(expected_instrument_info, instrument_info)


class TestCbrCurrenciesInfoDownloadParameters(unittest.TestCase):

    def test_safe_create_Success(self):
        _ = CbrCurrenciesInfoDownloadParameters.safe_create(rate_frequency=RateFrequencies.DAILY)

    def test_safe_create_RaiseWrongFrequency(self):
        with self.assertRaises(TypeError):
            # noinspection PyTypeChecker
            _ = CbrCurrenciesInfoDownloadParameters.safe_create(rate_frequency=None)


class TestCbrCurrencyHistoryDownloadParameters(unittest.TestCase):

    def test_safe_create_Success(self):
        _ = CbrCurrencyHistoryDownloadParameters.safe_create(currency_id='ID')

    def test_clone_with_instrument_info_parameters_Success(self):
        params = CbrCurrencyHistoryDownloadParameters.safe_create(currency_id='ID')
        expected_result = params

        result = params.clone_with_instrument_info_parameters(None, None)

        self.assertEqual(expected_result, result)


class TestCbrDownloadParametersFactory(CommonTestCases.CommonDownloadParametersFactoryTests):

    def get_download_parameters_factory(self) -> DownloadParametersFactory:
        return CbrDownloadParametersFactory()

    def get_generate_history_download_parameters_from_expected_result_with_none(self) \
            -> InstrumentHistoryDownloadParameters:
        # noinspection PyTypeChecker
        expected_result = CbrCurrencyHistoryDownloadParameters(currency_id=None)
        return expected_result

    def get_download_parameter_values_storage(self) -> DownloadParameterValuesStorage:
        return CbrCurrencyDownloadParameterValuesStorage()


class TestMetaStrAndRepr(CommonTestCases.CommonStrAndReprTests):

    def get_testing_module(self):
        from sane_finances.sources.cbr.v2016 import meta
        return meta
