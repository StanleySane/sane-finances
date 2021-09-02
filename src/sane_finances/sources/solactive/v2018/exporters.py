#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Tools for download (export) index history data from solactive.com
"""

import datetime
import decimal
import logging
import urllib.parse
import typing

from .meta import (
    IndexHistoryTypes, SolactiveIndexHistoryDownloadParameters,
    SolactiveIndexesInfoDownloadParameters, SolactiveDownloadParametersFactory)
from .parsers import SolactiveJsonParser, SolactiveIndexInfoParser
from ....communication.downloader import Downloader, DownloadStringResult
from ...base import (
    ApiActualityChecker, InstrumentStringDataDownloader, InstrumentExporterFactory,
    InstrumentHistoryValuesExporter, InstrumentsInfoExporter,
    DownloadParameterValuesStorage, ParseError,
    CheckApiActualityError)
from ...generic import GenericInstrumentHistoryValuesExporter, GenericInstrumentsInfoExporter

logging.getLogger().addHandler(logging.NullHandler())


class SolactiveStringDataDownloader(InstrumentStringDataDownloader):
    """ Data downloader from Solactive.com.
    """

    IndexHistoryUrl = 'https://www.solactive.com/indices/'

    def __init__(self, downloader: Downloader):
        """
        """
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

        self.downloader = downloader

        # headers HTTP
        self.headers = {}

        # query parameters
        self.index_history_type = IndexHistoryTypes.MAX

    def download_instrument_history_string(
            self,
            parameters: SolactiveIndexHistoryDownloadParameters,
            moment_from: datetime.datetime,
            moment_to: datetime.datetime) -> DownloadStringResult:
        return self.download_index_history_string(parameters.isin)

    def download_instruments_info_string(
            self,
            parameters: SolactiveIndexesInfoDownloadParameters) -> DownloadStringResult:
        return self.download_all_indexes_info_string()

    def download_index_history_string(self, isin: str) -> DownloadStringResult:
        """ Downloads data for one index as string.

        :param isin: ISIN.
        :return: Container with downloaded string.
        """
        params = [
            ('indexhistory', isin),  # index ID
            ('indexhistorytype', self.index_history_type.value),  # period
        ]

        headers = dict(self.headers)  # make a copy

        # additional headers, mandatory for REST API operability
        headers.update({'Referer': self.IndexHistoryUrl + '?' + urllib.parse.urlencode({'index': isin})})

        self.downloader.parameters = params
        self.downloader.headers = headers

        return self.downloader.download_string(self.IndexHistoryUrl)

    def download_all_indexes_info_string(self) -> DownloadStringResult:
        """ Downloads string with the list of all available indexes

        :return: Container with downloaded string.
        """
        self.downloader.parameters = []
        self.downloader.headers = {}

        return self.downloader.download_string(self.IndexHistoryUrl)


class SolactiveApiActualityChecker(ApiActualityChecker):
    """ Verifies actuality and accessibility of REST API of solactive.com.
    """

    ActualityCheckISIN = 'DE000SLA4YD9'  # FXUS, Solactive GBS United States Large & Mid Cap Index NTR

    _expectedFirstMomentDate = datetime.date(2006, 5, 8)
    _expectedFirstValue = decimal.Decimal('466.44')

    def __init__(self,
                 string_data_downloader: SolactiveStringDataDownloader,
                 json_parser: SolactiveJsonParser):
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

        self.string_data_downloader = string_data_downloader
        self.json_parser = json_parser

    def check(self):
        expected_isin = self.ActualityCheckISIN

        self.logger.info(f"Check actuality via {expected_isin!r}")

        str_data_result = self.string_data_downloader.download_index_history_string(expected_isin)
        self.logger.debug(f"Got str data: {str_data_result.downloaded_string}")

        try:
            data = list(self.json_parser.parse(str_data_result.downloaded_string, tzinfo=None))
        except ParseError as ex:
            str_data_result.set_correctness(False)
            raise CheckApiActualityError(f"Unexpected index history JSON: {ex.message}") from ex
        except Exception:
            str_data_result.set_correctness(False)
            raise

        data.sort(key=lambda v: v.moment)

        first_value = data[0]  # for actuality checking one record is enough

        if first_value.index_id != expected_isin:
            str_data_result.set_correctness(False)
            raise CheckApiActualityError(
                f"Unexpected index ID. {first_value.index_id!r} != {expected_isin!r}")

        if first_value.moment.date() != self._expectedFirstMomentDate:
            str_data_result.set_correctness(False)
            raise CheckApiActualityError(
                f"Unexpected first date. {first_value.moment.date()} != {self._expectedFirstMomentDate}")

        if first_value.value != self._expectedFirstValue:
            str_data_result.set_correctness(False)
            raise CheckApiActualityError(
                f"Unexpected first value. {first_value.value} != {self._expectedFirstValue}")

        self.logger.info("Actuality check was successful")


class SolactiveDownloadParameterValuesStorage(DownloadParameterValuesStorage):
    """ Storage of indexes download parameters.
    """

    def is_dynamic_enum_type(self, cls: type) -> bool:
        return False

    def get_all_managed_types(self) -> typing.Iterable[typing.Type]:
        return ()

    def get_dynamic_enum_key(self, instance):
        return None


class SolactiveExporterFactory(InstrumentExporterFactory):
    """ Factory class for create instances of Solactive data exporter.
    """
    name: str = 'Solactive index data exporter. Version 2018.'
    provider_site: str = 'https://www.solactive.com/'

    def __init__(self):
        self._dynamic_enum_type_manager = None
        self._download_parameters_factory = None

    def create_history_values_exporter(self, downloader: Downloader) -> InstrumentHistoryValuesExporter:
        string_data_downloader = SolactiveStringDataDownloader(downloader)
        history_values_parser = SolactiveJsonParser()

        return GenericInstrumentHistoryValuesExporter(string_data_downloader, history_values_parser)

    def create_info_exporter(self, downloader: Downloader) -> InstrumentsInfoExporter:
        string_data_downloader = SolactiveStringDataDownloader(downloader)
        info_parser = SolactiveIndexInfoParser()

        return GenericInstrumentsInfoExporter(string_data_downloader, info_parser)

    def create_download_parameter_values_storage(self, downloader: Downloader) -> DownloadParameterValuesStorage:
        return SolactiveDownloadParameterValuesStorage()

    def create_api_actuality_checker(self, downloader: Downloader) -> SolactiveApiActualityChecker:
        string_data_downloader = SolactiveStringDataDownloader(downloader)
        history_values_parser = SolactiveJsonParser()

        return SolactiveApiActualityChecker(string_data_downloader, history_values_parser)

    @property
    def dynamic_enum_type_manager(self) -> SolactiveDownloadParameterValuesStorage:
        if self._dynamic_enum_type_manager is None:
            self._dynamic_enum_type_manager = SolactiveDownloadParameterValuesStorage()

        return self._dynamic_enum_type_manager

    @property
    def download_parameters_factory(self) -> SolactiveDownloadParametersFactory:
        if self._download_parameters_factory is None:
            self._download_parameters_factory = SolactiveDownloadParametersFactory()

        return self._download_parameters_factory
