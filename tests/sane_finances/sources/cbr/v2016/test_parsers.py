#!/usr/bin/env python
# -*- coding: utf-8 -*-

import decimal
import unittest
import datetime

from sane_finances.sources.base import ParseError
from sane_finances.sources.cbr.v2016.meta import CurrencyInfo, CurrencyRateValue
from sane_finances.sources.cbr.v2016.parsers import CbrCurrencyHistoryXmlParser, CbrCurrencyInfoParser


class TestCbrCurrencyHistoryXmlParser(unittest.TestCase):

    def test_parse_Success(self):
        parser = CbrCurrencyHistoryXmlParser()

        expected_result = [CurrencyRateValue(
            date=datetime.date(2000, 1, 1),
            value=decimal.Decimal("27.0100"),
            nominal=1,
            currency_id="R01235")]

        expected_id, expected_nominal_str = expected_result[0].currency_id, str(expected_result[0].nominal)
        expected_date_str = expected_result[0].date.strftime(parser.date_format)
        expected_value_str = f"{expected_result[0].value}".replace('.', ',')

        valid_xml = f"""<?xml version="1.0" encoding="windows-1251"?>
<ValCurs ID="{expected_id}" DateRange1="01.01.2000" DateRange2="01.02.2000" name="Foreign Currency Market Dynamic">
    <Record Date="{expected_date_str}" Id="{expected_id}">
        <Nominal>{expected_nominal_str}</Nominal>
        <Value>{expected_value_str}</Value>
        </Record>
</ValCurs>"""

        result = list(parser.parse(valid_xml, tzinfo=None))

        self.assertSequenceEqual(result, expected_result)

    def test_parse_raisesWhenNoData(self):
        parser = CbrCurrencyHistoryXmlParser()

        invalid_xml = ''

        with self.assertRaises(ParseError):
            list(parser.parse(invalid_xml, tzinfo=None))

    def test_parse_WhenEmptyList(self):
        parser = CbrCurrencyHistoryXmlParser()

        valid_xml = f"""<?xml version="1.0" encoding="windows-1251"?>
<ValCurs ID="R01235" DateRange1="02.01.2000" DateRange2="02.01.2000" name="Foreign Currency Market Dynamic"/>
"""
        result = list(parser.parse(valid_xml, tzinfo=None))

        self.assertEqual(len(result), 0)

    def test_parse_raisesWhenNotList(self):
        parser = CbrCurrencyHistoryXmlParser()

        invalid_xml = """<?xml version="1.0" encoding="windows-1251"?><WRONG_TAG></WRONG_TAG>"""

        with self.assertRaises(ParseError):
            list(parser.parse(invalid_xml, tzinfo=None))

    def test_parse_raisesWhenNoDateAttrib(self):
        parser = CbrCurrencyHistoryXmlParser()

        invalid_xml = """<?xml version="1.0" encoding="windows-1251"?>
        <ValCurs ID="R01235" DateRange1="01.01.2000" DateRange2="01.02.2000" name="Foreign Currency Market Dynamic">
            <Record Date__="01.01.2000" Id="R01235">
                <Nominal>1</Nominal>
                <Value>27,0000</Value>
            </Record>
        </ValCurs>"""

        with self.assertRaises(ParseError):
            list(parser.parse(invalid_xml, tzinfo=None))

    def test_parse_raisesWhenNoIdAttrib(self):
        parser = CbrCurrencyHistoryXmlParser()

        invalid_xml = """<?xml version="1.0" encoding="windows-1251"?>
        <ValCurs ID="R01235" DateRange1="01.01.2000" DateRange2="01.02.2000" name="Foreign Currency Market Dynamic">
            <Record Date="01.01.2000" Id__="R01235">
                <Nominal>1</Nominal>
                <Value>27,0000</Value>
            </Record>
        </ValCurs>"""

        with self.assertRaises(ParseError):
            list(parser.parse(invalid_xml, tzinfo=None))

    def test_parse_raisesWhenNoNominalTag(self):
        parser = CbrCurrencyHistoryXmlParser()

        invalid_xml = """<?xml version="1.0" encoding="windows-1251"?>
        <ValCurs ID="R01235" DateRange1="01.01.2000" DateRange2="01.02.2000" name="Foreign Currency Market Dynamic">
            <Record Date="01.01.2000" Id="R01235">
                <Nominal__>1</Nominal__>
                <Value>27,0000</Value>
            </Record>
        </ValCurs>"""

        with self.assertRaises(ParseError):
            list(parser.parse(invalid_xml, tzinfo=None))

    def test_parse_raisesWhenNoValueTag(self):
        parser = CbrCurrencyHistoryXmlParser()

        invalid_xml = """<?xml version="1.0" encoding="windows-1251"?>
        <ValCurs ID="R01235" DateRange1="01.01.2000" DateRange2="01.02.2000" name="Foreign Currency Market Dynamic">
            <Record Date="01.01.2000" Id="R01235">
                <Nominal>1</Nominal>
                <Value__>27,0000</Value__>
            </Record>
        </ValCurs>"""

        with self.assertRaises(ParseError):
            list(parser.parse(invalid_xml, tzinfo=None))


class TestCbrCurrencyInfoParser(unittest.TestCase):

    def test_parse_success(self):
        expected_result = [CurrencyInfo(
            currency_id='R01010',
            name='Австралийский доллар',
            eng_name='Australian Dollar',
            nominal=1,
            parent_code='R01010')]

        expected_name, expected_id = expected_result[0].name, expected_result[0].currency_id
        expected_eng_name = expected_result[0].eng_name
        expected_nominal = expected_result[0].nominal
        expected_parent_code = expected_result[0].parent_code

        xml = f"""<?xml version="1.0" encoding="windows-1251"?><Valuta name="Foreign Currency Market Lib">
    <Item ID="{expected_id}">
        <Name>{expected_name}</Name>
        <EngName>{expected_eng_name}</EngName>
        <Nominal>{expected_nominal}</Nominal>
        <ParentCode>{expected_parent_code} </ParentCode>
    </Item>
</Valuta>
        """

        parser = CbrCurrencyInfoParser()

        result = list(parser.parse(xml))

        self.assertSequenceEqual(result, expected_result)

    def test_parse_raisesWithoutName(self):
        xml = """<?xml version="1.0" encoding="windows-1251"?><Valuta name="Foreign Currency Market Lib">
            <Item ID="R01010">
                <Name__>Австралийский доллар</Name__>
                <EngName>Australian Dollar</EngName>
                <Nominal>1</Nominal>
                <ParentCode>R01010 </ParentCode>
            </Item>
        </Valuta>"""

        parser = CbrCurrencyInfoParser()

        with self.assertRaises(ParseError):
            list(parser.parse(xml))

    def test_parse_raisesWithoutEngName(self):
        xml = """<?xml version="1.0" encoding="windows-1251"?><Valuta name="Foreign Currency Market Lib">
            <Item ID="R01010">
                <Name>Австралийский доллар</Name>
                <EngName__>Australian Dollar</EngName__>
                <Nominal>1</Nominal>
                <ParentCode>R01010 </ParentCode>
            </Item>
        </Valuta>"""

        parser = CbrCurrencyInfoParser()

        with self.assertRaises(ParseError):
            list(parser.parse(xml))

    def test_parse_raisesWithoutNominal(self):
        xml = """<?xml version="1.0" encoding="windows-1251"?><Valuta name="Foreign Currency Market Lib">
            <Item ID="R01010">
                <Name>Австралийский доллар</Name>
                <EngName>Australian Dollar</EngName>
                <Nominal__>1</Nominal__>
                <ParentCode>R01010 </ParentCode>
            </Item>
        </Valuta>"""

        parser = CbrCurrencyInfoParser()

        with self.assertRaises(ParseError):
            list(parser.parse(xml))

    def test_parse_raisesWithoutParentCode(self):
        xml = """<?xml version="1.0" encoding="windows-1251"?><Valuta name="Foreign Currency Market Lib">
            <Item ID="R01010">
                <Name>Австралийский доллар</Name>
                <EngName>Australian Dollar</EngName>
                <Nominal>1</Nominal>
                <ParentCode__>R01010 </ParentCode__>
            </Item>
        </Valuta>"""

        parser = CbrCurrencyInfoParser()

        with self.assertRaises(ParseError):
            list(parser.parse(xml))

    def test_parse_raisesWithoutIdTag(self):
        xml = """<?xml version="1.0" encoding="windows-1251"?><Valuta name="Foreign Currency Market Lib">
            <Item ID__="R01010">
                <Name>Австралийский доллар</Name>
                <EngName>Australian Dollar</EngName>
                <Nominal>1</Nominal>
                <ParentCode__>R01010 </ParentCode__>
            </Item>
        </Valuta>"""

        parser = CbrCurrencyInfoParser()

        with self.assertRaises(ParseError):
            list(parser.parse(xml))

    def test_parse_raisesWrongTagName(self):
        xml = """<?xml version="1.0" encoding="windows-1251"?><WRONG_TAG name="Foreign Currency Market Lib">
    <Item ID="R01010">
        <Name>Австралийский доллар</Name>
        <EngName>Australian Dollar</EngName>
        <Nominal>1</Nominal>
        <ParentCode>R01010 </ParentCode>
    </Item>
</WRONG_TAG>"""

        parser = CbrCurrencyInfoParser()

        with self.assertRaises(ParseError):
            list(parser.parse(xml))

    def test_parse_raisesEmptyList(self):
        xml = """<?xml version="1.0" encoding="windows-1251"?><Valuta name="Foreign Currency Market Lib">
        </Valuta>"""

        parser = CbrCurrencyInfoParser()

        with self.assertRaises(ParseError):
            list(parser.parse(xml))

    def test_parse_raisesEmptyString(self):
        xml = ""

        parser = CbrCurrencyInfoParser()

        with self.assertRaises(ParseError):
            list(parser.parse(xml))
