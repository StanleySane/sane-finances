#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Metadata for export index data from www.lbma.org.uk
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
    """ History JSON field names
    """
    DATE = 'd'
    VALUE = 'v'


class PricePeriods(enum.Enum):
    """ Precious Metal Prices periods
    """
    ANTE_MERIDIEM = 'am'
    POST_MERIDIEM = 'pm'


class PreciousMetals(enum.Enum):
    """ Precious Metals
    """

    def __new__(cls, value: str, description: str, period: typing.Optional[PricePeriods] = None):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.description = str(description)
        obj.period = None if period is None else PricePeriods(period)
        return obj

    def __repr__(self):
        return f"<{self.__class__.__name__}.{self.name}: " \
               f"'{self.value}', '{self.period}'>"

    GOLD_AM = ('gold_am', 'Gold AM', PricePeriods.ANTE_MERIDIEM)
    GOLD_PM = ('gold_pm', 'Gold PM', PricePeriods.POST_MERIDIEM)
    SILVER = ('silver', 'Silver', None)
    PLATINUM_AM = ('platinum_am', 'Platinum AM', PricePeriods.ANTE_MERIDIEM)
    PLATINUM_PM = ('platinum_pm', 'Platinum PM', PricePeriods.POST_MERIDIEM)
    PALLADIUM_AM = ('palladium_am', 'Palladium AM', PricePeriods.ANTE_MERIDIEM)
    PALLADIUM_PM = ('palladium_pm', 'Palladium PM', PricePeriods.POST_MERIDIEM)


class Currencies(enum.Enum):
    """ Precious Metal Prices currencies
    """

    def __new__(cls, value: str, history_position: int):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.history_position = int(history_position)
        return obj

    def __repr__(self):
        return f"<{self.__class__.__name__}.{self.name}: " \
               f"'{self.value}', '{self.history_position}'>"

    USD = ('USD', 0)
    GBP = ('GBP', 1)
    EUR = ('EUR', 2)


@dataclasses.dataclass
class PreciousMetalPrice(InstrumentValueProvider):
    """ Container for Precious Metal Price.
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
        return (f"LBMA Precious Metal Price("
                f"date={self.date.isoformat()}, "
                f"value={self.value})")

    def get_instrument_value(self, tzinfo: typing.Optional[datetime.timezone]) -> InstrumentValue:
        moment = datetime.datetime.combine(self.date, datetime.time.min, tzinfo)
        return InstrumentValue(value=self.value, moment=moment)


@dataclasses.dataclass
class PreciousMetalInfo(InstrumentInfoProvider):
    """ Container for Precious Metal information.
    """
    metal: PreciousMetals

    def __init__(self,
                 *,
                 metal: PreciousMetals):
        self.metal = PreciousMetals(metal)  # pylint: disable=no-value-for-parameter

    def __str__(self):
        return f"LBMA Precious Metal(metal={self.metal})"

    @property
    def instrument_info(self) -> InstrumentInfo:
        return InstrumentInfo(code=self.metal.value, name=self.metal.description)


class LbmaPreciousMetalInfoDownloadParameters(typing.NamedTuple):
    """ Container for ``LbmaStringDataDownloader.download_instruments_info_string parameters``.
    """

    @classmethod
    def safe_create(
            cls: typing.Type['LbmaPreciousMetalInfoDownloadParameters']) -> 'LbmaPreciousMetalInfoDownloadParameters':
        """ Create new instance of ``ISharesInstrumentInfoDownloadParameters`` with arguments check.

        :return: ``LbmaPreciousMetalInfoDownloadParameters`` instance.
        """
        return cls()


@dataclasses.dataclass
class LbmaPreciousMetalHistoryDownloadParameters(InstrumentHistoryDownloadParameters):
    """ Container for ``LbmaStringDataDownloader.download_instrument_history_string parameters``.
    """
    metal: Annotated[PreciousMetals, InstrumentInfoParameter(instrument_identity=True)]
    currency: Currencies

    def clone_with_instrument_info_parameters(
            self,
            info_download_parameters: typing.Optional[LbmaPreciousMetalInfoDownloadParameters],
            instrument_info: typing.Optional[PreciousMetalInfo]) -> 'LbmaPreciousMetalHistoryDownloadParameters':
        return LbmaPreciousMetalHistoryDownloadParameters.generate_from(self, info_download_parameters, instrument_info)

    # noinspection PyUnusedLocal
    @classmethod
    def generate_from(
            cls: typing.Type['LbmaPreciousMetalHistoryDownloadParameters'],
            history_download_parameters: typing.Optional['LbmaPreciousMetalHistoryDownloadParameters'],
            info_download_parameters: typing.Optional[LbmaPreciousMetalInfoDownloadParameters],
            instrument_info: typing.Optional[PreciousMetalInfo]) -> 'LbmaPreciousMetalHistoryDownloadParameters':
        """ Create new history download parameters instance with data from its arguments.

        :param history_download_parameters: Optional instrument history download parameters for cloning.
        :param info_download_parameters: Optional instrument info download parameters for cloning.
        :param instrument_info: Optional instrument info for cloning.
        :return: Cloned history download parameters instance (self) with replacing some attributes from
            `info_download_parameters` and `instrument_info`.
        """
        return cls(
            metal=(
                (None if history_download_parameters is None else history_download_parameters.metal)
                if instrument_info is None
                else instrument_info.metal),
            currency=(None if history_download_parameters is None else history_download_parameters.currency))

    @classmethod
    def safe_create(
            cls: typing.Type['LbmaPreciousMetalHistoryDownloadParameters'],
            *,
            metal: PreciousMetals,
            currency: Currencies) -> 'LbmaPreciousMetalHistoryDownloadParameters':
        """ Create new instance of ``LbmaPreciousMetalHistoryDownloadParameters`` with arguments check.

        :param metal: Precious Metal.
        :param currency: Currency
        :return: ``LbmaPreciousMetalHistoryDownloadParameters`` instance.
        """
        if not isinstance(metal, PreciousMetals):
            raise TypeError(f"'metal' is not PreciousMetals: {metal!r}")
        if not isinstance(currency, Currencies):
            raise TypeError(f"'currency' is not Currencies: {currency!r}")

        return cls(metal=metal, currency=currency)


class LbmaDownloadParametersFactory(DownloadParametersFactory):
    """ Download parameters factories and generators for LBMA.
    """

    @property
    def download_history_parameters_class(self) -> typing.Type[LbmaPreciousMetalHistoryDownloadParameters]:
        return LbmaPreciousMetalHistoryDownloadParameters

    @property
    def download_history_parameters_factory(self) -> typing.Callable[..., LbmaPreciousMetalHistoryDownloadParameters]:
        return LbmaPreciousMetalHistoryDownloadParameters.safe_create

    @property
    def download_info_parameters_class(self):
        return LbmaPreciousMetalInfoDownloadParameters

    @property
    def download_info_parameters_factory(self) -> typing.Callable[..., typing.Any]:
        return LbmaPreciousMetalInfoDownloadParameters.safe_create

    def generate_history_download_parameters_from(
            self,
            history_download_parameters: typing.Optional[LbmaPreciousMetalHistoryDownloadParameters],
            info_download_parameters: typing.Optional[LbmaPreciousMetalInfoDownloadParameters],
            instrument_info: typing.Optional[PreciousMetalInfo]) -> LbmaPreciousMetalHistoryDownloadParameters:
        return LbmaPreciousMetalHistoryDownloadParameters.generate_from(
            history_download_parameters,
            info_download_parameters,
            instrument_info)
