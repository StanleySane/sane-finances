#!/usr/bin/env python
# -*- coding: utf-8 -*-
import datetime
import decimal
import unittest

from sane_finances.sources.base import ParseError
from sane_finances.sources.yahoo.v8.meta import InstrumentQuoteInfo, InstrumentQuoteValue
from sane_finances.sources.yahoo.v8.parsers import YahooQuotesJsonParser, YahooInstrumentInfoParser


class TestYahooQuotesJsonParser(unittest.TestCase):

    def setUp(self) -> None:
        self.parser = YahooQuotesJsonParser()

    def check_parse_raise(self, invalid_json: str, message: str):
        with self.assertRaisesRegex(ParseError, message):
            _ = list(self.parser.parse(invalid_json, tzinfo=None))

    def test_parse_Success(self):
        expected_symbol = '^GSPC'
        expected_timestamp1 = datetime.datetime(1970, 1, 1)
        expected_timestamp2 = datetime.datetime(1988, 1, 4, hour=14, minute=30)
        expected_close_value = decimal.Decimal('42.42')
        expected_result = [
            InstrumentQuoteValue(
                symbol=expected_symbol,
                timestamp=expected_timestamp1,
                close=expected_close_value),
            InstrumentQuoteValue(
                symbol=expected_symbol,
                timestamp=expected_timestamp2,
                close=expected_close_value)
        ]

        valid_json = '''{"chart": {"result": [
        {
            "meta": {"symbol": "^GSPC"},
            "timestamp": [0, 568305000],
            "indicators": {"quote": [{"close": [42.42, 42.42]}]}
        }],
        "error": null
        }}'''

        self.assertSequenceEqual(expected_result, list(self.parser.parse(valid_json, tzinfo=None)))

    def test_parse_raisesWhenNoData(self):
        invalid_json = ''

        self.check_parse_raise(invalid_json, '')

    def test_parse_raisesWhenNotDict(self):
        invalid_json = '[42]'

        self.check_parse_raise(invalid_json, 'not dict')

    def test_parse_raisesWhenSourceReturnError(self):
        invalid_json = '''{"chart": {"result": null,
        "error": {
            "code": "ERROR CODE",
            "description": "ERROR DESCRIPTION"
        }}}'''

        self.check_parse_raise(invalid_json, 'Source returned error.*ERROR CODE.*ERROR DESCRIPTION')

    def test_parse_raisesWhenNoChartField(self):
        invalid_json = '''{"__chart": {"result": [
        {
            "meta": {"symbol": "^GSPC"},
            "timestamp": [0],
            "indicators": {"quote": [{"close": [42.42]}]}
        }],
        "error": null}}'''

        self.check_parse_raise(invalid_json, 'chart')

    def test_parse_raisesWhenNoResultField(self):
        invalid_json = '''{"chart": {"__result": [
        {
            "meta": {"symbol": "^GSPC"},
            "timestamp": [0],
            "indicators": {"quote": [{"close": [42.42]}]}
        }],
        "error": null}}'''

        self.check_parse_raise(invalid_json, 'result')

    def test_parse_raisesWhenResultIsNotList(self):
        invalid_json = '''{"chart": {"result": {},
        "error": null}}'''

        self.check_parse_raise(invalid_json, 'result')

    def test_parse_raisesWhenResultIsEmpty(self):
        invalid_json = '''{"chart": {"result": [],
        "error": null}}'''

        self.check_parse_raise(invalid_json, 'result')

    def test_parse_raisesWhenResultItemIsNotDict(self):
        invalid_json = '''{"chart": {"result": [42],
        "error": null}}'''

        self.check_parse_raise(invalid_json, 'result')

    def test_parse_raisesWhenNoMetaField(self):
        invalid_json = '''{"chart": {"result": [
        {
            "__meta": {"symbol": "^GSPC"},
            "timestamp": [0],
            "indicators": {"quote": [{"close": [42.42]}]}
        }],
        "error": null}}'''

        self.check_parse_raise(invalid_json, 'meta')

    def test_parse_raisesWhenMetaIsNotDict(self):
        invalid_json = '''{"chart": {"result": [
        {
            "meta": [],
            "timestamp": [0],
            "indicators": {"quote": [{"close": [42.42]}]}
        }],
        "error": null}}'''

        self.check_parse_raise(invalid_json, 'meta')

    def test_parse_raisesWhenNoSymbolField(self):
        invalid_json = '''{"chart": {"result": [
        {
            "meta": {"__symbol": "^GSPC"},
            "timestamp": [0],
            "indicators": {"quote": [{"close": [42.42]}]}
        }],
        "error": null}}'''

        self.check_parse_raise(invalid_json, 'symbol')

    def test_parse_raisesWhenNoTimestampField(self):
        invalid_json = '''{"chart": {"result": [
        {
            "meta": {"symbol": "^GSPC"},
            "__timestamp": [0],
            "indicators": {"quote": [{"close": [42.42]}]}
        }],
        "error": null}}'''

        self.check_parse_raise(invalid_json, 'timestamp')

    def test_parse_raisesWhenTimestampIsNotList(self):
        invalid_json = '''{"chart": {"result": [
        {
            "meta": {"symbol": "^GSPC"},
            "timestamp": {},
            "indicators": {"quote": [{"close": [42.42]}]}
        }],
        "error": null}}'''

        self.check_parse_raise(invalid_json, 'timestamp')

    def test_parse_raisesWhenNoIndicatorsField(self):
        invalid_json = '''{"chart": {"result": [
        {
            "meta": {"symbol": "^GSPC"},
            "timestamp": [0],
            "__indicators": {"quote": [{"close": [42.42]}]}
        }],
        "error": null}}'''

        self.check_parse_raise(invalid_json, 'indicators')

    def test_parse_raisesWhenIndicatorsIsNotDict(self):
        invalid_json = '''{"chart": {"result": [
        {
            "meta": {"symbol": "^GSPC"},
            "timestamp": [0],
            "indicators": []
        }],
        "error": null}}'''

        self.check_parse_raise(invalid_json, 'indicators')

    def test_parse_raisesWhenNoQuoteField(self):
        invalid_json = '''{"chart": {"result": [
        {
            "meta": {"symbol": "^GSPC"},
            "timestamp": [0],
            "indicators": {"__quote": [{"close": [42.42]}]}
        }],
        "error": null}}'''

        self.check_parse_raise(invalid_json, 'quote')

    def test_parse_raisesWhenQuoteIsNotList(self):
        invalid_json = '''{"chart": {"result": [
        {
            "meta": {"symbol": "^GSPC"},
            "timestamp": [0],
            "indicators": {"quote": 42}
        }],
        "error": null}}'''

        self.check_parse_raise(invalid_json, 'quote')

    def test_parse_raisesWhenQuoteIsEmpty(self):
        invalid_json = '''{"chart": {"result": [
        {
            "meta": {"symbol": "^GSPC"},
            "timestamp": [0],
            "indicators": {"quote": []}
        }],
        "error": null}}'''

        self.check_parse_raise(invalid_json, 'quote')

    def test_parse_raisesWhenQuoteItemsIsNotDict(self):
        invalid_json = '''{"chart": {"result": [
        {
            "meta": {"symbol": "^GSPC"},
            "timestamp": [0],
            "indicators": {"quote": [42]}
        }],
        "error": null}}'''

        self.check_parse_raise(invalid_json, 'quote')

    def test_parse_raisesWhenNoCloseField(self):
        invalid_json = '''{"chart": {"result": [
        {
            "meta": {"symbol": "^GSPC"},
            "timestamp": [0],
            "indicators": {"quote": [{"__close": [42.42]}]}
        }],
        "error": null}}'''

        self.check_parse_raise(invalid_json, 'close')

    def test_parse_raisesWhenCloseIsNotList(self):
        invalid_json = '''{"chart": {"result": [
        {
            "meta": {"symbol": "^GSPC"},
            "timestamp": [0],
            "indicators": {"quote": [{"close": 42}]}
        }],
        "error": null}}'''

        self.check_parse_raise(invalid_json, 'close')

    def test_parse_raisesWhenTimestampLengthNotEqualToClosesLength(self):
        invalid_json = '''{"chart": {"result": [
        {
            "meta": {"symbol": "^GSPC"},
            "timestamp": [1, 2],
            "indicators": {"quote": [{"close": [42.42]}]}
        }],
        "error": null}}'''

        self.check_parse_raise(invalid_json, 'not equals to length')


class TestYahooInstrumentInfoParser(unittest.TestCase):

    def setUp(self) -> None:
        self.parser = YahooInstrumentInfoParser()

    def check_parse_raise(self, invalid_json: str, message: str):
        with self.assertRaisesRegex(ParseError, message):
            _ = list(self.parser.parse(invalid_json))

    def test_parse_success(self):
        expected_result = [InstrumentQuoteInfo(
            symbol='QQQ',
            exchange='NGM',
            short_name='Invesco QQQ Trust, Series 1',
            long_name='Invesco QQQ Trust',
            type_disp='ETF',
            exchange_disp='NASDAQ',
            is_yahoo_finance=True
        )]

        valid_json = '''{"quotes": [
        {
            "exchange": "NGM",
            "shortname": "Invesco QQQ Trust, Series 1",
            "quoteType": "ETF",
            "symbol": "QQQ",
            "index": "quotes",
            "typeDisp": "ETF",
            "longname": "Invesco QQQ Trust",
            "exchDisp": "NASDAQ",
            "isYahooFinance": true
        }]}'''

        result = list(self.parser.parse(valid_json))

        self.assertSequenceEqual(result, expected_result)

    def test_parse_success_MinimumFields(self):
        expected_result = [InstrumentQuoteInfo(
            symbol='QQQ',
            exchange='NGM',
            short_name='Invesco QQQ Trust, Series 1',
            long_name=None,
            type_disp=None,
            exchange_disp=None,
            is_yahoo_finance=False
        )]

        valid_json = '''{"quotes": [
        {
            "exchange": "NGM",
            "shortname": "Invesco QQQ Trust, Series 1",
            "symbol": "QQQ"
        }]}'''

        result = list(self.parser.parse(valid_json))

        self.assertSequenceEqual(result, expected_result)

    def test_parse_raisesWhenNoData(self):
        invalid_json = ''

        self.check_parse_raise(invalid_json, '')

    def test_parse_raisesWhenNotDict(self):
        invalid_json = '[42]'

        self.check_parse_raise(invalid_json, 'not dict')

    def test_parse_raisesWhenSourceReturnError(self):
        invalid_json = '''{"finance": {"result": null,
        "error": {
            "code": "ERROR CODE",
            "description": "ERROR DESCRIPTION"
        }}}'''

        self.check_parse_raise(invalid_json, 'Source returned error.*ERROR CODE.*ERROR DESCRIPTION')

    def test_parse_raisesWhenSourceHasNoErrorField(self):
        # field "finance" usually contains "error" node
        # if it`s not, then it must have "quotes" field
        invalid_json = '''{"finance": {"result": null,
        "__error": {
            "code": "ERROR CODE",
            "description": "ERROR DESCRIPTION"
        }}}'''

        self.check_parse_raise(invalid_json, 'quotes')

    def test_parse_raisesWhenNoQuotesField(self):
        invalid_json = '''{"__quotes": [
        {
            "exchange": "NGM",
            "shortname": "Invesco QQQ Trust, Series 1",
            "quoteType": "ETF",
            "symbol": "QQQ",
            "index": "quotes",
            "typeDisp": "ETF",
            "longname": "Invesco QQQ Trust",
            "exchDisp": "NASDAQ",
            "isYahooFinance": true
        }]}'''

        self.check_parse_raise(invalid_json, 'quotes')

    def test_parse_raisesWhenQuotesIsNotList(self):
        invalid_json = '''{"quotes": {}}'''

        self.check_parse_raise(invalid_json, 'quotes')

    def test_parse_raisesWhenQuotesItemIsNotDict(self):
        invalid_json = '''{"quotes": [42]}'''

        self.check_parse_raise(invalid_json, 'quotes')

    def test_parse_raisesWhenNoSymbolField(self):
        invalid_json = '''{"quotes": [
        {
            "exchange": "NGM",
            "shortname": "Invesco QQQ Trust, Series 1",
            "quoteType": "ETF",
            "__symbol": "QQQ",
            "index": "quotes",
            "typeDisp": "ETF",
            "longname": "Invesco QQQ Trust",
            "exchDisp": "NASDAQ",
            "isYahooFinance": true
        }]}'''

        self.check_parse_raise(invalid_json, 'symbol')

    def test_parse_raisesWhenNoExchangeField(self):
        invalid_json = '''{"quotes": [
        {
            "__exchange": "NGM",
            "shortname": "Invesco QQQ Trust, Series 1",
            "quoteType": "ETF",
            "symbol": "QQQ",
            "index": "quotes",
            "typeDisp": "ETF",
            "longname": "Invesco QQQ Trust",
            "exchDisp": "NASDAQ",
            "isYahooFinance": true
        }]}'''

        self.check_parse_raise(invalid_json, 'exchange')

    def test_parse_raisesWhenNoShortnameField(self):
        invalid_json = '''{"quotes": [
        {
            "exchange": "NGM",
            "__shortname": "Invesco QQQ Trust, Series 1",
            "quoteType": "ETF",
            "symbol": "QQQ",
            "index": "quotes",
            "typeDisp": "ETF",
            "longname": "Invesco QQQ Trust",
            "exchDisp": "NASDAQ",
            "isYahooFinance": true
        }]}'''

        self.check_parse_raise(invalid_json, 'shortname')
