#!/usr/bin/env python
# -*- coding: utf-8 -*-

import typing
import datetime

from sane_finances.communication.downloader import DownloadStringResult
from sane_finances.sources.solactive.v2018.meta import (
    IndexValue, IndexInfo)
from sane_finances.sources.solactive.v2018.parsers import (
    SolactiveJsonParser, SolactiveIndexInfoParser)
from sane_finances.sources.solactive.v2018.exporters import (
    SolactiveStringDataDownloader)

from ....communication.fakes import FakeDownloader


class FakeSolactiveStringDataDownloader(SolactiveStringDataDownloader):

    def __init__(self, fake_info_data, fake_history_data):
        super().__init__(FakeDownloader(None))

        self.download_instruments_info_string_results: typing.List[DownloadStringResult] = []
        self.download_instrument_history_string_results: typing.List[DownloadStringResult] = []

        self.fake_history_data = fake_history_data
        self.fake_info_data = fake_info_data

    def download_index_history_string(self, isin):
        result = DownloadStringResult(self.fake_history_data)
        self.download_instrument_history_string_results.append(result)
        return result

    def download_all_indexes_info_string(self):
        result = DownloadStringResult(self.fake_info_data)
        self.download_instruments_info_string_results.append(result)
        return result


class FakeSolactiveJsonParser(SolactiveJsonParser):

    def __init__(self, fake_data: typing.Iterable[IndexValue]):
        super().__init__()

        self.fake_data = fake_data
        self.parse_exception = None

    def parse(self, raw_json_text: str, tzinfo: typing.Optional[datetime.timezone]) -> typing.Iterable[IndexValue]:
        if self.parse_exception is not None:
            raise self.parse_exception

        return self.fake_data


class FakeSolactiveIndexInfoParser(SolactiveIndexInfoParser):

    def __init__(self, fake_data: typing.Iterable[IndexInfo]):
        super().__init__()

        self.fake_data = fake_data
        self.parse_exception = None

    def parse(self, html) -> typing.Iterable[IndexInfo]:
        if self.parse_exception is not None:
            raise self.parse_exception

        return self.fake_data
