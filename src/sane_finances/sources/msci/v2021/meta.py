#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Metadata for export index data from app2.msci.com
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


class Scopes(enum.Enum):
    """ Index scope.
    """

    def __new__(cls, value: str, description: str):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.description = str(description)
        return obj

    def __repr__(self):
        return f"<{self.__class__.__name__}.{self.name}: " \
               f"'{self.value}' ('{self.description}')>"

    REGIONAL = ('Region', 'Regional')
    COUNTRY = ('Country', 'Country')


class Market(typing.NamedTuple):
    """ Market from msci.com.
    """
    identity: str
    name: str
    scope: typing.Optional[Scopes] = None

    @classmethod
    def safe_create(
            cls: typing.Type['Market'],
            *,
            identity: str,
            name: str,
            scope: Scopes = None) -> 'Market':
        """ Create new instance of ``Market`` with arguments check.

        :param identity: Identity value.
        :param name: Name.
        :param scope: Scope. ``None`` if market is available for all scopes.
        :return: ``Market`` instance.
        """
        if scope is not None and not isinstance(scope, Scopes):
            raise TypeError("'scope' is not Scopes")

        # see https://github.com/PyCQA/pylint/issues/1801 for pylint disable hint details
        return cls(
            identity=str(identity),
            name=str(name),
            scope=None if scope is None else Scopes(scope))  # pylint: disable=no-value-for-parameter


class Currency(typing.NamedTuple):
    """ Index currency.

    The MSCI Country and Regional Indices are calculated in local currency as well as in USD.
    The concept of a “local currency” calculation excludes the impact of currency fluctuations.
    """
    identity: str
    name: str

    @classmethod
    def safe_create(
            cls: typing.Type['Currency'],
            *,
            identity: str,
            name: str) -> 'Currency':
        """ Create new instance of ``Currency`` with arguments check.

        :param identity: Identity value.
        :param name: Currency name.
        :return: ``Currency`` instance.
        """
        return cls(identity=str(identity), name=str(name))


class IndexLevel(typing.NamedTuple):
    """ Index level (or price level).

    Total return indices measure the market performance,
    including price performance and income from regular cash distributions
    (cash dividend payments or capital repayments).

    Gross Daily Total Return: This series approximates the maximum possible reinvestment
    of regular cash distributions (dividends or capital repayments).
    The amount reinvested is the cash distributed to individuals resident in the country of the company,
    but does not include tax credits.

    Net Daily Total Return: This series approximates the minimum possible reinvestment
    of regular cash distributions. Provided that the regular capital repayment is not subject to withholding tax,
    the reinvestment in the Net Daily Total Return is free of withholding tax.

    The Total Return Index that represents the weighted return of the MSCI parent index
    and the cash component.

    The Excess Return Index that represents the return of the Total Return Index
    minus the return of the cash component.
    """
    identity: str
    name: str

    @classmethod
    def safe_create(
            cls: typing.Type['IndexLevel'],
            *,
            identity: str,
            name: str) -> 'IndexLevel':
        """ Create new instance of ``IndexLevel`` with arguments check.

        :param identity: Identity value.
        :param name: Index level name.
        :return: ``IndexLevel`` instance.
        """
        return cls(identity=str(identity), name=str(name))


class Frequency(typing.NamedTuple):
    """ Index values frequency.
    """
    identity: str
    name: str

    @classmethod
    def safe_create(
            cls: typing.Type['Frequency'],
            *,
            identity: str,
            name: str) -> 'Frequency':
        """ Create new instance of ``Frequency`` with arguments check.

        :param identity: Identity value.
        :param name: Frequency name.
        :return: ``Frequency`` instance.
        """
        return cls(identity=str(identity), name=str(name))


class Style(typing.NamedTuple):
    """ Index style.
    """
    identity: str
    name: str

    @classmethod
    def safe_create(
            cls: typing.Type['Style'],
            *,
            identity: str,
            name: str) -> 'Style':
        """ Create new instance of ``Style`` with arguments check.

        :param identity: Identity value.
        :param name: Style name.
        :return: ``Style`` instance.
        """
        return cls(identity=str(identity), name=str(name))


class Size(typing.NamedTuple):
    """ Index size.
    """
    identity: str
    name: str

    @classmethod
    def safe_create(
            cls: typing.Type['Size'],
            *,
            identity: str,
            name: str) -> 'Size':
        """ Create new instance of ``Size`` with arguments check.

        :param identity: Identity value.
        :param name: Size name.
        :return: ``Size`` instance.
        """
        return cls(identity=str(identity), name=str(name))


class IndexSuiteGroup(typing.NamedTuple):
    """ Group of index suites.
    """
    name: str

    @classmethod
    def safe_create(
            cls: typing.Type['IndexSuiteGroup'],
            *,
            name: str) -> 'IndexSuiteGroup':
        """ Create new instance of ``IndexSuiteGroup`` with arguments check.

        :param name: Index suite group name.
        :return: ``IndexSuiteGroup`` instance.
        """
        return cls(name=str(name))


class IndexSuite(typing.NamedTuple):
    """ Index suite.
    """
    identity: str
    name: str
    group: typing.Optional[IndexSuiteGroup] = None

    @classmethod
    def safe_create(
            cls: typing.Type['IndexSuite'],
            *,
            identity: str,
            name: str,
            group: typing.Optional[IndexSuiteGroup] = None) -> 'IndexSuite':
        """ Create new instance of ``IndexSuite`` with arguments check.

        :param identity: Identity value.
        :param name: Index suite name.
        :param group: Index suite group. ``None`` if index suite is not inside any group.
        :return: ``IndexSuite`` instance.
        """
        if group is not None and not isinstance(group, IndexSuiteGroup):
            raise TypeError("'group' is not IndexSuiteGroup")

        return cls(identity=str(identity), name=str(name), group=group)


class IndexPanelData(typing.NamedTuple):
    """ Container for index panel data from msci.com.
    """
    markets: typing.Tuple[Market, ...]
    currencies: typing.Tuple[Currency, ...]
    index_levels: typing.Tuple[IndexLevel, ...]
    frequencies: typing.Tuple[Frequency, ...]
    index_suite_groups: typing.Tuple[IndexSuiteGroup, ...]
    index_suites: typing.Tuple[IndexSuite, ...]
    sizes: typing.Tuple[Size, ...]
    styles: typing.Tuple[Style, ...]
    daily_frequency: Frequency
    monthly_frequency: Frequency


@dataclasses.dataclass
class IndexValue(InstrumentValueProvider):
    """ Container for index history item.
    """
    calc_date: datetime.date
    level_eod: decimal.Decimal
    msci_index_code: str
    index_variant_type: IndexLevel
    currency: Currency

    def __init__(self,
                 *,
                 calc_date: datetime.date,
                 level_eod: decimal.Decimal,
                 msci_index_code: str,
                 index_variant_type: IndexLevel,
                 currency: Currency):
        if not isinstance(calc_date, datetime.date):
            raise TypeError("'calc_date' is not date")
        if not isinstance(index_variant_type, IndexLevel):
            raise TypeError("'index_variant_type' is not IndexLevel")
        if not isinstance(currency, Currency):
            raise TypeError("'currency' is not Currency")

        self.calc_date = calc_date
        self.level_eod = decimal.Decimal(level_eod)

        self.msci_index_code = str(msci_index_code)
        self.index_variant_type = index_variant_type
        self.currency = currency

    def get_instrument_value(self, tzinfo: typing.Optional[datetime.timezone]) -> InstrumentValue:
        return InstrumentValue(
            value=self.level_eod,
            moment=datetime.datetime.combine(self.calc_date, datetime.time.min, tzinfo=tzinfo))


@dataclasses.dataclass
class IndexInfo(InstrumentInfoProvider):
    """ Container for index information.
    """
    msci_index_code: str
    index_name: str

    def __init__(self, *, msci_index_code: str, index_name: str):
        self.msci_index_code = str(msci_index_code)
        self.index_name = str(index_name)

    def __str__(self):
        return (f"MSCI index ("
                f"msci_index_code={self.msci_index_code}, "
                f"index_name={self.index_name})")

    @property
    def instrument_info(self) -> InstrumentInfo:
        return InstrumentInfo(code=self.msci_index_code, name=self.index_name)


class MsciIndexesInfoDownloadParameters(typing.NamedTuple):
    """ Container for ``MsciStringDataDownloader.download_instruments_info_string parameters``.
    """
    index_scope: Scopes
    index_market: Market
    index_size: Size
    index_style: Style
    index_suite: IndexSuite

    @classmethod
    def safe_create(
            cls: typing.Type['MsciIndexesInfoDownloadParameters'],
            *,
            index_scope: Scopes,
            index_market: Market,
            index_size: Size,
            index_style: Style,
            index_suite: IndexSuite) -> 'MsciIndexesInfoDownloadParameters':
        """ Create new instance of ``MsciIndexesInfoDownloadParameters`` with arguments check.

        :param index_scope: Index scope.
        :param index_market: Index market.
        :param index_size: Index size.
        :param index_style: Index style.
        :param index_suite: Index suite.
        :return: ``MsciIndexesInfoDownloadParameters`` instance.
        """
        if not isinstance(index_scope, Scopes):
            raise TypeError(f"'index_scope' is not Scopes: {index_scope!r}")
        if not isinstance(index_market, Market):
            raise TypeError(f"'index_market' is not Market: {index_market!r}")
        if not isinstance(index_size, Size):
            raise TypeError(f"'index_size' is not Size: {index_size!r}")
        if not isinstance(index_style, Style):
            raise TypeError(f"'index_style' is not Style: {index_style!r}")
        if not isinstance(index_suite, IndexSuite):
            raise TypeError(f"'index_suite' is not IndexSuite: {index_suite!r}")

        return cls(
            index_scope=index_scope,
            index_market=index_market,
            index_size=index_size,
            index_style=index_style,
            index_suite=index_suite)


@dataclasses.dataclass
class MsciIndexHistoryDownloadParameters(InstrumentHistoryDownloadParameters):
    """ Container for ``MsciStringDataDownloader.download_instrument_history_string parameters``.
    """
    index_code: Annotated[str, InstrumentInfoParameter(instrument_identity=True)]
    currency: Currency
    index_variant: IndexLevel

    def clone_with_instrument_info_parameters(
            self,
            info_download_parameters: typing.Optional[MsciIndexesInfoDownloadParameters],
            instrument_info: typing.Optional[IndexInfo]) -> 'MsciIndexHistoryDownloadParameters':
        return MsciIndexHistoryDownloadParameters.generate_from(self, info_download_parameters, instrument_info)

    # noinspection PyUnusedLocal
    @classmethod
    def generate_from(
            cls: typing.Type['MsciIndexHistoryDownloadParameters'],
            history_download_parameters: typing.Optional['MsciIndexHistoryDownloadParameters'],
            info_download_parameters: typing.Optional[MsciIndexesInfoDownloadParameters],
            instrument_info: typing.Optional[IndexInfo]) -> 'MsciIndexHistoryDownloadParameters':
        """ Create new history download parameters instance with data from its arguments.

        :param history_download_parameters: Optional instrument history download parameters for cloning.
        :param info_download_parameters: Optional instrument info download parameters for cloning.
        :param instrument_info: Optional instrument info for cloning.
        :return: Cloned history download parameters instance (self) with replacing some attributes from
            `info_download_parameters` and `instrument_info`.
        """
        return cls(
            index_code=((None if history_download_parameters is None else history_download_parameters.index_code)
                        if instrument_info is None
                        else instrument_info.msci_index_code),
            currency=(None if history_download_parameters is None else history_download_parameters.currency),
            index_variant=(None if history_download_parameters is None else history_download_parameters.index_variant)
        )

    @classmethod
    def safe_create(
            cls: typing.Type['MsciIndexHistoryDownloadParameters'],
            *,
            index_code: str,
            currency: Currency,
            index_variant: IndexLevel) -> 'MsciIndexHistoryDownloadParameters':
        """ Create new instance of ``MsciIndexHistoryDownloadParameters`` with arguments check.

        :param index_code: Index code.
        :param currency: Currency.
        :param index_variant: Index level.
        :return: ``MsciIndexHistoryDownloadParameters`` instance.
        """
        if not isinstance(currency, Currency):
            raise TypeError(f"'currency' is not Currency: {currency!r}")
        if not isinstance(index_variant, IndexLevel):
            raise TypeError(f"'index_variant' is not IndexLevel: {index_variant!r}")

        return cls(
            index_code=str(index_code),
            currency=currency,
            index_variant=index_variant)


class MsciDownloadParametersFactory(DownloadParametersFactory):
    """ Download parameters factories and generators for MSCI.
    """

    @property
    def download_history_parameters_class(self) -> typing.Type[MsciIndexHistoryDownloadParameters]:
        return MsciIndexHistoryDownloadParameters

    @property
    def download_history_parameters_factory(self) -> typing.Callable[..., MsciIndexHistoryDownloadParameters]:
        return MsciIndexHistoryDownloadParameters.safe_create

    @property
    def download_info_parameters_class(self):
        return MsciIndexesInfoDownloadParameters

    @property
    def download_info_parameters_factory(self) -> typing.Callable[..., typing.Any]:
        return MsciIndexesInfoDownloadParameters.safe_create

    def generate_history_download_parameters_from(
            self,
            history_download_parameters: typing.Optional[MsciIndexHistoryDownloadParameters],
            info_download_parameters: typing.Optional[MsciIndexesInfoDownloadParameters],
            instrument_info: typing.Optional[IndexInfo]) -> MsciIndexHistoryDownloadParameters:
        return MsciIndexHistoryDownloadParameters.generate_from(
            history_download_parameters,
            info_download_parameters,
            instrument_info)
