#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import decimal
import unittest

from sane_finances.sources.base import ParseError
from sane_finances.sources.lbma.v2021.meta import (
    PreciousMetalInfo, PreciousMetalPrice, PreciousMetals, Currencies, LbmaPreciousMetalHistoryDownloadParameters)
from sane_finances.sources.lbma.v2021.parsers import (
    LbmaInfoParser, LbmaHistoryJsonParser)


class TestLbmaInfoParser(unittest.TestCase):

    def setUp(self) -> None:
        self.parser = LbmaInfoParser()

    def test_parse_Success(self):
        expected_result = [PreciousMetalInfo(metal=metal) for metal in PreciousMetals]

        result = list(self.parser.parse('WHATEVER'))

        self.assertSequenceEqual(expected_result, result)


class TestLbmaHistoryJsonParser(unittest.TestCase):

    def setUp(self) -> None:
        self.parser = LbmaHistoryJsonParser()
        self.currency = Currencies.USD
        self.parser.download_parameters = LbmaPreciousMetalHistoryDownloadParameters.safe_create(
            metal=PreciousMetals.GOLD_AM,
            currency=self.currency)

        self.expected_result = [
            PreciousMetalPrice(date=datetime.date(1999, 12, 31), value=decimal.Decimal('42.42')),
            PreciousMetalPrice(date=datetime.date(2000, 1, 1), value=decimal.Decimal('43.43'))
        ]

    def get_json_to_parse(self):
        date_format = '%Y-%m-%d'
        items = []
        for price in self.expected_result:
            date_str = price.date.strftime(date_format)
            values_str = ','.join(str(price.value if index == self.currency.history_position else 0)
                                  for index
                                  in range(len(Currencies)))

            items.append('{'+f'"d":"{date_str}","v":[{values_str}]' + '}')

        json_to_parse = '[' + ",".join(items) + ']'

        return json_to_parse

    def test_parse_Success(self):
        valid_json = self.get_json_to_parse()

        result = list(self.parser.parse(valid_json, None))

        self.assertSequenceEqual(self.expected_result, result)

    def test_parse_SuccessWithZeroValues(self):
        expected_result = list(self.expected_result)  # copy
        # add zero values
        self.expected_result.append(PreciousMetalPrice(date=datetime.date.today(), value=decimal.Decimal(0)))

        self.assertGreater(len(self.expected_result), len(expected_result))

        valid_json = self.get_json_to_parse()

        result = list(self.parser.parse(valid_json, None))

        self.assertSequenceEqual(expected_result, result)

    def test_parse_RaiseWithNoDownloadParameters(self):
        self.parser.download_parameters = None
        valid_json = self.get_json_to_parse()

        with self.assertRaisesRegex(ParseError, "'download_parameters'"):
            _ = list(self.parser.parse(valid_json, None))

    def test_parse_RaiseWithEmptyString(self):
        invalid_json = ''

        with self.assertRaises(ParseError):
            _ = list(self.parser.parse(invalid_json, None))

    def test_parse_RaiseWhenNotList(self):
        invalid_json = '{}'

        with self.assertRaisesRegex(ParseError, 'is not list'):
            _ = list(self.parser.parse(invalid_json, None))

    def test_parse_RaiseWhenItemIsNotDict(self):
        invalid_json = '[42]'

        with self.assertRaisesRegex(ParseError, 'item is not dict'):
            _ = list(self.parser.parse(invalid_json, None))

    def test_parse_RaiseWhenNoDateField(self):
        invalid_json = '[{"__d":"1968-01-02","v":[35.18,14.64,0]}]'

        with self.assertRaisesRegex(ParseError, "'d'"):
            _ = list(self.parser.parse(invalid_json, None))

    def test_parse_RaiseWhenNoValueField(self):
        invalid_json = '[{"d":"1968-01-02","__v":[35.18,14.64,0]}]'

        with self.assertRaisesRegex(ParseError, "'v'"):
            _ = list(self.parser.parse(invalid_json, None))

    def test_parse_RaiseWhenValueIsNotList(self):
        invalid_json = '[{"d":"1968-01-02","v":42}]'

        with self.assertRaisesRegex(ParseError, "'v'"):
            _ = list(self.parser.parse(invalid_json, None))

    def test_parse_RaiseWhenNotEnoughValues(self):
        invalid_json = '[{"d":"1968-01-02","v":[]}]'

        with self.assertRaisesRegex(ParseError, "has not enough values"):
            _ = list(self.parser.parse(invalid_json, None))

    def test_parse_RaiseWhenWrongDate(self):
        invalid_json = '[{"d":"WRONG_DATE","v":[35.18,14.64,0]}]'

        with self.assertRaisesRegex(ParseError, "Can't create date from"):
            _ = list(self.parser.parse(invalid_json, None))

    def test_parse_RaiseWhenWrongValue(self):
        invalid_json = '[{"d":"1968-01-02","v":["WRONG","WRONG","WRONG"]}]'

        with self.assertRaisesRegex(ParseError, "Can't convert.*?to decimal"):
            _ = list(self.parser.parse(invalid_json, None))
