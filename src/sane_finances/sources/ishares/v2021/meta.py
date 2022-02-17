#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Metadata for export index data from www.ishares.com
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


class InfoFieldNames(enum.Enum):
    """ Field names in info JSON.
    """
    LOCAL_EXCHANGE_TICKER = 'localExchangeTicker'
    ISIN = 'isin'
    FUND_NAME = 'fundName'
    INCEPTION_DATE = 'inceptionDate'
    INCEPTION_DATE_R = 'r'
    PRODUCT_PAGE_URL = 'productPageUrl'


@dataclasses.dataclass
class PerformanceValue(InstrumentValueProvider):
    """ Container for instrument history value.
    """
    date: datetime.date
    value: decimal.Decimal

    def __init__(self,
                 *,
                 date: datetime.date,
                 value: decimal.Decimal):
        if not isinstance(date, datetime.date):
            raise TypeError("'date' is not datetime.date")

        self.date = date
        self.value = decimal.Decimal(value)

    def __str__(self):
        return (f"iShares performance value("
                f"date={self.date.isoformat()}, "
                f"value={self.value})")

    def get_instrument_value(self, tzinfo: typing.Optional[datetime.timezone]) -> InstrumentValue:
        moment = datetime.datetime.combine(self.date, datetime.time.min, tzinfo)
        return InstrumentValue(value=self.value, moment=moment)


@dataclasses.dataclass
class ProductInfo(InstrumentInfoProvider):
    """ Container for instrument information.
    """
    local_exchange_ticker: str
    isin: str
    fund_name: str
    inception_date: datetime.date
    product_page_url: str

    def __init__(self,
                 *,
                 local_exchange_ticker: str,
                 isin: str,
                 fund_name: str,
                 inception_date: datetime.date,
                 product_page_url: str):
        if not isinstance(inception_date, datetime.date):
            raise TypeError("'inception_date' is not datetime.date")

        self.local_exchange_ticker = str(local_exchange_ticker)
        self.isin = str(isin)
        self.fund_name = str(fund_name)
        self.inception_date = inception_date
        self.product_page_url = str(product_page_url)

    def __str__(self):
        return (f"iShares instrument("
                f"local_exchange_ticker={self.local_exchange_ticker}, "
                f"isin={self.isin}, "
                f"fund_name={self.fund_name}, "
                f"inception_date={self.inception_date.isoformat()}, "
                f"product_page_url={self.product_page_url})")

    @property
    def instrument_info(self) -> InstrumentInfo:
        return InstrumentInfo(code=self.local_exchange_ticker, name=self.fund_name)


class ISharesInstrumentInfoDownloadParameters(typing.NamedTuple):
    """ Container for ``ISharesStringDataDownloader.download_instruments_info_string parameters``.
    """

    @classmethod
    def safe_create(
            cls: typing.Type['ISharesInstrumentInfoDownloadParameters']) -> 'ISharesInstrumentInfoDownloadParameters':
        """ Create new instance of ``ISharesInstrumentInfoDownloadParameters`` with arguments check.

        :return: ``ISharesInstrumentInfoDownloadParameters`` instance.
        """
        return cls()


@dataclasses.dataclass
class ISharesInstrumentHistoryDownloadParameters(InstrumentHistoryDownloadParameters):
    """ Container for ``ISharesStringDataDownloader.download_instrument_history_string parameters``.
    """
    product_page_url: Annotated[str, InstrumentInfoParameter(instrument_identity=True)]

    def clone_with_instrument_info_parameters(
            self,
            info_download_parameters: typing.Optional[ISharesInstrumentInfoDownloadParameters],
            instrument_info: typing.Optional[ProductInfo]) -> 'ISharesInstrumentHistoryDownloadParameters':
        return ISharesInstrumentHistoryDownloadParameters.generate_from(self, info_download_parameters, instrument_info)

    # noinspection PyUnusedLocal
    @classmethod
    def generate_from(
            cls: typing.Type['ISharesInstrumentHistoryDownloadParameters'],
            history_download_parameters: typing.Optional['ISharesInstrumentHistoryDownloadParameters'],
            info_download_parameters: typing.Optional[ISharesInstrumentInfoDownloadParameters],
            instrument_info: typing.Optional[ProductInfo]) -> 'ISharesInstrumentHistoryDownloadParameters':
        """ Create new history download parameters instance with data from its arguments.

        :param history_download_parameters: Optional instrument history download parameters for cloning.
        :param info_download_parameters: Optional instrument info download parameters for cloning.
        :param instrument_info: Optional instrument info for cloning.
        :return: Cloned history download parameters instance (self) with replacing some attributes from
            `info_download_parameters` and `instrument_info`.
        """
        return cls(
            product_page_url=(
                (None if history_download_parameters is None else history_download_parameters.product_page_url)
                if instrument_info is None
                else instrument_info.product_page_url))

    @classmethod
    def safe_create(
            cls: typing.Type['ISharesInstrumentHistoryDownloadParameters'],
            *,
            product_page_url: str) -> 'ISharesInstrumentHistoryDownloadParameters':
        """ Create new instance of ``ISharesInstrumentHistoryDownloadParameters`` with arguments check.

        :param product_page_url: Product page URL.
        :return: ``ISharesInstrumentHistoryDownloadParameters`` instance.
        """
        return cls(product_page_url=str(product_page_url))


class ISharesDownloadParametersFactory(DownloadParametersFactory):
    """ Download parameters factories and generators for iShares.
    """

    @property
    def download_history_parameters_class(self) -> typing.Type[ISharesInstrumentHistoryDownloadParameters]:
        return ISharesInstrumentHistoryDownloadParameters

    @property
    def download_history_parameters_factory(self) -> typing.Callable[..., ISharesInstrumentHistoryDownloadParameters]:
        return ISharesInstrumentHistoryDownloadParameters.safe_create

    @property
    def download_info_parameters_class(self):
        return ISharesInstrumentInfoDownloadParameters

    @property
    def download_info_parameters_factory(self) -> typing.Callable[..., typing.Any]:
        return ISharesInstrumentInfoDownloadParameters.safe_create

    def generate_history_download_parameters_from(
            self,
            history_download_parameters: typing.Optional[ISharesInstrumentHistoryDownloadParameters],
            info_download_parameters: typing.Optional[ISharesInstrumentInfoDownloadParameters],
            instrument_info: typing.Optional[ProductInfo]) -> ISharesInstrumentHistoryDownloadParameters:
        return ISharesInstrumentHistoryDownloadParameters.generate_from(
            history_download_parameters,
            info_download_parameters,
            instrument_info)
