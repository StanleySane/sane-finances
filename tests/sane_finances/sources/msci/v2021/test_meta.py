#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import decimal
import unittest

from sane_finances.sources.base import (
    InstrumentValue, InstrumentInfo, DownloadParametersFactory, InstrumentHistoryDownloadParameters)
from sane_finances.sources.msci.v2021.meta import (
    Market, Currency, IndexLevel, IndexSuite, Size, Style, Scopes,
    IndexValue, IndexInfo, MsciIndexHistoryDownloadParameters, MsciIndexesInfoDownloadParameters,
    MsciDownloadParametersFactory)
from .common import CommonTestCases


class TestMarket(unittest.TestCase):

    def test_safe_create_raiseWrongScope(self):
        with self.assertRaises(TypeError):
            # noinspection PyTypeChecker
            _ = Market.safe_create(identity='ID', name='NAME', scope=42)


class TestIndexSuite(unittest.TestCase):

    def test_safe_create_raiseWrongScope(self):
        with self.assertRaises(TypeError):
            # noinspection PyTypeChecker
            _ = IndexSuite.safe_create(identity='ID', name='NAME', group=42)


class TestIndexValue(unittest.TestCase):

    def test_instrument_value_Success(self):
        index_value = IndexValue(
            calc_date=datetime.date(2000, 12, 31),
            level_eod=decimal.Decimal(42),
            msci_index_code='990300',
            index_variant_type=IndexLevel(identity='ID', name='NAME'),
            currency=Currency(identity='ID', name='NAME'))
        expected_instrument_value = InstrumentValue(
            value=index_value.level_eod,
            moment=datetime.datetime.combine(index_value.calc_date, datetime.time.min, tzinfo=datetime.timezone.utc))

        instrument_value = index_value.get_instrument_value(datetime.timezone.utc)

        self.assertEqual(expected_instrument_value, instrument_value)

    def test_raiseWrongDate(self):
        with self.assertRaises(TypeError):
            # noinspection PyTypeChecker
            _ = IndexValue(
                calc_date=None,
                level_eod=decimal.Decimal(42),
                msci_index_code='990300',
                index_variant_type=IndexLevel(identity='ID', name='NAME'),
                currency=Currency(identity='ID', name='NAME'))

    def test_raiseWrongLevel(self):
        with self.assertRaises(TypeError):
            # noinspection PyTypeChecker
            _ = IndexValue(
                calc_date=datetime.date(2000, 12, 31),
                level_eod=decimal.Decimal(42),
                msci_index_code='990300',
                index_variant_type=None,
                currency=Currency(identity='ID', name='NAME'))

    def test_raiseWrongCurrency(self):
        with self.assertRaises(TypeError):
            # noinspection PyTypeChecker
            _ = IndexValue(
                calc_date=datetime.date(2000, 12, 31),
                level_eod=decimal.Decimal(42),
                msci_index_code='990300',
                index_variant_type=IndexLevel(identity='ID', name='NAME'),
                currency=None)


class TestIndexInfo(unittest.TestCase):

    def test_instrument_value_Success(self):
        index_info = IndexInfo(
            msci_index_code='CODE',
            index_name='NAME')
        expected_instrument_info = InstrumentInfo(code=index_info.msci_index_code, name=index_info.index_name)

        instrument_info = index_info.instrument_info

        self.assertEqual(expected_instrument_info, instrument_info)


class TestMsciIndexesInfoDownloadParameters(unittest.TestCase):

    def test_safe_create_Success(self):
        _ = MsciIndexesInfoDownloadParameters.safe_create(
            index_scope=Scopes.REGIONAL,
            index_market=Market(identity='ID', name='NAME'),
            index_size=Size(identity='ID', name='NAME'),
            index_style=Style(identity='ID', name='NAME'),
            index_suite=IndexSuite(identity='ID', name='NAME'))

    def test_safe_create_raiseWrongScope(self):
        with self.assertRaises(TypeError):
            # noinspection PyTypeChecker
            _ = MsciIndexesInfoDownloadParameters.safe_create(
                index_scope=None,
                index_market=Market(identity='ID', name='NAME'),
                index_size=Size(identity='ID', name='NAME'),
                index_style=Style(identity='ID', name='NAME'),
                index_suite=IndexSuite(identity='ID', name='NAME'))

    def test_safe_create_raiseWrongMarket(self):
        with self.assertRaises(TypeError):
            # noinspection PyTypeChecker
            _ = MsciIndexesInfoDownloadParameters.safe_create(
                index_scope=Scopes.REGIONAL,
                index_market=None,
                index_size=Size(identity='ID', name='NAME'),
                index_style=Style(identity='ID', name='NAME'),
                index_suite=IndexSuite(identity='ID', name='NAME'))

    def test_safe_create_raiseWrongSize(self):
        with self.assertRaises(TypeError):
            # noinspection PyTypeChecker
            _ = MsciIndexesInfoDownloadParameters.safe_create(
                index_scope=Scopes.REGIONAL,
                index_market=Market(identity='ID', name='NAME'),
                index_size=None,
                index_style=Style(identity='ID', name='NAME'),
                index_suite=IndexSuite(identity='ID', name='NAME'))

    def test_safe_create_raiseWrongStyle(self):
        with self.assertRaises(TypeError):
            # noinspection PyTypeChecker
            _ = MsciIndexesInfoDownloadParameters.safe_create(
                index_scope=Scopes.REGIONAL,
                index_market=Market(identity='ID', name='NAME'),
                index_size=Size(identity='ID', name='NAME'),
                index_style=None,
                index_suite=IndexSuite(identity='ID', name='NAME'))

    def test_safe_create_raiseWrongIndexSuite(self):
        with self.assertRaises(TypeError):
            # noinspection PyTypeChecker
            _ = MsciIndexesInfoDownloadParameters.safe_create(
                index_scope=Scopes.REGIONAL,
                index_market=Market(identity='ID', name='NAME'),
                index_size=Size(identity='ID', name='NAME'),
                index_style=Style(identity='ID', name='NAME'),
                index_suite=None)


class TestMsciIndexHistoryDownloadParameters(unittest.TestCase):

    def test_safe_create_Success(self):
        _ = MsciIndexHistoryDownloadParameters.safe_create(
            index_code='CODE',
            currency=Currency(identity='ID', name='NAME'),
            index_variant=IndexLevel(identity='ID', name='NAME'))

    def test_safe_create_raiseWrongCurrency(self):
        with self.assertRaises(TypeError):
            # noinspection PyTypeChecker
            _ = MsciIndexHistoryDownloadParameters.safe_create(
                index_code='CODE',
                currency=None,
                index_variant=IndexLevel(identity='ID', name='NAME'))

    def test_safe_create_raiseWrongIndexLevel(self):
        with self.assertRaises(TypeError):
            # noinspection PyTypeChecker
            _ = MsciIndexHistoryDownloadParameters.safe_create(
                index_code='CODE',
                currency=Currency(identity='ID', name='NAME'),
                index_variant=None)

    def test_clone_with_instrument_info_parameters_Success(self):
        params = MsciIndexHistoryDownloadParameters(
            index_code='CODE',
            currency=Currency(identity='ID', name='NAME'),
            index_variant=IndexLevel(identity='ID', name='NAME'))
        expected_result = params

        result = params.clone_with_instrument_info_parameters(None, None)

        self.assertEqual(expected_result, result)


class TestMsciDownloadParametersFactory(CommonTestCases.CommonDownloadParametersFactoryTests):

    def get_download_parameters_factory(self) -> DownloadParametersFactory:
        return MsciDownloadParametersFactory()

    def get_generate_history_download_parameters_from_expected_result_with_none(self) \
            -> InstrumentHistoryDownloadParameters:
        # noinspection PyTypeChecker
        expected_result = MsciIndexHistoryDownloadParameters(index_code=None, currency=None, index_variant=None)
        return expected_result
