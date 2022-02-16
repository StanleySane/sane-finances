#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Metadata for export index data from https://www.spglobal.com/spdji/
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
from ....annotations import LEGACY_ANNOTATIONS, Volatile

if LEGACY_ANNOTATIONS:  # pragma: no cover
    from ....annotations import Annotated
else:  # pragma: no cover
    from typing import Annotated  # pylint: disable=no-name-in-module


class HistoryFieldNames(enum.Enum):
    """ Field names in history JSON.
    """
    RETURN_TYPE_HOLDER = 'idsIndexReturnTypeHolder'
    RETURN_TYPE_CODE = 'returnTypeCode'
    RETURN_TYPE_NAME = 'returnTypeName'
    CURRENCY_HOLDER = 'idsIndexCurrencyHolder'
    CURRENCY_CODE = 'currencyCode'
    DETAIL_HOLDER = 'indexDetailHolder'
    LEVELS_HOLDER = 'indexLevelsHolder'
    LEVELS = 'indexLevels'
    EFFECTIVE_DATE = 'effectiveDate'
    INDEX_ID = 'indexId'
    INDEX_VALUE = 'indexValue'
    SERVICE_MESSAGES = 'serviceMessages'
    STATUS = 'status'


class InfoFieldNames(enum.Enum):
    """ Field names in info JSON.
    """
    PAGINATION = 'pagination'
    PAGE_SIZE = 'pageSize'
    START_PAGE_INDEX = 'startPageIndex'
    TOTAL_PAGES = 'totalPages'
    RESPONSE = 'response'
    INDEX_ID = 'indexId'
    INDEX_NAME = 'indexName'
    URL_TITLE = 'urlTitle'


class IndexFinderFilterGroup(typing.NamedTuple):
    """ Index finder filter group
    """
    name: str
    label: str

    @classmethod
    def safe_create(
            cls: typing.Type['IndexFinderFilterGroup'],
            *,
            name: str,
            label: str) -> 'IndexFinderFilterGroup':
        """ Create new instance of ``IndexFinderFilterGroup`` with arguments check.

        :param name: Name of filter group.
        :param label: Label for filter group.
        :return: ``IndexFinderFilterGroup`` instance.
        """
        return cls(name=str(name), label=str(label))


class IndexFinderFilter(typing.NamedTuple):
    """ Index finder filter
    """
    group: IndexFinderFilterGroup
    label: str
    value: str

    @classmethod
    def safe_create(
            cls: typing.Type['IndexFinderFilter'],
            *,
            group: IndexFinderFilterGroup,
            label: str,
            value: str) -> 'IndexFinderFilter':
        """ Create new instance of ``IndexFinderFilter`` with arguments check.

        :param group: Index finder filter group.
        :param label: Label for filter parameter.
        :param value: Value of filter parameter.
        :return: ``IndexFinderFilter`` instance.
        """
        if not isinstance(group, IndexFinderFilterGroup):
            raise TypeError("'group' is not IndexFinderFilterGroup")

        return cls(
            group=group,
            label=str(label),
            value=str(value))


class Currency(typing.NamedTuple):
    """ Index currency.
    """
    currency_code: str

    @classmethod
    def safe_create(
            cls: typing.Type['Currency'],
            *,
            currency_code: str) -> 'Currency':
        """ Create new instance of ``Currency`` with arguments check.

        :param currency_code: Currency code.
        :return: ``Currency`` instance.
        """
        return cls(currency_code=str(currency_code))


class ReturnType(typing.NamedTuple):
    """ Index return type.

    For example price return, total return or net total return.
    """
    return_type_code: str
    return_type_name: str

    @classmethod
    def safe_create(
            cls: typing.Type['ReturnType'],
            *,
            return_type_code: str,
            return_type_name: str) -> 'ReturnType':
        """ Create new instance of ``ReturnType`` with arguments check.

        :param return_type_code: Return type code.
        :param return_type_name: Return type name.
        :return: ``ReturnType`` instance.
        """
        return cls(return_type_code=str(return_type_code), return_type_name=str(return_type_name))


class IndexMetaData(typing.NamedTuple):
    """ Container for index meta data
    """
    currencies: typing.Tuple[Currency, ...]
    return_types: typing.Tuple[ReturnType, ...]
    index_finder_filters: typing.Tuple[IndexFinderFilter, ...]


@dataclasses.dataclass
class IndexLevel(InstrumentValueProvider):
    """ Container for index history value.
    """
    index_id: str
    effective_date: datetime.datetime
    index_value: decimal.Decimal

    def __init__(self,
                 *,
                 index_id: str,
                 effective_date: datetime.datetime,
                 index_value: decimal.Decimal):
        if not isinstance(effective_date, datetime.datetime):
            raise TypeError("'effective_date' is not datetime")

        self.index_id = index_id
        self.effective_date = effective_date
        self.index_value = decimal.Decimal(index_value)

    def __str__(self):
        return (f"S&P Dow Jones index level ("
                f"index_id={self.index_id}, "
                f"effective_date={self.effective_date.isoformat()}, "
                f"index_value={self.index_value})")

    def get_instrument_value(self, tzinfo: typing.Optional[datetime.timezone]) -> InstrumentValue:
        moment = self.effective_date.astimezone(tzinfo)
        return InstrumentValue(value=self.index_value, moment=moment)


@dataclasses.dataclass
class IndexInfo(InstrumentInfoProvider):
    """ Container for index information.
    """
    index_id: str
    index_name: str
    url: str

    def __init__(self, *, index_id: str, index_name: str, url: str):
        self.index_id = str(index_id)
        self.index_name = str(index_name)
        self.url = str(url)

    def __str__(self):
        return (f"S&P Dow Jones index ("
                f"index_id={self.index_id}, "
                f"index_name={self.index_name}, "
                f"url={self.url})")

    @property
    def instrument_info(self) -> InstrumentInfo:
        return InstrumentInfo(code=self.index_id, name=self.index_name)


class SpdjIndexesInfoDownloadParameters(typing.NamedTuple):
    """ Container for ``SpdjStringDataDownloader.download_instruments_info_string parameters``.
    """
    page_number: Annotated[int, Volatile(generator=lambda ctx: 1, stub_value=1)]
    index_finder_filter: IndexFinderFilter = None

    @classmethod
    def safe_create(
            cls: typing.Type['SpdjIndexesInfoDownloadParameters'],
            *,
            page_number: int,
            index_finder_filter: IndexFinderFilter = None) -> 'SpdjIndexesInfoDownloadParameters':
        """ Create new instance of ``SpdjIndexesInfoDownloadParameters`` with arguments check.

        :param page_number: Number of page to download.
        :param index_finder_filter: Index finder filters or ``None``.
        :return: ``SpdjIndexesInfoDownloadParameters`` instance.
        """
        if index_finder_filter is not None and not isinstance(index_finder_filter, IndexFinderFilter):
            raise TypeError("'index_finder_filter' is not IndexFinderFilter")

        return cls(index_finder_filter=index_finder_filter, page_number=int(page_number))


@dataclasses.dataclass
class SpdjIndexHistoryDownloadParameters(InstrumentHistoryDownloadParameters):
    """ Container for ``SpdjStringDataDownloader.download_instrument_history_string parameters``.
    """
    index_id: Annotated[str, InstrumentInfoParameter(instrument_identity=True)]
    currency: Currency
    return_type: ReturnType

    def clone_with_instrument_info_parameters(
            self,
            info_download_parameters: typing.Optional[SpdjIndexesInfoDownloadParameters],
            instrument_info: typing.Optional[IndexInfo]) -> 'SpdjIndexHistoryDownloadParameters':
        return SpdjIndexHistoryDownloadParameters.generate_from(self, info_download_parameters, instrument_info)

    # noinspection PyUnusedLocal
    @classmethod
    def generate_from(
            cls: typing.Type['SpdjIndexHistoryDownloadParameters'],
            history_download_parameters: typing.Optional['SpdjIndexHistoryDownloadParameters'],
            info_download_parameters: typing.Optional[SpdjIndexesInfoDownloadParameters],
            instrument_info: typing.Optional[IndexInfo]) -> 'SpdjIndexHistoryDownloadParameters':
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
            currency=(None if history_download_parameters is None else history_download_parameters.currency),
            return_type=(None if history_download_parameters is None else history_download_parameters.return_type)
        )

    @classmethod
    def safe_create(
            cls: typing.Type['SpdjIndexHistoryDownloadParameters'],
            *,
            index_id: str,
            currency: Currency,
            return_type: ReturnType) -> 'SpdjIndexHistoryDownloadParameters':
        """ Create new instance of ``SpdjIndexHistoryDownloadParameters`` with arguments check.

        :param index_id: Index code.
        :param currency: Currency.
        :param return_type: Return type.
        :return: ``SpdjIndexHistoryDownloadParameters`` instance.
        """
        if not isinstance(currency, Currency):
            raise TypeError(f"'currency' is not Currency: {currency!r}")
        if not isinstance(return_type, ReturnType):
            raise TypeError(f"'return_type' is not ReturnType: {return_type!r}")

        return cls(
            index_id=str(index_id),
            currency=currency,
            return_type=return_type)


class SpdjDownloadParametersFactory(DownloadParametersFactory):
    """ Download parameters factories and generators for S&P Dow Jones.
    """

    @property
    def download_history_parameters_class(self) -> typing.Type[SpdjIndexHistoryDownloadParameters]:
        return SpdjIndexHistoryDownloadParameters

    @property
    def download_history_parameters_factory(self) -> typing.Callable[..., SpdjIndexHistoryDownloadParameters]:
        return SpdjIndexHistoryDownloadParameters.safe_create

    @property
    def download_info_parameters_class(self):
        return SpdjIndexesInfoDownloadParameters

    @property
    def download_info_parameters_factory(self) -> typing.Callable[..., typing.Any]:
        return SpdjIndexesInfoDownloadParameters.safe_create

    def generate_history_download_parameters_from(
            self,
            history_download_parameters: typing.Optional[SpdjIndexHistoryDownloadParameters],
            info_download_parameters: typing.Optional[SpdjIndexesInfoDownloadParameters],
            instrument_info: typing.Optional[IndexInfo]) -> SpdjIndexHistoryDownloadParameters:
        return SpdjIndexHistoryDownloadParameters.generate_from(
            history_download_parameters,
            info_download_parameters,
            instrument_info)
