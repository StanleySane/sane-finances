#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Tools for download (export) index data from app2.msci.com
"""
import logging
import typing
import datetime
import decimal
import inspect

from .meta import (
    Market, Currency, IndexLevel, Frequency, Style, Size, Scopes,
    IndexSuite, IndexSuiteGroup, IndexPanelData,
    MsciIndexHistoryDownloadParameters, MsciIndexesInfoDownloadParameters,
    MsciDownloadParametersFactory)
from .parsers import MsciHistoryJsonParser, MsciIndexInfoParser, MsciIndexPanelDataJsonParser
from ...base import (
    ApiActualityChecker, InstrumentStringDataDownloader, ParseError,
    InstrumentExporterFactory, InstrumentHistoryValuesExporter, InstrumentsInfoExporter, DynamicEnumTypeManager,
    DownloadParameterValuesStorage, CheckApiActualityError)
from ...generic import GenericInstrumentHistoryValuesExporter, GenericInstrumentsInfoExporter
from ....communication.downloader import Downloader, DownloadStringResult

logging.getLogger().addHandler(logging.NullHandler())


class MsciDynamicEnumTypeManager(DynamicEnumTypeManager):
    """ MSCI dynamic enum types manager.
    """

    def __init__(self):
        self._managed_types: typing.Dict[typing.Type, typing.Tuple] = {
            Market: ('markets', lambda it: it.identity),
            Currency: ('currencies', lambda it: it.identity),
            IndexLevel: ('index_levels', lambda it: it.identity),
            Frequency: ('frequencies', lambda it: it.identity),
            IndexSuiteGroup: ('index_suite_groups', lambda it: it.name),
            IndexSuite: ('index_suites', lambda it: it.identity),
            Size: ('sizes', lambda it: it.identity),
            Style: ('styles', lambda it: it.identity),
        }

    def is_dynamic_enum_type(self, cls: type) -> bool:
        if not inspect.isclass(cls):
            return False

        return cls in self._managed_types

    def get_all_managed_types(self) -> typing.Iterable[typing.Type]:
        return self._managed_types.keys()

    def get_dynamic_enum_key(self, instance):
        for managed_type, (_, key_getter, *_) in self._managed_types.items():
            if isinstance(instance, managed_type):
                return key_getter(instance)

        return None


class MsciIndexDownloadParameterValuesStorage(MsciDynamicEnumTypeManager, DownloadParameterValuesStorage):
    """ Storage of indexes download parameters.
    """
    index_panel_data_url = \
        'https://app2.msci.com/products/index-data-search/resources/index-data-search/js/data/index-panel-data.json'

    def __init__(
            self,
            downloader: Downloader,
            index_panel_data_json_parser: MsciIndexPanelDataJsonParser):
        super().__init__()
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

        self.downloader = downloader
        self.index_panel_data_json_parser = index_panel_data_json_parser

        # headers for HTTP
        self.headers: typing.Dict[str, str] = {}

        self._extended_managed_types: typing.Dict[typing.Type, typing.Tuple] = {
            Market: (self._get_markets_choices,),
            Currency: (self._get_currencies_choices,),
            IndexLevel: (self._get_index_levels_choices,),
            Frequency: (self._get_frequencies_choices,),
            IndexSuiteGroup: (self._get_index_suite_groups_choices,),
            IndexSuite: (self._get_index_suites_choices,),
            Size: (self._get_sizes_choices,),
            Style: (self._get_styles_choices,)
        }
        assert set(self._extended_managed_types.keys()) == set(self._managed_types.keys()), \
            ("MoexDynamicEnumTypeManager and MoexDownloadParameterValuesStorage "
             "has different managed types.")

        self.index_panel_data: typing.Optional[IndexPanelData] = None

    def reload(self) -> None:
        self.downloader.headers = self.headers
        self.downloader.parameters = []
        json_string_result = self.downloader.download_string(self.index_panel_data_url)
        try:
            index_panel_data = self.index_panel_data_json_parser.parse(json_string_result.downloaded_string)

        except Exception:
            json_string_result.set_correctness(False)
            raise

        json_string_result.set_correctness(True)
        self.index_panel_data = index_panel_data

    def _ensure_loaded(self):
        if self.index_panel_data is None:
            self.reload()

    @property
    def daily_frequency(self) -> Frequency:
        """ Value of daily frequency.
        """
        self._ensure_loaded()

        return self.index_panel_data.daily_frequency

    @property
    def monthly_frequency(self) -> Frequency:
        """ Value of monthly frequency.
        """
        self._ensure_loaded()

        return self.index_panel_data.monthly_frequency

    def _get_dynamic_enum_value_by_key(self, cls: type, key):
        """ """
        index_panel_data_attr_name, key_getter, *_ = self._managed_types[cls]
        enum_values = getattr(self.index_panel_data, index_panel_data_attr_name)

        for enum_value in enum_values:
            if key == key_getter(enum_value):
                return enum_value

        return None

    def get_dynamic_enum_value_by_key(self, cls: type, key) -> typing.Any:
        if not self.is_dynamic_enum_type(cls):
            return None

        self._ensure_loaded()

        return self._get_dynamic_enum_value_by_key(cls, key)

    def get_dynamic_enum_value_by_choice(self, cls: type, choice: str) -> typing.Any:
        if not self.is_dynamic_enum_type(cls):
            return None

        self._ensure_loaded()

        return self._get_dynamic_enum_value_by_key(cls, str(choice))

    def get_all_parameter_values_for(self, cls: type) -> typing.Optional[typing.Iterable]:
        if not self.is_dynamic_enum_type(cls):
            return None

        self._ensure_loaded()

        index_panel_data_attr_name, *_ = self._managed_types[cls]
        return getattr(self.index_panel_data, index_panel_data_attr_name)

    def get_parameter_type_choices(self, cls: type) \
            -> typing.Optional[
                typing.List[typing.Tuple[typing.Any, typing.Union[str, typing.List[typing.Tuple[typing.Any, str]]]]]
            ]:
        if not self.is_dynamic_enum_type(cls):
            return None

        self._ensure_loaded()

        choices_getter, *_ = self._extended_managed_types[cls]
        return choices_getter()

    def _get_markets_choices(self):
        markets_without_scope = [(market.identity, market.name)
                                 for market
                                 in self.index_panel_data.markets
                                 if market.scope is None]
        scopes = set(market.scope for market in self.index_panel_data.markets if market.scope is not None)
        scoped_markets = [(f"Available for {scope.description!r} scope:",
                           [(market.identity, market.name)
                            for market
                            in self.index_panel_data.markets
                            if market.scope == scope])
                          for scope in scopes]

        # noinspection PyTypeChecker
        return markets_without_scope + scoped_markets

    def _get_currencies_choices(self):
        return [(currency.identity, currency.name)
                for currency
                in self.index_panel_data.currencies]

    def _get_index_levels_choices(self):
        return [(index_level.identity, index_level.name)
                for index_level
                in self.index_panel_data.index_levels]

    def _get_frequencies_choices(self):
        return [(frequency.identity, frequency.name)
                for frequency
                in self.index_panel_data.frequencies]

    def _get_index_suite_groups_choices(self):
        return [(index_suite_group.name, index_suite_group.name)
                for index_suite_group
                in self.index_panel_data.index_suite_groups]

    def _get_index_suites_choices(self):
        suites_without_groups = [
            (suite.identity, suite.name)
            for suite in self.index_panel_data.index_suites
            if suite.group is None]
        grouped_suites = [
            (group.name, [(suite.identity, suite.name)
                          for suite
                          in self.index_panel_data.index_suites
                          if suite.group == group])
            for group
            in self.index_panel_data.index_suite_groups]

        # noinspection PyTypeChecker
        return suites_without_groups + grouped_suites

    def _get_sizes_choices(self):
        return [(size.identity, size.name)
                for size
                in self.index_panel_data.sizes]

    def _get_styles_choices(self):
        return [(style.identity, style.name)
                for style
                in self.index_panel_data.styles]


class MsciStringDataDownloader(InstrumentStringDataDownloader):
    """ Data downloader from app2.msci.com.
    """

    index_data_url = 'https://app2.msci.com/products/service/index/indexmaster/getLevelDataForGraph'
    search_indexes_url = 'https://app2.msci.com/products/service/index/indexmaster/searchIndexes'
    minimal_date_to = datetime.date(1997, 1, 1)

    def __init__(
            self,
            downloader: Downloader,
            download_parameter_values_storage: MsciIndexDownloadParameterValuesStorage):
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

        self.downloader = downloader
        self.download_parameter_values_storage = download_parameter_values_storage

        # headers for HTTP
        self.headers: typing.Dict[str, str] = {}

    def adjust_download_instrument_history_parameters(
            self,
            parameters: MsciIndexHistoryDownloadParameters,
            moment_from: datetime.datetime,
            moment_to: datetime.datetime
    ) -> typing.Tuple[MsciIndexHistoryDownloadParameters, datetime.datetime, datetime.datetime]:

        parameters, moment_from, moment_to = super().adjust_download_instrument_history_parameters(
            parameters, moment_from, moment_to)
        parameters: MsciIndexHistoryDownloadParameters

        if moment_to.date() < self.minimal_date_to:
            moment_to = datetime.datetime.combine(self.minimal_date_to, datetime.time.min, tzinfo=moment_to.tzinfo)

        return parameters, moment_from, moment_to

    def download_instrument_history_string(
            self,
            parameters: MsciIndexHistoryDownloadParameters,
            moment_from: datetime.datetime,
            moment_to: datetime.datetime) -> DownloadStringResult:
        date_from = moment_from.date()
        date_to = moment_to.date()
        if moment_to.time() != datetime.time.min:
            # if we ask some minutes from date_to beginning, then we must read next day too
            date_to += datetime.timedelta(days=1)

        return self.download_index_history_string(
            parameters.index_code,
            parameters.currency,
            parameters.index_variant,
            date_from,
            date_to)

    def download_instruments_info_string(
            self,
            parameters: MsciIndexesInfoDownloadParameters) -> DownloadStringResult:
        return self.download_indexes_info_string(
            parameters.index_scope,
            parameters.index_market,
            parameters.index_size,
            parameters.index_style,
            parameters.index_suite)

    def download_index_history_string(
            self,
            index_code: str,
            currency: Currency,
            index_variant: IndexLevel,
            date_from: datetime.date,
            date_to: datetime.date) -> DownloadStringResult:
        """ Downloads data for one index as string

        :param index_code: Index code.
        :param currency: Currency
        :param index_variant: Index level.
        :param date_from: Download interval beginning.
        :param date_to: Download interval ending.
        :return: Container with downloaded string.
        """
        params = [
            ('currency_symbol', str(currency.identity)),
            ('index_variant', str(index_variant.identity)),
            ('start_date', date_from.strftime("%Y%m%d")),
            ('end_date', date_to.strftime("%Y%m%d")),
            ('data_frequency', str(self.download_parameter_values_storage.daily_frequency.identity)),
            ('index_codes', str(index_code)),
        ]

        self.downloader.parameters = params
        self.downloader.headers = self.headers

        return self.downloader.download_string(self.index_data_url)

    def download_indexes_info_string(
            self,
            scope: Scopes,
            market: Market,
            size: Size,
            style: Style,
            index_suite: IndexSuite) -> DownloadStringResult:
        """ Downloads the list of all available indexes by specified parameters

        :param scope: Index scope.
        :param market: Index market.
        :param size: Index size.
        :param style: Index style.
        :param index_suite: Index suite.
        :return: Container with downloaded string.
        """
        self.downloader.headers = {}
        self.downloader.parameters = [
            ('index_market', market.identity),
            ('index_scope', scope.value),
            ('index_size', size.identity),
            ('index_style', style.identity),
            ('index_suite', index_suite.identity)
        ]

        return self.downloader.download_string(self.search_indexes_url)


class MsciApiActualityChecker(ApiActualityChecker):
    """ Verifies actuality and accessibility of REST API of app2.msci.com.
    """

    _expected_index_market_id = '16384'  # Developed Markets (DM)
    _expected_index_scope = Scopes.REGIONAL
    _expected_index_size_id = '12'  # Standard (Large+Mid Cap)
    _expected_index_style_id = 'None'  # None
    _expected_index_suite_id = 'C'  # None
    _expected_index_code = '990300'
    _expected_index_name = 'EAFE'
    _expected_currency_id = 'USD'  # USD
    _expected_index_level_id = 'STRD'  # Price
    _expected_start_date = datetime.date(1969, 12, 31)
    _expected_end_date = datetime.date(1997, 1, 1)
    _expected_value = decimal.Decimal(100)

    def __init__(self,
                 parameter_values_storage: MsciIndexDownloadParameterValuesStorage,
                 string_data_downloader: MsciStringDataDownloader,
                 history_json_parser: MsciHistoryJsonParser,
                 index_info_parser: MsciIndexInfoParser):
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

        self.parameter_values_storage = parameter_values_storage
        self.string_data_downloader = string_data_downloader
        self.history_json_parser = history_json_parser
        self.index_info_parser = index_info_parser

    def check(self):
        self.logger.info("Check actuality via index list")

        market = self.parameter_values_storage.get_dynamic_enum_value_by_key(Market, self._expected_index_market_id)
        if market is None:
            raise CheckApiActualityError(f"Not found market {self._expected_index_market_id!r}")

        size = self.parameter_values_storage.get_dynamic_enum_value_by_key(Size, self._expected_index_size_id)
        if size is None:
            raise CheckApiActualityError(f"Not found size {self._expected_index_size_id!r}")

        style = self.parameter_values_storage.get_dynamic_enum_value_by_key(Style, self._expected_index_style_id)
        if style is None:
            raise CheckApiActualityError(f"Not found style {self._expected_index_style_id!r}")

        suite = self.parameter_values_storage.get_dynamic_enum_value_by_key(IndexSuite, self._expected_index_suite_id)
        if suite is None:
            raise CheckApiActualityError(f"Not found index suite {self._expected_index_suite_id!r}")

        currency = self.parameter_values_storage.get_dynamic_enum_value_by_key(Currency, self._expected_currency_id)
        if currency is None:
            raise CheckApiActualityError(f"Not found currency {self._expected_currency_id!r}")

        index_level = self.parameter_values_storage.get_dynamic_enum_value_by_key(IndexLevel,
                                                                                  self._expected_index_level_id)
        if index_level is None:
            raise CheckApiActualityError(f"Not found index level {self._expected_index_level_id!r}")

        json_data_result = self.string_data_downloader.download_indexes_info_string(
            scope=self._expected_index_scope, market=market, size=size, style=style, index_suite=suite)

        self.logger.debug(f"Got JSON data:\n{json_data_result.downloaded_string}")

        try:
            info_dict = {index_info.msci_index_code: index_info
                         for index_info
                         in self.index_info_parser.parse(json_data_result.downloaded_string)}
        except ParseError as ex:
            json_data_result.set_correctness(False)
            raise CheckApiActualityError(f"Unexpected index info JSON: {ex.message}") from ex
        except Exception:
            json_data_result.set_correctness(False)
            raise

        if len(info_dict) == 0:
            json_data_result.set_correctness(False)
            raise CheckApiActualityError("Unexpected index info list. No data")

        index_info = info_dict.get(self._expected_index_code, None)
        if index_info is None:
            json_data_result.set_correctness(False)
            raise CheckApiActualityError(f"Not found index with code {self._expected_index_code!r}")
        if index_info.index_name != self._expected_index_name:
            json_data_result.set_correctness(False)
            raise CheckApiActualityError(f"Index with code {self._expected_index_code!r} changed name "
                                         f"from {self._expected_index_name} to {index_info.index_name}")

        # here we know that check via index list was successful

        self.logger.info(f"Check actuality via index {self._expected_index_name!r}")

        json_history_result = self.string_data_downloader.download_index_history_string(
            index_code=self._expected_index_code,
            currency=currency,
            index_variant=index_level,
            date_from=self._expected_start_date,
            date_to=self._expected_end_date
        )

        try:
            history = list(self.history_json_parser.parse(json_history_result.downloaded_string, tzinfo=None))
        except ParseError as ex:
            json_history_result.set_correctness(False)
            raise CheckApiActualityError(f"Unexpected index history JSON: {ex.message}") from ex
        except Exception:
            json_history_result.set_correctness(False)
            raise

        if not history:
            json_history_result.set_correctness(False)
            raise CheckApiActualityError("History is empty")

        history.sort(key=lambda v: v.calc_date)

        first_value = history[0]  # for actuality checking one record is enough

        if first_value.msci_index_code != self._expected_index_code:
            json_history_result.set_correctness(False)
            raise CheckApiActualityError(
                f"Unexpected index code. {first_value.msci_index_code!r} != {self._expected_index_code!r}")

        if first_value.calc_date != self._expected_start_date:
            json_history_result.set_correctness(False)
            raise CheckApiActualityError(
                f"Unexpected first date. {first_value.calc_date} != {self._expected_start_date}")

        if first_value.level_eod != self._expected_value:
            json_history_result.set_correctness(False)
            raise CheckApiActualityError(
                f"Unexpected first value. {first_value.level_eod} != {self._expected_value}")

        self.logger.info("Actuality check was successful")


class MsciIndexExporterFactory(InstrumentExporterFactory):
    """ Factory class for create instances of MSCI data exporter.
    """
    name: str = 'MSCI index data exporter. Version 2021.'
    provider_site: str = 'https://www.msci.com/'
    api_url: str = 'https://app2.msci.com/products/index-data-search/'

    def __init__(self):
        self._dynamic_enum_type_manager = None
        self._download_parameters_factory = None

    def create_history_values_exporter(self, downloader: Downloader) -> InstrumentHistoryValuesExporter:
        index_panel_data_json_parser = MsciIndexPanelDataJsonParser()
        parameter_values_storage = MsciIndexDownloadParameterValuesStorage(downloader, index_panel_data_json_parser)
        string_data_downloader = MsciStringDataDownloader(downloader, parameter_values_storage)
        history_values_parser = MsciHistoryJsonParser(parameter_values_storage)

        return GenericInstrumentHistoryValuesExporter(string_data_downloader, history_values_parser)

    def create_info_exporter(self, downloader: Downloader) -> InstrumentsInfoExporter:
        index_panel_data_json_parser = MsciIndexPanelDataJsonParser()
        parameter_values_storage = MsciIndexDownloadParameterValuesStorage(downloader, index_panel_data_json_parser)
        string_data_downloader = MsciStringDataDownloader(downloader, parameter_values_storage)
        info_parser = MsciIndexInfoParser()

        return GenericInstrumentsInfoExporter(string_data_downloader, info_parser)

    def create_download_parameter_values_storage(self, downloader: Downloader) -> DownloadParameterValuesStorage:
        index_panel_data_json_parser = MsciIndexPanelDataJsonParser()
        return MsciIndexDownloadParameterValuesStorage(downloader, index_panel_data_json_parser)

    def create_api_actuality_checker(self, downloader: Downloader) -> MsciApiActualityChecker:
        index_panel_data_json_parser = MsciIndexPanelDataJsonParser()
        parameter_values_storage = MsciIndexDownloadParameterValuesStorage(downloader, index_panel_data_json_parser)
        string_data_downloader = MsciStringDataDownloader(downloader, parameter_values_storage)
        history_values_parser = MsciHistoryJsonParser(parameter_values_storage)
        info_parser = MsciIndexInfoParser()

        return MsciApiActualityChecker(
            parameter_values_storage,
            string_data_downloader,
            history_values_parser,
            info_parser)

    @property
    def dynamic_enum_type_manager(self) -> MsciDynamicEnumTypeManager:
        if self._dynamic_enum_type_manager is None:
            self._dynamic_enum_type_manager = MsciDynamicEnumTypeManager()

        return self._dynamic_enum_type_manager

    @property
    def download_parameters_factory(self) -> MsciDownloadParametersFactory:
        if self._download_parameters_factory is None:
            self._download_parameters_factory = MsciDownloadParametersFactory()

        return self._download_parameters_factory
