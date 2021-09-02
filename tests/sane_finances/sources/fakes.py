#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import typing

from sane_finances.communication.downloader import DownloadStringResult, Downloader
from sane_finances.sources.base import (
    InstrumentStringDataDownloader,
    InstrumentValuesHistoryParser, InstrumentInfoParser,
    InstrumentInfoProvider, InstrumentValueProvider,
    InstrumentHistoryDownloadParameters, InstrumentInfo, InstrumentValue, InstrumentExporterFactory,
    DownloadParametersFactory, DynamicEnumTypeManager, ApiActualityChecker, DownloadParameterValuesStorage,
    InstrumentsInfoExporter, InstrumentHistoryValuesExporter)


class FakeInstrumentInfoProvider(InstrumentInfoProvider):

    def __init__(self, value: InstrumentInfo):
        self.value = value

    @property
    def instrument_info(self) -> InstrumentInfo:
        return self.value


class FakeInstrumentValueProvider(InstrumentValueProvider):

    def __init__(self, value: InstrumentValue):
        self.value = value

    def get_instrument_value(self, tzinfo: typing.Optional[datetime.timezone]) -> InstrumentValue:
        return self.value


class FakeInstrumentHistoryDownloadParameters(InstrumentHistoryDownloadParameters):

    def clone_with_instrument_info_parameters(
            self,
            info_download_parameters: typing.Any,
            instrument_info: typing.Optional[InstrumentInfoProvider]) -> InstrumentHistoryDownloadParameters:
        return FakeInstrumentHistoryDownloadParameters()


class FakeInstrumentStringDataDownloader(InstrumentStringDataDownloader):

    def __init__(self, fake_info_string: str, fake_history_string: str):
        self.fake_info_string = fake_info_string
        self.fake_history_string = fake_history_string

        self.download_instruments_info_string_results: typing.List[DownloadStringResult] = []
        self.download_instrument_history_string_results: typing.List[DownloadStringResult] = []

        self.download_instruments_info_string_counter = 0
        self.download_instrument_history_string_counter = 0

    def adjust_download_instrument_history_parameters(
            self,
            parameters: InstrumentHistoryDownloadParameters,
            moment_from: datetime.datetime,
            moment_to: datetime.datetime
    ) -> typing.Tuple[InstrumentHistoryDownloadParameters, datetime.datetime, datetime.datetime]:
        # by default DO NOT adjust anything for testing simplicity !!!
        return parameters, moment_from, moment_to

    def paginate_download_instrument_history_parameters(
            self,
            parameters: InstrumentHistoryDownloadParameters,
            moment_from: datetime.datetime,
            moment_to: datetime.datetime
    ) -> typing.Iterable[typing.Tuple[InstrumentHistoryDownloadParameters, datetime.datetime, datetime.datetime]]:
        # by default DO NOT paginate anything for testing simplicity !!!
        yield parameters, moment_from, moment_to

    def download_instruments_info_string(self, parameters) -> DownloadStringResult:

        self.download_instruments_info_string_counter += 1
        result = DownloadStringResult(self.fake_info_string)
        self.download_instruments_info_string_results.append(result)
        return result

    def download_instrument_history_string(
            self,
            parameters: InstrumentHistoryDownloadParameters,
            moment_from: datetime.datetime,
            moment_to: datetime.datetime) -> DownloadStringResult:

        self.download_instrument_history_string_counter += 1
        result = DownloadStringResult(self.fake_history_string)
        self.download_instrument_history_string_results.append(result)
        return result


class FakeInstrumentValuesHistoryParser(InstrumentValuesHistoryParser):
    fake_result: typing.Iterable[InstrumentValueProvider]

    def __init__(self, expected_raw_text: str):
        self.expected_raw_text = expected_raw_text
        self.parse_exception = None

        self.parse_counter = 0

    def parse(
            self,
            raw_text: str,
            tzinfo: typing.Optional[datetime.timezone]
    ) -> typing.Iterable[InstrumentValueProvider]:
        if raw_text != self.expected_raw_text:
            raise ValueError("Not expected 'raw_text'")

        if self.parse_exception is not None:
            raise self.parse_exception

        self.parse_counter += 1
        yield from self.fake_result


class FakeInstrumentInfoParser(InstrumentInfoParser):
    fake_result: typing.Iterable[InstrumentInfoProvider]

    def __init__(self, expected_raw_text: str):
        self.expected_raw_text = expected_raw_text
        self.parse_exception = None

        self.parse_counter = 0

    def parse(self, raw_text: str) -> typing.Iterable[InstrumentInfoProvider]:
        if raw_text != self.expected_raw_text:
            raise ValueError("Not expected 'raw_text'")

        if self.parse_exception is not None:
            raise self.parse_exception

        self.parse_counter += 1
        return self.fake_result


class FakeInstrumentExporterFactory(InstrumentExporterFactory):
    history_values_exporter: InstrumentHistoryValuesExporter
    info_exporter: InstrumentsInfoExporter
    download_parameter_values_storage: DownloadParameterValuesStorage
    api_actuality_checker: ApiActualityChecker

    def __init__(
            self,
            dynamic_enum_type_manager: DynamicEnumTypeManager = None,
            download_parameters_factory: DownloadParametersFactory = None):
        self._dynamic_enum_type_manager = dynamic_enum_type_manager
        self._download_parameters_factory = download_parameters_factory

    def create_history_values_exporter(self, downloader: Downloader) -> InstrumentHistoryValuesExporter:
        return self.history_values_exporter

    def create_info_exporter(self, downloader: Downloader) -> InstrumentsInfoExporter:
        return self.info_exporter

    def create_download_parameter_values_storage(self, downloader: Downloader) -> DownloadParameterValuesStorage:
        return self.download_parameter_values_storage

    def create_api_actuality_checker(self, downloader: Downloader) -> ApiActualityChecker:
        return self.api_actuality_checker

    @property
    def dynamic_enum_type_manager(self) -> DynamicEnumTypeManager:
        return self._dynamic_enum_type_manager

    @property
    def download_parameters_factory(self) -> DownloadParametersFactory:
        return self._download_parameters_factory
