#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Metadata for export index data from solactive.com
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
    from typing import Annotated


class IndexHistoryTypes(enum.Enum):
    """ History type (period).
    """
    INTRADAY = 'intraday'
    MAX = 'max'


class FileExtensions(enum.Enum):
    """ File extension.
    """
    JSON = '.json'


class FieldNames(enum.Enum):
    """ Field name in JSON.
    """
    INDEX_ID = 'indexId'
    TIMESTAMP = 'timestamp'
    VALUE = 'value'


@dataclasses.dataclass
class IndexValue(InstrumentValueProvider):
    """ Container for index history item.
    """
    index_id: str
    moment: datetime.datetime
    value: decimal.Decimal

    def __init__(self, *, index_id: str, moment: datetime.datetime, value: decimal.Decimal):
        """ Initialize index value.

        :param index_id: Index ID
        :param moment: Moment.
        :param value: Value of index.
        """
        if not isinstance(moment, datetime.datetime):
            raise TypeError("'moment' is not datetime")

        self.index_id = str(index_id)
        self.moment = moment
        self.value = decimal.Decimal(value)

    def get_instrument_value(self, tzinfo: typing.Optional[datetime.timezone]) -> InstrumentValue:
        moment = self.moment.astimezone(tzinfo)
        return InstrumentValue(value=self.value, moment=moment)


@dataclasses.dataclass
class IndexInfo(InstrumentInfoProvider):
    """ Container for index information.
    """
    isin: str
    name: str

    def __init__(self, *, isin: str, name: str):
        self.isin = str(isin)
        self.name = str(name)

    def __str__(self):
        return (f"Splactive index ("
                f"isin={self.isin}, "
                f"name={self.name})")

    @property
    def instrument_info(self) -> InstrumentInfo:
        return InstrumentInfo(code=self.isin, name=self.name)


class SolactiveIndexesInfoDownloadParameters(typing.NamedTuple):
    """ Container for ``SolactiveStringDataDownloader.download_instruments_info_string`` parameters.
    """

    @classmethod
    def safe_create(
            cls: typing.Type['SolactiveIndexesInfoDownloadParameters']) -> 'SolactiveIndexesInfoDownloadParameters':
        """ Create new instance of ``SolactiveIndexesInfoDownloadParameters`` with arguments check.

        :return: ``SolactiveIndexesInfoDownloadParameters`` instance.
        """
        return cls()


@dataclasses.dataclass
class SolactiveIndexHistoryDownloadParameters(InstrumentHistoryDownloadParameters):
    """ Container for ``SolactiveStringDataDownloader.download_instrument_history_string`` parameters.
    """
    isin: Annotated[str, InstrumentInfoParameter(instrument_identity=True)]

    def clone_with_instrument_info_parameters(
            self,
            info_download_parameters: typing.Optional[SolactiveIndexesInfoDownloadParameters],
            instrument_info: typing.Optional[IndexInfo]) -> 'SolactiveIndexHistoryDownloadParameters':
        return SolactiveIndexHistoryDownloadParameters.generate_from(self, info_download_parameters, instrument_info)

    # noinspection PyUnusedLocal
    @classmethod
    def generate_from(
            cls: typing.Type['SolactiveIndexHistoryDownloadParameters'],
            history_download_parameters: typing.Optional['SolactiveIndexHistoryDownloadParameters'],
            info_download_parameters: typing.Optional[SolactiveIndexesInfoDownloadParameters],
            instrument_info: typing.Optional[IndexInfo]) -> 'SolactiveIndexHistoryDownloadParameters':
        """ Create new history download parameters instance with data from its arguments.

        :param history_download_parameters: Optional instrument history download parameters for cloning.
        :param info_download_parameters: Optional instrument info download parameters for cloning.
        :param instrument_info: Optional instrument info for cloning.
        :return: Cloned history download parameters instance (self) with replacing some attributes from
            `info_download_parameters` and `instrument_info`.
        """
        return cls(
            isin=((None if history_download_parameters is None else history_download_parameters.isin)
                  if instrument_info is None
                  else instrument_info.isin)
        )

    @classmethod
    def safe_create(
            cls: typing.Type['SolactiveIndexHistoryDownloadParameters'],
            *,
            isin: str) -> 'SolactiveIndexHistoryDownloadParameters':
        """ Create new instance of ``SolactiveIndexHistoryDownloadParameters`` with arguments check.

        :param isin: ISIN.
        :return: ``SolactiveIndexHistoryDownloadParameters`` instance.
        """
        return cls(isin=str(isin))


class SolactiveDownloadParametersFactory(DownloadParametersFactory):
    """ Download parameters factories and generators for Solactive.
    """

    @property
    def download_history_parameters_class(self) -> typing.Type[SolactiveIndexHistoryDownloadParameters]:
        return SolactiveIndexHistoryDownloadParameters

    @property
    def download_history_parameters_factory(self) -> typing.Callable[..., SolactiveIndexHistoryDownloadParameters]:
        return SolactiveIndexHistoryDownloadParameters.safe_create

    @property
    def download_info_parameters_class(self):
        return SolactiveIndexesInfoDownloadParameters

    @property
    def download_info_parameters_factory(self) -> typing.Callable[..., typing.Any]:
        return SolactiveIndexesInfoDownloadParameters.safe_create

    def generate_history_download_parameters_from(
            self,
            history_download_parameters: typing.Optional[SolactiveIndexHistoryDownloadParameters],
            info_download_parameters: typing.Optional[SolactiveIndexesInfoDownloadParameters],
            instrument_info: typing.Optional[IndexInfo]) -> SolactiveIndexHistoryDownloadParameters:
        return SolactiveIndexHistoryDownloadParameters.generate_from(
            history_download_parameters,
            info_download_parameters,
            instrument_info)
