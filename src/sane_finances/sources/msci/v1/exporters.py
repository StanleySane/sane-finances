#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Tools for download (export) index data from app2.msci.com
"""
import collections
import dataclasses
import logging
import typing
import datetime
import decimal
import inspect

from .meta import (Markets, Formats, Currencies, IndexLevels, Frequencies, Styles, Sizes, Scopes, Context,
                   IndexSuites, IndexSuiteGroups,
                   MsciIndexHistoryDownloadParameters, MsciIndexesInfoDownloadParameters,
                   MsciDownloadParametersFactory)
from .parsers import MsciHistoryXmlParser, MsciIndexInfoParser
from ...base import (
    ApiActualityChecker, InstrumentStringDataDownloader, ParseError,
    InstrumentExporterFactory, InstrumentHistoryValuesExporter, InstrumentsInfoExporter,
    DownloadParameterValuesStorage, CheckApiActualityError)
from ...generic import GenericInstrumentHistoryValuesExporter, GenericInstrumentsInfoExporter
from ....communication.downloader import Downloader, DownloadStringResult

logging.getLogger().addHandler(logging.NullHandler())


class MsciStringDataDownloader(InstrumentStringDataDownloader):
    """ Data downloader from app2.msci.com.

    The list of all instruments can be obtained from
    https://app2.msci.com/webapp/indexperf/pages/IEIPerformanceRegional.jsf

    There inside HTML, we can find all necessary instruments and their available values for REST API.

    Examples of HTML pages for browsing of index history:
    https://app2.msci.com/products/indexes/performance/regional_chart.html?asOf=Feb%2025,%202020&size=36&scope=R&style=C&currency=15&priceLevel=0&indexId=3478
    or
    https://app2.msci.com/products/indexes/performance/country_chart.html?asOf=Mar%2020,%202020&size=30&scope=C&style=C&currency=15&priceLevel=0&indexId=104

    When clicked "Add/Remove indexes" executes request like
    https://app2.msci.com/webapp/indexperf/charts?style=C&market=1896&getIndices=true&size=36&site=gimi&scope=R

    It returns list of indexes by specified parameters in form like
    ``<?xml version="1.0" ?><indices><index id="2670" name="AC AMERICAS" />...</indices>``

    When clicked "Update chart" executes request like
    https://app2.msci.com/webapp/indexperf/charts?endDate=25%20Feb%2C%202020&baseValue=false&frequency=D&currency=15&indices=3478%2CC%2C36&format=XML&site=gimi&scope=R&startDate=25%20Feb%2C%202016&priceLevel=0

    It returns a history of index values by specified parameters in form like
    ::

        <?xml version="1.0" ?>  <performance>
        <index id="EAFE,C,36">
          <asOf>
            <date>03/11/2016</date>
            <value>1,644.941</value>
          </asOf>
          ...
        </index>
      </performance>
    """

    IndexDataUrl = 'https://app2.msci.com/webapp/indexperf/charts'

    def __init__(self, downloader: Downloader):
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

        self.downloader = downloader

        # headers for HTTP
        self.headers: typing.Dict[str, str] = {}

        # common requests parameters
        self.get_indices = True
        self.site = 'gimi'
        self.format = Formats.XML
        self.base_value = False
        self.frequency = Frequencies.DAILY

    def adjust_download_instrument_history_parameters(
            self,
            parameters: MsciIndexHistoryDownloadParameters,
            moment_from: datetime.datetime,
            moment_to: datetime.datetime
    ) -> typing.Tuple[MsciIndexHistoryDownloadParameters, datetime.datetime, datetime.datetime]:

        parameters, moment_from, moment_to = super().adjust_download_instrument_history_parameters(
            parameters, moment_from, moment_to)
        parameters: MsciIndexHistoryDownloadParameters

        date_from = parameters.date_from
        if date_from < moment_from.date():
            # try to shift date_from closer to moment_from
            date_from = moment_from.date()

            parameters = dataclasses.replace(parameters, date_from=date_from)

        date_to = parameters.date_to
        if date_to != moment_to.date():
            # try to shift date_to closer to moment_from
            date_to = moment_to.date()

            parameters = dataclasses.replace(parameters, date_to=date_to)

        return parameters, moment_from, moment_to

    def paginate_download_instrument_history_parameters(
            self,
            parameters: MsciIndexHistoryDownloadParameters,
            moment_from: datetime.datetime,
            moment_to: datetime.datetime
    ) -> typing.Iterable[typing.Tuple[MsciIndexHistoryDownloadParameters, datetime.datetime, datetime.datetime]]:

        assert parameters.date_from <= parameters.date_to
        assert moment_from <= moment_to

        if moment_from.date() == moment_to.date():
            # if we need data only for one day, then we can't split it
            yield parameters, moment_from, moment_to
            return

        today = datetime.date.today()
        # this API can download daily data only for last 5 years
        five_years_ago = today.replace(year=today.year - 5)  # minimum date when we can get daily data

        if moment_from.date() >= five_years_ago or moment_to.date() < five_years_ago:
            # if we need data only for less than last 5 years,
            # or we don't need data for last 5 years,
            # then there's nothing to do
            yield parameters, moment_from, moment_to
            return

        # otherwise, we split interval in two parts:
        # - first part (data older than 5 years) will treat in monthly frequency
        # - second part (last 5 years) will treat in any desired frequency

        first_moment_from = moment_from
        date_to = five_years_ago - datetime.timedelta(days=1)
        first_moment_to = datetime.datetime.combine(date_to, datetime.time.min, tzinfo=moment_to.tzinfo)
        params_first = dataclasses.replace(parameters, date_to=date_to)
        if params_first.date_from > params_first.date_to:
            params_first = dataclasses.replace(params_first, date_from=params_first.date_to)

        second_moment_from = datetime.datetime.combine(five_years_ago, datetime.time.min, tzinfo=moment_from.tzinfo)
        second_moment_to = moment_to
        params_second = dataclasses.replace(parameters, date_from=five_years_ago)
        if params_second.date_from > params_second.date_to:
            params_second = dataclasses.replace(params_second, date_to=params_second.date_from)

        yield params_first, first_moment_from, first_moment_to
        yield params_second, second_moment_from, second_moment_to

    def download_instrument_history_string(
            self,
            parameters: MsciIndexHistoryDownloadParameters,
            moment_from: datetime.datetime,
            moment_to: datetime.datetime) -> DownloadStringResult:
        date_from = moment_from.date()
        date_to = moment_to.date()
        if moment_to.time() != datetime.time.min:
            date_to += datetime.timedelta(days=1)

        return self.download_index_history_string(
            parameters.index_id,
            parameters.context,
            parameters.index_level,
            parameters.currency,
            date_from,
            date_to)

    def download_instruments_info_string(self, parameters: MsciIndexesInfoDownloadParameters) -> DownloadStringResult:
        return self.download_indexes_info_string(parameters.market, parameters.context)

    def download_index_history_string(
            self,
            index_id: str,
            context: Context,
            index_level: IndexLevels,
            currency: Currencies,
            date_from: datetime.date,
            date_to: datetime.date) -> DownloadStringResult:
        """ Downloads data for one index as string.

        :param index_id: Index ID.
        :param context: Context.
        :param index_level: Index level.
        :param currency: Currency.
        :param date_from: Download interval beginning.
        :param date_to: Download interval ending.
        :return: Container with downloaded string.
        """
        index_param = f"{index_id},{context.style.value},{context.size.value}"

        params = [
            ('format', self.format.value),
            ('site', self.site),
            ('baseValue', str(self.base_value).lower()),
            ('indices', index_param),
            ('scope', context.scope.value),
            ('frequency', self.frequency.value),
            ('currency', currency.value),
            ('priceLevel', index_level.value),
            ('startDate', date_from.strftime("%d %b, %Y")),  # WARNING!!! locale dependent format
            ('endDate', date_to.strftime("%d %b, %Y"))  # WARNING!!! locale dependent format
        ]

        self.downloader.parameters = params
        self.downloader.headers = self.headers

        return self.downloader.download_string(self.IndexDataUrl)

    def download_indexes_info_string(self, market: Markets, context: Context) -> DownloadStringResult:
        """ Downloads the list of all available indexes by specified parameters

        :param market: Market.
        :param context: Context.
        :return: Container with downloaded string.
        """
        self.downloader.headers = {}
        self.downloader.parameters = [
            ('getIndices', str(self.get_indices).lower()),
            ('site', self.site),
            ('market', market.value),
            ('style', context.style.value),
            ('size', context.size.value),
            ('scope', context.scope.value)
        ]

        return self.downloader.download_string(self.IndexDataUrl)


class MsciApiActualityChecker(ApiActualityChecker):
    """ Verifies actuality and accessibility of REST API of app2.msci.com.
    """

    _expectedIndexName = 'USA'
    _expectedIndexContext = Context(style=Styles.NONE, size=Sizes.COUNTRY_STANDARD, scope=Scopes.COUNTRY)
    _expectedFirstDate = datetime.date(1969, 12, 31)
    _expectedFirstValue = decimal.Decimal('100.0')

    def __init__(self,
                 string_data_downloader: MsciStringDataDownloader,
                 history_xml_parser: MsciHistoryXmlParser,
                 index_info_parser: MsciIndexInfoParser):
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

        self.string_data_downloader = string_data_downloader
        self.history_xml_parser = history_xml_parser
        self.index_info_parser = index_info_parser

    def check(self):
        self.logger.info("Check actuality via index list")

        index_id = '104'  # USA
        index_market = Markets.COUNTRY_DEVELOPED_MARKETS
        index_context = self._expectedIndexContext
        index_level = IndexLevels.PRICE
        index_currency = Currencies.USD
        index_history_date_from, index_history_date_to = self._expectedFirstDate, datetime.date(2020, 1, 1)

        self.string_data_downloader.get_indices = True
        self.string_data_downloader.format = Formats.XML
        self.string_data_downloader.base_value = False
        self.string_data_downloader.frequency = Frequencies.MONTHLY

        xml_list_result = self.string_data_downloader.download_indexes_info_string(index_market, index_context)
        self.logger.debug(f"Got XML data:\n{xml_list_result.downloaded_string}")

        try:
            info_list = list(self.index_info_parser.parse(xml_list_result.downloaded_string))
        except ParseError as ex:
            xml_list_result.set_correctness(False)
            raise CheckApiActualityError(f"Unexpected index info XML: {ex.message}") from ex
        except Exception:
            xml_list_result.set_correctness(False)
            raise

        if len(info_list) == 0:
            xml_list_result.set_correctness(False)
            raise CheckApiActualityError("Unexpected index info list. No data")

        # here we know that check via index list was successful

        self.logger.info(f"Check actuality via index {index_id!r}")

        xml_history_result = self.string_data_downloader.download_index_history_string(
            index_id,
            index_context,
            index_level,
            index_currency,
            index_history_date_from,
            index_history_date_to
        )

        try:
            history = list(self.history_xml_parser.parse(
                xml_history_result.downloaded_string,
                tzinfo=None))
        except ParseError as ex:
            xml_history_result.set_correctness(False)
            raise CheckApiActualityError(f"Unexpected index history XML: {ex.message}") from ex
        except Exception:
            xml_history_result.set_correctness(False)
            raise

        history.sort(key=lambda v: v.date)

        first_value = history[0]  # for actuality checking one record is enough

        if first_value.index_name != self._expectedIndexName:
            xml_history_result.set_correctness(False)
            raise CheckApiActualityError(
                f"Unexpected index name. {first_value.index_name!r} != {self._expectedIndexName!r}")

        if first_value.size != self._expectedIndexContext.size:
            xml_history_result.set_correctness(False)
            raise CheckApiActualityError(
                f"Unexpected index size. {first_value.size!r} != {self._expectedIndexContext.size!r}")

        if first_value.style != self._expectedIndexContext.style:
            xml_history_result.set_correctness(False)
            raise CheckApiActualityError(
                f"Unexpected index style. {first_value.style} != {self._expectedIndexContext.style}")

        if first_value.date != self._expectedFirstDate:
            xml_history_result.set_correctness(False)
            raise CheckApiActualityError(
                f"Unexpected first date. {first_value.date} != {self._expectedFirstDate}")

        if first_value.value != self._expectedFirstValue:
            xml_history_result.set_correctness(False)
            raise CheckApiActualityError(
                f"Unexpected first value. {first_value.value} != {self._expectedFirstValue}")

        self.logger.info("Actuality check was successful")


class MsciIndexDownloadParameterValuesStorage(DownloadParameterValuesStorage):
    """ Storage of indexes download parameters.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

        self._special_handlers: typing.Dict[type, typing.Callable] = {
            Markets: self._get_markets_choices,
            Sizes: self._get_sizes_choices,
            IndexSuites: self._get_index_suites_choices
        }

    def is_dynamic_enum_type(self, cls: type) -> bool:
        return False

    def get_all_managed_types(self) -> typing.Iterable[typing.Type]:
        return ()

    def get_dynamic_enum_key(self, instance):
        return None

    def get_parameter_type_choices(self, cls: type) \
            -> typing.Optional[
                typing.List[typing.Tuple[typing.Any, typing.Union[str, typing.List[typing.Tuple[typing.Any, str]]]]]
            ]:

        if not inspect.isclass(cls):
            return None

        if cls not in self._special_handlers:
            return None

        return self._special_handlers[cls]()

    @staticmethod
    def _get_markets_choices():
        market: Markets

        grouped_markets = collections.OrderedDict()
        for market in Markets:
            if market.scope not in grouped_markets:
                grouped_markets[market.scope] = []
            grouped_markets[market.scope].append(market)

        return [(f"Available for {scope.description!r} scope:",
                 [(market.value, market.description) for market in markets])
                for scope, markets
                in grouped_markets.items()]

    @staticmethod
    def _get_sizes_choices():
        size: Sizes

        grouped_sizes = collections.OrderedDict({None: []})
        for size in Sizes:
            if not size.scopes:  # available for all scopes
                grouped_sizes[None].append(size)
            else:
                for scope in size.scopes:
                    if scope not in grouped_sizes:
                        grouped_sizes[scope] = []
                    grouped_sizes[scope].append(size)

        return [(size.value, size.description) for size in grouped_sizes[None]] + \
               [(f"Available for {scope.description!r} scope:",
                 [(size.value, size.description) for size in sizes])
                for scope, sizes
                in grouped_sizes.items() if scope is not None]

    @staticmethod
    def _get_index_suites_choices():
        suite: IndexSuites
        group: IndexSuiteGroups

        suites_without_groups = [(suite.value, suite.description) for suite in IndexSuites if suite.group is None]
        grouped_suites = [(group.value, [(suite.value, suite.description)
                                         for suite
                                         in IndexSuites
                                         if suite.group == group])
                          for group in IndexSuiteGroups]

        return suites_without_groups + grouped_suites


class MsciIndexExporterFactory(InstrumentExporterFactory):
    """ Factory class for create instances of MSCI data exporter.
    """
    name: str = 'MSCI index data exporter. Version before 2021.'
    provider_site: str = 'https://www.msci.com/'
    api_url: str = 'https://app2.msci.com/webapp/indexperf/pages/IEIPerformanceRegional.jsf'

    def __init__(self):
        self._dynamic_enum_type_manager = None
        self._download_parameters_factory = None

    def create_history_values_exporter(self, downloader: Downloader) -> InstrumentHistoryValuesExporter:
        string_data_downloader = MsciStringDataDownloader(downloader)
        history_values_parser = MsciHistoryXmlParser()

        return GenericInstrumentHistoryValuesExporter(string_data_downloader, history_values_parser)

    def create_info_exporter(self, downloader: Downloader) -> InstrumentsInfoExporter:
        string_data_downloader = MsciStringDataDownloader(downloader)
        info_parser = MsciIndexInfoParser()

        return GenericInstrumentsInfoExporter(string_data_downloader, info_parser)

    def create_download_parameter_values_storage(self, downloader: Downloader) -> DownloadParameterValuesStorage:
        return MsciIndexDownloadParameterValuesStorage()

    def create_api_actuality_checker(self, downloader: Downloader) -> MsciApiActualityChecker:
        string_data_downloader = MsciStringDataDownloader(downloader)
        history_values_parser = MsciHistoryXmlParser()
        info_parser = MsciIndexInfoParser()

        return MsciApiActualityChecker(string_data_downloader, history_values_parser, info_parser)

    @property
    def dynamic_enum_type_manager(self) -> MsciIndexDownloadParameterValuesStorage:
        if self._dynamic_enum_type_manager is None:
            self._dynamic_enum_type_manager = MsciIndexDownloadParameterValuesStorage()

        return self._dynamic_enum_type_manager

    @property
    def download_parameters_factory(self) -> MsciDownloadParametersFactory:
        if self._download_parameters_factory is None:
            self._download_parameters_factory = MsciDownloadParametersFactory()

        return self._download_parameters_factory
