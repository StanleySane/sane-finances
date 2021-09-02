#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import decimal
import re
import unittest

from sane_finances.sources.base import ParseError, InstrumentValuesHistoryEmpty
from sane_finances.sources.moex.v1_3.meta import (
    Market, TradeEngine, Board,
    SecurityValue, SecurityInfo, GlobalIndexData)
from sane_finances.sources.moex.v1_3.parsers import (
    MoexHistoryJsonParser, MoexSecurityInfoJsonParser, MoexGlobalIndexJsonParser)
from .fakes import FakeMoexDownloadParameterValuesStorage


class TestMoexHistoryJsonParser(unittest.TestCase):

    def setUp(self):
        self.parser = MoexHistoryJsonParser()

        self.expected_close_str = '12345.6789'
        self.expected_result = [SecurityValue(
            trade_date=datetime.date(2000, 12, 31),
            close=decimal.Decimal(self.expected_close_str))]

        self.expected_date_str = self.expected_result[0].trade_date.strftime(self.parser.trade_date_format)

    def test_parse_SuccessWithClose(self):
        valid_json = f"""
        {{
        "history": {{
            "columns": ["BOARDID", "TRADEDATE", "SECID", "CLOSE"],
            "data": [["TQBR", "{self.expected_date_str}", "ABRD", {self.expected_close_str}]]
        }}}}"""
        result = list(self.parser.parse(valid_json, tzinfo=None))

        self.assertSequenceEqual(result, self.expected_result)

    def test_parse_AcceptNulls(self):
        expected_result = []
        valid_json = f"""
        {{
        "history": {{
            "columns": ["BOARDID", "TRADEDATE", "SECID", "CLOSE"],
            "data": [["TQBR", "{self.expected_date_str}", "ABRD", null]]
        }}}}"""
        result = list(self.parser.parse(valid_json, tzinfo=None))

        self.assertSequenceEqual(result, expected_result)

    def test_parse_SuccessWithLegalClosePrice(self):
        valid_json = f"""
        {{
        "history": {{
            "columns": ["BOARDID", "TRADEDATE", "SECID", "LEGALCLOSEPRICE"],
            "data": [["TQBR", "{self.expected_date_str}", "ABRD", {self.expected_close_str}]]
        }}}}"""
        result = list(self.parser.parse(valid_json, tzinfo=None))

        self.assertSequenceEqual(result, self.expected_result)

    def test_parse_SuccessBonds(self):
        face_value = decimal.Decimal(1000)
        self.expected_result[0].close *= face_value / 100
        valid_json = f"""
        {{
        "history": {{
            "columns": ["BOARDID", "TRADEDATE", "SECID", "LEGALCLOSEPRICE", "FACEVALUE"],
            "data": [["TQBR", "{self.expected_date_str}", "ABRD", {self.expected_close_str}, {face_value}]]
        }}}}"""
        result = list(self.parser.parse(valid_json, tzinfo=None))

        self.assertSequenceEqual(result, self.expected_result)

    def test_parse_AcceptNullFaceValue(self):
        valid_json = f"""
        {{
        "history": {{
            "columns": ["BOARDID", "TRADEDATE", "SECID", "LEGALCLOSEPRICE", "FACEVALUE"],
            "data": [["TQBR", "{self.expected_date_str}", "ABRD", {self.expected_close_str}, null]]
        }}}}"""
        result = list(self.parser.parse(valid_json, tzinfo=None))

        self.assertSequenceEqual(result, self.expected_result)

    def test_parse_raisesWhenNoCloseColumns(self):
        invalid_json = f"""
        {{
        "history": {{
            "columns": ["BOARDID", "TRADEDATE", "SECID"],
            "data": [["TQBR", "{self.expected_date_str}", "ABRD"]]
        }}}}"""

        with self.assertRaises(ParseError):
            _ = list(self.parser.parse(invalid_json, tzinfo=None))

    def test_parse_raisesWhenWrongDate(self):
        # wrong format
        invalid_json = f"""
        {{
        "history": {{
            "columns": ["BOARDID", "TRADEDATE", "SECID"],
            "data": [["TQBR", "9999-9999-9999", "ABRD"]]
        }}}}"""

        with self.assertRaises(ParseError):
            _ = list(self.parser.parse(invalid_json, tzinfo=None))

        # wrong type
        invalid_json = f"""
        {{
        "history": {{
            "columns": ["BOARDID", "TRADEDATE", "SECID"],
            "data": [["TQBR", 42, "ABRD"]]
        }}}}"""

        with self.assertRaises(ParseError):
            _ = list(self.parser.parse(invalid_json, tzinfo=None))

    def test_parse_raisesWhenWrongCloseValue(self):
        # wrong format
        invalid_json = f"""
        {{
        "history": {{
            "columns": ["BOARDID", "TRADEDATE", "SECID", "CLOSE"],
            "data": [["TQBR", "{self.expected_date_str}", "ABRD", "123.123.123"]]
        }}}}"""

        with self.assertRaises(ParseError):
            _ = list(self.parser.parse(invalid_json, tzinfo=None))

    def test_parse_raisesWhenNoRequiredColumn(self):
        invalid_json = f"""
        {{
        "history": {{
            "columns": ["BOARDID", "TRADEDATE__", "SECID", "CLOSE"],
            "data": [["TQBR", "{self.expected_date_str}", "ABRD", {self.expected_close_str}]]
        }}}}"""

        with self.assertRaises(ParseError):
            _ = list(self.parser.parse(invalid_json, tzinfo=None))

    def test_parse_raisesWhenNoColumnInData(self):
        invalid_json = f"""
        {{
        "history": {{
            "columns": ["BOARDID", "TRADEDATE", "SECID", "CLOSE"],
            "data": [["TQBR", "{self.expected_date_str}", "ABRD"]]
        }}}}"""

        with self.assertRaises(ParseError):
            _ = list(self.parser.parse(invalid_json, tzinfo=None))

    def test_parse_raisesWhenNoColumnsBlock(self):
        invalid_json = f"""
        {{
        "history": {{
            "columns__": ["BOARDID", "TRADEDATE", "SECID", "CLOSE"],
            "data": [["TQBR", "{self.expected_date_str}", "ABRD", {self.expected_close_str}]]
        }}}}"""

        with self.assertRaises(ParseError):
            _ = list(self.parser.parse(invalid_json, tzinfo=None))

    def test_parse_raisesWhenWrongColumnsType(self):
        invalid_json = f"""
        {{
        "history": {{
            "columns": 42,
            "data": [["TQBR", "{self.expected_date_str}", "ABRD", {self.expected_close_str}]]
        }}}}"""

        with self.assertRaises(ParseError):
            _ = list(self.parser.parse(invalid_json, tzinfo=None))

    def test_parse_raisesWhenNoDataBlock(self):
        invalid_json = f"""
        {{
        "history": {{
            "columns": ["BOARDID", "TRADEDATE", "SECID", "CLOSE"],
            "data__": [["TQBR", "{self.expected_date_str}", "ABRD", {self.expected_close_str}]]
        }}}}"""

        with self.assertRaises(ParseError):
            _ = list(self.parser.parse(invalid_json, tzinfo=None))

    def test_parse_raisesWhenWrongDataType(self):
        invalid_json = f"""
        {{
        "history": {{
            "columns": ["BOARDID", "TRADEDATE", "SECID", "CLOSE"],
            "data": 42
        }}}}"""

        with self.assertRaises(ParseError):
            _ = list(self.parser.parse(invalid_json, tzinfo=None))

    def test_parse_raisesWhenEmptyHistory(self):
        invalid_json = f"""
        {{
        "history": {{
            "columns": ["BOARDID", "TRADEDATE", "SECID", "CLOSE"],
            "data": []
        }}}}"""

        with self.assertRaises(InstrumentValuesHistoryEmpty):
            _ = list(self.parser.parse(invalid_json, tzinfo=None))

    def test_parse_raisesWhenEmptyString(self):
        invalid_json = ''

        with self.assertRaises(ParseError):
            _ = list(self.parser.parse(invalid_json, tzinfo=None))

    def test_parse_raisesWhenWrongJson(self):
        invalid_json = """[]"""

        with self.assertRaises(ParseError):
            _ = list(self.parser.parse(invalid_json, tzinfo=None))

    def test_parse_raisesWhenUnknownJson(self):
        invalid_json = """{}"""

        with self.assertRaises(ParseError):
            _ = list(self.parser.parse(invalid_json, tzinfo=None))


class TestMoexSecurityInfoJsonParser(unittest.TestCase):

    def setUp(self):
        engine = TradeEngine(identity=42, name='NAME', title='TITLE')
        market = Market(identity=42, trade_engine=engine, name='NAME', title='TITLE', marketplace='MARKETPLACE')
        self.board = Board(
            identity=42,
            trade_engine=engine,
            market=market,
            boardid='BOARDID',
            title='TITLE',
            is_traded=True,
            has_candles=True,
            is_primary=True)
        global_index_data = GlobalIndexData(
            trade_engines=(engine,),
            markets=(market,),
            boards=(self.board,),
        )
        self.parser = MoexSecurityInfoJsonParser(FakeMoexDownloadParameterValuesStorage(global_index_data))

    def test_parse_SuccessAllColumns(self):
        sec_info = SecurityInfo(
            sec_id='ID',
            board=self.board,
            short_name='SHORT NAME',
            lot_size=42,
            sec_name='SEC NAME',
            isin='ISIN',
            lat_name='LAT NAME',
            reg_number='REGNUMBER')
        expected_result = [sec_info]

        json = f"""{{
            "securities": {{
                "columns": ["SECID", "BOARDID", "SHORTNAME", "LOTSIZE", "SECNAME", "NAME", "ISIN", "LATNAME",
                            "REGNUMBER"],
                "data": [["{sec_info.sec_id}", "{sec_info.board.boardid}", "{sec_info.short_name}", 
                           {sec_info.lot_size}, "{sec_info.sec_name}", "{sec_info.sec_name}", "{sec_info.isin}",
                           "{sec_info.lat_name}", "{sec_info.reg_number}"]]
            }}}}"""

        result = list(self.parser.parse(json))

        self.assertSequenceEqual(result, expected_result)

    def test_parse_SuccessOnlyRequiredColumns(self):
        sec_info = SecurityInfo(
            sec_id='ID',
            board=self.board,
            short_name='SHORT NAME')
        expected_result = [sec_info]

        json = f"""{{
            "securities": {{
                "columns": ["SECID", "BOARDID", "SHORTNAME"],
                "data": [["{sec_info.sec_id}", "{sec_info.board.boardid}", "{sec_info.short_name}"]]
            }}}}"""

        result = list(self.parser.parse(json))

        self.assertSequenceEqual(result, expected_result)

    def test_parse_SuccessEmptyList(self):
        expected_result = []

        json = """{
            "securities": {
                "columns": ["SECID", "BOARDID", "SHORTNAME"],
                "data": []
            }}"""

        result = list(self.parser.parse(json))

        self.assertSequenceEqual(result, expected_result)

    def test_parse_raisesWrongBoard(self):
        sec_info = SecurityInfo(
            sec_id='ID',
            board=self.board,
            short_name='SHORT NAME')
        wrong_json = f"""{{
            "securities": {{
                "columns": ["SECID", "BOARDID", "SHORTNAME"],
                "data": [["{sec_info.sec_id}", "WRONG", "{sec_info.short_name}"]]
            }}}}"""

        with self.assertRaises(ParseError):
            list(self.parser.parse(wrong_json))

    def test_parse_raisesEmptyString(self):
        wrong_json = ''

        with self.assertRaises(ParseError):
            list(self.parser.parse(wrong_json))

    def test_parse_raisesWrongJson(self):
        wrong_json = '[]'

        with self.assertRaises(ParseError):
            list(self.parser.parse(wrong_json))


class TestMoexGlobalIndexJsonParser(unittest.TestCase):

    def setUp(self):
        self.engine = TradeEngine(
            identity=1,
            name='stock',
            title='Фондовый рынок и рынок депозитов')
        self.market = Market(
            identity=1,
            trade_engine=self.engine,
            name='shares',
            title='Рынок акций',
            marketplace='MXSE')
        self.board = Board(
            identity=178,
            trade_engine=self.engine,
            market=self.market,
            boardid='TQTF',
            title='Т+: ETF - безадрес.',
            is_traded=True,
            has_candles=True,
            is_primary=True)
        self.expected_result = GlobalIndexData(
            trade_engines=(self.engine,),
            markets=(self.market,),
            boards=(self.board,))

        self.parser = MoexGlobalIndexJsonParser()

    def generate_valid_json(self):
        valid_json = f"""
        {{
        "engines": {{
            "metadata": {{
                "id": {{"type": "int32"}},
                "name": {{"type": "string", "bytes": 45, "max_size": 0}},
                "title": {{"type": "string", "bytes": 765, "max_size": 0}}
            }},
            "columns": ["id", "name", "title"], 
            "data": [[{self.engine.identity}, "{self.engine.name}", "{self.engine.title}"]]
        }},
        "markets": {{
            "metadata": {{
                "id": {{"type": "int32"}},
                "trade_engine_id": {{"type": "int32"}},
                "trade_engine_name": {{"type": "string", "bytes": 45, "max_size": 0}},
                "trade_engine_title": {{"type": "string", "bytes": 765, "max_size": 0}},
                "market_name": {{"type": "string", "bytes": 45, "max_size": 0}},
                "market_title": {{"type": "string", "bytes": 765, "max_size": 0}},
                "market_id": {{"type": "int32"}},
                "marketplace": {{"type": "string", "bytes": 48, "max_size": 0}}
            }},
            "columns": ["id", "trade_engine_id", "trade_engine_name", "trade_engine_title", "market_name", 
                        "market_title", "market_id", "marketplace"], 
            "data": [[{self.market.identity}, {self.engine.identity}, "{self.engine.name}", "{self.engine.title}",
                      "{self.market.name}", "{self.market.title}", {self.market.identity}, "{self.market.marketplace}"]]
        }},
        "boards": {{
            "metadata": {{
                "id": {{"type": "int32"}},
                "board_group_id": {{"type": "int32"}},
                "engine_id": {{"type": "int32"}},
                "market_id": {{"type": "int32"}},
                "boardid": {{"type": "string", "bytes": 12, "max_size": 0}},
                "board_title": {{"type": "string", "bytes": 381, "max_size": 0}},
                "is_traded": {{"type": "int32"}},
                "has_candles": {{"type": "int32"}},
                "is_primary": {{"type": "int32"}}
            }},
            "columns": ["id", "board_group_id", "engine_id", "market_id", "boardid", "board_title", "is_traded",
                        "has_candles", "is_primary"], 
            "data": [[{self.board.identity}, 57, {self.engine.identity}, {self.market.identity},
                      "{self.board.boardid}", "{self.board.title}",
                      {1 if self.board.is_traded else 0}, {1 if self.board.has_candles else 0}, 
                      {1 if self.board.is_primary else 0}]]
        }}
        }}"""

        return valid_json

    def spoil_block_data(self, block_name: str, new_data_content: str):
        spoil_pattern = re.compile(
            fr'"{block_name}"\s*:\s*{{(.*?)"data"\s*:\s*.*?}}',
            re.IGNORECASE | re.MULTILINE | re.DOTALL)
        return spoil_pattern.sub(fr'"{block_name}":{{\1"data":{new_data_content}}}', self.generate_valid_json())

    def test_parse_Success(self):
        result = self.parser.parse(self.generate_valid_json())

        self.assertEqual(result, self.expected_result)

    def test_parse_raisesEmptyString(self):
        wrong_json = ''

        with self.assertRaises(ParseError):
            _ = list(self.parser.parse(wrong_json))

    def test_parse_raisesWrongJson(self):
        wrong_json = '[]'

        with self.assertRaises(ParseError):
            _ = list(self.parser.parse(wrong_json))

    def test_parse_raisesWhenWrongEnginesContent(self):
        # no block
        wrong_json = self.generate_valid_json().replace(f'"engines"', f'"engines__"')

        with self.assertRaises(ParseError):
            _ = list(self.parser.parse(wrong_json))

        # bad data content type
        wrong_json = self.spoil_block_data('engines', '{}')

        with self.assertRaises(ParseError):
            _ = list(self.parser.parse(wrong_json))

    def test_parse_raisesWhenWrongMarketsContent(self):
        # no block
        wrong_json = self.generate_valid_json().replace(f'"markets"', f'"markets__"')

        with self.assertRaises(ParseError):
            _ = list(self.parser.parse(wrong_json))

        # bad data content type
        wrong_json = self.spoil_block_data('markets', '{}')

        with self.assertRaises(ParseError):
            _ = list(self.parser.parse(wrong_json))

        # bad engine id
        wrong_json = self.spoil_block_data(
            'markets',
            f"""[[{self.market.identity}, -1, "{self.engine.name}", "{self.engine.title}",
                  "{self.market.name}", "{self.market.title}", {self.market.identity}, "{self.market.marketplace}"]]""")

        with self.assertRaises(ParseError):
            _ = list(self.parser.parse(wrong_json))

    def test_parse_raisesWhenWrongBoardsContent(self):
        # no block
        wrong_json = self.generate_valid_json().replace(f'"boards"', f'"boards__"')

        with self.assertRaises(ParseError):
            _ = list(self.parser.parse(wrong_json))

        # bad data content type
        wrong_json = self.spoil_block_data('boards', '{}')

        with self.assertRaises(ParseError):
            _ = list(self.parser.parse(wrong_json))

        # bad engine id
        wrong_json = self.spoil_block_data(
            'boards',
            f"""[[{self.board.identity}, 57, -1, {self.market.identity},
                  "{self.board.boardid}", "{self.board.title}",
                  {1 if self.board.is_traded else 0}, {1 if self.board.has_candles else 0}, 
                  {1 if self.board.is_primary else 0}]]""")

        with self.assertRaises(ParseError):
            _ = list(self.parser.parse(wrong_json))

        # bad market id
        wrong_json = self.spoil_block_data(
            'boards',
            f"""[[{self.board.identity}, 57, {self.engine.identity}, -1,
                  "{self.board.boardid}", "{self.board.title}",
                  {1 if self.board.is_traded else 0}, {1 if self.board.has_candles else 0}, 
                  {1 if self.board.is_primary else 0}]]""")

        with self.assertRaises(ParseError):
            _ = list(self.parser.parse(wrong_json))
