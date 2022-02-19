#!/usr/bin/env python
# -*- coding: utf-8 -*-

import typing
import datetime

from sane_finances.communication.downloader import DownloadStringResult
from sane_finances.sources.lbma.v2021.meta import (
    PreciousMetalInfo, PreciousMetalPrice, LbmaPreciousMetalInfoDownloadParameters, PreciousMetals)
from sane_finances.sources.lbma.v2021.parsers import (
    LbmaHistoryJsonParser, LbmaInfoParser)
from sane_finances.sources.lbma.v2021.exporters import (
    LbmaStringDataDownloader, LbmaDownloadParameterValuesStorage)

from ....communication.fakes import FakeDownloader


class FakeLbmaDownloadParameterValuesStorage(LbmaDownloadParameterValuesStorage):
    pass


class FakeLbmaInfoParser(LbmaInfoParser):

    def __init__(self, fake_data: typing.Iterable[PreciousMetalInfo]):
        super().__init__()

        self.fake_data = fake_data
        self.parse_exception = None

    def parse(self, raw_text: str) -> typing.Iterable[PreciousMetalInfo]:
        if self.parse_exception is not None:
            raise self.parse_exception

        return self.fake_data


class FakeLbmaHistoryJsonParser(LbmaHistoryJsonParser):

    def __init__(self, fake_data: typing.Iterable[PreciousMetalPrice]):
        super().__init__()

        self.fake_data = fake_data
        self.parse_exception = None

    def parse(
            self,
            raw_json_text: str,
            tzinfo: typing.Optional[datetime.timezone]) -> typing.Iterable[PreciousMetalPrice]:
        if self.parse_exception is not None:
            raise self.parse_exception

        return self.fake_data


class FakeLbmaStringDataDownloader(LbmaStringDataDownloader):

    def __init__(self, fake_info_data, fake_history_data):
        super().__init__(FakeDownloader(None))

        self.download_instruments_info_string_results: typing.List[DownloadStringResult] = []
        self.download_instrument_history_string_results: typing.List[DownloadStringResult] = []

        self.fake_history_data = fake_history_data
        self.fake_info_data = fake_info_data

    def download_history_string(
            self,
            metal: PreciousMetals) -> DownloadStringResult:
        result = DownloadStringResult(self.fake_history_data)
        self.download_instrument_history_string_results.append(result)
        return result

    def download_instruments_info_string(
            self,
            parameters: LbmaPreciousMetalInfoDownloadParameters) -> DownloadStringResult:
        result = DownloadStringResult(self.fake_info_data)
        self.download_instruments_info_string_results.append(result)
        return result
