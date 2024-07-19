#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Tools for download (export) instrument data from www.bloomberg.com
"""
import datetime
import inspect
import logging
import typing
import urllib.parse

from .meta import (
    Timeframes, Intervals,
    BloombergInfoDownloadParameters, BloombergDownloadParametersFactory,
    BloombergHistoryDownloadParameters)
from .parsers import BloombergInfoJsonParser, BloombergHistoryJsonParser
from ...base import (
    ApiActualityChecker, InstrumentStringDataDownloader, ParseError,
    InstrumentExporterFactory, InstrumentHistoryValuesExporter, InstrumentsInfoExporter,
    DownloadParameterValuesStorage, DownloadStringResult,
    CheckApiActualityError)
from ...generic import GenericInstrumentHistoryValuesExporter, GenericInstrumentsInfoExporter
from ....communication.downloader import Downloader

logging.getLogger().addHandler(logging.NullHandler())


class BloombergStringDataDownloader(InstrumentStringDataDownloader):
    """ Data downloader from www.bloomberg.com
    """

    _history_url_pattern = 'https://www.bloomberg.com/markets2/api/history/%s/PX_LAST'
    info_url = 'https://search.bloomberg.com/lookup.json'

    def __init__(self, downloader: Downloader):
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

        self.downloader = downloader

        # headers for HTTP
        self.headers: typing.Dict[str, str] = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0'
        }

        self.search_types = 'Company_Public,Index,Fund,Currency,Commodity,Bond'

    def download_instrument_history_string(
            self,
            parameters: BloombergHistoryDownloadParameters,
            moment_from: datetime.datetime,
            moment_to: datetime.datetime) -> DownloadStringResult:
        return self.download_history_string(parameters.ticker, parameters.timeframe, parameters.interval)

    def download_instruments_info_string(
            self,
            parameters: BloombergInfoDownloadParameters) -> DownloadStringResult:
        return self.download_info_string(search_string=parameters.search_string)

    def download_history_string(
            self,
            ticker: str,
            timeframe: Timeframes,
            interval: Intervals) -> DownloadStringResult:
        """ Downloads history data for one instrument as string.

        :param ticker: Ticker.
        :param timeframe: Timeframe to load.
        :param interval: Interval type to load.
        :return: Container with downloaded string.
        """
        params = [
            ('timeframe', str(timeframe.value)),
            ('period', str(interval.value))
        ]

        self.downloader.parameters = params
        self.downloader.headers = self.headers

        url = self._history_url_pattern % urllib.parse.quote(str(ticker))
        return self.downloader.download_string(url)

    def download_info_string(
            self,
            search_string: str) -> DownloadStringResult:
        """ Downloads the list of all available instruments by specified parameters.

        :param search_string: Search string
        :return: Container with downloaded string.
        """
        self.downloader.headers = self.headers
        self.downloader.parameters = [
            ('query', str(search_string)),
            ('types', self.search_types)
        ]

        return self.downloader.download_string(self.info_url)


class BloombergDownloadParameterValuesStorage(DownloadParameterValuesStorage):
    """ Storage of instruments download parameters.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

        self._special_handlers: typing.Dict[type, typing.Callable] = {
            Timeframes: self._get_timeframes_choices,
            Intervals: self._get_intervals_choices
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
    def _get_timeframes_choices():
        timeframe: Timeframes
        return [(timeframe.value, timeframe.description)  # pylint: disable=undefined-variable, used-before-assignment
                for timeframe
                in Timeframes]

    @staticmethod
    def _get_intervals_choices():
        interval: Intervals
        return [(interval.value, interval.value)  # pylint: disable=undefined-variable, used-before-assignment
                for interval
                in Intervals]


class BloombergApiActualityChecker(ApiActualityChecker):
    """ Verifies actuality and accessibility of REST API of www.bloomberg.com
    """

    search_string_to_check = 'DJ'  # Suppose Dow Jones always exists
    ticker_to_check = 'I28893:IND'  # Some instrument with available history
    timeframe_to_check = Timeframes.FIVE_YEARS
    interval_to_check = Intervals.DAILY

    def __init__(
            self,
            string_data_downloader: BloombergStringDataDownloader,
            info_parser: BloombergInfoJsonParser,
            history_values_parser: BloombergHistoryJsonParser):
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

        self.string_data_downloader = string_data_downloader
        self.history_values_parser = history_values_parser
        self.info_parser = info_parser

    def check(self):
        self.logger.info("Check actuality via instruments list")

        info_string_result = self.string_data_downloader.download_info_string(
            search_string=self.search_string_to_check)
        self.logger.debug(f"Got JSON data:\n{info_string_result.downloaded_string}")
        # read all available instruments
        try:
            _ = tuple(self.info_parser.parse(info_string_result.downloaded_string))
        except ParseError as ex:
            info_string_result.set_correctness(False)
            raise CheckApiActualityError(f"Unexpected indexes info JSON: {ex.message}") from ex
        except Exception:
            info_string_result.set_correctness(False)
            raise

        # now test history data
        self.logger.info(f"Check actuality via ticker {self.ticker_to_check!r}")

        history_data_string_result = self.string_data_downloader.download_history_string(
            ticker=self.ticker_to_check,
            timeframe=self.timeframe_to_check,
            interval=self.interval_to_check)
        self.logger.debug(f"Got JSON data:\n{history_data_string_result.downloaded_string}")
        try:
            history_data = tuple(self.history_values_parser.parse(
                history_data_string_result.downloaded_string,
                tzinfo=None))
        except ParseError as ex:
            history_data_string_result.set_correctness(False)
            raise CheckApiActualityError(f"Unexpected indexes history JSON: {ex.message}") from ex
        except Exception:
            history_data_string_result.set_correctness(False)
            raise

        if not history_data:
            history_data_string_result.set_correctness(False)
            raise CheckApiActualityError(
                f"Not found history values for {self.ticker_to_check!r}")

        self.logger.info("Actuality check was successful")


class BloombergExporterFactory(InstrumentExporterFactory):
    """ Factory class for create instances of Bloomberg data exporter.
    """
    name: str = 'Bloomberg. Version 2021'
    provider_site: str = 'https://www.bloomberg.com/'
    api_url: str = 'https://www.bloomberg.com/'

    def __init__(self):
        self._dynamic_enum_type_manager = None
        self._download_parameters_factory = None

    def create_history_values_exporter(self, downloader: Downloader) -> InstrumentHistoryValuesExporter:
        string_data_downloader = BloombergStringDataDownloader(downloader)
        history_values_parser = BloombergHistoryJsonParser()

        return GenericInstrumentHistoryValuesExporter(string_data_downloader, history_values_parser)

    def create_info_exporter(self, downloader: Downloader) -> InstrumentsInfoExporter:
        string_data_downloader = BloombergStringDataDownloader(downloader)
        info_parser = BloombergInfoJsonParser()

        return GenericInstrumentsInfoExporter(string_data_downloader, info_parser)

    def create_download_parameter_values_storage(
            self, downloader: Downloader) -> BloombergDownloadParameterValuesStorage:
        return BloombergDownloadParameterValuesStorage()

    def create_api_actuality_checker(self, downloader: Downloader) -> BloombergApiActualityChecker:
        string_data_downloader = BloombergStringDataDownloader(downloader)
        history_values_parser = BloombergHistoryJsonParser()
        info_parser = BloombergInfoJsonParser()

        return BloombergApiActualityChecker(
            string_data_downloader,
            info_parser,
            history_values_parser)

    @property
    def dynamic_enum_type_manager(self) -> BloombergDownloadParameterValuesStorage:
        if self._dynamic_enum_type_manager is None:
            self._dynamic_enum_type_manager = BloombergDownloadParameterValuesStorage()

        return self._dynamic_enum_type_manager

    @property
    def download_parameters_factory(self) -> BloombergDownloadParametersFactory:
        if self._download_parameters_factory is None:
            self._download_parameters_factory = BloombergDownloadParametersFactory()

        return self._download_parameters_factory
