#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Metadata for export index data from moex.com
"""

import decimal
import typing
import enum
import datetime
import dataclasses

from ...base import (
    InstrumentValue, InstrumentInfo, InstrumentValueProvider, InstrumentInfoProvider,
    InstrumentHistoryDownloadParameters, DownloadParametersFactory)
from ...inspection import InstrumentInfoParameter
from ....annotations import LEGACY_ANNOTATIONS, Volatile

if LEGACY_ANNOTATIONS:  # pragma: no cover
    from ....annotations import Annotated
else:  # pragma: no cover
    from typing import Annotated


class ResponseFormats(enum.Enum):
    """ Response formats
    """
    XML = 'xml'
    CSV = 'csv'
    JSON = 'json'
    HTML = 'html'


class JsonFormats(enum.Enum):
    """ JSON formats
    """
    COMPACT = 'compact'
    EXTENDED = 'extended'


class Limits(enum.Enum):
    """ Limits of data (page size) in one response
    """
    ONE = 1
    FIVE = 5
    TEN = 10
    TWENTY = 20
    FIFTY = 50
    HUNDRED = 100


class TradeEngine(typing.NamedTuple):
    """ Trade engine from moex.com.
    """
    identity: int
    name: str
    title: str

    @classmethod
    def safe_create(
            cls: typing.Type['TradeEngine'],
            *,
            identity: int,
            name: str,
            title: str) -> 'TradeEngine':
        """ Create new instance of ``TradeEngine`` with arguments check.

        :param identity: Identity value.
        :param name: Name.
        :param title: Title.
        :return: ``TradeEngine`` instance.
        """
        return cls(identity=int(identity), name=str(name), title=str(title))


class Market(typing.NamedTuple):
    """ Market from moex.com.
    """
    identity: int
    trade_engine: TradeEngine
    name: str
    title: str
    marketplace: str

    @classmethod
    def safe_create(
            cls: typing.Type['Market'],
            *,
            identity: int,
            trade_engine: TradeEngine,
            name: str,
            title: str,
            marketplace: str) -> 'Market':
        """ Create new instance of ``Market`` with arguments check.

        :param identity: Identity value.
        :param trade_engine: Trade engine.
        :param name: Name.
        :param title: Title.
        :param marketplace: Marketplace.
        :return: ``Market`` instance.
        """
        if not isinstance(trade_engine, TradeEngine):
            raise TypeError("'trade_engine' is not TradeEngine")

        return cls(
            identity=int(identity),
            trade_engine=trade_engine,
            name=str(name),
            title=str(title),
            marketplace=str(marketplace))


class Board(typing.NamedTuple):
    """ Board from moex.com.
    """
    identity: int
    trade_engine: TradeEngine
    market: Market
    boardid: str
    title: str
    is_traded: bool
    has_candles: bool
    is_primary: bool

    @classmethod
    def safe_create(
            cls: typing.Type['Board'],
            *,
            identity: int,
            trade_engine: TradeEngine,
            market: Market,
            boardid: str,
            title: str,
            is_traded: bool,
            has_candles: bool,
            is_primary: bool) -> 'Board':
        """ Create new instance of ``Board`` with arguments check.

        :param identity: Identity value.
        :param trade_engine: Trade engine.
        :param market: Market.
        :param boardid: Board ID.
        :param title: Title.
        :param is_traded: Is board traded.
        :param has_candles: Has board candles.
        :param is_primary: Is board primary.
        :return: ``Board`` instance.
        """
        if not isinstance(trade_engine, TradeEngine):
            raise TypeError("'trade_engine' is not TradeEngine")
        if not isinstance(market, Market):
            raise TypeError("'market' is not Market")

        return cls(
            identity=int(identity),
            trade_engine=trade_engine,
            market=market,
            boardid=str(boardid),
            title=str(title),
            is_traded=bool(is_traded),
            has_candles=bool(has_candles),
            is_primary=bool(is_primary))


class GlobalIndexData(typing.NamedTuple):
    """ Container for global index data from moex.com.
    """
    trade_engines: typing.Tuple[TradeEngine, ...]
    markets: typing.Tuple[Market, ...]
    boards: typing.Tuple[Board, ...]


@dataclasses.dataclass
class SecurityValue(InstrumentValueProvider):
    """ Container for security history item.
    """
    trade_date: datetime.date
    close: decimal.Decimal

    def __init__(self,
                 *,
                 trade_date: datetime.date,
                 close: decimal.Decimal):
        """ Initialize instance.

        :param trade_date: Trade date.
        :param close: Close value.
        """
        if not isinstance(trade_date, datetime.date):
            raise TypeError("'trade_date' is not date")

        self.trade_date = trade_date
        self.close = decimal.Decimal(close)

    def get_instrument_value(self, tzinfo: typing.Optional[datetime.timezone]) -> InstrumentValue:
        return InstrumentValue(
            value=self.close,
            moment=datetime.datetime.combine(self.trade_date, datetime.time.min, tzinfo=tzinfo))


@dataclasses.dataclass
class SecurityInfo(InstrumentInfoProvider):
    """ Container for security information.
    """
    sec_id: str
    board: Board
    short_name: str
    lot_size: typing.Optional[int]
    sec_name: typing.Optional[str]
    isin: typing.Optional[str]
    lat_name: typing.Optional[str]
    reg_number: typing.Optional[str]
    coupon_period: typing.Optional[int]
    coupon_percent: typing.Optional[float]

    def __init__(self,
                 *,
                 sec_id: str,
                 board: Board,
                 short_name: str,
                 lot_size: int = None,
                 sec_name: str = None,
                 isin: str = None,
                 lat_name: str = None,
                 reg_number: str = None,
                 coupon_period: int = None,
                 coupon_percent: float = None):
        if not isinstance(board, Board):
            raise TypeError("'board' is not Board")

        self.sec_id = str(sec_id)
        self.board = board
        self.short_name = str(short_name)
        self.lot_size = None if lot_size is None else int(lot_size)
        self.sec_name = None if sec_name is None else str(sec_name)
        self.isin = None if isin is None else str(isin)
        self.lat_name = None if lat_name is None else str(lat_name)
        self.reg_number = None if reg_number is None else str(reg_number)
        self.coupon_period = None if coupon_period is None else int(coupon_period)
        self.coupon_percent = None if coupon_percent is None else float(coupon_percent)

    def __str__(self):
        return (f"MOEX security ("
                f"sec_id={self.sec_id!r}, "
                f"short_name={self.short_name!r}, "
                f"sec_name={self.sec_name!r}, "
                f"isin={self.isin!r}, "
                f"lat_name={self.lat_name!r}, "
                f"lot_size={self.lot_size}, "
                f"engine={self.board.trade_engine.name!r}, "
                f"market={self.board.market.name!r}, "
                f"board={self.board.boardid!r}, "
                f"reg_number={self.reg_number!r}, "
                f"coupon_period={self.coupon_period}, "
                f"coupon_percent={self.coupon_percent})")

    @property
    def instrument_info(self) -> InstrumentInfo:
        return InstrumentInfo(code=self.sec_id, name=self.short_name)


class MoexSecuritiesInfoDownloadParameters(typing.NamedTuple):
    """ Container for ``MoexStringDataDownloader.download_instruments_info_string`` parameters.
    """
    board: Board

    @classmethod
    def safe_create(
            cls: typing.Type['MoexSecuritiesInfoDownloadParameters'],
            *,
            board: Board) -> 'MoexSecuritiesInfoDownloadParameters':
        """ Create new instance of ``MoexSecuritiesInfoDownloadParameters`` with arguments check.

        :param board: Board.
        :return: ``MoexSecuritiesInfoDownloadParameters`` instance.
        """
        if not isinstance(board, Board):
            raise TypeError("'board' is not Board")

        return cls(board=board)


@dataclasses.dataclass
class MoexSecurityHistoryDownloadParameters(InstrumentHistoryDownloadParameters):
    """ Container for ``MoexStringDataDownloader.download_instrument_history_string`` parameters.
    """
    board: Annotated[Board, InstrumentInfoParameter()]
    sec_id: Annotated[str, InstrumentInfoParameter(instrument_identity=True)]
    start: Annotated[int, Volatile(generator=lambda ctx: 0, stub_value=0)]

    def clone_with_instrument_info_parameters(
            self,
            info_download_parameters: typing.Optional[MoexSecuritiesInfoDownloadParameters],
            instrument_info: typing.Optional[SecurityInfo]) -> 'MoexSecurityHistoryDownloadParameters':
        return MoexSecurityHistoryDownloadParameters.generate_from(self, info_download_parameters, instrument_info)

    @classmethod
    def generate_from(
            cls: typing.Type['MoexSecurityHistoryDownloadParameters'],
            history_download_parameters: typing.Optional['MoexSecurityHistoryDownloadParameters'],
            info_download_parameters: typing.Optional[MoexSecuritiesInfoDownloadParameters],
            instrument_info: typing.Optional[SecurityInfo]) -> 'MoexSecurityHistoryDownloadParameters':
        """ Create new history download parameters instance with data from its arguments.

        :param history_download_parameters: Optional instrument history download parameters for cloning.
        :param info_download_parameters: Optional instrument info download parameters for cloning.
        :param instrument_info: Optional instrument info for cloning.
        :return: Cloned history download parameters instance (self) with replacing some attributes from
            `info_download_parameters` and `instrument_info`.
        """
        return cls(
            board=((None if history_download_parameters is None else history_download_parameters.board)
                   if info_download_parameters is None
                   else info_download_parameters.board),
            sec_id=((None if history_download_parameters is None else history_download_parameters.sec_id)
                    if instrument_info is None
                    else instrument_info.sec_id),
            start=(0 if history_download_parameters is None else history_download_parameters.start)
        )

    @classmethod
    def safe_create(
            cls: typing.Type['MoexSecurityHistoryDownloadParameters'],
            *,
            board: Board,
            sec_id: str,
            start: int) -> 'MoexSecurityHistoryDownloadParameters':
        """ Create new instance of ``MoexSecurityHistoryDownloadParameters`` with arguments check.

        :param board: Board.
        :param sec_id: Security ID.
        :param start: Start value.
        :return: ``MoexSecurityHistoryDownloadParameters`` instance.
        """
        if not isinstance(board, Board):
            raise TypeError(f"{board!r} is not Board")

        return cls(
            board=board,
            sec_id=str(sec_id),
            start=int(start))


class MoexDownloadParametersFactory(DownloadParametersFactory):
    """ Download parameters factories and generators for Moscow Exchange.
    """

    @property
    def download_history_parameters_class(self) -> typing.Type[MoexSecurityHistoryDownloadParameters]:
        return MoexSecurityHistoryDownloadParameters

    @property
    def download_history_parameters_factory(self) -> typing.Callable[..., MoexSecurityHistoryDownloadParameters]:
        return MoexSecurityHistoryDownloadParameters.safe_create

    @property
    def download_info_parameters_class(self):
        return MoexSecuritiesInfoDownloadParameters

    @property
    def download_info_parameters_factory(self) -> typing.Callable[..., typing.Any]:
        return MoexSecuritiesInfoDownloadParameters.safe_create

    def generate_history_download_parameters_from(
            self,
            history_download_parameters: typing.Optional[MoexSecurityHistoryDownloadParameters],
            info_download_parameters: typing.Optional[MoexSecuritiesInfoDownloadParameters],
            instrument_info: typing.Optional[SecurityInfo]) -> MoexSecurityHistoryDownloadParameters:
        return MoexSecurityHistoryDownloadParameters.generate_from(
            history_download_parameters,
            info_download_parameters,
            instrument_info)
