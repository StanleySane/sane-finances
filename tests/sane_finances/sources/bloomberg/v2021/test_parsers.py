#!/usr/bin/env python
# -*- coding: utf-8 -*-
import datetime
import decimal
import json
import unittest

from sane_finances.sources.base import ParseError
from sane_finances.sources.bloomberg.v2021.meta import (
    InstrumentPrice, BloombergInstrumentInfo)
from sane_finances.sources.bloomberg.v2021.parsers import (
    BloombergHistoryJsonParser, BloombergInfoJsonParser)


class TestBloombergHistoryJsonParser(unittest.TestCase):

    def setUp(self) -> None:
        self.parser = BloombergHistoryJsonParser()

    def check_parse_raise(self, invalid_json: str, message: str):
        with self.assertRaisesRegex(ParseError, message):
            _ = list(self.parser.parse(invalid_json, tzinfo=None))

    def test_convert_float_to_decimal_SuccessWithFloat(self):
        float_value = 42.42
        expected_result = decimal.Decimal('42.42')

        self.assertEqual(expected_result, self.parser.convert_float_to_decimal(float_value))

    def test_convert_float_to_decimal_SuccessWithString(self):
        float_value = '42.42'
        expected_result = decimal.Decimal('42.42')

        # noinspection PyTypeChecker
        self.assertEqual(expected_result, self.parser.convert_float_to_decimal(float_value))

    def test_parse_Success(self):
        valid_json = '''[{
                "ticker":"I28893:IND",
                "price":[
                    {"dateTime":"2017-02-20","value":178.371},
                    {"dateTime":"2017-02-21","value":178.095}
                    ]
                }]'''

        raw_data = json.loads(valid_json)

        expected_result = [
            InstrumentPrice(
                ticker=raw_data[0]['ticker'],
                price_date=datetime.datetime.strptime(price_data['dateTime'], self.parser.date_format).date(),
                price_value=self.parser.convert_float_to_decimal(price_data['value']))
            for price_data
            in raw_data[0]['price']]

        self.assertSequenceEqual(expected_result, list(self.parser.parse(valid_json, tzinfo=None)))

    def test_parse_RaiseWhenEmptyString(self):
        invalid_json = ''

        self.check_parse_raise(invalid_json, '')

    def test_parse_RaiseWhenNoData(self):
        invalid_json = '[]'

        self.check_parse_raise(invalid_json, 'Data not found')

    def test_parse_RaiseWhenNotList(self):
        invalid_json = '{}'

        self.check_parse_raise(invalid_json, 'is not list')

    def test_parse_RaiseWhenItemIsNotDict(self):
        invalid_json = '''[42]'''

        self.check_parse_raise(invalid_json, 'Data item is not dict')

    def test_parse_RaiseWhenNoTickerField(self):
        invalid_json = '''[{"__ticker":"I28893:IND", "price":[{"dateTime":"2017-02-20","value":178.371}]}]'''

        self.check_parse_raise(invalid_json, "'ticker'")

    def test_parse_RaiseWhenNoPriceField(self):
        invalid_json = '''[{"ticker":"I28893:IND", "__price":[{"dateTime":"2017-02-20","value":178.371}]}]'''

        self.check_parse_raise(invalid_json, "'price'")

    def test_parse_RaiseWhenPriceIsNotList(self):
        invalid_json = '''[{"ticker":"I28893:IND", "price":42}]'''

        self.check_parse_raise(invalid_json, "'price'")

    def test_parse_RaiseWhenPriceItemsIsNotDict(self):
        invalid_json = '''[{"ticker":"I28893:IND", "price":[42]}]'''

        self.check_parse_raise(invalid_json, "Price item is not dict")

    def test_parse_RaiseWhenNoDateField(self):
        invalid_json = '''[{"ticker":"I28893:IND", "price":[{"__dateTime":"2017-02-20","value":178.371}]}]'''

        self.check_parse_raise(invalid_json, "'dateTime'")

    def test_parse_RaiseWhenNoValueField(self):
        invalid_json = '''[{"ticker":"I28893:IND", "price":[{"dateTime":"2017-02-20","__value":178.371}]}]'''

        self.check_parse_raise(invalid_json, "'value'")

    def test_parse_RaiseWhenWrongDateValue(self):
        invalid_json = '''[{"ticker":"I28893:IND", "price":[{"dateTime":"WRONG_DATE","value":178.371}]}]'''

        self.check_parse_raise(invalid_json, "Can't create date")

    def test_parse_RaiseWhenWrongValue(self):
        invalid_json = '''[{"ticker":"I28893:IND", "price":[{"dateTime":"2017-02-20","value":"WRONG_VALUE"}]}]'''

        self.check_parse_raise(invalid_json, "Can't convert value.*?to decimal")


class TestBloombergInfoJsonParser(unittest.TestCase):

    def setUp(self) -> None:
        self.parser = BloombergInfoJsonParser()

    def check_parse_raise(self, invalid_json: str, message: str):
        with self.assertRaisesRegex(ParseError, message):
            _ = list(self.parser.parse(invalid_json))

    # noinspection PyMethodMayBeStatic
    def get_valid_json(self):
        valid_json = '''{"total_results":1,
                "results":[
                    {"country":"US",
                     "ticker_symbol":"DJP:US",
                     "resource_type":"Fund",
                     "name":"iPath Bloomberg Commodity Index Total Return ETN",
                     "resource_id":"DJP:US",
                     "security_type":"ETP",
                     "url":"some url"},
                    {"ticker_symbol":"TICKER",
                     "name":"NAME"}
                    ]}'''
        return valid_json

    def test_parse_success(self):
        valid_json = self.get_valid_json()

        raw_data = json.loads(valid_json)

        expected_result = [
            BloombergInstrumentInfo(
                ticker_symbol=results_data['ticker_symbol'],
                name=results_data['name'],
                country=results_data.get('country'),
                resource_type=results_data.get('resource_type'),
                resource_id=results_data.get('resource_id'),
                security_type=results_data.get('security_type'),
                url=results_data.get('url'))
            for results_data
            in raw_data['results']]

        self.assertSequenceEqual(expected_result, list(self.parser.parse(valid_json)))

    def test_parse_RaiseWhenNoData(self):
        invalid_json = ''

        self.check_parse_raise(invalid_json, '')

    def test_parse_RaiseWhenNotDict(self):
        invalid_json = '[42]'

        self.check_parse_raise(invalid_json, 'is not dict')

    def test_parse_RaiseWhenNoResultsField(self):
        invalid_json = '''{"total_results":1, "__results":[{"ticker_symbol":"TICKER","name":"NAME"}]}'''

        self.check_parse_raise(invalid_json, "'results'")

    def test_parse_RaiseWhenResultsIsNotList(self):
        invalid_json = '''{"total_results":1, "results":42}'''

        self.check_parse_raise(invalid_json, "'results'")

    def test_parse_RaiseWhenItemInResultsNotDict(self):
        invalid_json = '''{"total_results":1, "results":[42]}'''

        self.check_parse_raise(invalid_json, "'results'.*?not dict")

    def test_parse_RaiseWhenNoTickerField(self):
        invalid_json = '''{"total_results":1, "results":[{"__ticker_symbol":"TICKER","name":"NAME"}]}'''

        self.check_parse_raise(invalid_json, "'ticker_symbol'")

    def test_parse_RaiseWhenNoNameField(self):
        invalid_json = '''{"total_results":1, "results":[{"ticker_symbol":"TICKER","__name":"NAME"}]}'''

        self.check_parse_raise(invalid_json, "'name'")
