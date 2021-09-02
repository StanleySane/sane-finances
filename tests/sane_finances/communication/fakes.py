#!/usr/bin/env python
# -*- coding: utf-8 -*-

import typing
import datetime

from sane_finances.communication.downloader import Downloader, DownloadStringResult
from sane_finances.communication.cachers import ExpiryCalculator, DummyCacher, InMemoryCacher


class FakeDummyCacher(DummyCacher):

    def __init__(self):
        self.retrieve_count = 0
        self.drop_count = 0
        self.has_count = 0
        self.is_empty_count = 0
        self.full_clear_count = 0

    def retrieve(
            self,
            url: str,
            parameters: typing.List[typing.Tuple[str, str]],
            headers: typing.Dict[str, str],
            reviver: typing.Callable[[], str]) -> typing.Tuple[bool, str]:
        self.retrieve_count += 1
        return super().retrieve(url, parameters, headers, reviver)

    def drop(
            self,
            url: str,
            parameters: typing.List[typing.Tuple[str, str]],
            headers: typing.Dict[str, str]) -> bool:
        self.drop_count += 1
        return super().drop(url, parameters, headers)

    def has(
            self,
            url: str,
            parameters: typing.List[typing.Tuple[str, str]],
            headers: typing.Dict[str, str]) -> bool:
        self.has_count += 1
        return super().has(url, parameters, headers)

    def is_empty(self) -> bool:
        """ True if cache is empty
        """
        self.is_empty_count += 1
        return super().is_empty()

    def full_clear(self):
        """ Full clear of internal storage.
        """
        self.full_clear_count += 1
        return super().full_clear()


class FakeExpirableCacher(InMemoryCacher):
    # create full fake of 'ExpirableCacher' is very time-consuming and laborious
    # so assume that 'InMemoryCacher' is absolutely correct (:wink:) and take it
    pass


class FakeExpiryCalculator(ExpiryCalculator):

    def __init__(self, now: datetime.datetime):
        self.now = now

    def is_expired(self, expiry_moment: datetime.datetime) -> bool:
        return self.now > expiry_moment

    def get_expiry_moment(self, delta: datetime.timedelta, start_from: datetime.datetime = None) -> datetime.datetime:
        if start_from is None:
            start_from = self.now
        return start_from + delta

    def get_revive_moment(self) -> datetime.datetime:
        return self.now


class FakeDownloader(Downloader):

    def __init__(self, fake_data: typing.Optional[str]):
        self.fake_data = fake_data
        self.download_string_results: typing.List[DownloadStringResult] = []

    @property
    def parameters(self) -> typing.List[typing.Tuple[str, str]]:
        return []

    @parameters.setter
    def parameters(self, value) -> None:
        pass

    @property
    def headers(self) -> typing.Dict[str, str]:
        return {}

    @headers.setter
    def headers(self, value) -> None:
        pass

    def download_string(self, *args, **kwargs) -> DownloadStringResult:
        result = DownloadStringResult(self.fake_data)
        self.download_string_results.append(result)
        return result
