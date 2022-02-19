#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Metadata for export data from https://finance.yahoo.com/
"""

import decimal
import datetime
import enum
import typing
import dataclasses

from ...base import (
    InstrumentValue, InstrumentInfo, InstrumentValueProvider, InstrumentInfoProvider,
    InstrumentHistoryDownloadParameters, DownloadParametersFactory)
from ...inspection import InstrumentInfoParameter
from ....annotations import LEGACY_ANNOTATIONS

if LEGACY_ANNOTATIONS:  # pragma: no cover
    from ....annotations import Annotated
else:  # pragma: no cover
    from typing import Annotated  # pylint: disable=no-name-in-module


class IntervalTypes(enum.Enum):
    """ History interval type.
    """
    ONE_MINUTE = '1m'
    TWO_MINUTES = '2m'
    FIVE_MINUTES = '5m'
    FIFTEEN_MINUTES = '15m'
    THIRTY_MINUTES = '30m'
    SIXTY_MINUTES = '60m'
    NINETY_MINUTES = '90m'
    ONE_HOUR = '1h'
    ONE_DAY = '1d'
    FIVE_DAYS = '5d'
    ONE_WEEK = '1wk'
    ONE_MONTH = '1mo'
    THREE_MONTHS = '3mo'


class SearchInfoFieldNames(enum.Enum):
    """ Field names in JSON from search result
    """
    FINANCE = 'finance'
    ERROR = 'error'
    ERROR_CODE = 'code'
    ERROR_DESCRIPTION = 'description'
    QUOTES = 'quotes'
    SYMBOL = 'symbol'
    EXCHANGE = 'exchange'
    SHORT_NAME = 'shortname'
    LONG_NAME = 'longname'
    TYPE_DISP = 'typeDisp'
    EXCHANGE_DISP = 'exchDisp'
    IS_YAHOO_FINANCE = 'isYahooFinance'


class QuoteHistoryFieldNames(enum.Enum):
    """ Field names in JSON from quote history request
    """
    CHART = 'chart'
    ERROR = 'error'
    ERROR_CODE = 'code'
    ERROR_DESCRIPTION = 'description'
    RESULT = 'result'
    META = 'meta'
    SYMBOL = 'symbol'
    TIMESTAMP = 'timestamp'
    INDICATORS = 'indicators'
    QUOTE = 'quote'
    CLOSE = 'close'


@dataclasses.dataclass
class InstrumentQuoteValue(InstrumentValueProvider):
    """ Container for Yahoo instrument history item.
    """
    symbol: str
    timestamp: datetime.datetime
    close: decimal.Decimal

    def __init__(self, *, symbol: str, timestamp: datetime.datetime, close: decimal.Decimal):
        """ Initialize Yahoo instrument value.

        :param symbol: Yahoo instrument symbol.
        :param timestamp: Moment.
        :param close: Close value of instrument.
        """
        if not isinstance(timestamp, datetime.datetime):
            raise TypeError("'timestamp' is not datetime")

        self.symbol = str(symbol)
        self.timestamp = timestamp
        self.close = decimal.Decimal(close)

    def get_instrument_value(self, tzinfo: typing.Optional[datetime.timezone]) -> InstrumentValue:
        timestamp = self.timestamp.astimezone(tzinfo)
        return InstrumentValue(value=self.close, moment=timestamp)


@dataclasses.dataclass
class InstrumentQuoteInfo(InstrumentInfoProvider):
    """ Container for Yahoo instrument information.
    """
    symbol: str
    exchange: str
    short_name: str
    long_name: typing.Optional[str]
    type_disp: typing.Optional[str]
    exchange_disp: typing.Optional[str]
    is_yahoo_finance: bool

    def __init__(
            self,
            *,
            symbol: str,
            exchange: str,
            short_name: str,
            long_name: typing.Optional[str],
            type_disp: typing.Optional[str],
            exchange_disp: typing.Optional[str],
            is_yahoo_finance: bool):
        self.symbol = str(symbol)
        self.exchange = str(exchange)
        self.short_name = str(short_name)
        self.long_name = None if long_name is None else str(long_name)
        self.type_disp = None if type_disp is None else str(type_disp)
        self.exchange_disp = None if exchange_disp is None else str(exchange_disp)
        self.is_yahoo_finance = bool(is_yahoo_finance)

    def __str__(self):
        return (f"Yahoo Finance quote ("
                f"symbol={self.symbol}, "
                f"exchange={self.exchange}, "
                f"short_name={self.short_name}, "
                f"long_name={self.long_name}, "
                f"type_disp={self.type_disp}, "
                f"exchange_disp={self.exchange_disp}, "
                f"is_yahoo_finance={self.is_yahoo_finance})")

    @property
    def instrument_info(self) -> InstrumentInfo:
        return InstrumentInfo(code=self.symbol, name=self.short_name)


class YahooInstrumentInfoDownloadParameters(typing.NamedTuple):
    """ Container for ``YahooStringDataDownloader.download_instruments_info_string`` parameters.
    """
    search_string: str

    @classmethod
    def safe_create(
            cls: typing.Type['YahooInstrumentInfoDownloadParameters'],
            *,
            search_string: str) -> 'YahooInstrumentInfoDownloadParameters':
        """ Create new instance of ``YahooInstrumentInfoDownloadParameters`` with arguments check.

        :param search_string: Search string.
        :return: ``YahooInstrumentInfoDownloadParameters`` instance.
        """
        return cls(search_string=str(search_string))


@dataclasses.dataclass
class YahooInstrumentHistoryDownloadParameters(InstrumentHistoryDownloadParameters):
    """ Container for ``YahooStringDataDownloader.download_instrument_history_string`` parameters.
    """
    symbol: Annotated[str, InstrumentInfoParameter(instrument_identity=True)]

    def clone_with_instrument_info_parameters(
            self,
            info_download_parameters: typing.Optional[YahooInstrumentInfoDownloadParameters],
            instrument_info: typing.Optional[InstrumentQuoteInfo]) -> 'YahooInstrumentHistoryDownloadParameters':
        return YahooInstrumentHistoryDownloadParameters.generate_from(self, info_download_parameters, instrument_info)

    # noinspection PyUnusedLocal
    @classmethod
    def generate_from(
            cls: typing.Type['YahooInstrumentHistoryDownloadParameters'],
            history_download_parameters: typing.Optional['YahooInstrumentHistoryDownloadParameters'],
            info_download_parameters: typing.Optional[YahooInstrumentInfoDownloadParameters],
            instrument_info: typing.Optional[InstrumentQuoteInfo]) -> 'YahooInstrumentHistoryDownloadParameters':
        """ Create new history download parameters instance with data from its arguments.

        :param history_download_parameters: Optional instrument history download parameters for cloning.
        :param info_download_parameters: Optional instrument info download parameters for cloning.
        :param instrument_info: Optional instrument info for cloning.
        :return: Cloned history download parameters instance (self) with replacing some attributes from
            `info_download_parameters` and `instrument_info`.
        """
        return cls(
            symbol=((None if history_download_parameters is None else history_download_parameters.symbol)
                    if instrument_info is None
                    else instrument_info.symbol)
        )

    @classmethod
    def safe_create(
            cls: typing.Type['YahooInstrumentHistoryDownloadParameters'],
            *,
            symbol: str) -> 'YahooInstrumentHistoryDownloadParameters':
        """ Create new instance of ``YahooInstrumentHistoryDownloadParameters`` with arguments check.

        :param symbol: Instrument symbol.
        :return: ``YahooInstrumentHistoryDownloadParameters`` instance.
        """
        return cls(symbol=str(symbol))


class YahooDownloadParametersFactory(DownloadParametersFactory):
    """ Download parameters factories and generators for Yahoo Finance.
    """

    @property
    def download_history_parameters_class(self) -> typing.Type[YahooInstrumentHistoryDownloadParameters]:
        return YahooInstrumentHistoryDownloadParameters

    @property
    def download_history_parameters_factory(self) -> typing.Callable[..., YahooInstrumentHistoryDownloadParameters]:
        return YahooInstrumentHistoryDownloadParameters.safe_create

    @property
    def download_info_parameters_class(self):
        return YahooInstrumentInfoDownloadParameters

    @property
    def download_info_parameters_factory(self) -> typing.Callable[..., typing.Any]:
        return YahooInstrumentInfoDownloadParameters.safe_create

    def generate_history_download_parameters_from(
            self,
            history_download_parameters: typing.Optional[YahooInstrumentHistoryDownloadParameters],
            info_download_parameters: typing.Optional[YahooInstrumentInfoDownloadParameters],
            instrument_info: typing.Optional[InstrumentQuoteInfo]) -> YahooInstrumentHistoryDownloadParameters:
        return YahooInstrumentHistoryDownloadParameters.generate_from(
            history_download_parameters,
            info_download_parameters,
            instrument_info)
