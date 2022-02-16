#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import decimal
import unittest

from sane_finances.sources.solactive.v2018.exporters import SolactiveDownloadParameterValuesStorage

from sane_finances.sources.base import (
    InstrumentValue, InstrumentInfo, DownloadParametersFactory, InstrumentHistoryDownloadParameters,
    DownloadParameterValuesStorage)
from sane_finances.sources.solactive.v2018.meta import (
    IndexValue, IndexInfo, SolactiveIndexesInfoDownloadParameters, SolactiveIndexHistoryDownloadParameters,
    SolactiveDownloadParametersFactory)
from .common import CommonTestCases


class TestIndexValue(unittest.TestCase):

    def test_instrument_value_Success(self):
        index_value = IndexValue(
            index_id='ID',
            moment=datetime.datetime(2000, 12, 31, 12, tzinfo=datetime.timezone.utc),
            value=decimal.Decimal(42))
        expected_instrument_value = InstrumentValue(
            value=index_value.value,
            moment=index_value.moment)

        instrument_value = index_value.get_instrument_value(datetime.timezone.utc)

        self.assertEqual(expected_instrument_value, instrument_value)

    def test_raiseWrongMoment(self):
        with self.assertRaises(TypeError):
            # noinspection PyTypeChecker
            _ = IndexValue(
                index_id='ID',
                moment=None,
                value=decimal.Decimal(42))


class TestIndexInfo(unittest.TestCase):

    def test_instrument_value_Success(self):
        index_info = IndexInfo(
            isin='ISIN',
            name='NAME')
        expected_instrument_info = InstrumentInfo(code=index_info.isin, name=index_info.name)

        instrument_info = index_info.instrument_info

        self.assertEqual(expected_instrument_info, instrument_info)


class TestSolactiveIndexesInfoDownloadParameters(unittest.TestCase):

    def test_safe_create_Success(self):
        self.assertIsInstance(
            SolactiveIndexesInfoDownloadParameters.safe_create(),
            SolactiveIndexesInfoDownloadParameters)


class TestSolactiveIndexHistoryDownloadParameters(unittest.TestCase):

    def test_safe_create_Success(self):
        _ = SolactiveIndexHistoryDownloadParameters.safe_create(isin='ISIN')

    def test_clone_with_instrument_info_parameters_Success(self):
        params = SolactiveIndexHistoryDownloadParameters.safe_create(isin='ISIN')
        expected_result = params

        result = params.clone_with_instrument_info_parameters(None, None)

        self.assertEqual(expected_result, result)


class TestSolactiveDownloadParametersFactory(CommonTestCases.CommonDownloadParametersFactoryTests):

    def get_download_parameters_factory(self) -> DownloadParametersFactory:
        return SolactiveDownloadParametersFactory()

    def get_generate_history_download_parameters_from_expected_result_with_none(self) \
            -> InstrumentHistoryDownloadParameters:
        # noinspection PyTypeChecker
        expected_result = SolactiveIndexHistoryDownloadParameters(isin=None)
        return expected_result

    def get_download_parameter_values_storage(self) -> DownloadParameterValuesStorage:
        return SolactiveDownloadParameterValuesStorage()
