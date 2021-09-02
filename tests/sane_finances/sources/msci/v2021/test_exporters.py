#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import datetime
import decimal

from sane_finances.sources.base import CheckApiActualityError, ParseError, InstrumentExporterFactory
from sane_finances.sources.msci.v2021.exporters import (
    MsciDynamicEnumTypeManager, MsciIndexDownloadParameterValuesStorage,
    MsciStringDataDownloader, MsciApiActualityChecker, MsciIndexExporterFactory)
from sane_finances.sources.msci.v2021.meta import (
    MsciIndexHistoryDownloadParameters, MsciIndexesInfoDownloadParameters,
    IndexValue, IndexInfo, IndexPanelData, Frequency, Market, IndexSuite, IndexSuiteGroup,
    Style, Size, Scopes, IndexLevel, Currency)

from .fakes import (
    FakeDownloader, FakeMsciIndexPanelDataJsonParser,
    FakeIndexInfoParser, FakeMsciHistoryJsonParser, FakeMsciStringDataDownloader,
    FakeMsciIndexDownloadParameterValuesStorage)
from .common import CommonTestCases


class TestMsciDynamicEnumTypeManager(unittest.TestCase):

    def test_is_dynamic_enum_type_Success(self):
        manager = MsciDynamicEnumTypeManager()
        all_types = manager.get_all_managed_types()

        for dynamic_enum_type in all_types:
            self.assertTrue(manager.is_dynamic_enum_type(dynamic_enum_type))

    def test_is_dynamic_enum_type_FalseWithWrongType(self):
        manager = MsciDynamicEnumTypeManager()

        # noinspection PyTypeChecker
        self.assertFalse(manager.is_dynamic_enum_type(None))

    def test_get_dynamic_enum_key_Success(self):
        manager = MsciDynamicEnumTypeManager()
        instance = Market(identity='ID', name='NAME')

        self.assertEqual(manager.get_dynamic_enum_key(instance), instance.identity)

    def test_get_dynamic_enum_key_NoneWithWrongType(self):
        manager = MsciDynamicEnumTypeManager()

        self.assertIsNone(manager.get_dynamic_enum_key(None))


class TestMsciIndexDownloadParameterValuesStorage(unittest.TestCase):

    def setUp(self):
        self.daily_frequency = Frequency(identity='DAILY', name='Daily')
        self.monthly_frequency = Frequency(identity='END_OF_MONTH', name='Monthly')
        index_suite_group = IndexSuiteGroup(name='ID')
        self.fake_index_panel_data = IndexPanelData(
            markets=(Market(identity='ID', name='NAME'),),
            currencies=(Currency(identity='ID', name='NAME'),),
            index_levels=(IndexLevel(identity='ID', name='NAME'),),
            frequencies=(self.daily_frequency, self.monthly_frequency, Frequency(identity='ID', name='NAME')),
            index_suite_groups=(index_suite_group,),
            index_suites=(IndexSuite(identity='ID', name='NAME', group=index_suite_group),),
            sizes=(Size(identity='ID', name='NAME'),),
            styles=(Style(identity='ID', name='NAME'),),
            daily_frequency=self.daily_frequency,
            monthly_frequency=self.monthly_frequency
        )

        self.downloader = FakeDownloader(None)
        self.index_panel_data_json_parser = FakeMsciIndexPanelDataJsonParser(self.fake_index_panel_data)
        self.storage = MsciIndexDownloadParameterValuesStorage(
            self.downloader,
            self.index_panel_data_json_parser)

    def test_reload_Success(self):
        self.storage.reload()

        self.assertGreaterEqual(len(self.downloader.download_string_results), 1)
        self.assertTrue(all(result.is_correct
                            for result
                            in self.downloader.download_string_results))

    def test_reload_LastDownloadStringResultIsNotCorrectWhenError(self):
        self.index_panel_data_json_parser.parse_exception = ParseError('Error')

        with self.assertRaises(Exception):
            self.storage.reload()

        self.assertGreaterEqual(len(self.downloader.download_string_results), 1)
        self.assertIs(self.downloader.download_string_results[-1].is_correct, False)

    def test_daily_frequency_Success(self):
        self.assertEqual(self.storage.daily_frequency, self.daily_frequency)

    def test_monthly_frequency_Success(self):
        self.assertEqual(self.storage.monthly_frequency, self.monthly_frequency)

    def test_get_dynamic_enum_value_by_key_Success(self):
        all_types = self.storage.get_all_managed_types()
        for dynamic_enum_type in all_types:
            value = self.storage.get_dynamic_enum_value_by_key(dynamic_enum_type, 'ID')

            self.assertIsNotNone(value)

        # noinspection PyTypeChecker
        value = self.storage.get_dynamic_enum_value_by_key(None, 'ID')

        self.assertIsNone(value)

    def test_get_dynamic_enum_value_by_choice_Success(self):
        all_types = self.storage.get_all_managed_types()
        for dynamic_enum_type in all_types:
            value = self.storage.get_dynamic_enum_value_by_choice(dynamic_enum_type, 'ID')

            self.assertIsNotNone(value)

        # noinspection PyTypeChecker
        value = self.storage.get_dynamic_enum_value_by_choice(None, 'ID')

        self.assertIsNone(value)

    def test_get_all_parameter_values_for_Success(self):
        all_types = self.storage.get_all_managed_types()
        for dynamic_enum_type in all_types:
            value = self.storage.get_all_parameter_values_for(dynamic_enum_type)

            self.assertIsNotNone(value)

        # noinspection PyTypeChecker
        value = self.storage.get_all_parameter_values_for(None)

        self.assertIsNone(value)

    def test_get_parameter_type_choices_Success(self):
        all_types = self.storage.get_all_managed_types()
        for dynamic_enum_type in all_types:
            choices = self.storage.get_parameter_type_choices(dynamic_enum_type)

            self.assertIsNotNone(choices)

        # noinspection PyTypeChecker
        choices = self.storage.get_parameter_type_choices(None)

        self.assertIsNone(choices)


class TestMsciStringDataDownloader(unittest.TestCase):

    def setUp(self):
        self.fake_data = 'data'

        daily_frequency = Frequency(identity='FREQ ID', name='FREQ NAME')
        # noinspection PyTypeChecker
        self.index_panel_data = IndexPanelData(
            markets=(Market(identity='ID', name='NAME'),),
            currencies=(Currency(identity='ID', name='NAME'),),
            index_levels=(IndexLevel(identity='ID', name='NAME'),),
            frequencies=(),
            index_suite_groups=(),
            index_suites=(IndexSuite(identity='ID', name='NAME'),),
            sizes=(Size(identity='ID', name='NAME'),),
            styles=(Style(identity='ID', name='NAME'),),
            daily_frequency=daily_frequency,
            monthly_frequency=None
        )

        self.string_data_downloader = MsciStringDataDownloader(
            FakeDownloader(self.fake_data),
            FakeMsciIndexDownloadParameterValuesStorage(self.index_panel_data)
        )
        self.history_download_params = MsciIndexHistoryDownloadParameters(
            index_code='WHATEVER',
            currency=self.index_panel_data.currencies[0],
            index_variant=self.index_panel_data.index_levels[0])

    def test_adjust_download_instrument_history_parameters_Success(self):
        date_to = datetime.datetime.combine(
            self.string_data_downloader.minimal_date_to - datetime.timedelta(days=1),
            datetime.time.min)  # date before minimum allowed date to
        date_from = date_to - datetime.timedelta(days=1)

        params, moment_from, moment_to = self.string_data_downloader.adjust_download_instrument_history_parameters(
            parameters=self.history_download_params,
            moment_from=date_from,
            moment_to=date_to)

        self.assertEqual(moment_to.date(), self.string_data_downloader.minimal_date_to)
        self.assertLessEqual(moment_from, moment_to)
        self.assertIsNotNone(params)

    def test_download_instrument_history_string_Success(self):
        moment_from = datetime.datetime(2010, 1, 1, 12)  # has hours
        moment_to = moment_from + datetime.timedelta(days=1)

        result = self.string_data_downloader.download_instrument_history_string(
            self.history_download_params,
            moment_from,
            moment_to)

        self.assertEqual(result.downloaded_string, self.fake_data)

    def test_download_index_history_string_Success(self):
        date_from = datetime.date(2010, 1, 1)
        date_to = date_from + datetime.timedelta(days=1)

        result = self.string_data_downloader.download_index_history_string(
            'WHATEVER',
            self.index_panel_data.currencies[0],
            self.index_panel_data.index_levels[0],
            date_from,
            date_to)

        self.assertEqual(result.downloaded_string, self.fake_data)

    def test_download_instruments_info_string_Success(self):
        params = MsciIndexesInfoDownloadParameters.safe_create(
            index_scope=Scopes.REGIONAL,
            index_market=self.index_panel_data.markets[0],
            index_size=self.index_panel_data.sizes[0],
            index_style=self.index_panel_data.styles[0],
            index_suite=self.index_panel_data.index_suites[0])

        result = self.string_data_downloader.download_instruments_info_string(params)

        self.assertEqual(result.downloaded_string, self.fake_data)

    def test_download_indexes_info_string_Success(self):
        result = self.string_data_downloader.download_indexes_info_string(
            Scopes.REGIONAL,
            self.index_panel_data.markets[0],
            self.index_panel_data.sizes[0],
            self.index_panel_data.styles[0],
            self.index_panel_data.index_suites[0])

        self.assertEqual(result.downloaded_string, self.fake_data)


class TestMsciAPIActualityChecker(unittest.TestCase):

    def setUp(self):
        daily_frequency = Frequency(identity='DAY ID', name='FREQ NAME')
        monthly_frequency = Frequency(identity='MONTH ID', name='FREQ NAME')
        self.index_panel_data = IndexPanelData(
            markets=(Market(identity=MsciApiActualityChecker._expected_index_market_id, name='NAME'),),
            currencies=(Currency(identity=MsciApiActualityChecker._expected_currency_id, name='NAME'),),
            index_levels=(IndexLevel(identity=MsciApiActualityChecker._expected_index_level_id, name='NAME'),),
            frequencies=(daily_frequency,),
            index_suite_groups=(),
            index_suites=(IndexSuite(identity=MsciApiActualityChecker._expected_index_suite_id, name='NAME'),),
            sizes=(Size(identity=MsciApiActualityChecker._expected_index_size_id, name='NAME'),),
            styles=(Style(identity=MsciApiActualityChecker._expected_index_style_id, name='NAME'),),
            daily_frequency=daily_frequency,
            monthly_frequency=monthly_frequency
        )

        self.success_info_data = [IndexInfo(
            msci_index_code=MsciApiActualityChecker._expected_index_code,
            index_name=MsciApiActualityChecker._expected_index_name)
        ]
        self.index_info_parser = FakeIndexInfoParser(self.success_info_data)

        self.success_history_data = [IndexValue(
            calc_date=MsciApiActualityChecker._expected_start_date,
            level_eod=MsciApiActualityChecker._expected_value,
            msci_index_code=MsciApiActualityChecker._expected_index_code,
            index_variant_type=self.index_panel_data.index_levels[0],
            currency=self.index_panel_data.currencies[0]
        )]
        self.history_parser = FakeMsciHistoryJsonParser(self.success_history_data)
        self.string_data_downloader = FakeMsciStringDataDownloader(None, None)

    def get_checker(self):
        return MsciApiActualityChecker(
            FakeMsciIndexDownloadParameterValuesStorage(self.index_panel_data),
            self.string_data_downloader,
            self.history_parser,
            self.index_info_parser)

    def test_check_Success(self):
        checker = self.get_checker()
        checker.check()

        # check that there is no incorrect downloaded strings
        self.assertGreaterEqual(len(self.string_data_downloader.download_instruments_info_string_results), 1)
        self.assertFalse(any(result.is_correct is False
                             for result
                             in self.string_data_downloader.download_instruments_info_string_results))
        self.assertGreaterEqual(len(self.string_data_downloader.download_instrument_history_string_results), 1)
        self.assertFalse(any(result.is_correct is False
                             for result
                             in self.string_data_downloader.download_instrument_history_string_results))

    def test_check_raisesWhenInfoParseError(self):
        # corrupt data
        self.index_info_parser.parse_exception = ParseError('Error')
        checker = self.get_checker()

        with self.assertRaises(CheckApiActualityError):
            checker.check()

        self.assertGreaterEqual(len(self.string_data_downloader.download_instruments_info_string_results), 1)
        self.assertIs(self.string_data_downloader.download_instruments_info_string_results[-1].is_correct, False)

    def test_check_raisesWhenInfoUnknownError(self):
        # corrupt data
        self.index_info_parser.parse_exception = Exception('Error')
        checker = self.get_checker()

        with self.assertRaises(Exception):
            checker.check()

        self.assertGreaterEqual(len(self.string_data_downloader.download_instruments_info_string_results), 1)
        self.assertIs(self.string_data_downloader.download_instruments_info_string_results[-1].is_correct, False)

    def test_check_raisesWhenNoInfo(self):
        # corrupt data
        self.index_info_parser.fake_data = []  # No data
        checker = self.get_checker()

        with self.assertRaises(CheckApiActualityError):
            checker.check()

        self.assertGreaterEqual(len(self.string_data_downloader.download_instruments_info_string_results), 1)
        self.assertIs(self.string_data_downloader.download_instruments_info_string_results[-1].is_correct, False)

    def test_check_raisesWhenHistoryParseError(self):
        # corrupt data
        self.history_parser.parse_exception = ParseError('Error')
        checker = self.get_checker()

        with self.assertRaises(CheckApiActualityError):
            checker.check()

        self.assertGreaterEqual(len(self.string_data_downloader.download_instrument_history_string_results), 1)
        self.assertIs(self.string_data_downloader.download_instrument_history_string_results[-1].is_correct, False)

    def test_check_raisesWhenHistoryUnknownError(self):
        # corrupt data
        self.history_parser.parse_exception = Exception('Error')
        checker = self.get_checker()

        with self.assertRaises(Exception):
            checker.check()

        self.assertGreaterEqual(len(self.string_data_downloader.download_instrument_history_string_results), 1)
        self.assertIs(self.string_data_downloader.download_instrument_history_string_results[-1].is_correct, False)

    def test_check_raisesWhenNoHistory(self):
        # corrupt data
        self.history_parser.fake_data = []  # No data
        checker = self.get_checker()

        with self.assertRaises(CheckApiActualityError):
            checker.check()

        self.assertGreaterEqual(len(self.string_data_downloader.download_instrument_history_string_results), 1)
        self.assertIs(self.string_data_downloader.download_instrument_history_string_results[-1].is_correct, False)

    def test_check_raisesWhenWrongFirstDate(self):
        # corrupt data
        self.success_history_data[0].calc_date = datetime.date.max
        checker = self.get_checker()

        with self.assertRaises(CheckApiActualityError):
            checker.check()

    def test_check_raisesWhenWrongFirstValue(self):
        # corrupt data
        self.success_history_data[0].level_eod = decimal.Decimal(-1)
        checker = self.get_checker()

        with self.assertRaises(CheckApiActualityError):
            checker.check()

    def test_check_raisesWhenWrongFirstCode(self):
        # corrupt data
        self.success_history_data[0].msci_index_code = 'WRONG'
        checker = self.get_checker()

        with self.assertRaises(CheckApiActualityError):
            checker.check()

    def test_check_raisesWhenWrongMarket(self):
        # corrupt data
        self.index_panel_data = self.index_panel_data._replace(
            markets=(Market(identity='WRONG', name='NAME'),))

        checker = self.get_checker()

        with self.assertRaises(CheckApiActualityError):
            checker.check()

    def test_check_raisesWhenWrongCurrency(self):
        # corrupt data
        self.index_panel_data = self.index_panel_data._replace(
            currencies=(Currency(identity='WRONG', name='NAME'),))

        checker = self.get_checker()

        with self.assertRaises(CheckApiActualityError):
            checker.check()

    def test_check_raisesWhenWrongIndexLevel(self):
        # corrupt data
        self.index_panel_data = self.index_panel_data._replace(
            index_levels=(IndexLevel(identity='WRONG', name='NAME'),))

        checker = self.get_checker()

        with self.assertRaises(CheckApiActualityError):
            checker.check()

    def test_check_raisesWhenWrongIndexSuite(self):
        # corrupt data
        self.index_panel_data = self.index_panel_data._replace(
            index_suites=(IndexSuite(identity='WRONG', name='NAME'),))

        checker = self.get_checker()

        with self.assertRaises(CheckApiActualityError):
            checker.check()

    def test_check_raisesWhenWrongSize(self):
        # corrupt data
        self.index_panel_data = self.index_panel_data._replace(
            sizes=(Size(identity='WRONG', name='NAME'),))

        checker = self.get_checker()

        with self.assertRaises(CheckApiActualityError):
            checker.check()

    def test_check_raisesWhenWrongStyle(self):
        # corrupt data
        self.index_panel_data = self.index_panel_data._replace(
            styles=(Style(identity='WRONG', name='NAME'),))

        checker = self.get_checker()

        with self.assertRaises(CheckApiActualityError):
            checker.check()

    def test_check_raisesWhenIncorrectInfoJson(self):
        self.index_info_parser.parse_exception = ParseError('Fake error')
        checker = self.get_checker()

        with self.assertRaises(CheckApiActualityError):
            checker.check()

    def test_check_raisesWhenIncorrectHistoryJson(self):
        self.history_parser.parse_exception = ParseError('Fake error')
        checker = self.get_checker()

        with self.assertRaises(CheckApiActualityError):
            checker.check()

    def test_check_raisesWhenUnknownIndexCode(self):
        self.success_info_data[0] = IndexInfo(
            msci_index_code='WRONG',
            index_name=MsciApiActualityChecker._expected_index_name)
        checker = self.get_checker()

        with self.assertRaises(CheckApiActualityError):
            checker.check()

    def test_check_raisesWhenUnknownIndexName(self):
        self.success_info_data[0] = IndexInfo(
            msci_index_code=MsciApiActualityChecker._expected_index_code,
            index_name='WRONG')
        checker = self.get_checker()

        with self.assertRaises(CheckApiActualityError):
            checker.check()


class TestMsciIndexExporterFactory(CommonTestCases.CommonIndexExporterFactoryTests):

    def get_exporter_factory(self) -> InstrumentExporterFactory:
        return MsciIndexExporterFactory()

    def is_dynamic_enum_type_manager_singleton(self):
        return True

    def is_download_parameters_factory_singleton(self):
        return True
