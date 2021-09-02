#!/usr/bin/env python
# -*- coding: utf-8 -*-

import typing
import datetime

from sane_finances.communication.downloader import DownloadStringResult
from sane_finances.sources.cbr.v2016.meta import (
    CurrencyRateValue, CurrencyInfo)
from sane_finances.sources.cbr.v2016.parsers import (
    CbrCurrencyInfoParser, CbrCurrencyHistoryXmlParser)
from sane_finances.sources.cbr.v2016.exporters import (
    CbrStringDataDownloader)

from ....communication.fakes import FakeDownloader


class FakeCbrCurrencyInfoParser(CbrCurrencyInfoParser):

    def __init__(self, fake_data: typing.Iterable[CurrencyInfo]):
        super().__init__()

        self.fake_data = fake_data
        self.parse_exception = None

    def parse(self, xml) -> typing.Iterable[CurrencyInfo]:
        if self.parse_exception is not None:
            raise self.parse_exception

        return self.fake_data


class FakeCbrCurrencyHistoryXmlParser(CbrCurrencyHistoryXmlParser):

    def __init__(self, fake_data: typing.Iterable[CurrencyRateValue]):
        super().__init__()

        self.fake_data = fake_data
        self.parse_exception = None

    def parse(
            self,
            raw_xml_text: str,
            tzinfo: typing.Optional[datetime.timezone]
    ) -> typing.Iterable[CurrencyRateValue]:
        if self.parse_exception is not None:
            raise self.parse_exception

        return self.fake_data


class FakeCbrStringDataDownloader(CbrStringDataDownloader):

    def __init__(self, fake_info_data, fake_history_data):
        super().__init__(FakeDownloader(None))

        self.download_instruments_info_string_results: typing.List[DownloadStringResult] = []
        self.download_instrument_history_string_results: typing.List[DownloadStringResult] = []

        self.fake_history_data = fake_history_data
        self.fake_info_data = fake_info_data

    def download_currency_history_string(
            self,
            currency_id,
            date_from,
            date_to) -> DownloadStringResult:
        result = DownloadStringResult(self.fake_history_data)
        self.download_instrument_history_string_results.append(result)
        return result

    def download_currencies_info_string(self, rate_frequency) -> DownloadStringResult:
        result = DownloadStringResult(self.fake_info_data)
        self.download_instruments_info_string_results.append(result)
        return result
