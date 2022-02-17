#!/usr/bin/env python
# -*- coding: utf-8 -*-
import datetime
import decimal
import json
import typing
import unittest
import re

from sane_finances.sources.base import ParseError
from sane_finances.sources.ishares.v2021.meta import (ProductInfo, PerformanceValue)
from sane_finances.sources.ishares.v2021.parsers import (
    ISharesHistoryHtmlParser, ISharesInfoJsonParser, make_date_from_iso_int)


class TestISharesInfoJsonParser(unittest.TestCase):

    def setUp(self) -> None:
        self.parser = ISharesInfoJsonParser()

    def check_parse_raise(self, invalid_json: str, message: str):
        with self.assertRaisesRegex(ParseError, message):
            _ = list(self.parser.parse(invalid_json))

    # noinspection PyMethodMayBeStatic
    def get_valid_info_json(self):
        valid_json = '''{
        "239726":
          {
            "fees":{"d":"0.03","r":0.03},
            "fundName":"iShares Core S&P 500 ETF",
            "inceptionDate":{"d":"May 15, 2000","r":20000515},
            "investmentStyle":"[Index]",
            "investorClassName":" ",
            "isin":"US4642872000",
            "localExchangeTicker":"IVV",
            "mgt":{"d":"0.03","r":0.03},
            "productPageUrl":"/us/products/239726/ishares-core-sp-500-etf",
            "ter":{"d":"0.03","r":0.03}
          },
        "239725":
          {
            "fees":{"d":"0.18","r":0.18},
            "fundName":"iShares S&P 500 Growth ETF",
            "inceptionDate":{"d":"May 22, 2000","r":20000522},
            "investmentStyle":"[Index]",
            "investorClassName":" ",
            "isin":"US4642873099",
            "localExchangeTicker":"IVW",
            "mgt":{"d":"0.18","r":0.18},
            "productPageUrl":"/us/products/239725/ishares-sp-500-growth-etf",
            "ter":{"d":"0.18","r":0.18}
          }
        }'''
        return valid_json

    def test_parse_Success(self):
        valid_json = self.get_valid_info_json()

        raw_data: typing.Dict[str, typing.Dict[str, typing.Any]] = json.loads(valid_json)

        expected_result = [
            ProductInfo(
                local_exchange_ticker=info_data['localExchangeTicker'],
                isin=info_data['isin'],
                fund_name=info_data['fundName'],
                inception_date=make_date_from_iso_int(int(info_data['inceptionDate']['r'])),
                product_page_url=info_data['productPageUrl'])
            for info_data
            in raw_data.values()]

        result = list(self.parser.parse(valid_json))

        self.assertSequenceEqual(expected_result, result)

    def test_parse_RaiseWhenNoData(self):
        invalid_json = ''

        self.check_parse_raise(invalid_json, '')

    def test_parse_RaiseWhenNotDict(self):
        invalid_json = '[42]'

        self.check_parse_raise(invalid_json, 'is not dict')

    def test_parse_RaiseWhenItemsNotDict(self):
        invalid_json = '{"attr":[]}'

        self.check_parse_raise(invalid_json, 'Items are not dict')

    def test_parse_RaiseWhenNoRequiredFields(self):
        valid_json = self.get_valid_info_json()
        for field_to_check in ('localExchangeTicker', 'isin', 'fundName', 'productPageUrl', 'inceptionDate', 'r'):
            # corrupt JSON
            pattern_to_corrupt = f'"{field_to_check}"'
            invalid_json = re.sub(pattern_to_corrupt, f'"__{field_to_check}"', valid_json)

            self.check_parse_raise(invalid_json, f"'{field_to_check}'")

    def test_parse_RaiseWhenInceptionDateIsNotDict(self):
        valid_json = self.get_valid_info_json()

        # corrupt JSON
        invalid_json = re.sub(r'"inceptionDate":{.*?}',
                              '"inceptionDate":42',
                              valid_json)

        self.check_parse_raise(invalid_json, "'inceptionDate'")

    def test_parse_RaiseWhenInceptionDateRIsNotInt(self):
        valid_json = self.get_valid_info_json()

        # corrupt JSON
        invalid_json = re.sub(r'"inceptionDate":{.*?}',
                              '"inceptionDate":{"r":"NOT_INT"}',
                              valid_json)

        self.check_parse_raise(invalid_json, "Can't convert.*?to int")

    def test_parse_RaiseWhenWrongInceptionDate(self):
        valid_json = self.get_valid_info_json()

        # corrupt JSON
        invalid_json = re.sub(r'"inceptionDate":{.*?}',
                              '"inceptionDate":{"r":9999999999}',
                              valid_json)

        self.check_parse_raise(invalid_json, "Can't create date from")


class TestISharesHistoryHtmlParser(unittest.TestCase):

    def setUp(self) -> None:
        self.parser = ISharesHistoryHtmlParser()

        self.expected_result = [
            PerformanceValue(date=datetime.date(1999, 12, 31), value=decimal.Decimal(42)),
            PerformanceValue(date=datetime.date(2000, 1, 1), value=decimal.Decimal(43))
        ]

    def get_html_to_parse(self):
        date_format = '%a, %b %d, %Y'
        perf_data = ",".join([
            '{'+f'x:Date.UTC({perf_value.date.year},{perf_value.date.month-1},{perf_value.date.day}),'
                f'y:Number(({perf_value.value}).toFixed(2)),formattedX: "{perf_value.date.strftime(date_format)}"' + '}'
            for perf_value
            in self.expected_result])

        html = f"""<!DOCTYPE html>
        <html xmlns="http://www.w3.org/1999/xhtml" prefix="og: http://ogp.me/ns#" lang="en" xml:lang="en">
        <head>
            <title>iShares Core S&P 500 ETF | IVV</title>
        </head>
        <body id="us-ishares">
            <script nonce="Hdk1jsMIJVe99omXlyZrWA==">
                //<![CDATA[
                var yDecimalsNavChart = 2;
                var yDecimals = 2;
                var performanceData = [{perf_data}];
                var chartTooltipDateFormat = 'EEE, MMM dd, yyyy';
                //]]>
            </script>
        </body>
        </html>"""

        return html

    def test_parse_Success(self):
        html = self.get_html_to_parse()

        result = list(self.parser.parse(html, None))

        self.assertSequenceEqual(self.expected_result, result)

    def test_parse_RaiseWithEmptyString(self):
        html = ""

        with self.assertRaisesRegex(ParseError, 'No data found'):
            _ = list(self.parser.parse(html, None))

    def test_parse_RaiseWithNoData(self):
        self.expected_result = []
        html = self.get_html_to_parse()

        with self.assertRaisesRegex(ParseError, 'No data found'):
            _ = list(self.parser.parse(html, None))

    def test_parse_RaiseWhenWrongDate(self):
        valid_html = self.get_html_to_parse()
        # corrupt HTML
        bad_html = re.sub(r"Date.UTC", "BAD_DATE", valid_html)

        with self.assertRaisesRegex(ParseError, "Not found date in HTML"):
            _ = list(self.parser.parse(bad_html, None))

    def test_parse_RaiseWhenNoNumber(self):
        valid_html = self.get_html_to_parse()
        # corrupt HTML
        bad_html = re.sub(r"Number", "BAD_VALUE", valid_html)

        with self.assertRaisesRegex(ParseError, "Not found value in HTML"):
            _ = list(self.parser.parse(bad_html, None))

    def test_parse_RaiseWhenWrongValue(self):
        valid_html = self.get_html_to_parse()
        # corrupt HTML
        bad_html = re.sub(r"Number\(\(.*?\)", "Number((WRONG)", valid_html)

        with self.assertRaisesRegex(ParseError, "Can't convert value.*?to decimal"):
            _ = list(self.parser.parse(bad_html, None))

    def test_parse_RaiseWhenWrongDateParts(self):
        valid_html = self.get_html_to_parse()
        # corrupt HTML
        search_pattern = re.compile(
            r"Date.UTC\((?P<year>\d*?),(?P<month>\d*?),(?P<day>\d*?)\)",
            re.IGNORECASE | re.MULTILINE | re.DOTALL
        )
        for corrupt_pattern, field_name in (
                (r"Date.UTC(,\g<month>,\g<day>)", 'year'),
                (r"Date.UTC(\g<year>,,\g<day>)", 'month'),
                (r"Date.UTC(\g<year>,\g<month>,)", 'day')):
            bad_html = re.sub(search_pattern, corrupt_pattern, valid_html)

            with self.assertRaisesRegex(ParseError, f"Can't convert '{field_name}' value.*?to int"):
                _ = list(self.parser.parse(bad_html, None))

    def test_parse_RaiseWhenWrongDateValue(self):
        valid_html = self.get_html_to_parse()
        # corrupt HTML
        search_pattern = re.compile(
            r"Date.UTC\((?P<year>\d*?),(?P<month>\d*?),(?P<day>\d*?)\)",
            re.IGNORECASE | re.MULTILINE | re.DOTALL
        )
        for corrupt_pattern in (
                r"Date.UTC(99999999999,\g<month>,\g<day>)",
                r"Date.UTC(\g<year>,99999,\g<day>)",
                r"Date.UTC(\g<year>,\g<month>,99999)"):
            bad_html = re.sub(search_pattern, corrupt_pattern, valid_html)

            with self.assertRaisesRegex(ParseError, "Can't create date"):
                _ = list(self.parser.parse(bad_html, None))
