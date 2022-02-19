#!/usr/bin/env python
# -*- coding: utf-8 -*-

import typing
import datetime

from sane_finances.communication.downloader import DownloadStringResult
from sane_finances.sources.ishares.v2021.meta import (
    PerformanceValue, ProductInfo)
from sane_finances.sources.ishares.v2021.parsers import (
    ISharesHistoryHtmlParser, ISharesInfoJsonParser)
from sane_finances.sources.ishares.v2021.exporters import (
    ISharesStringDataDownloader, ISharesDownloadParameterValuesStorage)

from ....communication.fakes import FakeDownloader


class FakeISharesDownloadParameterValuesStorage(ISharesDownloadParameterValuesStorage):
    pass


class FakeISharesInfoJsonParser(ISharesInfoJsonParser):

    def __init__(self, fake_data: typing.Iterable[ProductInfo]):
        super().__init__()

        self.fake_data = fake_data
        self.parse_exception = None

    def parse(self, raw_json_text: str) -> typing.Iterable[ProductInfo]:
        if self.parse_exception is not None:
            raise self.parse_exception

        return self.fake_data


class FakeISharesHistoryHtmlParser(ISharesHistoryHtmlParser):

    def __init__(self, fake_data: typing.Iterable[PerformanceValue]):
        super().__init__()

        self.fake_data = fake_data
        self.parse_exception = None

    def parse(
            self,
            raw_json_text: str,
            tzinfo: typing.Optional[datetime.timezone]) -> typing.Iterable[PerformanceValue]:
        if self.parse_exception is not None:
            raise self.parse_exception

        return self.fake_data


class FakeISharesStringDataDownloader(ISharesStringDataDownloader):

    def __init__(self, fake_info_data, fake_history_data):
        super().__init__(FakeDownloader(None))

        self.download_instruments_info_string_results: typing.List[DownloadStringResult] = []
        self.download_instrument_history_string_results: typing.List[DownloadStringResult] = []

        self.fake_history_data = fake_history_data
        self.fake_info_data = fake_info_data

    def download_history_string(
            self,
            product_page_url: str) -> DownloadStringResult:
        result = DownloadStringResult(self.fake_history_data)
        self.download_instrument_history_string_results.append(result)
        return result

    def download_info_string(self) -> DownloadStringResult:
        result = DownloadStringResult(self.fake_info_data)
        self.download_instruments_info_string_results.append(result)
        return result
