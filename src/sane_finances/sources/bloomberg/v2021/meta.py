#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Metadata for export index data from www.bloomberg.com
"""

import dataclasses
import datetime
import decimal
import enum
import typing

from ...base import (
    InstrumentValue, InstrumentInfo, InstrumentValueProvider, InstrumentInfoProvider,
    InstrumentHistoryDownloadParameters, DownloadParametersFactory)
from ...inspection import InstrumentInfoParameter
from ....annotations import LEGACY_ANNOTATIONS

if LEGACY_ANNOTATIONS:  # pragma: no cover
    from ....annotations import Annotated
else:  # pragma: no cover
    from typing import Annotated  # pylint: disable=no-name-in-module


class HistoryFieldNames(enum.Enum):
    """ Field names in history JSON.
    """
    TICKER = 'ticker'
    PRICE = 'price'
    DATE_TIME = 'dateTime'
    VALUE = 'value'


class InfoFieldNames(enum.Enum):
    """ Field names in info JSON.
    """
    RESULTS = 'results'
    TICKER_SYMBOL = 'ticker_symbol'
    NAME = 'name'
    COUNTRY = 'country'
    RESOURCE_TYPE = 'resource_type'
    RESOURCE_ID = 'resource_id'
    SECURITY_TYPE = 'security_type'
    URL = 'url'


class Timeframes(enum.Enum):
    """ Timeframes of history data
    """

    def __new__(cls, value: str, description: str):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.description = str(description)
        return obj

    def __repr__(self):
        return f"<{self.__class__.__name__}.{self.name}: " \
               f"'{self.value}' ('{self.description}')>"

    ONE_DAY = ('1_DAY', 'One day')
    ONE_WEEK = ('1_WEEK', 'One week')
    ONE_MONTH = ('1_MONTH', 'One month')
    SIX_MONTHS = ('6_MONTH', 'Six months')
    YEAR_TO_DATE = ('YTD', 'Year-to-date')
    ONE_YEAR = ('1_YEAR', 'One year')
    FIVE_YEARS = ('5_YEAR', 'Five years')


class Intervals(enum.Enum):
    """ Intervals of history data
    """
    DAILY = 'daily'
    WEEKLY = 'weekly'
    MONTHLY = 'monthly'


@dataclasses.dataclass
class InstrumentPrice(InstrumentValueProvider):
    """ Container for instrument history value.
    """
    ticker: str
    price_date: datetime.date
    price_value: decimal.Decimal

    def __init__(self,
                 *,
                 ticker: str,
                 price_date: datetime.date,
                 price_value: decimal.Decimal):
        if not isinstance(price_date, datetime.date):
            raise TypeError("'price_date' is not date")

        self.ticker = ticker
        self.price_date = price_date
        self.price_value = decimal.Decimal(price_value)

    def __str__(self):
        return (f"Bloomberg price ("
                f"ticker={self.ticker}, "
                f"price_date={self.price_date.isoformat()}, "
                f"price_value={self.price_value})")

    def get_instrument_value(self, tzinfo: typing.Optional[datetime.timezone]) -> InstrumentValue:
        moment = datetime.datetime.combine(self.price_date, datetime.time.min, tzinfo)
        return InstrumentValue(value=self.price_value, moment=moment)


@dataclasses.dataclass
class BloombergInstrumentInfo(InstrumentInfoProvider):
    """ Container for instrument information.
    """
    ticker_symbol: str
    name: str
    country: typing.Optional[str]
    resource_type: typing.Optional[str]
    resource_id: typing.Optional[str]
    security_type: typing.Optional[str]
    url: typing.Optional[str]

    def __init__(
            self,
            *,
            ticker_symbol: str,
            name: str,
            country: typing.Optional[str],
            resource_type: typing.Optional[str],
            resource_id: typing.Optional[str],
            security_type: typing.Optional[str],
            url: typing.Optional[str]):
        self.ticker_symbol = str(ticker_symbol)
        self.name = str(name)
        self.country = None if country is None else str(country)
        self.resource_type = None if resource_type is None else str(resource_type)
        self.resource_id = None if resource_id is None else str(resource_id)
        self.security_type = None if security_type is None else str(security_type)
        self.url = None if url is None else str(url)

    def __str__(self):
        return (f"Bloomberg instrument("
                f"ticker_symbol={self.ticker_symbol}, "
                f"name={self.name}, "
                f"country={self.country}, "
                f"resource_type={self.resource_type}, "
                f"resource_id={self.resource_id}, "
                f"security_type={self.security_type}, "
                f"url={self.url})")

    @property
    def instrument_info(self) -> InstrumentInfo:
        return InstrumentInfo(code=self.ticker_symbol, name=self.name)


class BloombergInfoDownloadParameters(typing.NamedTuple):
    """ Container for ``BloombergStringDataDownloader.download_instruments_info_string parameters``.
    """
    search_string: str

    @classmethod
    def safe_create(
            cls: typing.Type['BloombergInfoDownloadParameters'],
            *,
            search_string: str) -> 'BloombergInfoDownloadParameters':
        """ Create new instance of ``BloombergInfoDownloadParameters`` with arguments check.

        :param search_string: Search string.
        :return: ``BloombergInfoDownloadParameters`` instance.
        """
        return cls(search_string=str(search_string))


@dataclasses.dataclass
class BloombergHistoryDownloadParameters(InstrumentHistoryDownloadParameters):
    """ Container for ``BloombergStringDataDownloader.download_instrument_history_string parameters``.
    """
    ticker: Annotated[str, InstrumentInfoParameter(instrument_identity=True)]
    timeframe: Timeframes
    interval: Intervals

    def clone_with_instrument_info_parameters(
            self,
            info_download_parameters: typing.Optional[BloombergInfoDownloadParameters],
            instrument_info: typing.Optional[BloombergInstrumentInfo]) -> 'BloombergHistoryDownloadParameters':
        return BloombergHistoryDownloadParameters.generate_from(self, info_download_parameters, instrument_info)

    # noinspection PyUnusedLocal
    @classmethod
    def generate_from(
            cls: typing.Type['BloombergHistoryDownloadParameters'],
            history_download_parameters: typing.Optional['BloombergHistoryDownloadParameters'],
            info_download_parameters: typing.Optional[BloombergInfoDownloadParameters],
            instrument_info: typing.Optional[BloombergInstrumentInfo]) -> 'BloombergHistoryDownloadParameters':
        """ Create new history download parameters instance with data from its arguments.

        :param history_download_parameters: Optional instrument history download parameters for cloning.
        :param info_download_parameters: Optional instrument info download parameters for cloning.
        :param instrument_info: Optional instrument info for cloning.
        :return: Cloned history download parameters instance (self) with replacing some attributes from
            `info_download_parameters` and `instrument_info`.
        """
        return cls(
            ticker=((None if history_download_parameters is None else history_download_parameters.ticker)
                    if instrument_info is None
                    else instrument_info.ticker_symbol),
            timeframe=(None if history_download_parameters is None else history_download_parameters.timeframe),
            interval=(None if history_download_parameters is None else history_download_parameters.interval)
        )

    @classmethod
    def safe_create(
            cls: typing.Type['BloombergHistoryDownloadParameters'],
            *,
            ticker: str,
            timeframe: Timeframes,
            interval: Intervals) -> 'BloombergHistoryDownloadParameters':
        """ Create new instance of ``BloombergHistoryDownloadParameters`` with arguments check.

        :param ticker: Instrument ticker.
        :param timeframe: Timeframe for download.
        :param interval: Interval type.
        :return: ``BloombergHistoryDownloadParameters`` instance.
        """
        if not isinstance(timeframe, Timeframes):
            raise TypeError(f"'timeframe' is not Timeframes: {timeframe!r}")
        if not isinstance(interval, Intervals):
            raise TypeError(f"'interval' is not Intervals: {interval!r}")

        return cls(
            ticker=str(ticker),
            timeframe=timeframe,
            interval=interval)


class BloombergDownloadParametersFactory(DownloadParametersFactory):
    """ Download parameters factories and generators for Bloomberg.
    """

    @property
    def download_history_parameters_class(self) -> typing.Type[BloombergHistoryDownloadParameters]:
        return BloombergHistoryDownloadParameters

    @property
    def download_history_parameters_factory(self) -> typing.Callable[..., BloombergHistoryDownloadParameters]:
        return BloombergHistoryDownloadParameters.safe_create

    @property
    def download_info_parameters_class(self):
        return BloombergInfoDownloadParameters

    @property
    def download_info_parameters_factory(self) -> typing.Callable[..., typing.Any]:
        return BloombergInfoDownloadParameters.safe_create

    def generate_history_download_parameters_from(
            self,
            history_download_parameters: typing.Optional[BloombergHistoryDownloadParameters],
            info_download_parameters: typing.Optional[BloombergInfoDownloadParameters],
            instrument_info: typing.Optional[BloombergInstrumentInfo]) -> BloombergHistoryDownloadParameters:
        return BloombergHistoryDownloadParameters.generate_from(
            history_download_parameters,
            info_download_parameters,
            instrument_info)
