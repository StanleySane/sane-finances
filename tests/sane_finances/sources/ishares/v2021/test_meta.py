#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import decimal
import unittest

from sane_finances.sources.base import (
    InstrumentValue, DownloadParametersFactory, InstrumentHistoryDownloadParameters,
    DownloadParameterValuesStorage, InstrumentInfo)
from sane_finances.sources.ishares.v2021.meta import (
    PerformanceValue, ProductInfo, ISharesDownloadParametersFactory,
    ISharesInstrumentInfoDownloadParameters, ISharesInstrumentHistoryDownloadParameters)
from .common import CommonTestCases
from .fakes import FakeISharesDownloadParameterValuesStorage


class TestPerformanceValue(unittest.TestCase):

    def test_instrument_value_Success(self):
        performance_value = PerformanceValue(
            date=datetime.date(2000, 12, 31),
            value=decimal.Decimal(42))
        expected_instrument_value = InstrumentValue(
            value=performance_value.value,
            moment=datetime.datetime.combine(performance_value.date, datetime.time.min, datetime.timezone.utc))

        instrument_value = performance_value.get_instrument_value(datetime.timezone.utc)

        self.assertEqual(expected_instrument_value, instrument_value)

    def test_RaiseWrongDate(self):
        with self.assertRaisesRegex(TypeError, "'date'"):
            # noinspection PyTypeChecker
            _ = PerformanceValue(
                date=None,
                value=decimal.Decimal(42))


class TestProductInfo(unittest.TestCase):

    def test_instrument_value_Success(self):
        product_info = ProductInfo(
            local_exchange_ticker='TICKER',
            isin='ISIN',
            fund_name='FUND_NAME',
            inception_date=datetime.date(2000, 1, 1),
            product_page_url='URL')
        expected_instrument_info = InstrumentInfo(code=product_info.local_exchange_ticker, name=product_info.fund_name)

        instrument_info = product_info.instrument_info

        self.assertEqual(expected_instrument_info, instrument_info)

    def test_RaiseWrongDate(self):
        with self.assertRaisesRegex(TypeError, "'inception_date'"):
            # noinspection PyTypeChecker
            _ = ProductInfo(
                local_exchange_ticker='TICKER',
                isin='ISIN',
                fund_name='FUND_NAME',
                inception_date=None,
                product_page_url='URL')


class TestISharesInstrumentInfoDownloadParameters(unittest.TestCase):

    def test_safe_create_Success(self):
        self.assertIsInstance(
            ISharesInstrumentInfoDownloadParameters.safe_create(),
            ISharesInstrumentInfoDownloadParameters)


class TestISharesInstrumentHistoryDownloadParameters(unittest.TestCase):

    def test_safe_create_Success(self):
        self.assertIsInstance(
            ISharesInstrumentHistoryDownloadParameters.safe_create(product_page_url='URL'),
            ISharesInstrumentHistoryDownloadParameters)

    def test_clone_with_instrument_info_parameters_Success(self):
        params = ISharesInstrumentHistoryDownloadParameters.safe_create(product_page_url='URL')
        expected_result = params

        result = params.clone_with_instrument_info_parameters(None, None)

        self.assertEqual(expected_result, result)


class TestISharesDownloadParametersFactory(CommonTestCases.CommonDownloadParametersFactoryTests):

    def get_download_parameters_factory(self) -> DownloadParametersFactory:
        return ISharesDownloadParametersFactory()

    def get_generate_history_download_parameters_from_expected_result_with_none(self) \
            -> InstrumentHistoryDownloadParameters:
        # noinspection PyTypeChecker
        expected_result = ISharesInstrumentHistoryDownloadParameters(product_page_url=None)
        return expected_result

    def get_download_parameter_values_storage(self) -> DownloadParameterValuesStorage:
        return FakeISharesDownloadParameterValuesStorage()


class TestMetaStrAndRepr(CommonTestCases.CommonStrAndReprTests):

    def get_testing_module(self):
        from sane_finances.sources.ishares.v2021 import meta
        return meta
