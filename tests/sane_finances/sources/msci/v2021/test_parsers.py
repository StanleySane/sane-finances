#!/usr/bin/env python
# -*- coding: utf-8 -*-

import decimal
import re
import typing
import unittest
import datetime

from sane_finances.sources.base import ParseError, SourceDownloadError, InstrumentValuesHistoryEmpty
from sane_finances.sources.msci.v2021.meta import (
    Market, Currency, IndexLevel, Frequency, IndexSuite, Size, Style, IndexSuiteGroup, Scopes,
    IndexValue, IndexInfo, IndexPanelData)
from sane_finances.sources.msci.v2021.parsers import (
    MsciHistoryJsonParser, MsciIndexInfoParser, MsciIndexPanelDataJsonParser)

from .fakes import FakeMsciIndexDownloadParameterValuesStorage


class TestMsciHistoryJsonParser(unittest.TestCase):

    def setUp(self):
        # noinspection PyTypeChecker
        self.index_panel_data = IndexPanelData(
            markets=(Market(identity='ID', name='NAME'),),
            currencies=(Currency(identity='ID', name='NAME'),),
            index_levels=(IndexLevel(identity='ID', name='NAME'),),
            frequencies=(),
            index_suite_groups=(),
            index_suites=(),
            sizes=(),
            styles=(),
            daily_frequency=None,
            monthly_frequency=None
        )

        self.parser = MsciHistoryJsonParser(FakeMsciIndexDownloadParameterValuesStorage(self.index_panel_data))

        self.expected_level_eod_str = '12345.6789'
        self.expected_result = [IndexValue(
            calc_date=datetime.date(2000, 12, 31),
            level_eod=decimal.Decimal(self.expected_level_eod_str),
            msci_index_code='990300',
            index_variant_type=self.index_panel_data.index_levels[0],
            currency=self.index_panel_data.currencies[0])]

        self.expected_date_str = self.expected_result[0].calc_date.strftime(self.parser.date_format)

    def check_parse_raise(self, error: typing.Type[Exception], invalid_json: str):
        with self.assertRaises(error):
            _ = list(self.parser.parse(invalid_json, tzinfo=None))

    def test_parse_Success(self):
        valid_json = f"""
{{
    "msci_index_code":"{self.expected_result[0].msci_index_code}",
    "index_variant_type":"{self.expected_result[0].index_variant_type.identity}",
    "ISO_currency_symbol":"{self.expected_result[0].currency.identity}",
    "indexes":{{
        "INDEX_LEVELS":[{{"level_eod":{self.expected_level_eod_str},"calc_date":{self.expected_date_str}}}]
    }}
}}
"""
        result = list(self.parser.parse(valid_json, tzinfo=None))

        self.assertSequenceEqual(result, self.expected_result)

    def test_parse_raisesWhenUnknownLevel(self):
        invalid_json = f"""
        {{
            "msci_index_code":"{self.expected_result[0].msci_index_code}",
            "index_variant_type":"WRONG",
            "ISO_currency_symbol":"{self.expected_result[0].currency.identity}",
            "indexes":{{
                "INDEX_LEVELS":[{{"level_eod":{self.expected_level_eod_str},"calc_date":{self.expected_date_str}}}]
            }}
        }}
        """
        self.check_parse_raise(ParseError, invalid_json)

    def test_parse_raisesWhenUnknownCurrency(self):
        invalid_json = f"""
        {{
            "msci_index_code":"{self.expected_result[0].msci_index_code}",
            "index_variant_type":"{self.expected_result[0].index_variant_type.identity}",
            "ISO_currency_symbol":"WRONG",
            "indexes":{{
                "INDEX_LEVELS":[{{"level_eod":{self.expected_level_eod_str},"calc_date":{self.expected_date_str}}}]
            }}
        }}
        """
        self.check_parse_raise(ParseError, invalid_json)

    def test_parse_raisesWhenEmptyHistory(self):
        valid_json = f"""
        {{
            "msci_index_code":"{self.expected_result[0].msci_index_code}",
            "index_variant_type":"{self.expected_result[0].index_variant_type.identity}",
            "ISO_currency_symbol":"{self.expected_result[0].currency.identity}",
            "indexes":{{
                "INDEX_LEVELS":[]
            }}
        }}
        """
        self.check_parse_raise(InstrumentValuesHistoryEmpty, valid_json)

    def test_parse_raisesWhenWrongValue(self):
        invalid_json = f"""
        {{
            "msci_index_code":"{self.expected_result[0].msci_index_code}",
            "index_variant_type":"{self.expected_result[0].index_variant_type.identity}",
            "ISO_currency_symbol":"{self.expected_result[0].currency.identity}",
            "indexes":{{
                "INDEX_LEVELS":[{{"level_eod":"WRONG","calc_date":{self.expected_date_str}}}]
            }}
        }}
        """
        self.check_parse_raise(ParseError, invalid_json)

    def test_parse_raisesWhenWrongDate(self):
        invalid_json = f"""
        {{
            "msci_index_code":"{self.expected_result[0].msci_index_code}",
            "index_variant_type":"{self.expected_result[0].index_variant_type.identity}",
            "ISO_currency_symbol":"{self.expected_result[0].currency.identity}",
            "indexes":{{
                "INDEX_LEVELS":[{{"level_eod":{self.expected_level_eod_str},"calc_date":"WRONG"}}]
            }}
        }}
        """
        self.check_parse_raise(ParseError, invalid_json)

    def test_parse_raisesWhenNoCode(self):
        invalid_json = f"""
        {{
            "msci_index_code__":"{self.expected_result[0].msci_index_code}",
            "index_variant_type":"{self.expected_result[0].index_variant_type.identity}",
            "ISO_currency_symbol":"{self.expected_result[0].currency.identity}",
            "indexes":{{
                "INDEX_LEVELS":[{{"level_eod":{self.expected_level_eod_str},"calc_date":{self.expected_date_str}}}]
            }}
        }}
        """
        self.check_parse_raise(ParseError, invalid_json)

    def test_parse_raisesWhenNoCurrency(self):
        invalid_json = f"""
        {{
            "msci_index_code":"{self.expected_result[0].msci_index_code}",
            "index_variant_type":"{self.expected_result[0].index_variant_type.identity}",
            "ISO_currency_symbol__":"{self.expected_result[0].currency.identity}",
            "indexes":{{
                "INDEX_LEVELS":[{{"level_eod":{self.expected_level_eod_str},"calc_date":{self.expected_date_str}}}]
            }}
        }}
        """
        self.check_parse_raise(ParseError, invalid_json)

    def test_parse_raisesWhenNoVariantType(self):
        invalid_json = f"""
        {{
            "msci_index_code":"{self.expected_result[0].msci_index_code}",
            "index_variant_type__":"{self.expected_result[0].index_variant_type.identity}",
            "ISO_currency_symbol":"{self.expected_result[0].currency.identity}",
            "indexes":{{
                "INDEX_LEVELS":[{{"level_eod":{self.expected_level_eod_str},"calc_date":{self.expected_date_str}}}]
            }}
        }}
        """
        self.check_parse_raise(ParseError, invalid_json)

    def test_parse_raisesWhenNoIndexes(self):
        invalid_json = f"""
        {{
            "msci_index_code":"{self.expected_result[0].msci_index_code}",
            "index_variant_type":"{self.expected_result[0].index_variant_type.identity}",
            "ISO_currency_symbol":"{self.expected_result[0].currency.identity}",
            "indexes__":{{
                "INDEX_LEVELS":[{{"level_eod":{self.expected_level_eod_str},"calc_date":{self.expected_date_str}}}]
            }}
        }}
        """
        self.check_parse_raise(ParseError, invalid_json)

    def test_parse_raisesWhenWrongIndexes(self):
        invalid_json = f"""
        {{
            "msci_index_code":"{self.expected_result[0].msci_index_code}",
            "index_variant_type":"{self.expected_result[0].index_variant_type.identity}",
            "ISO_currency_symbol":"{self.expected_result[0].currency.identity}",
            "indexes":[]
        }}
        """
        self.check_parse_raise(ParseError, invalid_json)

    def test_parse_raisesWhenNoIndexLevels(self):
        invalid_json = f"""
        {{
            "msci_index_code":"{self.expected_result[0].msci_index_code}",
            "index_variant_type":"{self.expected_result[0].index_variant_type.identity}",
            "ISO_currency_symbol":"{self.expected_result[0].currency.identity}",
            "indexes":{{
                "INDEX_LEVELS__":[{{"level_eod":{self.expected_level_eod_str},"calc_date":{self.expected_date_str}}}]
            }}
        }}
        """
        self.check_parse_raise(ParseError, invalid_json)

    def test_parse_raisesWhenWrongIndexLevels(self):
        invalid_json = f"""
        {{
            "msci_index_code":"{self.expected_result[0].msci_index_code}",
            "index_variant_type":"{self.expected_result[0].index_variant_type.identity}",
            "ISO_currency_symbol":"{self.expected_result[0].currency.identity}",
            "indexes":{{
                "INDEX_LEVELS":[42]
            }}
        }}
        """
        self.check_parse_raise(ParseError, invalid_json)

    def test_parse_raisesWhenNoLevel(self):
        invalid_json = f"""
        {{
            "msci_index_code":"{self.expected_result[0].msci_index_code}",
            "index_variant_type":"{self.expected_result[0].index_variant_type.identity}",
            "ISO_currency_symbol":"{self.expected_result[0].currency.identity}",
            "indexes":{{
                "INDEX_LEVELS":[{{"level_eod__":{self.expected_level_eod_str},"calc_date":{self.expected_date_str}}}]
            }}
        }}
        """
        self.check_parse_raise(ParseError, invalid_json)

    def test_parse_raisesWhenNoDate(self):
        invalid_json = f"""
        {{
            "msci_index_code":"{self.expected_result[0].msci_index_code}",
            "index_variant_type":"{self.expected_result[0].index_variant_type.identity}",
            "ISO_currency_symbol":"{self.expected_result[0].currency.identity}",
            "indexes":{{
                "INDEX_LEVELS":[{{"level_eod":{self.expected_level_eod_str},"calc_date__":{self.expected_date_str}}}]
            }}
        }}
        """
        self.check_parse_raise(ParseError, invalid_json)

    def test_parse_raisesWhenNoData(self):
        invalid_json = ''

        self.check_parse_raise(ParseError, invalid_json)

    def test_parse_raisesWhenSourceError(self):
        invalid_json = """
{
    "timestamp":"Aug 14, 2021 4:20:12 PM",
    "user":"sys_x_bmapip01",
    "error_code":" 100",
    "error_message":" null Invalid Parameter end_date : '19691231. Calculation date cannot be earlier than 19970101'"
}
"""
        self.check_parse_raise(SourceDownloadError, invalid_json)

    def test_parse_raisesWhenWrongJson(self):
        invalid_json = """[]"""

        self.check_parse_raise(ParseError, invalid_json)

    def test_parse_raisesWhenUnknownJson(self):
        invalid_json = """{}"""

        self.check_parse_raise(ParseError, invalid_json)


class TestMsciIndexInfoParser(unittest.TestCase):

    def setUp(self):
        self.parser = MsciIndexInfoParser()

    def test_parse_Success(self):
        expected_result = [IndexInfo(msci_index_code='INDEX CODE', index_name='INDEX NAME')]

        json = f"""{{"indexes":[
        {{"msci_index_code":"{expected_result[0].msci_index_code}","index_name":"{expected_result[0].index_name}"}}
        ]}}"""

        result = list(self.parser.parse(json))

        self.assertSequenceEqual(result, expected_result)

    def test_parse_SuccessEmptyList(self):
        expected_result = []

        json = """{"indexes":[]}"""

        result = list(self.parser.parse(json))

        self.assertSequenceEqual(result, expected_result)

    def test_parse_raisesEmptyString(self):
        wrong_json = ''

        with self.assertRaises(ParseError):
            list(self.parser.parse(wrong_json))

    def test_parse_raisesWrongJson(self):
        wrong_json = '[]'

        with self.assertRaises(ParseError):
            list(self.parser.parse(wrong_json))

    def test_parse_raisesNoIndexes(self):
        wrong_json = """{}"""

        with self.assertRaises(ParseError):
            list(self.parser.parse(wrong_json))

    def test_parse_raisesWrongIndexes(self):
        wrong_json = """{"indexes":[1]}"""

        with self.assertRaises(ParseError):
            list(self.parser.parse(wrong_json))

    def test_parse_raisesNoCode(self):
        wrong_json = """{"indexes":[{"msci_index_code__":"CODE","index_name":"NAME"}]}"""

        with self.assertRaises(ParseError):
            list(self.parser.parse(wrong_json))

    def test_parse_raisesNoName(self):
        wrong_json = """{"indexes":[{"msci_index_code":"CODE","index_name__":"NAME"}]}"""

        with self.assertRaises(ParseError):
            list(self.parser.parse(wrong_json))


class TestMsciIndexPanelDataJsonParser(unittest.TestCase):

    def setUp(self):
        self.daily_frequency = Frequency(identity='DAILY', name='Daily')
        self.monthly_frequency = Frequency(identity='END_OF_MONTH', name='Monthly')
        index_suite_group = IndexSuiteGroup(name='Capped')
        self.expected_result = IndexPanelData(
            markets=(Market(identity='24576', name='All Country (DM+EM)', scope=Scopes.REGIONAL),
                     Market(identity='16384', name='Developed Markets (DM)'),),
            currencies=(Currency(identity='USD', name='USD'),),
            index_levels=(IndexLevel(identity='STRD', name='Price'),),
            frequencies=(self.daily_frequency, self.monthly_frequency),
            index_suite_groups=(index_suite_group,),
            index_suites=(IndexSuite(identity='C', name='None'),
                          IndexSuite(identity='C', name='None', group=index_suite_group),),
            sizes=(Size(identity='ID', name='NAME'),),
            styles=(Style(identity='ID', name='NAME'),),
            daily_frequency=self.daily_frequency,
            monthly_frequency=self.monthly_frequency
        )

        self.parser = MsciIndexPanelDataJsonParser()

    def generate_valid_json(self):
        valid_json = f"""
        {{
            "market":[{{"id": "{self.expected_result.markets[0].identity}",
                        "name": "{self.expected_result.markets[0].name}"}},
                      {{"id": "{self.expected_result.markets[1].identity}",
                        "name": "{self.expected_result.markets[1].name}"}}],
            "currency":[{{"id": "{self.expected_result.currencies[0].identity}",
                          "name": "{self.expected_result.currencies[0].name}"}}],
            "indexLevels":[{{"id":"{self.expected_result.index_levels[0].identity}",
                             "name":"{self.expected_result.index_levels[0].name}"}}],
            "frequency":[{{"id":"{self.daily_frequency.identity}",
                           "name":"{self.daily_frequency.name}"}},
                         {{"id":"{self.monthly_frequency.identity}",
                           "name":"{self.monthly_frequency.name}"}}],
            "indexSuite":[
                {{
                    "id":"{self.expected_result.index_suites[0].identity}",
                    "name":"{self.expected_result.index_suites[0].name}"
                }},
                {{ 
                    "optgroup":"{self.expected_result.index_suite_groups[0].name}",
                    "options":[{{"id":"{self.expected_result.index_suites[1].identity}",
                                 "name":"{self.expected_result.index_suites[1].name}"}}]
                }}
            ],
            "size":[{{"id":"{self.expected_result.sizes[0].identity}",
                      "name":"{self.expected_result.sizes[0].name}"}}],
            "style":[{{"id":"{self.expected_result.styles[0].identity}",
                       "name":"{self.expected_result.styles[0].name}"}}]    
        }}"""

        return valid_json

    def spoil_block(self, block_name: str, new_content: str):
        spoil_pattern = re.compile(fr'"{block_name}"\s*:\s*\[.*?]', re.IGNORECASE | re.MULTILINE | re.DOTALL)
        return spoil_pattern.sub(f'"{block_name}":[{new_content}]', self.generate_valid_json())

    def test_parse_Success(self):
        result = self.parser.parse(self.generate_valid_json())

        self.assertEqual(result, self.expected_result)

    def test_parse_raisesEmptyString(self):
        wrong_json = ''

        with self.assertRaises(ParseError):
            list(self.parser.parse(wrong_json))

    def test_parse_raisesWrongJson(self):
        wrong_json = '[]'

        with self.assertRaises(ParseError):
            list(self.parser.parse(wrong_json))

    def test_parse_raisesNotFoundDailyFrequency(self):
        self.daily_frequency = Frequency(identity='WRONG', name='WRONG')
        wrong_json = self.generate_valid_json()

        with self.assertRaises(ParseError):
            list(self.parser.parse(wrong_json))

    def test_parse_raisesNotFoundMonthlyFrequency(self):
        self.monthly_frequency = Frequency(identity='WRONG', name='WRONG')
        wrong_json = self.generate_valid_json()

        with self.assertRaises(ParseError):
            list(self.parser.parse(wrong_json))

    def test_parse_raisesWhenWrongBlockContent(self):
        for block_name, spoil_content in (('market', True),
                                           ('currency', True),
                                           ('indexLevels', True),
                                           ('frequency', True),
                                           ('indexSuite', False),
                                           ('size', True),
                                           ('style', True)):
            # no block
            wrong_json = self.generate_valid_json().replace(f'"{block_name}"', f'"{block_name}__"')

            with self.assertRaises(ParseError):
                list(self.parser.parse(wrong_json))

            if spoil_content:
                # wrong element type
                wrong_json = self.spoil_block(block_name, '0')

                with self.assertRaises(ParseError):
                    list(self.parser.parse(wrong_json))

                # no ID
                wrong_json = self.spoil_block(block_name, '{"id__":"ID","name":"NAME"}')

                with self.assertRaises(ParseError):
                    list(self.parser.parse(wrong_json))

                # no name
                wrong_json = self.spoil_block(block_name, '{"id":"ID","name__":"NAME"}')

                with self.assertRaises(ParseError):
                    list(self.parser.parse(wrong_json))
