#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Tools for download (export) index data from www.ishares.com
"""
import datetime
import decimal
import logging
import typing

from .meta import (
    ISharesDownloadParametersFactory, ISharesInstrumentInfoDownloadParameters,
    ISharesInstrumentHistoryDownloadParameters)
from .parsers import ISharesInfoJsonParser, ISharesHistoryHtmlParser
from ...base import (
    ApiActualityChecker, InstrumentStringDataDownloader, ParseError,
    InstrumentExporterFactory, InstrumentHistoryValuesExporter, InstrumentsInfoExporter,
    DownloadParameterValuesStorage, DownloadStringResult,
    CheckApiActualityError)
from ...generic import GenericInstrumentHistoryValuesExporter, GenericInstrumentsInfoExporter
from ....communication.downloader import Downloader

logging.getLogger().addHandler(logging.NullHandler())


class ISharesStringDataDownloader(InstrumentStringDataDownloader):
    """ Data downloader from www.ishares.com
    """

    history_base_url = 'https://www.ishares.com'
    info_url = 'https://www.ishares.com/us/product-screener/product-screener-v3.1.jsn'

    def __init__(self, downloader: Downloader):
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

        self.downloader = downloader

        self.params = []
        # headers for HTTP
        self.headers: typing.Dict[str, str] = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/39.0.2171.95 Safari/537.36'
        }

        self.dcr_path = ('/templatedata/config/product-screener-v3/data/en/us-ishares/'
                         'ishares-product-screener-backend-config')

    def download_instrument_history_string(
            self,
            parameters: ISharesInstrumentHistoryDownloadParameters,
            moment_from: datetime.datetime,
            moment_to: datetime.datetime) -> DownloadStringResult:
        return self.download_history_string(parameters.product_page_url)

    def download_instruments_info_string(
            self,
            parameters: ISharesInstrumentInfoDownloadParameters) -> DownloadStringResult:
        return self.download_info_string()

    def download_history_string(
            self,
            product_page_url: str) -> DownloadStringResult:
        """ Downloads history data for one instrument as string.

        :param product_page_url: Product page url.
        :return: Container with downloaded string.
        """
        self.downloader.parameters = self.params
        self.downloader.headers = self.headers

        return self.downloader.download_string(self.history_base_url + product_page_url)

    def download_info_string(self) -> DownloadStringResult:
        """ Downloads the list of all available instruments by specified parameters.

        :return: Container with downloaded string.
        """
        self.downloader.headers = self.headers
        self.downloader.parameters = [
            ('dcrPath', self.dcr_path)
        ]

        return self.downloader.download_string(self.info_url)


class ISharesDownloadParameterValuesStorage(DownloadParameterValuesStorage):
    """ Storage of instrument download parameters.
    """

    def is_dynamic_enum_type(self, cls: type) -> bool:
        return False

    def get_all_managed_types(self) -> typing.Iterable[typing.Type]:
        return ()

    def get_dynamic_enum_key(self, instance):
        return None


class ISharesApiActualityChecker(ApiActualityChecker):
    """ Verifies actuality and accessibility of REST API of www.ishares.com
    """

    _ticker_to_check = 'IVV'  # iShares Core S&P 500 ETF
    _expected_performance_date = datetime.date(2000, 5, 15)
    _expected_value = decimal.Decimal('10000')

    def __init__(
            self,
            string_data_downloader: ISharesStringDataDownloader,
            info_parser: ISharesInfoJsonParser,
            history_values_parser: ISharesHistoryHtmlParser):
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

        self.string_data_downloader = string_data_downloader
        self.history_values_parser = history_values_parser
        self.info_parser = info_parser

    def check(self):
        self.logger.info("Check actuality via indexes list")

        info_string_result = self.string_data_downloader.download_info_string()
        self.logger.debug(f"Got JSON data:\n{info_string_result.downloaded_string}")
        # read all available indexes
        try:
            instruments = tuple(self.info_parser.parse(info_string_result.downloaded_string))
        except ParseError as ex:
            info_string_result.set_correctness(False)
            raise CheckApiActualityError(f"Unexpected indexes info JSON: {ex.message}") from ex
        except Exception:
            info_string_result.set_correctness(False)
            raise

        # find ticker to check
        instrument_info_to_check = None
        for instrument_info in instruments:
            if instrument_info.local_exchange_ticker == self._ticker_to_check:
                instrument_info_to_check = instrument_info

        if instrument_info_to_check is None:
            info_string_result.set_correctness(False)
            raise CheckApiActualityError(f"Not found instrument with ticker {self._ticker_to_check!r}")

        # now test history data
        self.logger.info(f"Check actuality via instrument {self._ticker_to_check!r}")

        history_data_string_result = self.string_data_downloader.download_history_string(
            product_page_url=instrument_info_to_check.product_page_url)
        self.logger.debug(f"Got history data:\n{history_data_string_result.downloaded_string}")
        try:
            history_data = tuple(self.history_values_parser.parse(
                history_data_string_result.downloaded_string,
                tzinfo=None))
        except ParseError as ex:
            history_data_string_result.set_correctness(False)
            raise CheckApiActualityError(f"Unexpected history data: {ex.message}") from ex
        except Exception:
            history_data_string_result.set_correctness(False)
            raise

        for performance_value in history_data:
            if performance_value.date == self._expected_performance_date \
                    and performance_value.value == self._expected_value:
                self.logger.info("Actuality check was successful")
                return

        history_data_string_result.set_correctness(False)
        raise CheckApiActualityError(
            f"Not found expected history value for {self._ticker_to_check!r}")


class ISharesExporterFactory(InstrumentExporterFactory):
    """ Factory class for create instances of iShares data exporter.
    """
    name: str = 'iShares. Version 2021'
    provider_site: str = 'https://www.ishares.com/us'
    api_url: str = 'https://www.ishares.com/us/products/etf-investments'

    def __init__(self):
        self._dynamic_enum_type_manager = None
        self._download_parameters_factory = None

    def create_history_values_exporter(self, downloader: Downloader) -> InstrumentHistoryValuesExporter:
        string_data_downloader = ISharesStringDataDownloader(downloader)
        history_values_parser = ISharesHistoryHtmlParser()

        return GenericInstrumentHistoryValuesExporter(string_data_downloader, history_values_parser)

    def create_info_exporter(self, downloader: Downloader) -> InstrumentsInfoExporter:
        string_data_downloader = ISharesStringDataDownloader(downloader)
        info_parser = ISharesInfoJsonParser()

        return GenericInstrumentsInfoExporter(string_data_downloader, info_parser)

    def create_download_parameter_values_storage(self, downloader: Downloader) -> ISharesDownloadParameterValuesStorage:
        return ISharesDownloadParameterValuesStorage()

    def create_api_actuality_checker(self, downloader: Downloader) -> ISharesApiActualityChecker:
        string_data_downloader = ISharesStringDataDownloader(downloader)
        history_values_parser = ISharesHistoryHtmlParser()
        info_parser = ISharesInfoJsonParser()

        return ISharesApiActualityChecker(
            string_data_downloader,
            info_parser,
            history_values_parser)

    @property
    def dynamic_enum_type_manager(self) -> ISharesDownloadParameterValuesStorage:
        if self._dynamic_enum_type_manager is None:
            self._dynamic_enum_type_manager = ISharesDownloadParameterValuesStorage()

        return self._dynamic_enum_type_manager

    @property
    def download_parameters_factory(self) -> ISharesDownloadParametersFactory:
        if self._download_parameters_factory is None:
            self._download_parameters_factory = ISharesDownloadParametersFactory()

        return self._download_parameters_factory
