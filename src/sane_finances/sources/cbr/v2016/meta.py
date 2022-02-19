#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Metadata for export currency rates from cbr.ru
"""

import decimal
import typing
import datetime
import enum
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


class RateFrequencies(enum.Enum):
    """ Frequencies of rate changing.
    """
    def __new__(cls, value: str, description: str):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.description = str(description)
        return obj

    def __repr__(self):
        return f"<{self.__class__.__name__}.{self.name}: " \
               f"'{self.value}' ('{self.description}')>"

    DAILY = ('0', 'Daily')
    MONTHLY = ('1', 'Monthly')


@dataclasses.dataclass
class CurrencyRateValue(InstrumentValueProvider):
    """ Container for currency rate history item.
    """
    date: datetime.date
    value: decimal.Decimal
    nominal: int
    currency_id: str

    def __init__(self,
                 *,
                 date: datetime.date,
                 value: decimal.Decimal,
                 nominal: int,
                 currency_id: str):
        if not isinstance(date, datetime.date):
            raise TypeError("value_date is not date")

        self.date = date
        self.value = decimal.Decimal(value)
        self.nominal = int(nominal)

        self.currency_id = str(currency_id)

    def get_instrument_value(self, tzinfo: typing.Optional[datetime.timezone]) -> InstrumentValue:
        return InstrumentValue(
            value=self.value/self.nominal,
            moment=datetime.datetime.combine(self.date, datetime.time.min, tzinfo=tzinfo))


@dataclasses.dataclass
class CurrencyInfo(InstrumentInfoProvider):
    """ Container for currency information.
    """
    currency_id: str
    name: str
    eng_name: str
    nominal: int
    parent_code: str

    def __init__(self, *, currency_id: str, name: str, eng_name: str, nominal: int, parent_code: str):
        self.currency_id = str(currency_id)
        self.name = str(name)
        self.eng_name = str(eng_name)
        self.nominal = int(nominal)
        self.parent_code = str(parent_code)

    def __str__(self):
        return (f"CBR currency ("
                f"currency_id={self.currency_id}, "
                f"name={self.name}, "
                f"eng_name={self.eng_name}, "
                f"nominal={self.nominal}, "
                f"parent_code={self.parent_code})")

    @property
    def instrument_info(self) -> InstrumentInfo:
        return InstrumentInfo(code=self.currency_id, name=self.name)


class CbrCurrenciesInfoDownloadParameters(typing.NamedTuple):
    """ Container for CbrStringDataDownloader.download_instruments_info_string parameters.
    """
    rate_frequency: RateFrequencies

    @classmethod
    def safe_create(
            cls: typing.Type['CbrCurrenciesInfoDownloadParameters'],
            *,
            rate_frequency: RateFrequencies) -> 'CbrCurrenciesInfoDownloadParameters':
        """ Create new instance of ``CbrCurrenciesInfoDownloadParameters`` with arguments check.

        :param rate_frequency: ``RateFrequencies`` value.
        :return: ``CbrCurrenciesInfoDownloadParameters`` instance.
        """
        if not isinstance(rate_frequency, RateFrequencies):
            raise TypeError(f"'rate_frequency' is not RateFrequencies: {rate_frequency!r}")

        # see https://github.com/PyCQA/pylint/issues/1801 for pylint disable hint details
        return cls(rate_frequency=RateFrequencies(rate_frequency))  # pylint: disable=no-value-for-parameter


@dataclasses.dataclass
class CbrCurrencyHistoryDownloadParameters(InstrumentHistoryDownloadParameters):
    """ Container for ``CbrStringDataDownloader.download_instrument_history_string`` parameters.
    """
    currency_id: Annotated[str, InstrumentInfoParameter(instrument_identity=True)]

    def clone_with_instrument_info_parameters(
            self,
            info_download_parameters: typing.Optional[CbrCurrenciesInfoDownloadParameters],
            instrument_info: typing.Optional[CurrencyInfo]) -> 'CbrCurrencyHistoryDownloadParameters':
        return CbrCurrencyHistoryDownloadParameters.generate_from(self, info_download_parameters, instrument_info)

    # noinspection PyUnusedLocal
    @classmethod
    def generate_from(
            cls: typing.Type['CbrCurrencyHistoryDownloadParameters'],
            history_download_parameters: typing.Optional['CbrCurrencyHistoryDownloadParameters'],
            info_download_parameters: typing.Optional[CbrCurrenciesInfoDownloadParameters],
            instrument_info: typing.Optional[CurrencyInfo]) -> 'CbrCurrencyHistoryDownloadParameters':
        """ Create new history download parameters instance with data from its arguments.

        :param history_download_parameters: Optional instrument history download parameters for cloning.
        :param info_download_parameters: Optional instrument info download parameters for cloning.
        :param instrument_info: Optional instrument info for cloning.
        :return: Cloned history download parameters instance (self) with replacing some attributes from
            `info_download_parameters` and `instrument_info`.
        """
        return cls(
            currency_id=((None if history_download_parameters is None else history_download_parameters.currency_id)
                         if instrument_info is None
                         else instrument_info.currency_id)
        )

    @classmethod
    def safe_create(
            cls: typing.Type['CbrCurrencyHistoryDownloadParameters'],
            *,
            currency_id: str) -> 'CbrCurrencyHistoryDownloadParameters':
        """ Create new instance of ``CbrCurrencyHistoryDownloadParameters`` with arguments check.

        :param currency_id: Currency ID value.
        :return: ``CbrCurrencyHistoryDownloadParameters`` instance.
        """
        return cls(currency_id=str(currency_id))


class CbrDownloadParametersFactory(DownloadParametersFactory):
    """ Download parameters factories and generators for Central Bank of Russia.
    """

    @property
    def download_history_parameters_class(self) -> typing.Type[CbrCurrencyHistoryDownloadParameters]:
        return CbrCurrencyHistoryDownloadParameters

    @property
    def download_history_parameters_factory(self) -> typing.Callable[..., CbrCurrencyHistoryDownloadParameters]:
        return CbrCurrencyHistoryDownloadParameters.safe_create

    @property
    def download_info_parameters_class(self):
        return CbrCurrenciesInfoDownloadParameters

    @property
    def download_info_parameters_factory(self) -> typing.Callable[..., typing.Any]:
        return CbrCurrenciesInfoDownloadParameters.safe_create

    def generate_history_download_parameters_from(
            self,
            history_download_parameters: typing.Optional[CbrCurrencyHistoryDownloadParameters],
            info_download_parameters: typing.Optional[CbrCurrenciesInfoDownloadParameters],
            instrument_info: typing.Optional[CurrencyInfo]) -> CbrCurrencyHistoryDownloadParameters:
        return CbrCurrencyHistoryDownloadParameters.generate_from(
            history_download_parameters,
            info_download_parameters,
            instrument_info)
