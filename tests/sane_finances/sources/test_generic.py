#!/usr/bin/python
# -*- coding: utf-8 -*-

import datetime
import decimal
import inspect
import typing
import unittest

from sane_finances.sources import generic
from sane_finances.sources.cbr.v2016.exporters import CbrCurrencyRatesExporterFactory
from sane_finances.sources.base import (
    MaxPagesLimitExceeded, InstrumentValuesHistoryEmpty,
    InstrumentInfo, InstrumentValue, ParseError, InstrumentExporterFactory, InstrumentExporterRegistry)
from .fakes import (
    FakeInstrumentHistoryDownloadParameters, FakeInstrumentInfoProvider, FakeInstrumentValueProvider,
    FakeInstrumentInfoParser, FakeInstrumentValuesHistoryParser, FakeInstrumentStringDataDownloader,
    FakeInstrumentExporterFactory)


class TestGenericInstrumentHistoryValuesExporter(unittest.TestCase):

    def setUp(self):
        self.string_data_downloader = FakeInstrumentStringDataDownloader('FAKE_INFO', 'FAKE_HISTORY')
        self.history_values_parser = FakeInstrumentValuesHistoryParser(
            self.string_data_downloader.fake_history_string)
        self.exporter = generic.GenericInstrumentHistoryValuesExporter(
            self.string_data_downloader, self.history_values_parser)

    def _prepare_expected_result(self, moment_from: datetime.datetime, moment_to: datetime.datetime):
        # parsed values contain dates below asked interval (before moment_from and after moment_to)
        parsed_values = []
        current_date = moment_from - datetime.timedelta(days=5)
        end_date = moment_to + datetime.timedelta(days=5)
        while current_date < end_date:
            parsed_values.append(FakeInstrumentValueProvider(InstrumentValue(
                moment=current_date, value=decimal.Decimal(42))))

            current_date += datetime.timedelta(days=1)

        # but expected result must contain only dates strictly inside the asked interval
        # (note FakeInstrumentStringDataDownloader adjusted parameters)
        expected_result = [
            parsed_value
            for parsed_value
            in parsed_values
            if moment_from <= parsed_value.get_instrument_value(tzinfo=moment_from.tzinfo).moment <= moment_to]

        # assert of arrange
        self.assertGreater(len([
            value
            for value
            in parsed_values
            if value.get_instrument_value(tzinfo=moment_from.tzinfo).moment < moment_from]), 0)
        self.assertGreater(len([
            value
            for value
            in parsed_values
            if value.get_instrument_value(tzinfo=moment_from.tzinfo).moment > moment_to]), 0)
        self.assertEqual(len([
            value
            for value
            in expected_result
            if (value.get_instrument_value(tzinfo=moment_from.tzinfo).moment < moment_from
                or value.get_instrument_value(tzinfo=moment_from.tzinfo).moment > moment_to)]), 0)

        return expected_result

    def test_success(self):
        moment_from = moment_to = datetime.datetime(2000, 1, 1)

        expected_result = [FakeInstrumentValueProvider(InstrumentValue(
            moment=moment_from, value=decimal.Decimal(42)))]
        self.history_values_parser.fake_result = expected_result

        history = list(self.exporter.export_instrument_history_values(
            FakeInstrumentHistoryDownloadParameters(),
            moment_from,
            moment_to))

        self.assertSequenceEqual(history, expected_result)
        self.assertEqual(self.string_data_downloader.download_instrument_history_string_counter, 1)
        self.assertTrue(all(result.is_correct
                            for result
                            in self.string_data_downloader.download_instrument_history_string_results))
        self.assertEqual(self.string_data_downloader.download_instruments_info_string_counter, 0)
        self.assertEqual(self.history_values_parser.parse_counter, 1)

    def test_returnOnlyAskedInterval(self):
        moment_from = datetime.datetime(2000, 1, 1)
        moment_to = moment_from + datetime.timedelta(days=5)

        # parsed values may contain dates below asked interval (before moment_from and after moment_to)
        # but expected result must contain only dates strictly inside the asked interval
        # (note that FakeInstrumentStringDataDownloader DO NOT adjust parameters here)
        expected_result = self._prepare_expected_result(moment_from, moment_to)
        self.history_values_parser.fake_result = expected_result

        history = list(self.exporter.export_instrument_history_values(
            FakeInstrumentHistoryDownloadParameters(),
            moment_from,
            moment_to))

        self.assertSequenceEqual(history, expected_result)
        self.assertEqual(self.string_data_downloader.download_instrument_history_string_counter, 1)
        self.assertTrue(all(result.is_correct
                            for result
                            in self.string_data_downloader.download_instrument_history_string_results))
        self.assertEqual(self.string_data_downloader.download_instruments_info_string_counter, 0)
        self.assertEqual(self.history_values_parser.parse_counter, 1)

    def test_returnOnlyAdjustedInterval(self):
        moment_from = datetime.datetime(2000, 1, 1)
        moment_to = moment_from + datetime.timedelta(days=5)
        adjusted_moment_from = moment_from - datetime.timedelta(days=2)
        adjusted_moment_to = moment_to + datetime.timedelta(days=2)

        self.assertNotEqual(moment_from, adjusted_moment_from)
        self.assertNotEqual(moment_to, adjusted_moment_to)

        # parsed values may contain dates below asked interval (before moment_from and after moment_to)
        # but expected result must contain only dates strictly inside the ADJUSTED interval
        # (note that FakeInstrumentStringDataDownloader DO adjust parameters here)
        expected_result = self._prepare_expected_result(adjusted_moment_from, adjusted_moment_to)

        # imitate adjustment:
        # noinspection PyUnusedLocal,PyShadowingNames
        def fake_adjust_download_instrument_history_parameters(parameters, moment_from, moment_to):
            return parameters, adjusted_moment_from, adjusted_moment_to

        self.string_data_downloader.adjust_download_instrument_history_parameters = \
            fake_adjust_download_instrument_history_parameters

        self.history_values_parser.fake_result = expected_result

        history = list(self.exporter.export_instrument_history_values(
            FakeInstrumentHistoryDownloadParameters(),
            moment_from,
            moment_to))

        self.assertSequenceEqual(history, expected_result)
        self.assertEqual(self.string_data_downloader.download_instrument_history_string_counter, 1)
        self.assertTrue(all(result.is_correct
                            for result
                            in self.string_data_downloader.download_instrument_history_string_results))
        self.assertEqual(self.string_data_downloader.download_instruments_info_string_counter, 0)
        self.assertEqual(self.history_values_parser.parse_counter, 1)

    def test_returnCallDownloadAndParseMultipleTimes(self):
        pages_count = 5
        moment_from = datetime.datetime(2000, 1, 1)
        moment_to = moment_from + datetime.timedelta(days=pages_count)

        # parsed values may contain dates below asked interval (before moment_from and after moment_to)
        # but expected result must contain only dates strictly inside the asked interval
        # (note that FakeInstrumentStringDataDownloader DO NOT adjust parameters here)
        parse_result = self._prepare_expected_result(moment_from, moment_to)
        expected_result = parse_result * pages_count

        # imitate pagination:
        # noinspection PyShadowingNames
        def fake_paginate_download_instrument_history_parameters(parameters, moment_from, moment_to):
            page_begin = moment_from
            while page_begin < moment_to:
                yield parameters, page_begin, page_begin
                page_begin += datetime.timedelta(days=1)

        self.string_data_downloader.paginate_download_instrument_history_parameters = \
            fake_paginate_download_instrument_history_parameters

        self.history_values_parser.fake_result = parse_result

        history = list(self.exporter.export_instrument_history_values(
            FakeInstrumentHistoryDownloadParameters(),
            moment_from,
            moment_to))

        self.assertSequenceEqual(history, expected_result)
        self.assertEqual(self.string_data_downloader.download_instrument_history_string_counter, pages_count)
        self.assertTrue(all(result.is_correct
                            for result
                            in self.string_data_downloader.download_instrument_history_string_results))
        self.assertEqual(self.string_data_downloader.download_instruments_info_string_counter, 0)
        self.assertEqual(self.history_values_parser.parse_counter, pages_count)

    def test_raiseWhenPagesLimitExceeded(self):
        pages_count = 5
        max_paged_parameters = pages_count - 1
        moment_from = datetime.datetime(2000, 1, 1)
        moment_to = moment_from + datetime.timedelta(days=pages_count)

        # parsed values may contain dates below asked interval (before moment_from and after moment_to)
        # but expected result must contain only dates strictly inside the asked interval
        # (note that FakeInstrumentStringDataDownloader DO NOT adjust parameters here)
        parse_result = self._prepare_expected_result(moment_from, moment_to)

        # imitate pagination:
        # noinspection PyShadowingNames
        def fake_paginate_download_instrument_history_parameters(parameters, moment_from, moment_to):
            page_begin = moment_from
            while page_begin < moment_to:
                yield parameters, page_begin, page_begin
                page_begin += datetime.timedelta(days=1)

        self.string_data_downloader.paginate_download_instrument_history_parameters = \
            fake_paginate_download_instrument_history_parameters

        self.history_values_parser.fake_result = parse_result
        self.exporter.max_paged_parameters = max_paged_parameters

        with self.assertRaises(MaxPagesLimitExceeded):
            _ = list(self.exporter.export_instrument_history_values(
                FakeInstrumentHistoryDownloadParameters(),
                moment_from,
                moment_to))

        self.assertTrue(all(result.is_correct
                            for result
                            in self.string_data_downloader.download_instrument_history_string_results))

    def test_raiseWhenMomentFromGreaterThenMomentTo(self):
        self.history_values_parser.fake_result = []

        moment_from = datetime.datetime(2000, 1, 1)
        moment_to = moment_from - datetime.timedelta(seconds=1)

        with self.assertRaises(ValueError):
            _ = list(self.exporter.export_instrument_history_values(
                FakeInstrumentHistoryDownloadParameters(),
                moment_from,
                moment_to))

    def test_acceptInstrumentValuesHistoryEmptyException(self):
        moment_from = datetime.datetime(2000, 1, 1)
        moment_to = moment_from + datetime.timedelta(days=5)

        fake_result = (result for result in ['DOESNT MATTER WHAT'])

        self.history_values_parser.parse_exception = InstrumentValuesHistoryEmpty()
        self.history_values_parser.fake_result = fake_result
        expected_result = []

        # verify arrange
        self.assertNotEqual(fake_result, expected_result)

        history = list(self.exporter.export_instrument_history_values(
            FakeInstrumentHistoryDownloadParameters(),
            moment_from,
            moment_to))

        self.assertSequenceEqual(history, expected_result)
        self.assertEqual(self.string_data_downloader.download_instruments_info_string_counter, 0)
        self.assertTrue(all(result.is_correct
                            for result
                            in self.string_data_downloader.download_instrument_history_string_results))

    def test_LastDownloadStringResultIsNotCorrectWhenError(self):
        moment_from = datetime.datetime(2000, 1, 1)
        moment_to = moment_from + datetime.timedelta(days=5)

        self.history_values_parser.parse_exception = ParseError('Error')
        self.history_values_parser.fake_result = []

        with self.assertRaises(Exception):
            _ = list(self.exporter.export_instrument_history_values(
                FakeInstrumentHistoryDownloadParameters(),
                moment_from,
                moment_to))

        self.assertEqual(self.string_data_downloader.download_instruments_info_string_counter, 0)
        self.assertGreaterEqual(len(self.string_data_downloader.download_instrument_history_string_results), 1)
        self.assertIs(self.string_data_downloader.download_instrument_history_string_results[-1].is_correct, False)


class TestGenericInstrumentsInfoExporter(unittest.TestCase):

    def setUp(self):
        self.string_data_downloader = FakeInstrumentStringDataDownloader('FAKE_INFO', 'FAKE_HISTORY')
        self.info_parser = FakeInstrumentInfoParser(self.string_data_downloader.fake_info_string)
        self.exporter = generic.GenericInstrumentsInfoExporter(
            self.string_data_downloader, self.info_parser)

    def test_success(self):
        expected_result = [
            FakeInstrumentInfoProvider(InstrumentInfo(code='SOME CODE', name='SOME NAME'))
        ]
        self.info_parser.fake_result = expected_result

        info_list = list(self.exporter.export_instruments_info(None))

        self.assertSequenceEqual(info_list, expected_result)
        self.assertEqual(self.string_data_downloader.download_instrument_history_string_counter, 0)
        self.assertEqual(self.string_data_downloader.download_instruments_info_string_counter, 1)
        self.assertTrue(all(result.is_correct
                            for result
                            in self.string_data_downloader.download_instruments_info_string_results))
        self.assertEqual(self.info_parser.parse_counter, 1)

    def test_LastDownloadStringResultIsNotCorrectWhenError(self):
        self.info_parser.fake_result = []
        self.info_parser.parse_exception = ParseError('Error')

        with self.assertRaises(Exception):
            _ = list(self.exporter.export_instruments_info(None))

        self.assertEqual(self.string_data_downloader.download_instrument_history_string_counter, 0)
        self.assertEqual(self.string_data_downloader.download_instruments_info_string_counter, 1)
        self.assertGreaterEqual(len(self.string_data_downloader.download_instruments_info_string_results), 1)
        self.assertIs(self.string_data_downloader.download_instruments_info_string_results[-1].is_correct, False)


class TestRegistry(unittest.TestCase):

    def test_get_all_instrument_exporters_Success(self):
        self.assertIsNotNone(generic.get_all_instrument_exporters())

    def test_get_instrument_exporter_by_factory_SuccessByClass(self):
        factory = CbrCurrencyRatesExporterFactory
        self.assertTrue(inspect.isclass(factory))

        self.assertIsNotNone(generic.get_instrument_exporter_by_factory(factory))

    def test_get_instrument_exporter_by_factory_SuccessByInstance(self):
        factory = CbrCurrencyRatesExporterFactory()
        self.assertTrue(isinstance(factory, InstrumentExporterFactory))

        self.assertIsNotNone(generic.get_instrument_exporter_by_factory(factory))

    def test_register_instrument_history_values_exporter_Success(self):
        fake_registry = InstrumentExporterRegistry(
            name='FACTORY NAME',
            factory=FakeInstrumentExporterFactory()
        )

        generic.register_instrument_history_values_exporter(fake_registry)

    def test_register_instrument_history_values_exporter_RaiseWithWrongArguments(self):
        new_factory_class = type('NewInstrumentExporterFactory', (FakeInstrumentExporterFactory,), {})

        expected_exceptions: typing.Tuple = (TypeError, ValueError)

        # can't register None
        with self.assertRaises(expected_exceptions):
            # noinspection PyTypeChecker
            generic.register_instrument_history_values_exporter(None)

        # can't register wrong type
        with self.assertRaises(expected_exceptions):
            # noinspection PyTypeChecker
            generic.register_instrument_history_values_exporter(object())

        # can't register with no name
        with self.assertRaises(expected_exceptions):
            # noinspection PyTypeChecker
            generic.register_instrument_history_values_exporter(InstrumentExporterRegistry(
                name=None,
                factory=new_factory_class()))

        # can't register with empty name
        with self.assertRaises(expected_exceptions):
            generic.register_instrument_history_values_exporter(InstrumentExporterRegistry(
                name='      ',  # spaces
                factory=new_factory_class()))

        # can't register with no factory
        with self.assertRaises(expected_exceptions):
            # noinspection PyTypeChecker
            generic.register_instrument_history_values_exporter(InstrumentExporterRegistry(
                name='FACTORY NAME',
                factory=None))

        # can't register with wrong factory
        with self.assertRaises(expected_exceptions):
            # noinspection PyTypeChecker
            generic.register_instrument_history_values_exporter(InstrumentExporterRegistry(
                name='FACTORY NAME',
                factory=object()))

        # register some factory
        generic.register_instrument_history_values_exporter(InstrumentExporterRegistry(
            name='FACTORY NAME',
            factory=new_factory_class()))

        # can't register same factory class
        with self.assertRaises(expected_exceptions):
            generic.register_instrument_history_values_exporter(InstrumentExporterRegistry(
                name='ANOTHER FACTORY NAME',
                factory=new_factory_class()))
