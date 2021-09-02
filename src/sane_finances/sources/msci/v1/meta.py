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
from ....annotations import Volatile, LEGACY_ANNOTATIONS, Description

if LEGACY_ANNOTATIONS:  # pragma: no cover
    from ....annotations import Annotated
else:  # pragma: no cover
    from typing import Annotated


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

    REGIONAL = ('R', 'Regional')
    COUNTRY = ('C', 'Country')


class Markets(enum.Enum):
    """ Market of index.
    """

    def __new__(cls, value: str, description: str, scope: Scopes):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.description = str(description)

        # see https://github.com/PyCQA/pylint/issues/1801 for pylint disable hint details
        obj.scope = Scopes(scope)  # pylint: disable=no-value-for-parameter
        return obj

    def __repr__(self):
        return f"<{self.__class__.__name__}.{self.name}: " \
               f"'{self.value}' ('{self.description}', '{self.scope.description}')>"

    REGIONAL_ALL_COUNTRY = ('1896', 'All Country (DM+EM)', Scopes.REGIONAL)
    REGIONAL_CHINA_MARKETS = ('2809', 'China Markets', Scopes.REGIONAL)
    REGIONAL_DEVELOPED_MARKETS = ('1897', 'Developed Markets (DM)', Scopes.REGIONAL)
    REGIONAL_EMERGING_MARKETS = ('1898', 'Emerging Markets (EM)', Scopes.REGIONAL)
    REGIONAL_FRONTIER_MARKETS = ('2115', 'Frontier Markets (FM)', Scopes.REGIONAL)
    REGIONAL_GCC_AND_ARABIAN_MARKETS = ('1899', 'GCC and Arabian Markets', Scopes.REGIONAL)

    COUNTRY_CHINA_MARKETS = ('2810', 'China Markets', Scopes.COUNTRY)
    COUNTRY_DEVELOPED_MARKETS = ('1900', 'Developed Markets (DM)', Scopes.COUNTRY)
    COUNTRY_EMERGING_MARKETS = ('1901', 'Emerging Markets (EM)', Scopes.COUNTRY)
    COUNTRY_FRONTIER_MARKETS = ('2114', 'Frontier Markets (FM)', Scopes.COUNTRY)
    COUNTRY_GCC_AND_ARABIAN_MARKETS = ('1902', 'GCC and Arabian Markets', Scopes.COUNTRY)


class Formats(enum.Enum):
    """ Response format.
    """
    XML = 'XML'
    CSV = 'CSV'

    @staticmethod
    def get_file_extension(response_format: 'Formats') -> str:
        """ Get suggested file extension (with dot).

        :param response_format: Response format
        :return: Suggested file extension (with dot).
        """
        return {Formats.XML: '.xml', Formats.CSV: '.csv'}[response_format]


class Currencies(enum.Enum):
    """ Index currency.

    The MSCI Country and Regional Indices are calculated in local currency as well as in USD.
    The concept of a “local currency” calculation excludes the impact of currency fluctuations.
    """

    def __new__(cls, value: str, description: str):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.description = str(description)
        return obj

    def __repr__(self):
        return f"<{self.__class__.__name__}.{self.name}: " \
               f"'{self.value}' ('{self.description}')>"

    LOCAL = ('0', 'Local')
    USD = ('15', 'United States Dollar')
    EUR = ('119', 'Euro')
    GBP = ('18', 'British Pound Sterling')
    JPY = ('10', 'Japanese Yen')
    CAD = ('16', 'Canadian Dollar')
    CHF = ('3', 'Swiss Franc')
    HKD = ('11', 'Hong Kong Dollar')
    AUD = ('1', 'Australian Dollar')


class IndexLevels(enum.Enum):
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

    def __new__(cls, value: str, description: str):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.description = str(description)
        return obj

    def __repr__(self):
        return f"<{self.__class__.__name__}.{self.name}: " \
               f"'{self.value}' ('{self.description}')>"

    PRICE = ('0', 'Price')
    NET = ('41', 'Net')
    GROSS = ('40', 'Gross')
    TOTAL_RETURN = ('51', 'TR (for Risk Control indexes)')
    EXCESS_RETURN = ('53', 'ER (for Risk Control indexes)')


class Frequencies(enum.Enum):
    """ Index values frequency.
    """
    DAILY = 'D'
    MONTHLY = 'M'
    YEARLY = 'Y'


class Styles(enum.Enum):
    """ Index style.
    """

    def __new__(cls, value: str, description: str):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.description = str(description)
        return obj

    def __repr__(self):
        return f"<{self.__class__.__name__}.{self.name}: " \
               f"'{self.value}' ('{self.description}')>"

    NONE = ('C', 'None')
    GROWTH = ('G', 'Growth')
    VALUE = ('V', 'Value')


class Sizes(enum.Enum):
    """ Index size.
    """

    def __new__(cls, value: str, description: str, scopes: typing.FrozenSet[Scopes]):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.description = str(description)
        obj.scopes = frozenset(scopes)
        return obj

    def __repr__(self):
        return f"<{self.__class__.__name__}.{self.name}: " \
               f"'{self.value}' ('{self.description}', {{{','.join(s.description for s in self.scopes)}}})>"

    A_SERIES = ('111', 'A-Series', ())
    REGIONAL_ALL_CAP = ('77', 'All Cap (Large+Mid+Small+Micro Cap)', {Scopes.REGIONAL})
    REGIONAL_ALL_MARKET = ('108', 'All Market', {Scopes.REGIONAL})
    REGIONAL_IMI = ('41', 'IMI (Large+Mid+Small Cap)', {Scopes.REGIONAL})
    REGIONAL_LARGE_CAP = ('37', 'Large Cap', {Scopes.REGIONAL})
    REGIONAL_MICRO_CAP = ('76', 'Micro Cap', {Scopes.REGIONAL})
    REGIONAL_MID_CAP = ('38', 'Mid Cap', {Scopes.REGIONAL})
    PROVISIONAL_IMI = ('119', 'Provisional IMI', ())
    PROVISIONAL_SMALL_CAP = ('99', 'Provisional Small Cap', ())
    PROVISIONAL_STANDARD = ('29', 'Provisional Standard', ())
    REGIONAL_SMID = ('40', 'SMID (Small+Mid Cap)', {Scopes.REGIONAL})
    REGIONAL_SMALL_PLUS_MICRO_CAP = ('79', 'Small + Micro Cap', {Scopes.REGIONAL})
    REGIONAL_SMALL_CAP = ('39', 'Small Cap', {Scopes.REGIONAL})
    REGIONAL_STANDARD = ('36', 'Standard (Large+Mid Cap)', {Scopes.REGIONAL})

    COUNTRY_ALL_CAP = ('75', 'All Cap (Large+Mid+Small+Micro Cap)', {Scopes.COUNTRY})
    COUNTRY_ALL_MARKET = ('107', 'All Market', {Scopes.COUNTRY})
    COUNTRY_IMI = ('35', 'IMI (Large+Mid+Small Cap)', {Scopes.COUNTRY})
    COUNTRY_LARGE_CAP = ('31', 'Large Cap', {Scopes.COUNTRY})
    COUNTRY_MICRO_CAP = ('74', 'Micro Cap', {Scopes.COUNTRY})
    COUNTRY_MID_CAP = ('32', 'Mid Cap', {Scopes.COUNTRY})
    COUNTRY_SMID = ('34', 'SMID (Small+Mid Cap)', {Scopes.COUNTRY})
    COUNTRY_SMALL_PLUS_MICRO_CAP = ('78', 'Small + Micro Cap', {Scopes.COUNTRY})
    COUNTRY_SMALL_CAP = ('33', 'Small Cap', {Scopes.COUNTRY})
    COUNTRY_STANDARD = ('30', 'Standard (Large+Mid Cap)', {Scopes.COUNTRY})


class IndexSuiteGroups(enum.Enum):
    """ Group of index suites.
    """
    CAPPED = 'Capped'
    DOMESTIC = 'Domestic'
    EQUAL_SECTOR_WEIGHTED = 'Equal Sector Weighted'
    EQUAL_COUNTRY_WEIGHTED = 'Equal Country Weighted'
    ESG = 'ESG'
    FACTOR_HIGH_EXPOSURE = 'Factor-High Exposure'
    FACTOR_HIGH_CAPACITY = 'Factor-High Capacity'
    HEDGED = 'Hedged'
    LISTED_REAL_ESTATE = 'Listed Real Estate'
    MULTI_FACTOR = 'Multi-Factor'
    THEMATIC = 'Thematic'
    WMA_PRIVATE_INVESTOR_INDICES = 'WMA Private Investor Indices'


class IndexSuites(enum.Enum):
    """ Index suite.

    See https://app2.msci.com/products/service/index/indexmaster/indexsuites
    """

    def __new__(cls, value: str, description: str, group: typing.Optional[IndexSuiteGroups]):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.description = str(description)
        obj.group = group
        return obj

    def __repr__(self):
        return f"<{self.__class__.__name__}.{self.name}: " \
               f"'{self.value}' ('{self.description}', {self.group.value!r})>"

    NONE = ('C', 'None', None)

    # Capped
    CAPPED_10_TO_40 = ('AA', '10/40', IndexSuiteGroups.CAPPED)
    CAPPED_25_TO_50 = ('2', '25/50', IndexSuiteGroups.CAPPED)
    STANDARD_CAPPED = ('9', 'Standard Capped', IndexSuiteGroups.CAPPED)

    # Domestic
    HONG_KONG_MPF_DOMESTIC = ('6', 'Hong Kong MPF Domestic', IndexSuiteGroups.DOMESTIC)
    HONG_KONG_MPF_HEDGED = ('8', 'Hong Kong MPF Hedged', IndexSuiteGroups.DOMESTIC)
    HONG_KONG_MPF_UNHEDGED = ('7', 'Hong Kong MPF Unhedged', IndexSuiteGroups.DOMESTIC)

    # Equal Sector Weighted
    EQUAL_SECTOR_WEIGHTED = ('ES', 'Equal Sector Weighted', IndexSuiteGroups.EQUAL_SECTOR_WEIGHTED)

    # Equal Country Weighted
    EQUAL_COUNTRY_WEIGHTED = ('EC', 'Equal Country Weighted', IndexSuiteGroups.EQUAL_COUNTRY_WEIGHTED)

    # ESG
    COUNTRY_ESG_LEADERS = ('CA', 'Country ESG LEADERS', IndexSuiteGroups.ESG)
    ESG_CUSTOM = ('E', 'ESG Custom', IndexSuiteGroups.ESG)
    ESG_FOCUS = ('EF', 'ESG Focus', IndexSuiteGroups.ESG)
    ESG_LEADERS = ('B', 'ESG LEADERS', IndexSuiteGroups.ESG)
    ESG_SCREENED = ('SR', 'ESG Screened', IndexSuiteGroups.ESG)
    ESG_UNIVERSAL = ('EU', 'ESG Universal', IndexSuiteGroups.ESG)
    EMPOWERING_WOMEN = ('EW', 'Empowering Women (WIN)', IndexSuiteGroups.ESG)
    ENVIRONMENTAL = ('Z', 'Environmental', IndexSuiteGroups.ESG)
    EX_CONTROVERSIAL_WEAPONS = ('X', 'Ex Controversial Weapons', IndexSuiteGroups.ESG)
    EX_TOBACCO_INVOLVEMENT = ('TB', 'Ex Tobacco Involvement', IndexSuiteGroups.ESG)
    SRI = ('J', 'SRI', IndexSuiteGroups.ESG)
    WOMENS_LEADERSHIP = ('WL', "Women's Leadership", IndexSuiteGroups.ESG)

    # Factor-High Exposure
    BARRA_FACTOR = ('R', 'Barra Factor', IndexSuiteGroups.FACTOR_HIGH_EXPOSURE)
    BUYBACK_YIELD = ('BY', 'Buyback Yield', IndexSuiteGroups.FACTOR_HIGH_EXPOSURE)
    DIVIDEND_MASTERS = ('DM', 'Dividend Masters', IndexSuiteGroups.FACTOR_HIGH_EXPOSURE)
    ENHANCED_VALUE = ('EV', 'Enhanced Value', IndexSuiteGroups.FACTOR_HIGH_EXPOSURE)
    EQUAL_WEIGHTED = ('W', 'Equal Weighted', IndexSuiteGroups.FACTOR_HIGH_EXPOSURE)
    EQUAL_WEIGHTED_BUYBACK_YIELD = ('EY', 'Equal Weighted Buyback Yield', IndexSuiteGroups.FACTOR_HIGH_EXPOSURE)
    FACTOR_ESG = ('FE', 'Factor ESG', IndexSuiteGroups.FACTOR_HIGH_EXPOSURE)
    GDP_WEIGHTED = ('D', 'GDP Weighted', IndexSuiteGroups.FACTOR_HIGH_EXPOSURE)
    GOVERNANCE_QUALITY = ('GQ', 'Governance-Quality', IndexSuiteGroups.FACTOR_HIGH_EXPOSURE)
    HIGH_DIVIDEND_YIELD = ('H', 'High Dividend Yield', IndexSuiteGroups.FACTOR_HIGH_EXPOSURE)
    MARKET_NEUTRAL = ('3', 'Market Neutral', IndexSuiteGroups.FACTOR_HIGH_EXPOSURE)
    MINIMUM_VOLATILITY = ('M', 'Minimum Volatility', IndexSuiteGroups.FACTOR_HIGH_EXPOSURE)
    MOMENTUM = ('1', 'Momentum', IndexSuiteGroups.FACTOR_HIGH_EXPOSURE)
    FACTOR_HIGH_EXPOSURE_OTHER = ('FO', 'Other', IndexSuiteGroups.FACTOR_HIGH_EXPOSURE)
    PRIME_VALUE = ('PV', 'Prime Value', IndexSuiteGroups.FACTOR_HIGH_EXPOSURE)
    QUALITY = ('U', 'Quality', IndexSuiteGroups.FACTOR_HIGH_EXPOSURE)
    RISK_CONTROL = ('P', 'Risk Control', IndexSuiteGroups.FACTOR_HIGH_EXPOSURE)
    RISK_WEIGHTED = ('K', 'Risk Weighted', IndexSuiteGroups.FACTOR_HIGH_EXPOSURE)
    SECTOR_NEUTRAL_QUALITY = ('NQ', 'Sector Neutral Quality', IndexSuiteGroups.FACTOR_HIGH_EXPOSURE)
    TOP_50_DIVIDEND = ('TD', 'Top 50 Dividend', IndexSuiteGroups.FACTOR_HIGH_EXPOSURE)
    TOTAL_SHAREHOLDER_YIELD = ('TS', 'Total Shareholder Yield', IndexSuiteGroups.FACTOR_HIGH_EXPOSURE)

    # Factor-High Capacity
    DIVIDEND_TILT = ('DT', 'Dividend Tilt', IndexSuiteGroups.FACTOR_HIGH_CAPACITY)
    MOMENTUM_TILT = ('MT', 'Momentum Tilt', IndexSuiteGroups.FACTOR_HIGH_CAPACITY)
    QUALITY_TILT = ('QT', 'Quality Tilt', IndexSuiteGroups.FACTOR_HIGH_CAPACITY)
    SIZE_TILT = ('ST', 'Size Tilt', IndexSuiteGroups.FACTOR_HIGH_CAPACITY)
    VALUE_WEIGHTED = ('L', 'Value Weighted', IndexSuiteGroups.FACTOR_HIGH_CAPACITY)
    VOLATILITY_TILT = ('VT', 'Volatility Tilt', IndexSuiteGroups.FACTOR_HIGH_CAPACITY)

    # Hedged
    HEDGED = ('5', 'Hedged', IndexSuiteGroups.HEDGED)
    FACTOR_HEDGED = ('FH', 'Factor Hedged', IndexSuiteGroups.HEDGED)
    ADAPTIVE_HEDGED = ('AH', 'Adaptive Hedged', IndexSuiteGroups.HEDGED)
    ESG_HEDGED = ('EH', 'ESG Hedged', IndexSuiteGroups.HEDGED)

    # Listed Real Estate
    CORE_REAL_ESTATE = ('CE', 'Core Real Estate', IndexSuiteGroups.LISTED_REAL_ESTATE)
    CORE_REAL_ESTATE_FACTOR = ('CF', 'Core Real Estate Factor', IndexSuiteGroups.LISTED_REAL_ESTATE)

    # Multi-Factor
    CUSTOM_FACTOR_MIX = ('CM', 'Custom Factor Mix', IndexSuiteGroups.MULTI_FACTOR)
    FACTOR_MIX_A_SERIES = ('4', 'Factor Mix A-Series', IndexSuiteGroups.MULTI_FACTOR)
    FACTOR_MIX_A_SERIES_CAPPED = ('MA', 'Factor Mix A-Series Capped', IndexSuiteGroups.MULTI_FACTOR)
    DIVERSIFIED_MULTIPLE_FACTOR = ('DF', 'Diversified Multiple-Factor', IndexSuiteGroups.MULTI_FACTOR)
    DIVERSIFIED_FACTOR_MIX = ('FM', 'Diversified Factor Mix', IndexSuiteGroups.MULTI_FACTOR)
    DIVERSIFIED_MULTIPLE_FACTOR_R_SERIES = ('MR', 'Diversified Multiple-Factor R-Series', IndexSuiteGroups.MULTI_FACTOR)
    DIVERSIFIED_MULTIPLE_FACTOR_LOW_VOLATILITY = ('MV', 'Diversified Multiple-Factor Low Volatility',
                                                  IndexSuiteGroups.MULTI_FACTOR)
    DIVERSIFIED_MULTIPLE_5_FACTOR = ('M5', 'Diversified Multiple 5-Factor', IndexSuiteGroups.MULTI_FACTOR)
    DIVERSIFIED_MULTIPLE_3_FACTOR = ('M3', 'Diversified Multiple 3-Factor', IndexSuiteGroups.MULTI_FACTOR)
    ADAPTIVE_MULTIPLE_FACTOR = ('AM', 'Adaptive Multiple Factor', IndexSuiteGroups.MULTI_FACTOR)
    MULTI_FACTOR_OTHER = ('MO', 'Other', IndexSuiteGroups.MULTI_FACTOR)

    # Thematic
    AGRICULTURE_AND_FOOD_CHAIN = ('V', 'Agriculture & Food Chain', IndexSuiteGroups.THEMATIC)
    AGRICULTURE_AND_FOOD_CHAIN_SECTOR_CAPPED = ('Q', 'Agriculture & Food Chain Sector Capped',
                                                IndexSuiteGroups.THEMATIC)
    COMMODITY_PRODUCERS = ('O', 'Commodity Producers', IndexSuiteGroups.THEMATIC)
    COMMODITY_PRODUCERS_SECTOR_CAPPED = ('Y', 'Commodity Producers Sector Capped', IndexSuiteGroups.THEMATIC)
    CONSUMER_DEMAND = ('AB', 'Consumer Demand', IndexSuiteGroups.THEMATIC)
    CONSUMER_GROWTH = ('CG', 'Consumer Growth', IndexSuiteGroups.THEMATIC)
    CYCLICAL_SECTORS = ('CS', 'Cyclical Sectors', IndexSuiteGroups.THEMATIC)
    CYCLICAL_SECTORS_CAPPED = ('CC', 'Cyclical Sectors Capped', IndexSuiteGroups.THEMATIC)
    DEFENSIVE_SECTORS = ('DS', 'Defensive Sectors', IndexSuiteGroups.THEMATIC)
    DEFENSIVE_SECTORS_CAPPED = ('DC', 'Defensive Sectors Capped', IndexSuiteGroups.THEMATIC)
    ECONOMIC_EXPOSURE = ('N', 'Economic Exposure', IndexSuiteGroups.THEMATIC)
    FAITH_BASED = ('F', 'Faith-based', IndexSuiteGroups.THEMATIC)
    INFRASTRUCTURE = ('S', 'Infrastructure', IndexSuiteGroups.THEMATIC)
    INFRASTRUCTURE_CAPPED = ('IC', 'Infrastructure Capped', IndexSuiteGroups.THEMATIC)
    ISLAMIC = ('I', 'Islamic', IndexSuiteGroups.THEMATIC)
    ISLAMIC_M_SERIES_NEW = ('IM', 'Islamic M -Series (New)', IndexSuiteGroups.THEMATIC)
    THEMATIC_OTHER = ('TO', 'Other', IndexSuiteGroups.THEMATIC)

    # WMA Private Investor Indices
    WMA_PRIVATE_INVESTOR_INDICES = ('WM', 'WMA Private Investor Indices',
                                    IndexSuiteGroups.WMA_PRIVATE_INVESTOR_INDICES)


@dataclasses.dataclass
class Context:
    """ Contains the group of parameters that identifies MSCI index apart from its ID.

    This context used by REST API even if we know exact index ID,
    i.e. context is ambiguous but mandatory.
    """
    style: Styles
    size: Sizes
    scope: Scopes

    def __init__(self, *, style: Styles, size: Sizes, scope: Scopes):
        self.style = Styles(style)  # pylint: disable=no-value-for-parameter
        self.size = Sizes(size)  # pylint: disable=no-value-for-parameter
        self.scope = Scopes(scope)  # pylint: disable=no-value-for-parameter


@dataclasses.dataclass
class IndexValue(InstrumentValueProvider):
    """ Container for index history item.
    """
    date: datetime.date
    value: decimal.Decimal
    index_name: str
    style: Styles
    size: Sizes

    def __init__(self,
                 *,
                 date: datetime.date,
                 value: decimal.Decimal,
                 index_name: str,
                 style: Styles,
                 size: Sizes):
        if not isinstance(date, datetime.date):
            raise TypeError("value_date is not date")

        self.date = date
        self.value = decimal.Decimal(value)

        self.index_name = str(index_name)
        self.style = Styles(style)  # pylint: disable=no-value-for-parameter
        self.size = Sizes(size)  # pylint: disable=no-value-for-parameter

    def get_instrument_value(self, tzinfo: typing.Optional[datetime.timezone]) -> InstrumentValue:
        return InstrumentValue(
            value=self.value,
            moment=datetime.datetime.combine(self.date, datetime.time.min, tzinfo=tzinfo))


@dataclasses.dataclass
class IndexInfo(InstrumentInfoProvider):
    """ Container for index information.
    """
    index_id: str
    name: str

    def __init__(self, *, index_id: str, name: str):
        self.index_id = str(index_id)
        self.name = str(name)

    def __str__(self):
        return (f"MSCI index ("
                f"index_id={self.index_id}, "
                f"name={self.name})")

    @property
    def instrument_info(self) -> InstrumentInfo:
        return InstrumentInfo(code=self.index_id, name=self.name)


class MsciIndexesInfoDownloadParameters(typing.NamedTuple):
    """ Container for ``MsciStringDataDownloader.download_instruments_info_string`` parameters.
    """
    market: Markets
    context: Context

    @classmethod
    def safe_create(
            cls: typing.Type['MsciIndexesInfoDownloadParameters'],
            *,
            market: Markets,
            context: Context) -> 'MsciIndexesInfoDownloadParameters':
        """ Create new instance of ``MsciIndexesInfoDownloadParameters`` with arguments check.

        :param market: Market.
        :param context: Context.
        :return: ``MsciIndexesInfoDownloadParameters`` instance.
        """
        if not isinstance(context, Context):
            raise TypeError(f"'context' is not Context: {context!r}")

        return cls(
            market=Markets(market),  # pylint: disable=no-value-for-parameter
            context=context)


@dataclasses.dataclass
class MsciIndexHistoryDownloadParameters(InstrumentHistoryDownloadParameters):
    """ Container for ``MsciStringDataDownloader.download_instrument_history_string`` parameters.
    """
    index_id: Annotated[str, InstrumentInfoParameter(instrument_identity=True)]
    context: Annotated[Context, InstrumentInfoParameter()]
    index_level: IndexLevels
    currency: Currencies
    date_from: Annotated[datetime.date,
                         Description(description="Minimum date of interval to download data. "
                                                 "Usually it equals to the first date of instrument history.")]
    date_to: Annotated[datetime.date,
                       Description(description="Maximum date of interval to download data. "
                                               "It have to be 'today' or '31-12-9999'."),
                       Volatile(generator=lambda ctx: datetime.date.today(), stub_value=datetime.date.max)]

    def clone_with_instrument_info_parameters(
            self,
            info_download_parameters: typing.Optional[MsciIndexesInfoDownloadParameters],
            instrument_info: typing.Optional[IndexInfo]) -> 'MsciIndexHistoryDownloadParameters':
        return MsciIndexHistoryDownloadParameters.generate_from(self, info_download_parameters, instrument_info)

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
            index_id=((None if history_download_parameters is None else history_download_parameters.index_id)
                      if instrument_info is None
                      else instrument_info.index_id),
            context=((None if history_download_parameters is None else history_download_parameters.context)
                     if info_download_parameters is None
                     else info_download_parameters.context),
            index_level=(None if history_download_parameters is None else history_download_parameters.index_level),
            currency=(None if history_download_parameters is None else history_download_parameters.currency),
            date_from=(None if history_download_parameters is None else history_download_parameters.date_from),
            date_to=(None if history_download_parameters is None else history_download_parameters.date_to),
        )

    @classmethod
    def safe_create(
            cls: typing.Type['MsciIndexHistoryDownloadParameters'],
            *,
            index_id: str,
            context: Context,
            index_level: IndexLevels,
            currency: Currencies,
            date_from: datetime.date,
            date_to: datetime.date) -> 'MsciIndexHistoryDownloadParameters':
        """ Create new instance of ``MsciIndexHistoryDownloadParameters`` with arguments check.

        :param index_id: Index ID.
        :param context: Context/
        :param index_level: Index level.
        :param currency: Currency.
        :param date_from: Download interval beginning.
        :param date_to: Download interval ending.
        :return: ``MsciIndexHistoryDownloadParameters`` instance.
        """
        if not isinstance(context, Context):
            raise TypeError(f"'context' is not Context: {context!r}")
        if not isinstance(date_from, datetime.date):
            raise TypeError(f"'date_from' is not datetime.date: {date_from!r}")
        if not isinstance(date_to, datetime.date):
            raise TypeError(f"'date_to' is not datetime.date: {date_to!r}")
        if date_from > date_to:
            raise ValueError(f"'date_from' ({date_from.isoformat()}) is greater than 'date_to' ({date_to.isoformat()})")

        return cls(
            index_id=str(index_id),
            context=context,
            index_level=IndexLevels(index_level),  # pylint: disable=no-value-for-parameter
            currency=Currencies(currency),  # pylint: disable=no-value-for-parameter
            date_from=date_from,
            date_to=date_to)


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
