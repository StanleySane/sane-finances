#!/usr/bin/env python
# -*- coding: utf-8 -*-

import typing
import datetime

from sane_finances.communication.downloader import DownloadStringResult
from sane_finances.sources.spdji.v2021.meta import (
    Currency, ReturnType, IndexLevel, IndexInfo, IndexFinderFilter, IndexMetaData)
from sane_finances.sources.spdji.v2021.parsers import (
    SpdjHistoryJsonParser, SpdjInfoJsonParser, SpdjMetaJsonParser, SpdjIndexFinderFiltersParser)
from sane_finances.sources.spdji.v2021.exporters import (
    SpdjStringDataDownloader, SpdjDownloadParameterValuesStorage)

from ....communication.fakes import FakeDownloader


class FakeSpdjMetaJsonParser(SpdjMetaJsonParser):

    def __init__(self, fake_index_meta_data: IndexMetaData):
        super().__init__()

        self.fake_index_meta_data = fake_index_meta_data
        self.parse_exception = None

    def parse(self, raw_json_text: str) -> IndexMetaData:
        if self.parse_exception is not None:
            raise self.parse_exception

        return self.fake_index_meta_data


class FakeSpdjIndexFinderFiltersParser(SpdjIndexFinderFiltersParser):

    def __init__(self, fake_index_finder_filters: typing.Iterable[IndexFinderFilter]):
        super().__init__()

        self.fake_index_finder_filters = fake_index_finder_filters
        self.parse_exception = None

    def parse(self, html: str) -> typing.Iterable[IndexFinderFilter]:
        if self.parse_exception is not None:
            raise self.parse_exception

        return self.fake_index_finder_filters


class FakeSpdjDownloadParameterValuesStorage(SpdjDownloadParameterValuesStorage):

    def __init__(
            self,
            fake_index_meta_data: IndexMetaData,
            fake_index_finder_filters: typing.Iterable[IndexFinderFilter]):
        super().__init__(
            FakeDownloader(None),
            FakeSpdjMetaJsonParser(fake_index_meta_data),
            FakeSpdjIndexFinderFiltersParser(fake_index_finder_filters))


class FakeSpdjInfoJsonParser(SpdjInfoJsonParser):

    def __init__(self, fake_data: typing.Iterable[IndexInfo]):
        super().__init__()

        self.fake_data = fake_data
        self.parse_exception = None

    def parse(self, raw_json_text: str) -> typing.Iterable[IndexInfo]:
        if self.parse_exception is not None:
            raise self.parse_exception

        return self.fake_data


class FakeSpdjHistoryJsonParser(SpdjHistoryJsonParser):

    def __init__(self, fake_data: typing.Iterable[IndexLevel]):
        super().__init__()

        self.fake_data = fake_data
        self.parse_exception = None

    def parse(
            self,
            raw_json_text: str,
            tzinfo: typing.Optional[datetime.timezone]) -> typing.Iterable[IndexLevel]:
        if self.parse_exception is not None:
            raise self.parse_exception

        return self.fake_data


class FakeSpdjStringDataDownloader(SpdjStringDataDownloader):

    def __init__(self, fake_info_data, fake_history_data):
        super().__init__(FakeDownloader(None))

        self.download_instruments_info_string_results: typing.List[DownloadStringResult] = []
        self.download_instrument_history_string_results: typing.List[DownloadStringResult] = []

        self.fake_history_data = fake_history_data
        self.fake_info_data = fake_info_data

    def download_index_history_string(
            self,
            index_id: str,
            currency: typing.Optional[Currency],
            return_type: typing.Optional[ReturnType]) -> DownloadStringResult:
        result = DownloadStringResult(self.fake_history_data)
        self.download_instrument_history_string_results.append(result)
        return result

    def download_index_info_string(
            self,
            page_number: int,
            index_finder_filter: typing.Optional[IndexFinderFilter]) -> DownloadStringResult:
        result = DownloadStringResult(self.fake_info_data)
        self.download_instruments_info_string_results.append(result)
        return result
