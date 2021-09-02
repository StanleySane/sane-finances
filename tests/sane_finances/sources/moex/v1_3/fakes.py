#!/usr/bin/env python
# -*- coding: utf-8 -*-

import typing
import datetime

from sane_finances.communication.downloader import DownloadStringResult
from sane_finances.sources.moex.v1_3.exporters import (
    MoexStringDataDownloader, MoexDownloadParameterValuesStorage)
from sane_finances.sources.moex.v1_3.meta import (
    SecurityValue, SecurityInfo, GlobalIndexData)
from sane_finances.sources.moex.v1_3.parsers import (
    MoexHistoryJsonParser, MoexGlobalIndexJsonParser, MoexSecurityInfoJsonParser)
from ....communication.fakes import FakeDownloader


class FakeMoexGlobalIndexJsonParser(MoexGlobalIndexJsonParser):

    def __init__(self, fake_global_index_data: GlobalIndexData):
        super().__init__()

        self.fake_global_index_data = fake_global_index_data
        self.parse_exception = None

    def parse(self, raw_json_text: str) -> GlobalIndexData:
        if self.parse_exception is not None:
            raise self.parse_exception

        return self.fake_global_index_data


class FakeMoexDownloadParameterValuesStorage(MoexDownloadParameterValuesStorage):

    def __init__(self, fake_global_index_data: GlobalIndexData):
        super().__init__(FakeDownloader(None), FakeMoexGlobalIndexJsonParser(fake_global_index_data))


class FakeMoexSecurityInfoJsonParser(MoexSecurityInfoJsonParser):

    def __init__(self, fake_data: typing.Iterable[SecurityInfo]):
        # noinspection PyTypeChecker
        super().__init__(None)

        self.fake_data = fake_data
        self.parse_exception = None

    def parse(self, xml) -> typing.Iterable[SecurityInfo]:
        if self.parse_exception is not None:
            raise self.parse_exception

        return self.fake_data


class FakeMoexHistoryJsonParser(MoexHistoryJsonParser):

    def __init__(self, fake_data: typing.Iterable[SecurityValue]):
        super().__init__()

        self.fake_data = fake_data
        self.parse_exception = None

    def parse(
            self,
            raw_xml_text: str,
            tzinfo: typing.Optional[datetime.timezone]
    ) -> typing.Iterable[SecurityValue]:
        if self.parse_exception is not None:
            raise self.parse_exception

        return self.fake_data


class FakeMoexStringDataDownloader(MoexStringDataDownloader):

    def __init__(self, fake_info_data, fake_history_data):
        super().__init__(FakeDownloader(None))

        self.download_instruments_info_string_results: typing.List[DownloadStringResult] = []
        self.download_instrument_history_string_results: typing.List[DownloadStringResult] = []

        self.fake_history_data = fake_history_data
        self.fake_info_data = fake_info_data

    def download_security_history_string(
            self,
            board,
            sec_id,
            start,
            date_from,
            date_to) -> DownloadStringResult:
        result = DownloadStringResult(self.fake_history_data)
        self.download_instrument_history_string_results.append(result)
        return result

    def download_securities_info_string(
            self,
            board) -> DownloadStringResult:
        result = DownloadStringResult(self.fake_info_data)
        self.download_instruments_info_string_results.append(result)
        return result
