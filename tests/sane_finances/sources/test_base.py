#!/usr/bin/python
# -*- coding: utf-8 -*-

import datetime
import typing
import unittest

from sane_finances.communication.downloader import DownloadStringResult
from sane_finances.sources.base import DownloadParameterValuesStorage
from sane_finances.sources.base import (
    InstrumentStringDataDownloader,
    InstrumentHistoryDownloadParameters)
from .fakes import FakeInstrumentHistoryDownloadParameters


class SomeDownloadParameterValuesStorage(DownloadParameterValuesStorage):

    def is_dynamic_enum_type(self, cls: type) -> bool:
        return False

    def get_all_managed_types(self) -> typing.Iterable[typing.Type]:
        return ()

    def get_dynamic_enum_key(self, instance):
        return None


class SomeInstrumentStringDataDownloader(InstrumentStringDataDownloader):

    def download_instrument_history_string(
            self,
            parameters: InstrumentHistoryDownloadParameters,
            moment_from: datetime.datetime,
            moment_to: datetime.datetime) -> DownloadStringResult:
        return DownloadStringResult('')

    def download_instruments_info_string(self, parameters) -> DownloadStringResult:
        return DownloadStringResult('')


class TestDownloadParameterValuesStorage(unittest.TestCase):
    """ Test default implementation of DownloadParameterValuesStorage base class
    """

    def test_reload_Success(self):
        storage = SomeDownloadParameterValuesStorage()

        storage.reload()

    def test_get_dynamic_enum_value_by_key_AlwaysReturnNone(self):
        storage = SomeDownloadParameterValuesStorage()

        self.assertIsNone(storage.get_dynamic_enum_value_by_key(int, 42))
        self.assertIsNone(storage.get_dynamic_enum_value_by_key(str, ''))
        self.assertIsNone(storage.get_dynamic_enum_value_by_key(DownloadParameterValuesStorage, None))

    def test_get_dynamic_enum_value_by_choice_AlwaysReturnNone(self):
        storage = SomeDownloadParameterValuesStorage()

        self.assertIsNone(storage.get_dynamic_enum_value_by_choice(int, '42'))
        self.assertIsNone(storage.get_dynamic_enum_value_by_choice(str, ''))
        self.assertIsNone(storage.get_dynamic_enum_value_by_choice(DownloadParameterValuesStorage, ''))

    def test_get_all_parameter_values_for_AlwaysReturnNone(self):
        storage = SomeDownloadParameterValuesStorage()

        self.assertIsNone(storage.get_all_parameter_values_for(int))
        self.assertIsNone(storage.get_all_parameter_values_for(str))
        self.assertIsNone(storage.get_all_parameter_values_for(DownloadParameterValuesStorage))

    def test_get_parameter_type_choices_AlwaysReturnNone(self):
        storage = SomeDownloadParameterValuesStorage()

        self.assertIsNone(storage.get_parameter_type_choices(int))
        self.assertIsNone(storage.get_parameter_type_choices(str))
        self.assertIsNone(storage.get_parameter_type_choices(DownloadParameterValuesStorage))


class TestInstrumentStringDataDownloader(unittest.TestCase):
    """ Test default implementation of InstrumentStringDataDownloader base class
    """

    def test_adjust_date_from_to_holidays_Success(self):
        storage = SomeInstrumentStringDataDownloader()

        date_from = datetime.datetime(2000, 1, 1, tzinfo=datetime.timezone.utc)  # New Year's Eve
        adjusted_date_from = storage.adjust_date_from_to_holidays(date_from)

        self.assertEqual(adjusted_date_from.year, date_from.year - 1)

        date_from = datetime.datetime(2000, 12, 25, tzinfo=datetime.timezone.utc)  # Christmas holidays
        adjusted_date_from = storage.adjust_date_from_to_holidays(date_from)

        self.assertLess(adjusted_date_from.day, date_from.day)

    def test_adjust_download_instrument_history_parameters_RaiseWhenWrongDates(self):
        storage = SomeInstrumentStringDataDownloader()

        params = FakeInstrumentHistoryDownloadParameters()
        moment_from = datetime.datetime(2000, 1, 1, tzinfo=datetime.timezone.utc)
        moment_to = moment_from - datetime.timedelta(days=1)

        self.assertGreater(moment_from, moment_to)

        with self.assertRaises(ValueError):
            _ = storage.adjust_download_instrument_history_parameters(
                params,
                moment_from,
                moment_to)

    def test_paginate_download_instrument_history_parameters_DoNothing(self):
        storage = SomeInstrumentStringDataDownloader()

        params = FakeInstrumentHistoryDownloadParameters()
        moment_from = datetime.datetime(2000, 1, 1, tzinfo=datetime.timezone.utc)
        moment_to = moment_from + datetime.timedelta(days=1)

        paginated_params = list(storage.paginate_download_instrument_history_parameters(
            params,
            moment_from,
            moment_to))

        self.assertSequenceEqual(paginated_params, [(params, moment_from, moment_to)])
