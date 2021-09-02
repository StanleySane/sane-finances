#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Utilities for parse data from moex.com.
"""
import decimal
import json
import logging
import typing
import datetime

from .meta import SecurityValue, SecurityInfo, GlobalIndexData, TradeEngine, Market, Board
from ...base import (
    InstrumentValuesHistoryParser, InstrumentInfoParser, InstrumentValuesHistoryEmpty, DownloadParameterValuesStorage,
    ParseError)

logging.getLogger().addHandler(logging.NullHandler())


def _parse_block(
        block_name: str,
        raw_data: typing.Dict,
        attrs_mapping: typing.Iterable[typing.Tuple[str, str, bool, typing.Any]],
        raise_when_data_block_is_empty=False) -> typing.Iterable[typing.Dict]:

    block = raw_data.get(block_name, None)
    if block is None:
        raise ParseError(f"Wrong JSON format. '{block_name}' block not found.")

    columns_block = block.get('columns', None)
    if columns_block is None:
        raise ParseError(f"Wrong JSON format. '{block_name}.columns' block not found.")
    if not isinstance(columns_block, list):
        raise ParseError(f"Wrong JSON format. '{block_name}.columns' block is not list.")

    data_block = block.get('data', None)
    if data_block is None:
        raise ParseError(f"Wrong JSON format. '{block_name}.data' block not found.")
    if not isinstance(data_block, list):
        raise ParseError(f"Wrong JSON format. '{block_name}.data' block is not list.")

    if not data_block and raise_when_data_block_is_empty:
        raise InstrumentValuesHistoryEmpty()

    data_mapping = []
    for attr_name, column_name, is_required, converter in attrs_mapping:
        try:
            column_index = columns_block.index(column_name)
        except ValueError as ex:
            if is_required:
                raise ParseError(f"Wrong JSON format. "
                                 f"Column {column_name!r} not found in '{block_name}.columns' block.") from ex
        else:
            data_mapping.append((attr_name, converter, column_index))

    for data_item in data_block:
        factory_kwargs = {}
        for attr_name, converter, column_index in data_mapping:
            try:
                attr_value = data_item[column_index]
            except IndexError as ex:
                raise ParseError(f"Wrong JSON format. "
                                 f"Column with index {column_index!r} not found in '{block_name}.data' block: "
                                 f"{data_item}") from ex

            if converter is not None:
                attr_value = converter(attr_value)

            factory_kwargs[attr_name] = attr_value

        yield factory_kwargs


class MoexHistoryJsonParser(InstrumentValuesHistoryParser):
    """ Parser for history data of JSON string.

    Accept JSON like::

            {
            "history": {
                "columns": ["BOARDID", "TRADEDATE", "SECID", "CLOSE", "LEGALCLOSEPRICE", "FACEVALUE"],
                "data": [
                    ["TQBR", "2014-06-25", "ABRD", 134.12, 134.12, 1000],
                    ...
                ]
            }}
    """

    trade_date_format = '%Y-%m-%d'

    def __init__(self):
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

        self._attrs_mapping = (
            ('trade_date', 'TRADEDATE', True, self._convert_trade_date_to_date),
            ('legal_close_price', 'LEGALCLOSEPRICE', False, self._convert_price_to_decimal),
            ('close', 'CLOSE', False, self._convert_price_to_decimal),
            ('face_value', 'FACEVALUE', False, self._convert_price_to_decimal)
        )

    def parse(  # pylint: disable=arguments-renamed
            self,
            raw_json_text: str,
            tzinfo: typing.Optional[datetime.timezone]
    ) -> typing.Iterable[SecurityValue]:

        try:
            raw_data = json.loads(raw_json_text)
        except json.decoder.JSONDecodeError as ex:
            raise ParseError(ex.msg) from ex

        if not isinstance(raw_data, dict):
            # can be Inf etc., but we accept only {}
            raise ParseError("Wrong JSON format. Top level is not dictionary.")

        for factory_kwargs in _parse_block(
                'history',
                raw_data,
                self._attrs_mapping,
                raise_when_data_block_is_empty=True):

            if 'legal_close_price' not in factory_kwargs and 'close' not in factory_kwargs:
                raise ParseError("Wrong JSON format. Neither 'LEGALCLOSEPRICE' nor 'CLOSE' column was found.")

            close = factory_kwargs.get('close', None)
            legal_close_price = factory_kwargs.get('legal_close_price', None)

            if legal_close_price is not None or close is not None:
                close = legal_close_price if legal_close_price is not None else close

                if 'face_value' in factory_kwargs:
                    face_value: decimal.Decimal = factory_kwargs['face_value']
                    if face_value is not None:
                        close *= face_value/100

                    del factory_kwargs['face_value']

                if 'legal_close_price' in factory_kwargs:
                    del factory_kwargs['legal_close_price']

                factory_kwargs['close'] = close
                yield SecurityValue(**factory_kwargs)

    def _convert_trade_date_to_date(self, trade_date: str):
        try:
            trade_date = datetime.datetime.strptime(trade_date, self.trade_date_format)
        except (ValueError, TypeError) as ex:
            raise ParseError(f"Wrong JSON format. "
                             f"Can't convert {trade_date!r} to date.") from ex

        trade_date = trade_date.date()
        return trade_date

    @staticmethod
    def _convert_price_to_decimal(price):
        if price is None:
            return None

        if isinstance(price, float):
            # hack to adjust floating point digits
            price = repr(price)

        try:
            decimal_price = decimal.Decimal(price)
        except (ValueError, TypeError, decimal.DecimalException) as ex:
            raise ParseError(f"Wrong JSON format. "
                             f"Can't convert {price!r} to decimal.") from ex

        return decimal_price


class MoexSecurityInfoJsonParser(InstrumentInfoParser):
    """ Parser for security info list from JSON.

    Accept JSON like::

            {
                "securities": {
                    ...
                    "columns": ["SECID", "BOARDID", "SHORTNAME", ...],
                    "data": [
                                ["AKMD", "TQTD", "ETF AKMD", ...],
                                ...
                            ]
                    ...
                },
                ...
            }
    """

    def __init__(self, parameter_values_storage: DownloadParameterValuesStorage):
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

        self.parameter_values_storage = parameter_values_storage

        self._attrs_mapping = (
            ('sec_id', 'SECID', True, None),
            ('board', 'BOARDID', True, self._get_board),
            ('short_name', 'SHORTNAME', True, None),
            ('lot_size', 'LOTSIZE', False, None),
            ('sec_name', 'SECNAME', False, None),
            ('sec_name', 'NAME', False, None),
            ('isin', 'ISIN', False, None),
            ('lat_name', 'LATNAME', False, None),
            ('reg_number', 'REGNUMBER', False, None)
        )
        self._boards = {}

    def parse(self, raw_json_text: str) -> typing.Iterable[SecurityInfo]:  # pylint: disable=arguments-renamed
        self._boards = {
            board.boardid: board
            for board
            in self.parameter_values_storage.get_all_parameter_values_for(Board)}

        try:
            raw_data = json.loads(raw_json_text)
        except json.decoder.JSONDecodeError as ex:
            raise ParseError(ex.msg) from ex

        if not isinstance(raw_data, dict):
            # can be Inf etc., but we accept only {}
            raise ParseError("Wrong JSON format. Top level is not dictionary.")

        return (SecurityInfo(**factory_kwargs)
                for factory_kwargs
                in _parse_block('securities', raw_data, self._attrs_mapping))

    def _get_board(self, boardid: str):
        if boardid not in self._boards:
            raise ParseError(f"Board {boardid} not found.")

        return self._boards[boardid]


class MoexGlobalIndexJsonParser:
    """ Parser for global index data from JSON.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

        self._engines_attrs_mapping = (
            ('identity', 'id', True, None),
            ('name', 'name', True, None),
            ('title', 'title', True, None)
        )
        self._markets_attrs_mapping = (
            ('identity', 'id', True, None),
            ('trade_engine', 'trade_engine_id', True, self._get_engine_by_id),
            ('name', 'market_name', True, None),
            ('title', 'market_title', True, None),
            ('marketplace', 'marketplace', True, None)
        )
        self._board_groups_attrs_mapping = (
            ('identity', 'id', True, None),
            ('trade_engine', 'trade_engine_id', True, self._get_engine_by_id),
            ('market', 'market_id', True, self._get_market_by_id),
            ('name', 'name', True, None),
            ('title', 'title', True, None),
            ('is_default', 'is_default', True, bool),
            ('is_traded', 'is_traded', True, bool)
        )
        self._boards_attrs_mapping = (
            ('identity', 'id', True, None),
            ('trade_engine', 'engine_id', True, self._get_engine_by_id),
            ('market', 'market_id', True, self._get_market_by_id),
            ('boardid', 'boardid', True, None),
            ('title', 'board_title', True, None),
            ('is_traded', 'is_traded', True, bool),
            ('has_candles', 'has_candles', True, bool),
            ('is_primary', 'is_primary', True, bool)
        )
        self._engines = {}
        self._markets = {}

    def parse(self, raw_json_text: str) -> GlobalIndexData:
        """ Parse global index data from JSON and return it.

        :param raw_json_text: JSON string with global index data.
        :return: ``GlobalIndexData`` instance.
        """
        try:
            raw_data = json.loads(raw_json_text)
        except json.decoder.JSONDecodeError as ex:
            raise ParseError(ex.msg) from ex

        if not isinstance(raw_data, dict):
            # can be Inf etc., but we accept only {}
            raise ParseError("Wrong JSON format. Top level is not dictionary.")

        engines = tuple(TradeEngine(**factory_kwargs)
                        for factory_kwargs
                        in _parse_block('engines', raw_data, self._engines_attrs_mapping))
        self._engines = {trade_engine.identity: trade_engine for trade_engine in engines}

        markets = tuple(Market(**factory_kwargs)
                        for factory_kwargs
                        in _parse_block('markets', raw_data, self._markets_attrs_mapping))
        self._markets = {market.identity: market for market in markets}

        boards = tuple(Board(**factory_kwargs)
                       for factory_kwargs
                       in _parse_block('boards', raw_data, self._boards_attrs_mapping))

        return GlobalIndexData(trade_engines=engines, markets=markets, boards=boards)

    def _get_engine_by_id(self, trade_engine_id: int):
        if trade_engine_id not in self._engines:
            raise ParseError(f"Trade engine with id = {trade_engine_id} not found.")

        return self._engines[trade_engine_id]

    def _get_market_by_id(self, market_id: int):
        if market_id not in self._markets:
            raise ParseError(f"Market with id = {market_id} not found.")

        return self._markets[market_id]
