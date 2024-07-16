#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Tools for download (export) index data from https://www.spglobal.com/spdji/
"""
import datetime
import itertools
import logging
import typing

from .parsers import SpdjIndexFinderFiltersParser
from .. import v2021
from ..v2021.exporters import SpdjApiActualityChecker, SpdjDownloadParameterValuesStorage, SpdjDynamicEnumTypeManager
from ..v2021.meta import (Currency, IndexFinderFilter, ReturnType, SpdjDownloadParametersFactory,
                          SpdjIndexHistoryDownloadParameters, SpdjIndexesInfoDownloadParameters)
from ..v2021.parsers import SpdjHistoryJsonParser, SpdjInfoJsonParser, SpdjMetaJsonParser
from ...base import (DownloadStringResult, InstrumentExporterFactory, InstrumentHistoryValuesExporter,
                     InstrumentStringDataDownloader, InstrumentsInfoExporter)
from ...generic import GenericInstrumentHistoryValuesExporter, GenericInstrumentsInfoExporter
from ....communication.downloader import Downloader

logging.getLogger().addHandler(logging.NullHandler())


class SpdjStringDataDownloader(v2021.exporters.SpdjStringDataDownloader):
    """ Data downloader from https://www.spglobal.com/spdji/
    """

    default_headers: typing.Dict[str, str] = {
        'Host': 'www.spglobal.com',
        'Accept': 'text/html,application/xhtml+xml,application/xml;'
                  'q=0.9,image/avif,image/webp,image/apng,*/*;'
                  'q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'en-US,en;q=0.9',
        'Cache-Control': 'no-cache',
        'Sec-Ch-Ua': '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/126.0.0.0 Safari/537.36',
    }

    def __init__(self, downloader: Downloader):
        super().__init__(downloader)

        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

        # headers for HTTP
        self.headers: typing.Dict[str, str] = dict(self.default_headers)


class SpdjExporterFactory(InstrumentExporterFactory):
    """ Factory class for create instances of S&P Dow Jones data exporter.
    """
    name: str = 'S&P Dow Jones Indices. Version 2024'
    provider_site: str = 'https://www.spglobal.com/spdji/en/'
    api_url: str = 'https://www.spglobal.com/spdji/en/index-finder/'

    def __init__(self):
        self._dynamic_enum_type_manager = None
        self._download_parameters_factory = None

    def create_history_values_exporter(self, downloader: Downloader) -> InstrumentHistoryValuesExporter:
        string_data_downloader = SpdjStringDataDownloader(downloader)
        history_values_parser = SpdjHistoryJsonParser()

        return GenericInstrumentHistoryValuesExporter(string_data_downloader, history_values_parser)

    def create_info_exporter(self, downloader: Downloader) -> InstrumentsInfoExporter:
        string_data_downloader = SpdjStringDataDownloader(downloader)
        info_parser = SpdjInfoJsonParser()

        return GenericInstrumentsInfoExporter(string_data_downloader, info_parser)

    def create_download_parameter_values_storage(self, downloader: Downloader) -> SpdjDownloadParameterValuesStorage:
        meta_json_parser = SpdjMetaJsonParser()
        index_finder_filters_parser = SpdjIndexFinderFiltersParser()

        return SpdjDownloadParameterValuesStorage(downloader, meta_json_parser, index_finder_filters_parser)

    def create_api_actuality_checker(self, downloader: Downloader) -> SpdjApiActualityChecker:
        string_data_downloader = SpdjStringDataDownloader(downloader)
        history_values_parser = SpdjHistoryJsonParser()
        info_parser = SpdjInfoJsonParser()

        return SpdjApiActualityChecker(
            string_data_downloader,
            info_parser,
            history_values_parser)

    @property
    def dynamic_enum_type_manager(self) -> SpdjDynamicEnumTypeManager:
        if self._dynamic_enum_type_manager is None:
            self._dynamic_enum_type_manager = SpdjDynamicEnumTypeManager()

        return self._dynamic_enum_type_manager

    @property
    def download_parameters_factory(self) -> SpdjDownloadParametersFactory:
        if self._download_parameters_factory is None:
            self._download_parameters_factory = SpdjDownloadParametersFactory()

        return self._download_parameters_factory
