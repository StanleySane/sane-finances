#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Tools for download (export) index data from www.lbma.org.uk
"""
import datetime
import decimal
import logging
import typing

from .meta import (
    LbmaPreciousMetalHistoryDownloadParameters, LbmaPreciousMetalInfoDownloadParameters, LbmaDownloadParametersFactory,
    PreciousMetals, Currencies)
from .parsers import LbmaHistoryJsonParser, LbmaInfoParser
from ...base import (
    ApiActualityChecker, InstrumentStringDataDownloader, ParseError,
    InstrumentExporterFactory, InstrumentHistoryValuesExporter, InstrumentsInfoExporter,
    DownloadParameterValuesStorage, DownloadStringResult,
    CheckApiActualityError)
from ...generic import GenericInstrumentHistoryValuesExporter, GenericInstrumentsInfoExporter
from ....communication.downloader import Downloader

logging.getLogger().addHandler(logging.NullHandler())


class LbmaStringDataDownloader(InstrumentStringDataDownloader):
    """ Data downloader from www.lbma.org.uk
    """

    history_base_url = 'https://prices.lbma.org.uk/json/'

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

    def download_instrument_history_string(
            self,
            parameters: LbmaPreciousMetalHistoryDownloadParameters,
            moment_from: datetime.datetime,
            moment_to: datetime.datetime) -> DownloadStringResult:
        return self.download_history_string(parameters.metal)

    def download_instruments_info_string(
            self,
            parameters: LbmaPreciousMetalInfoDownloadParameters) -> DownloadStringResult:
        """ Do nothing, because all instruments info is well known on compile time.

        :param parameters: Source specific instruments info download parameters.
        :return: Empty container.
        """
        return DownloadStringResult(downloaded_string='')

    def download_history_string(
            self,
            metal: PreciousMetals) -> DownloadStringResult:
        """ Downloads history data for one instrument as string.

        :param metal: Precious Metal.
        :return: Container with downloaded string.
        """
        self.downloader.parameters = self.params
        self.downloader.headers = self.headers

        return self.downloader.download_string(self.history_base_url + metal.value + '.json')


class LbmaDownloadParameterValuesStorage(DownloadParameterValuesStorage):
    """ Storage of instrument download parameters.
    """

    def is_dynamic_enum_type(self, cls: type) -> bool:
        return False

    def get_all_managed_types(self) -> typing.Iterable[typing.Type]:
        return ()

    def get_dynamic_enum_key(self, instance):
        return None


class LbmaApiActualityChecker(ApiActualityChecker):
    """ Verifies actuality and accessibility of REST API of www.lbma.org.uk
    """

    _metal_to_check = PreciousMetals.GOLD_AM
    _date_to_check = datetime.date(1968, 1, 2)
    _currency_to_check = Currencies.USD
    _expected_value = decimal.Decimal('35.18')

    def __init__(
            self,
            string_data_downloader: LbmaStringDataDownloader,
            history_values_parser: LbmaHistoryJsonParser):
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

        self.string_data_downloader = string_data_downloader
        self.history_values_parser = history_values_parser

    def check(self):
        self.logger.info("Check actuality via history")

        history_download_parameters = LbmaPreciousMetalHistoryDownloadParameters(
            metal=self._metal_to_check,
            currency=self._currency_to_check)
        history_data_string_result = self.string_data_downloader.download_history_string(
            metal=self._metal_to_check)
        self.logger.debug(f"Got history data:\n{history_data_string_result.downloaded_string}")
        self.history_values_parser.download_parameters = history_download_parameters
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

        for metal_price in history_data:
            if metal_price.date == self._date_to_check \
                    and metal_price.value == self._expected_value:
                self.logger.info("Actuality check was successful")
                return

        history_data_string_result.set_correctness(False)
        raise CheckApiActualityError(
            f"Not found expected history value for {self._metal_to_check!r}")


class LbmaExporterFactory(InstrumentExporterFactory):
    """ Factory class for create instances of LBMA data exporter.
    """
    name: str = 'LBMA. Version 2021'
    provider_site: str = 'https://www.ishares.com/us'
    api_url: str = 'https://www.ishares.com/us/products/etf-investments'

    def __init__(self):
        self._dynamic_enum_type_manager = None
        self._download_parameters_factory = None

    def create_history_values_exporter(self, downloader: Downloader) -> InstrumentHistoryValuesExporter:
        string_data_downloader = LbmaStringDataDownloader(downloader)
        history_values_parser = LbmaHistoryJsonParser()

        return GenericInstrumentHistoryValuesExporter(string_data_downloader, history_values_parser)

    def create_info_exporter(self, downloader: Downloader) -> InstrumentsInfoExporter:
        string_data_downloader = LbmaStringDataDownloader(downloader)
        info_parser = LbmaInfoParser()

        return GenericInstrumentsInfoExporter(string_data_downloader, info_parser)

    def create_download_parameter_values_storage(self, downloader: Downloader) -> LbmaDownloadParameterValuesStorage:
        return LbmaDownloadParameterValuesStorage()

    def create_api_actuality_checker(self, downloader: Downloader) -> LbmaApiActualityChecker:
        string_data_downloader = LbmaStringDataDownloader(downloader)
        history_values_parser = LbmaHistoryJsonParser()

        return LbmaApiActualityChecker(
            string_data_downloader,
            history_values_parser)

    @property
    def dynamic_enum_type_manager(self) -> LbmaDownloadParameterValuesStorage:
        if self._dynamic_enum_type_manager is None:
            self._dynamic_enum_type_manager = LbmaDownloadParameterValuesStorage()

        return self._dynamic_enum_type_manager

    @property
    def download_parameters_factory(self) -> LbmaDownloadParametersFactory:
        if self._download_parameters_factory is None:
            self._download_parameters_factory = LbmaDownloadParametersFactory()

        return self._download_parameters_factory
