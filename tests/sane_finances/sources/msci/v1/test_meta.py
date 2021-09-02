#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import decimal
import unittest

from sane_finances.sources.base import InstrumentValue, InstrumentInfo, DownloadParametersFactory, \
    InstrumentHistoryDownloadParameters
from sane_finances.sources.msci.v1.meta import (
    Scopes, Formats, Context,
    IndexValue, IndexInfo, MsciIndexHistoryDownloadParameters, MsciIndexesInfoDownloadParameters,
    MsciDownloadParametersFactory, Styles, Sizes, Markets, IndexLevels, Currencies)
from .common import CommonTestCases


class TestFormats(unittest.TestCase):

    def test_get_file_extension_Success(self):
        for value in Formats:
            _ = Formats.get_file_extension(value)


class TestIndexValue(unittest.TestCase):

    def test_instrument_value_Success(self):
        index_value = IndexValue(
            date=datetime.date(2000, 12, 31),
            value=decimal.Decimal(42),
            index_name='NAME',
            style=Styles.NONE,
            size=Sizes.REGIONAL_STANDARD)
        expected_instrument_value = InstrumentValue(
            value=index_value.value,
            moment=datetime.datetime.combine(index_value.date, datetime.time.min, tzinfo=datetime.timezone.utc))

        instrument_value = index_value.get_instrument_value(datetime.timezone.utc)

        self.assertEqual(expected_instrument_value, instrument_value)

    def test_raiseWrongDate(self):
        with self.assertRaises(TypeError):
            # noinspection PyTypeChecker
            _ = IndexValue(
                date=None,
                value=decimal.Decimal(42),
                index_name='NAME',
                style=Styles.NONE,
                size=Sizes.REGIONAL_STANDARD)


class TestIndexInfo(unittest.TestCase):

    def test_instrument_value_Success(self):
        index_info = IndexInfo(
            index_id='CODE',
            name='NAME')
        expected_instrument_info = InstrumentInfo(code=index_info.index_id, name=index_info.name)

        instrument_info = index_info.instrument_info

        self.assertEqual(expected_instrument_info, instrument_info)


class TestMsciIndexesInfoDownloadParameters(unittest.TestCase):

    def test_safe_create_Success(self):
        _ = MsciIndexesInfoDownloadParameters.safe_create(
            market=Markets.COUNTRY_DEVELOPED_MARKETS,
            context=Context(style=Styles.NONE, size=Sizes.REGIONAL_STANDARD, scope=Scopes.REGIONAL))

    def test_safe_create_raiseWrongContext(self):
        with self.assertRaises(TypeError):
            # noinspection PyTypeChecker
            _ = MsciIndexesInfoDownloadParameters.safe_create(
                market=Markets.COUNTRY_DEVELOPED_MARKETS,
                context=None)


class TestMsciIndexHistoryDownloadParameters(unittest.TestCase):

    def test_safe_create_Success(self):
        _ = MsciIndexHistoryDownloadParameters.safe_create(
            index_id='CODE',
            context=Context(style=Styles.NONE, size=Sizes.REGIONAL_STANDARD, scope=Scopes.REGIONAL),
            index_level=IndexLevels.PRICE,
            currency=Currencies.USD,
            date_from=datetime.date(2000, 12, 31),
            date_to=datetime.date(2000, 12, 31))

    def test_safe_create_raiseWrongContext(self):
        with self.assertRaises(TypeError):
            # noinspection PyTypeChecker
            _ = MsciIndexHistoryDownloadParameters.safe_create(
                index_id='CODE',
                context=None,
                index_level=IndexLevels.PRICE,
                currency=Currencies.USD,
                date_from=datetime.date(2000, 12, 31),
                date_to=datetime.date(2000, 12, 31))

    def test_safe_create_raiseWrongDateFrom(self):
        with self.assertRaises(TypeError):
            # noinspection PyTypeChecker
            _ = MsciIndexHistoryDownloadParameters.safe_create(
                index_id='CODE',
                context=Context(style=Styles.NONE, size=Sizes.REGIONAL_STANDARD, scope=Scopes.REGIONAL),
                index_level=IndexLevels.PRICE,
                currency=Currencies.USD,
                date_from=None,
                date_to=datetime.date(2000, 12, 31))

    def test_safe_create_raiseWrongDateTo(self):
        with self.assertRaises(TypeError):
            # noinspection PyTypeChecker
            _ = MsciIndexHistoryDownloadParameters.safe_create(
                index_id='CODE',
                context=Context(style=Styles.NONE, size=Sizes.REGIONAL_STANDARD, scope=Scopes.REGIONAL),
                index_level=IndexLevels.PRICE,
                currency=Currencies.USD,
                date_from=datetime.date(2000, 12, 31),
                date_to=None)

    def test_safe_create_raiseWrongDates(self):
        date_from = datetime.date(2000, 12, 31)
        date_to = date_from - datetime.timedelta(days=1)

        with self.assertRaises(ValueError):
            _ = MsciIndexHistoryDownloadParameters.safe_create(
                index_id='CODE',
                context=Context(style=Styles.NONE, size=Sizes.REGIONAL_STANDARD, scope=Scopes.REGIONAL),
                index_level=IndexLevels.PRICE,
                currency=Currencies.USD,
                date_from=date_from,
                date_to=date_to)

    def test_clone_with_instrument_info_parameters_Success(self):
        params = MsciIndexHistoryDownloadParameters(
            index_id='CODE',
            context=Context(style=Styles.NONE, size=Sizes.REGIONAL_STANDARD, scope=Scopes.REGIONAL),
            index_level=IndexLevels.PRICE,
            currency=Currencies.USD,
            date_from=datetime.date(2000, 12, 31),
            date_to=datetime.date(2000, 12, 31))
        expected_result = params

        result = params.clone_with_instrument_info_parameters(None, None)

        self.assertEqual(expected_result, result)


class TestMsciDownloadParametersFactory(CommonTestCases.CommonDownloadParametersFactoryTests):

    def get_download_parameters_factory(self) -> DownloadParametersFactory:
        return MsciDownloadParametersFactory()

    def get_generate_history_download_parameters_from_expected_result_with_none(self) \
            -> InstrumentHistoryDownloadParameters:
        # noinspection PyTypeChecker
        expected_result = MsciIndexHistoryDownloadParameters(
            index_id=None,
            context=None,
            index_level=None,
            currency=None,
            date_from=None,
            date_to=None)
        return expected_result
