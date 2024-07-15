#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Utility for download text from web.
"""

import gzip
import http.client
import logging
import typing
import urllib.error
import urllib.parse
import urllib.request

from .cachers import BaseCacher
from .downloader import DownloadError, DownloadStringResult, Downloader

logging.getLogger().addHandler(logging.NullHandler())


class UrlDownloadStringResult(DownloadStringResult):
    """ Contains downloaded string
    and provides mechanism for feedback of downloaded string quality (actuality, correctness, fullness, etc.)
    to downloader (e.g. for cache and throttle management)
    """

    def __init__(
            self,
            downloaded_string: str,
            cacher: BaseCacher,
            url: str,
            parameters: typing.List[typing.Tuple[str, str]],
            headers: typing.Dict[str, str]):
        """ Initialize instance.

        :param downloaded_string: Downloaded string.
        :param cacher: Cacher used for storing downloaded strings.
        :param url: URL of request.
        :param parameters: Parameters of request.
        :param headers: Headers of request.
        """
        super().__init__(downloaded_string)

        self.cacher = cacher
        self.url = url
        self.parameters = parameters
        self.headers = headers

    def set_correctness(self, is_correct: bool):
        super().set_correctness(is_correct)

        if not self.is_correct:
            self.cacher.drop(self.url, self.parameters, self.headers)


class UrlDownloader(Downloader):
    """ Cacheable string (text) downloader from web using ``urllib``.
    """

    default_timeout_in_seconds: float = 600.0
    default_encoding: str = 'utf-8'

    def __init__(
            self,
            cacher: BaseCacher,
            timeout_in_seconds: float = default_timeout_in_seconds,
            encoding: str = default_encoding):
        """ Initialize downloader.

        :param cacher: Cacher used for storing downloaded strings.
        :param timeout_in_seconds: Timeout value for download request.
        :param encoding: Encoding of downloaded strings.
        """
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

        self.cacher = cacher
        self.timeout_in_seconds = timeout_in_seconds
        self.encoding = encoding

        self._parameters: typing.List[typing.Tuple[str, str]] = []  # [(param_code, param_value)]
        self._headers: typing.Dict[str, str] = {}  # {header_code : header_value}

    @property
    def parameters(self) -> typing.List[typing.Tuple[str, str]]:
        return self._parameters

    @parameters.setter
    def parameters(self, value: typing.List[typing.Tuple[str, str]]) -> None:
        self._parameters = value

    @property
    def headers(self) -> typing.Dict[str, str]:
        return self._headers

    @headers.setter
    def headers(self, value: typing.Dict[str, str]) -> None:
        self._headers = value

    def read_string_from(self, request: urllib.request.Request, encoding: str) -> str:
        """ Read data from request as string

        Can be mocked in tests.

        :param request: ``urllib.request.Request`` instance.
        :param encoding: Encoding of downloaded string.
        :return: Downloaded string.
        """
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_in_seconds) as response:
                is_gzip = response.headers.get('Content-Encoding') == 'gzip'
                raw_data = response.read()
                data: bytes = bytes(raw_data)

        except (urllib.error.URLError, http.client.HTTPException) as ex:
            raise DownloadError() from ex

        self.logger.debug(f"Downloaded {len(data or '')} bytes")

        if is_gzip:
            data = gzip.decompress(data)

        return data.decode(encoding)

    def build_query(self, url: str) -> urllib.request.Request:
        """ Build request object based on `parameters` and `headers` attributes.

        :param url: URL of request.
        :return: ``urllib.request.Request`` instance.
        """
        data = urllib.parse.urlencode(self.parameters)
        if data:
            url += '?' + data
        req = urllib.request.Request(url, headers=self.headers, method='GET')

        return req

    def download_string_impl(self, request: urllib.request.Request, encoding: str) -> str:
        """ Calls when real (not cached) download needed.

        :param request: ``urllib.request.Request`` instance.
        :param encoding: Encoding of downloaded string.
        :return: Downloaded string.
        """
        self.logger.info(f"Download from {request.full_url!r} to string")

        return self.read_string_from(request, encoding)

    def download_string(self, url: str, encoding: str = None) -> UrlDownloadStringResult:
        request = self.build_query(url)
        encoding = self.encoding if encoding is None else encoding

        parameters = self.parameters.copy()
        headers = self.headers.copy()

        got_from_cache, result = self.cacher.retrieve(
            url,
            parameters,
            headers,
            lambda _request=request, _encoding=encoding: self.download_string_impl(_request, _encoding))

        if got_from_cache:
            self.logger.info(f"Got string for {request.full_url!r} from cache")

        return UrlDownloadStringResult(result, self.cacher, url, parameters, headers)
