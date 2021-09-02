#!/usr/bin/env python
# -*- coding: utf-8 -*-

import typing
import datetime

from sane_finances.communication.downloader import DownloadStringResult
from sane_finances.sources.msci.v1.meta import (
    IndexValue, IndexInfo)
from sane_finances.sources.msci.v1.parsers import (
    MsciHistoryXmlParser, MsciIndexInfoParser)
from sane_finances.sources.msci.v1.exporters import (
    MsciStringDataDownloader)

from ....communication.fakes import FakeDownloader


class FakeIndexInfoParser(MsciIndexInfoParser):

    def __init__(self, fake_data: typing.Iterable[IndexInfo]):
        super().__init__()

        self.fake_data = fake_data
        self.parse_exception = None

    def parse(self, xml) -> typing.Iterable[IndexInfo]:
        if self.parse_exception is not None:
            raise self.parse_exception

        return self.fake_data


class FakeMsciHistoryXmlParser(MsciHistoryXmlParser):

    def __init__(self, fake_data: typing.Iterable[IndexValue]):
        super().__init__()

        self.fake_data = fake_data
        self.parse_exception = None

    def parse(self, raw_xml_text: str, tzinfo: typing.Optional[datetime.timezone]) -> typing.Iterable[IndexValue]:
        if self.parse_exception is not None:
            raise self.parse_exception

        return self.fake_data


class FakeMsciStringDataDownloader(MsciStringDataDownloader):

    def __init__(self, fake_info_data, fake_history_data):
        super().__init__(FakeDownloader(None))

        self.download_instruments_info_string_results: typing.List[DownloadStringResult] = []
        self.download_instrument_history_string_results: typing.List[DownloadStringResult] = []

        self.fake_history_data = fake_history_data
        self.fake_info_data = fake_info_data

    def download_index_history_string(
            self,
            index_id,
            context,
            index_level,
            currency,
            date_from,
            date_to) -> DownloadStringResult:
        result = DownloadStringResult(self.fake_history_data)
        self.download_instrument_history_string_results.append(result)
        return result

    def download_indexes_info_string(self, market, context) -> DownloadStringResult:
        result = DownloadStringResult(self.fake_info_data)
        self.download_instruments_info_string_results.append(result)
        return result
