#!/usr/bin/env python
# -*- coding: utf-8 -*-

import typing
import datetime

from sane_finances.communication.downloader import DownloadStringResult
from sane_finances.sources.yahoo.v8.meta import (
    InstrumentQuoteInfo, InstrumentQuoteValue)
from sane_finances.sources.yahoo.v8.parsers import (
    YahooQuotesJsonParser, YahooInstrumentInfoParser)
from sane_finances.sources.yahoo.v8.exporters import (
    YahooFinanceStringDataDownloader)

from ....communication.fakes import FakeDownloader


class FakeYahooFinanceStringDataDownloader(YahooFinanceStringDataDownloader):

    def __init__(self, fake_info_data, fake_history_data):
        super().__init__(FakeDownloader(None))

        self.download_instruments_info_string_results: typing.List[DownloadStringResult] = []
        self.download_instrument_history_string_results: typing.List[DownloadStringResult] = []

        self.fake_history_data = fake_history_data
        self.fake_info_data = fake_info_data

    def download_quotes_string(
            self,
            symbol: str,
            moment_from: datetime.datetime,
            moment_to: datetime.datetime) -> DownloadStringResult:
        result = DownloadStringResult(self.fake_history_data)
        self.download_instrument_history_string_results.append(result)
        return result

    def download_instruments_search_string(self, search_string: str) -> DownloadStringResult:
        result = DownloadStringResult(self.fake_info_data)
        self.download_instruments_info_string_results.append(result)
        return result


class FakeYahooQuotesJsonParser(YahooQuotesJsonParser):

    def __init__(self, fake_data: typing.Iterable[InstrumentQuoteValue]):
        super().__init__()

        self.fake_data = fake_data
        self.parse_exception = None

    def parse(self,
              raw_json_text: str,
              tzinfo: typing.Optional[datetime.timezone]) -> typing.Iterable[InstrumentQuoteValue]:
        if self.parse_exception is not None:
            raise self.parse_exception

        return self.fake_data


class FakeYahooInstrumentInfoParser(YahooInstrumentInfoParser):

    def __init__(self, fake_data: typing.Iterable[InstrumentQuoteInfo]):
        super().__init__()

        self.fake_data = fake_data
        self.parse_exception = None

    def parse(self, raw_json_text: str, ) -> typing.Iterable[InstrumentQuoteInfo]:
        if self.parse_exception is not None:
            raise self.parse_exception

        return self.fake_data
