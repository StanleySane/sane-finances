#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import decimal
import unittest

from sane_finances.sources.base import (
    InstrumentValue, InstrumentInfo, DownloadParametersFactory, InstrumentHistoryDownloadParameters,
    DownloadParameterValuesStorage)
from sane_finances.sources.spdji.v2021.meta import (
    IndexFinderFilterGroup, IndexFinderFilter, Currency, ReturnType, IndexLevel, IndexInfo, IndexMetaData,
    SpdjIndexesInfoDownloadParameters, SpdjIndexHistoryDownloadParameters, SpdjDownloadParametersFactory)
from .common import CommonTestCases
from .fakes import FakeSpdjDownloadParameterValuesStorage


class TestIndexFinderFilterGroup(unittest.TestCase):

    def test_safe_create_Success(self):
        self.assertIsInstance(
            IndexFinderFilterGroup.safe_create(name='NAME', label='LABEL'),
            IndexFinderFilterGroup)


class TestIndexFinderFilter(unittest.TestCase):

    def test_safe_create_Success(self):
        self.assertIsInstance(
            IndexFinderFilter.safe_create(group=IndexFinderFilterGroup.safe_create(name='NAME', label='LABEL'),
                                          label='LABEL',
                                          value='VALUE'),
            IndexFinderFilter)

    def test_safe_create_RaiseWithWrongGroup(self):
        with self.assertRaisesRegex(TypeError, 'group'):
            # noinspection PyTypeChecker
            _ = IndexFinderFilter.safe_create(
                group=None,
                label='LABEL',
                value='VALUE'),


class TestCurrency(unittest.TestCase):

    def test_safe_create_Success(self):
        self.assertIsInstance(
            Currency.safe_create(currency_code='USD'),
            Currency)


class TestReturnType(unittest.TestCase):

    def test_safe_create_Success(self):
        self.assertIsInstance(
            ReturnType.safe_create(return_type_code='CODE', return_type_name='NAME'),
            ReturnType)


class TestIndexLevel(unittest.TestCase):

    def test_instrument_value_Success(self):
        index_level = IndexLevel(
            index_id='INDEX_ID',
            effective_date=datetime.datetime(2000, 12, 31, 12, tzinfo=datetime.timezone.utc),
            index_value=decimal.Decimal(42))
        expected_instrument_value = InstrumentValue(
            value=index_level.index_value,
            moment=index_level.effective_date.astimezone(datetime.timezone.utc))

        instrument_value = index_level.get_instrument_value(datetime.timezone.utc)

        self.assertEqual(expected_instrument_value, instrument_value)

    def test_RaiseWrongDate(self):
        with self.assertRaisesRegex(TypeError, 'effective_date'):
            # noinspection PyTypeChecker
            _ = IndexLevel(
                index_id='INDEX_ID',
                effective_date=None,
                index_value=decimal.Decimal(42))


class TestIndexInfo(unittest.TestCase):

    def test_instrument_value_Success(self):
        index_info = IndexInfo(
            index_id='INDEX_ID',
            index_name='NAME',
            url='URL')
        expected_instrument_info = InstrumentInfo(code=index_info.index_id, name=index_info.index_name)

        instrument_info = index_info.instrument_info

        self.assertEqual(expected_instrument_info, instrument_info)


class TestSpdjIndexesInfoDownloadParameters(unittest.TestCase):

    def test_safe_create_Success(self):
        self.assertIsInstance(
            SpdjIndexesInfoDownloadParameters.safe_create(index_finder_filter=None, page_number=1),
            SpdjIndexesInfoDownloadParameters)

    def test_safe_create_RaiseWithWrongFilters(self):
        with self.assertRaisesRegex(TypeError, 'index_finder_filter'):
            # noinspection PyTypeChecker
            _ = SpdjIndexesInfoDownloadParameters.safe_create(index_finder_filter=42, page_number=1)


class TestSpdjIndexHistoryDownloadParameters(unittest.TestCase):

    def test_safe_create_Success(self):
        currency = Currency(currency_code='USD')
        return_type = ReturnType(return_type_code='P-', return_type_name='PRICE')
        self.assertIsInstance(
            SpdjIndexHistoryDownloadParameters.safe_create(
                index_id='INDEX_ID',
                currency=currency,
                return_type=return_type),
            SpdjIndexHistoryDownloadParameters)

    def test_safe_create_RaiseWithWrongCurrency(self):
        currency = None
        return_type = ReturnType(return_type_code='P-', return_type_name='PRICE')
        with self.assertRaisesRegex(TypeError, 'currency'):
            # noinspection PyTypeChecker
            _ = SpdjIndexHistoryDownloadParameters.safe_create(
                index_id='INDEX_ID',
                currency=currency,
                return_type=return_type)

    def test_safe_create_RaiseWithWrongReturnType(self):
        currency = Currency(currency_code='USD')
        return_type = None
        with self.assertRaisesRegex(TypeError, 'return_type'):
            # noinspection PyTypeChecker
            _ = SpdjIndexHistoryDownloadParameters.safe_create(
                index_id='INDEX_ID',
                currency=currency,
                return_type=return_type)

    def test_clone_with_instrument_info_parameters_Success(self):
        currency = Currency(currency_code='USD')
        return_type = ReturnType(return_type_code='P-', return_type_name='PRICE')
        params = SpdjIndexHistoryDownloadParameters.safe_create(
            index_id='INDEX_ID',
            currency=currency,
            return_type=return_type)
        expected_result = params

        result = params.clone_with_instrument_info_parameters(None, None)

        self.assertEqual(expected_result, result)


class TestSpdjDownloadParametersFactory(CommonTestCases.CommonDownloadParametersFactoryTests):

    def get_download_parameters_factory(self) -> DownloadParametersFactory:
        return SpdjDownloadParametersFactory()

    def get_generate_history_download_parameters_from_expected_result_with_none(self) \
            -> InstrumentHistoryDownloadParameters:
        # noinspection PyTypeChecker
        expected_result = SpdjIndexHistoryDownloadParameters(
            index_id=None,
            currency=None,
            return_type=None)
        return expected_result

    def get_download_parameter_values_storage(self) -> DownloadParameterValuesStorage:
        fake_index_meta_data = IndexMetaData(
            currencies=(Currency.safe_create(currency_code='USD'),),
            return_types=(ReturnType.safe_create(return_type_code='P-', return_type_name='PRICE'),),
            index_finder_filters=()
        )
        group = IndexFinderFilterGroup.safe_create(name='GROUP_NAME', label='Group Label')
        fake_index_finder_filters = (
            IndexFinderFilter.safe_create(
                group=group,
                label='Label 1',
                value='ID'),
            IndexFinderFilter.safe_create(
                group=group,
                label='Label 2',
                value='ID2'))

        return FakeSpdjDownloadParameterValuesStorage(fake_index_meta_data, fake_index_finder_filters)


class TestMetaStrAndRepr(CommonTestCases.CommonStrAndReprTests):

    def get_testing_module(self):
        from sane_finances.sources.spdji.v2021 import meta
        return meta
