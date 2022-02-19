#!/usr/bin/env python
# -*- coding: utf-8 -*-

import typing
import datetime

from sane_finances.communication.downloader import DownloadStringResult
from sane_finances.sources.bloomberg.v2021.meta import (
    Timeframes, Intervals, InstrumentPrice, BloombergInstrumentInfo)
from sane_finances.sources.bloomberg.v2021.parsers import (
    BloombergHistoryJsonParser, BloombergInfoJsonParser)
from sane_finances.sources.bloomberg.v2021.exporters import (
    BloombergDownloadParameterValuesStorage, BloombergStringDataDownloader)

from ....communication.fakes import FakeDownloader


class FakeBloombergDownloadParameterValuesStorage(BloombergDownloadParameterValuesStorage):
    pass


class FakeBloombergInfoJsonParser(BloombergInfoJsonParser):

    def __init__(self, fake_data: typing.Iterable[BloombergInstrumentInfo]):
        super().__init__()

        self.fake_data = fake_data
        self.parse_exception = None

    def parse(self, raw_json_text: str) -> typing.Iterable[BloombergInstrumentInfo]:
        if self.parse_exception is not None:
            raise self.parse_exception

        return self.fake_data


class FakeBloombergHistoryJsonParser(BloombergHistoryJsonParser):

    def __init__(self, fake_data: typing.Iterable[InstrumentPrice]):
        super().__init__()

        self.fake_data = fake_data
        self.parse_exception = None

    def parse(
            self,
            raw_json_text: str,
            tzinfo: typing.Optional[datetime.timezone]) -> typing.Iterable[InstrumentPrice]:
        if self.parse_exception is not None:
            raise self.parse_exception

        return self.fake_data


class FakeBloombergStringDataDownloader(BloombergStringDataDownloader):

    def __init__(self, fake_info_data, fake_history_data):
        super().__init__(FakeDownloader(None))

        self.download_instruments_info_string_results: typing.List[DownloadStringResult] = []
        self.download_instrument_history_string_results: typing.List[DownloadStringResult] = []

        self.fake_history_data = fake_history_data
        self.fake_info_data = fake_info_data

    def download_history_string(
            self,
            ticker: str,
            timeframe: Timeframes,
            interval: Intervals) -> DownloadStringResult:
        result = DownloadStringResult(self.fake_history_data)
        self.download_instrument_history_string_results.append(result)
        return result

    def download_info_string(
            self,
            search_string: str) -> DownloadStringResult:
        result = DownloadStringResult(self.fake_info_data)
        self.download_instruments_info_string_results.append(result)
        return result
