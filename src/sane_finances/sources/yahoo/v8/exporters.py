#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Tools for download (export) instrument history data from https://finance.yahoo.com/
"""

import datetime
import logging
import typing
import urllib.parse

from .meta import (
    IntervalTypes, YahooInstrumentInfoDownloadParameters, YahooInstrumentHistoryDownloadParameters,
    YahooDownloadParametersFactory)
from .parsers import YahooQuotesJsonParser, YahooInstrumentInfoParser
from ...base import (
    ApiActualityChecker, InstrumentStringDataDownloader, InstrumentExporterFactory,
    InstrumentHistoryValuesExporter, InstrumentsInfoExporter,
    DownloadParameterValuesStorage, ParseError,
    CheckApiActualityError)
from ...generic import GenericInstrumentHistoryValuesExporter, GenericInstrumentsInfoExporter
from ....communication.downloader import Downloader, DownloadStringResult

logging.getLogger().addHandler(logging.NullHandler())


class YahooFinanceStringDataDownloader(InstrumentStringDataDownloader):
    """ Data downloader from https://finance.yahoo.com/.
    """

    quotes_history_url = 'https://query2.finance.yahoo.com/v8/finance/chart/'
    search_url = 'https://query2.finance.yahoo.com/v1/finance/search'

    def __init__(self, downloader: Downloader):
        """
        """
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

        self.downloader = downloader

        # headers HTTP
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/39.0.2171.95 Safari/537.36'
        }

        # query parameters
        self.instrument_history_interval_type = IntervalTypes.ONE_DAY

    def download_instrument_history_string(
            self,
            parameters: YahooInstrumentHistoryDownloadParameters,
            moment_from: datetime.datetime,
            moment_to: datetime.datetime) -> DownloadStringResult:
        return self.download_quotes_string(parameters.symbol, moment_from, moment_to)

    def download_instruments_info_string(
            self,
            parameters: YahooInstrumentInfoDownloadParameters) -> DownloadStringResult:
        return self.download_instruments_search_string(parameters.search_string)

    def download_quotes_string(
            self,
            symbol: str,
            moment_from: datetime.datetime,
            moment_to: datetime.datetime) -> DownloadStringResult:
        """ Downloads data for one instrument as string.

        :param symbol: Instrument symbol.
        :param moment_from: Download interval beginning.
        :param moment_to: Download interval ending.
        :return: Container with downloaded string.
        """
        headers = dict(self.headers)  # make a copy

        first_date = datetime.datetime(1970, 1, 1, tzinfo=moment_from.tzinfo)
        period1 = int((moment_from - first_date).total_seconds())
        period2 = int((moment_to - first_date).total_seconds())

        self.downloader.parameters = [
            ('interval', self.instrument_history_interval_type.value),
            ('period1', period1),
            ('period2', period2)
        ]
        self.downloader.headers = headers

        url = self.quotes_history_url + urllib.parse.quote(str(symbol))

        return self.downloader.download_string(url)

    def download_instruments_search_string(self, search_string: str) -> DownloadStringResult:
        """ Downloads string with the list of all found instruments

        :param search_string: String to search.
        :return: Container with downloaded string.
        """
        headers = dict(self.headers)  # make a copy

        self.downloader.parameters = [('q', str(search_string))]
        self.downloader.headers = headers

        return self.downloader.download_string(self.search_url)


class YahooFinanceApiActualityChecker(ApiActualityChecker):
    """ Verifies actuality and accessibility of REST API of finance.yahoo.com.
    """

    actuality_check_symbol = '^GSPC'  # S&P 500

    def __init__(self,
                 string_data_downloader: YahooFinanceStringDataDownloader,
                 json_parser: YahooQuotesJsonParser):
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

        self.string_data_downloader = string_data_downloader
        self.json_parser = json_parser

    def check(self):
        expected_symbol = self.actuality_check_symbol

        self.logger.info(f"Check actuality via {expected_symbol!r}")

        now = datetime.datetime.utcnow()
        str_data_result = self.string_data_downloader.download_quotes_string(
            symbol=expected_symbol,
            moment_from=now,
            moment_to=now
        )
        self.logger.debug(f"Got str data: {str_data_result.downloaded_string}")

        try:
            _ = list(self.json_parser.parse(str_data_result.downloaded_string, tzinfo=None))
        except ParseError as ex:
            str_data_result.set_correctness(False)
            raise CheckApiActualityError(f"Unexpected instrument history JSON: {ex.message}") from ex
        except Exception:
            str_data_result.set_correctness(False)
            raise

        self.logger.info("Actuality check was successful")


class YahooFinanceDownloadParameterValuesStorage(DownloadParameterValuesStorage):
    """ Storage of instruments download parameters.
    """

    def is_dynamic_enum_type(self, cls: type) -> bool:
        return False

    def get_all_managed_types(self) -> typing.Iterable[typing.Type]:
        return ()

    def get_dynamic_enum_key(self, instance):
        return None


class YahooFinanceExporterFactory(InstrumentExporterFactory):
    """ Factory class for create instances of Yahoo Finance data exporter.
    """
    name: str = 'Yahoo Finance data exporter. Version 8.'
    provider_site: str = 'https://finance.yahoo.com/'

    def __init__(self):
        self._dynamic_enum_type_manager = None
        self._download_parameters_factory = None

    def create_history_values_exporter(self, downloader: Downloader) -> InstrumentHistoryValuesExporter:
        string_data_downloader = YahooFinanceStringDataDownloader(downloader)
        history_values_parser = YahooQuotesJsonParser()

        return GenericInstrumentHistoryValuesExporter(string_data_downloader, history_values_parser)

    def create_info_exporter(self, downloader: Downloader) -> InstrumentsInfoExporter:
        string_data_downloader = YahooFinanceStringDataDownloader(downloader)
        info_parser = YahooInstrumentInfoParser()

        return GenericInstrumentsInfoExporter(string_data_downloader, info_parser)

    def create_download_parameter_values_storage(self, downloader: Downloader) -> DownloadParameterValuesStorage:
        return YahooFinanceDownloadParameterValuesStorage()

    def create_api_actuality_checker(self, downloader: Downloader) -> YahooFinanceApiActualityChecker:
        string_data_downloader = YahooFinanceStringDataDownloader(downloader)
        history_values_parser = YahooQuotesJsonParser()

        return YahooFinanceApiActualityChecker(string_data_downloader, history_values_parser)

    @property
    def dynamic_enum_type_manager(self) -> YahooFinanceDownloadParameterValuesStorage:
        if self._dynamic_enum_type_manager is None:
            self._dynamic_enum_type_manager = YahooFinanceDownloadParameterValuesStorage()

        return self._dynamic_enum_type_manager

    @property
    def download_parameters_factory(self) -> YahooDownloadParametersFactory:
        if self._download_parameters_factory is None:
            self._download_parameters_factory = YahooDownloadParametersFactory()

        return self._download_parameters_factory
