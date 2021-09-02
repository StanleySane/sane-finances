#!/usr/bin/env python
# -*- coding: utf-8 -*-

import typing
import datetime

from sane_finances.communication.downloader import DownloadStringResult
from sane_finances.sources.msci.v2021.meta import (
    IndexValue, IndexInfo, IndexPanelData)
from sane_finances.sources.msci.v2021.parsers import (
    MsciHistoryJsonParser, MsciIndexInfoParser, MsciIndexPanelDataJsonParser)
from sane_finances.sources.msci.v2021.exporters import (
    MsciStringDataDownloader, MsciIndexDownloadParameterValuesStorage)

from ....communication.fakes import FakeDownloader


class FakeMsciIndexPanelDataJsonParser(MsciIndexPanelDataJsonParser):

    def __init__(self, fake_index_panel_data: IndexPanelData):
        super().__init__()

        self.fake_index_panel_data = fake_index_panel_data
        self.parse_exception = None

    def parse(self, raw_json_text: str) -> IndexPanelData:
        if self.parse_exception is not None:
            raise self.parse_exception

        return self.fake_index_panel_data


class FakeMsciIndexDownloadParameterValuesStorage(MsciIndexDownloadParameterValuesStorage):

    def __init__(self, fake_index_panel_data: IndexPanelData):
        super().__init__(FakeDownloader(None), FakeMsciIndexPanelDataJsonParser(fake_index_panel_data))


class FakeIndexInfoParser(MsciIndexInfoParser):

    def __init__(self, fake_data: typing.Iterable[IndexInfo]):
        super().__init__()

        self.fake_data = fake_data
        self.parse_exception = None

    def parse(self, xml) -> typing.Iterable[IndexInfo]:
        if self.parse_exception is not None:
            raise self.parse_exception

        return self.fake_data


class FakeMsciHistoryJsonParser(MsciHistoryJsonParser):

    def __init__(self, fake_data: typing.Iterable[IndexValue]):
        # noinspection PyTypeChecker
        super().__init__(None)

        self.fake_data = fake_data
        self.parse_exception = None

    def parse(
            self,
            raw_xml_text: str,
            tzinfo: typing.Optional[datetime.timezone]
    ) -> typing.Iterable[IndexValue]:
        if self.parse_exception is not None:
            raise self.parse_exception

        return self.fake_data


class FakeMsciStringDataDownloader(MsciStringDataDownloader):

    def __init__(self, fake_info_data, fake_history_data):
        # noinspection PyTypeChecker
        super().__init__(FakeDownloader(None), None)

        self.download_instruments_info_string_results: typing.List[DownloadStringResult] = []
        self.download_instrument_history_string_results: typing.List[DownloadStringResult] = []

        self.fake_history_data = fake_history_data
        self.fake_info_data = fake_info_data

    def download_index_history_string(
            self,
            index_code,
            currency,
            index_variant,
            date_from,
            date_to) -> DownloadStringResult:
        result = DownloadStringResult(self.fake_history_data)
        self.download_instrument_history_string_results.append(result)
        return result

    def download_indexes_info_string(
            self,
            scope,
            market,
            size,
            style,
            index_suite) -> DownloadStringResult:
        result = DownloadStringResult(self.fake_info_data)
        self.download_instruments_info_string_results.append(result)
        return result
