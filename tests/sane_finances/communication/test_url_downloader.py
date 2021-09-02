#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import unittest.mock
import datetime
import urllib.error

from sane_finances.communication.url_downloader import UrlDownloader, UrlDownloadStringResult
from sane_finances.communication.downloader import DownloadError

from .fakes import FakeDummyCacher, FakeExpirableCacher


class TestUrlDownloadStringResult(unittest.TestCase):

    def setUp(self):
        self.cacher = FakeDummyCacher()
        self.result = UrlDownloadStringResult('OK', self.cacher, '', [], {})

    def test_set_correctness_DontDropWhenTrue(self):
        self.result.set_correctness(True)

        self.assertEqual(self.cacher.drop_count, 0)

    def test_set_correctness_DropWhenFalse(self):
        self.result.set_correctness(False)

        self.assertEqual(self.cacher.drop_count, 1)


class TestUrlDownloader(unittest.TestCase):

    def setUp(self):
        self.http_response_read_count = 0

        self.cacher = FakeExpirableCacher(initial_expiry=datetime.timedelta(days=1))
        self.downloader = UrlDownloader(self.cacher)

        # fake reader
        self.fake_data = 'data'
        self.http_response_error = None
        self.encoding = self.downloader.default_encoding
        mock_urlopen_patcher = unittest.mock.patch(
            'urllib.request.urlopen',
            **{'return_value.__enter__.return_value.read': self.fake_http_response_read})
        mock_urlopen_patcher.start()
        self.addCleanup(mock_urlopen_patcher.stop)

    def fake_http_response_read(self):
        self.http_response_read_count += 1

        if self.http_response_error is not None:
            raise self.http_response_error

        return self.fake_data.encode(self.encoding)

    def test_download_string_SuccessWithParameters(self):
        url = "http://localhost"
        self.downloader.parameters = [("some_param", "param_value")]
        self.downloader.headers = {"some_header": "header_value"}

        result = self.downloader.download_string(url)

        self.assertEqual(result.downloaded_string, self.fake_data)
        self.assertEqual(self.http_response_read_count, 1)

    def test_download_string_SuccessWithoutParameters(self):
        url = "http://localhost"

        result = self.downloader.download_string(url)

        self.assertEqual(result.downloaded_string, self.fake_data)
        self.assertEqual(self.http_response_read_count, 1)

    def test_download_string_UnicodeStringSuccess(self):
        url = "http://localhost"
        self.fake_data = 'Привет'  # unicode string with russian 'Hello'
        self.encoding = 'cp1251'

        result = self.downloader.download_string(url, encoding=self.encoding)

        self.assertEqual(result.downloaded_string, self.fake_data)
        self.assertEqual(self.http_response_read_count, 1)

    def test_download_string_CacheSuccess(self):
        url = "http://localhost"

        # first download
        result = self.downloader.download_string(url)

        self.assertEqual(result.downloaded_string, self.fake_data)
        self.assertEqual(self.http_response_read_count, 1)

        # verify that cacher expiry was initialised properly and not equal to default zero-delta
        self.assertNotEqual(self.cacher.expiry, self.cacher.default_expiry)

        # second download should result the same but without web trip (i.e. should be from cache)
        result = self.downloader.download_string(url)

        self.assertEqual(result.downloaded_string, self.fake_data)
        self.assertEqual(self.http_response_read_count, 1)  # didn't changed

    def test_download_string_RaiseProperExceptionOnErrors(self):
        url = "http://localhost"
        self.http_response_error = urllib.error.URLError("Some error")

        with self.assertRaises(DownloadError):
            _ = self.downloader.download_string(url)
