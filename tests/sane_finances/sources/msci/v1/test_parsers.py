#!/usr/bin/env python
# -*- coding: utf-8 -*-

import decimal
import unittest
import datetime

from sane_finances.sources.base import ParseError
from sane_finances.sources.msci.v1.meta import IndexValue, IndexInfo, Styles, Sizes
from sane_finances.sources.msci.v1.parsers import MsciHistoryXmlParser, MsciIndexInfoParser


class TestMsciHistoryXmlParser(unittest.TestCase):

    def test_parse_Success(self):
        parser = MsciHistoryXmlParser()

        expected_result = [IndexValue(
            date=datetime.date(2016, 11, 3),
            value=decimal.Decimal('1644.941'),
            index_name='EAFE',
            style=Styles.NONE,
            size=Sizes.REGIONAL_STANDARD)]

        expected_name, expected_style, expected_size = \
            expected_result[0].index_name, expected_result[0].style.value, expected_result[0].size.value
        expected_date_str = expected_result[0].date.strftime(parser.date_format)
        expected_value_str = f"{expected_result[0].value:,}"  # comma as separator for thousands

        valid_xml = f"""<?xml version="1.0" ?>  <performance>
        <index id="{expected_name},{expected_style},{expected_size}">
          <asOf>
            <date>{expected_date_str}</date>
            <value>{expected_value_str}</value>
          </asOf>
        </index>
      </performance>"""

        result = list(parser.parse(valid_xml, tzinfo=None))

        self.assertSequenceEqual(result, expected_result)

    def test_parse_raisesWhenNoData(self):
        parser = MsciHistoryXmlParser()

        invalid_xml = ''

        with self.assertRaises(ParseError):
            list(parser.parse(invalid_xml, tzinfo=None))

    def test_parse_raisesWhenEmptyList(self):
        parser = MsciHistoryXmlParser()

        invalid_xml = """<?xml version="1.0" ?>  <performance></performance>"""

        with self.assertRaises(ParseError):
            list(parser.parse(invalid_xml, tzinfo=None))

    def test_parse_raisesWhenNotList(self):
        parser = MsciHistoryXmlParser()

        invalid_xml = """<WRONG_TAG></WRONG_TAG>"""

        with self.assertRaises(ParseError):
            list(parser.parse(invalid_xml, tzinfo=None))

    def test_parse_raisesWhenWrongIndexId(self):
        parser = MsciHistoryXmlParser()

        invalid_xml = """<?xml version="1.0" ?>  <performance>
          <index id="WRONG">
            <asOf>
              <date>03/11/2016</date>
              <value>1,644.941</value>
            </asOf>
          </index>
        </performance>"""

        with self.assertRaises(ParseError):
            list(parser.parse(invalid_xml, tzinfo=None))

    def test_parse_raisesWhenNoDateTag(self):
        parser = MsciHistoryXmlParser()

        invalid_xml = """<?xml version="1.0" ?>  <performance>
          <index id="EAFE,C,36">
            <asOf>
              <date__>03/11/2016</date__>
              <value>1,644.941</value>
            </asOf>
          </index>
        </performance>"""

        with self.assertRaises(ParseError):
            list(parser.parse(invalid_xml, tzinfo=None))

    def test_parse_raisesWhenNoValueTag(self):
        parser = MsciHistoryXmlParser()

        invalid_xml = """<?xml version="1.0" ?>  <performance>
          <index id="EAFE,C,36">
            <asOf>
              <date>03/11/2016</date>
              <value__>1,644.941</value__>
            </asOf>
          </index>
        </performance>"""

        with self.assertRaises(ParseError):
            list(parser.parse(invalid_xml, tzinfo=None))

    def test_parse_raisesWhenWrongDate(self):
        parser = MsciHistoryXmlParser()

        invalid_xml = """<?xml version="1.0" ?>  <performance>
          <index id="EAFE,C,36">
            <asOf>
              <date>9999/9999/9999</date>
              <value>1,644.941</value>
            </asOf>
          </index>
        </performance>"""

        with self.assertRaises(ParseError):
            list(parser.parse(invalid_xml, tzinfo=None))

    def test_parse_raisesWhenWrongValue(self):
        parser = MsciHistoryXmlParser()

        invalid_xml = """<?xml version="1.0" ?>  <performance>
          <index id="EAFE,C,36">
            <asOf>
              <date>03/11/2016</date>
              <value>1.644.941</value>
            </asOf>
          </index>
        </performance>"""

        with self.assertRaises(ParseError):
            list(parser.parse(invalid_xml, tzinfo=None))


class TestMsciIndexInfoParser(unittest.TestCase):

    def test_parse_success(self):
        expected_result = [IndexInfo(index_id='2670', name='AC AMERICAS')]

        expected_name, expected_id = expected_result[0].name, expected_result[0].index_id

        xml = f"""<?xml version="1.0" ?><indices><index id="{expected_id}" name="{expected_name}" /></indices>
        """

        parser = MsciIndexInfoParser()

        result = list(parser.parse(xml))

        self.assertSequenceEqual(result, expected_result)

    def test_parse_raisesEmptyList(self):
        xml = """<?xml version="1.0" ?><indices></indices>"""

        parser = MsciIndexInfoParser()

        with self.assertRaises(ParseError):
            list(parser.parse(xml))

    def test_parse_raisesWithoutName(self):
        xml = """<?xml version="1.0" ?><indices><index id="2670" /></indices>"""

        parser = MsciIndexInfoParser()

        with self.assertRaises(ParseError):
            list(parser.parse(xml))

    def test_parse_raisesWithoutId(self):
        xml = """<?xml version="1.0" ?><indices><index name="AC AMERICAS" /></indices>"""

        parser = MsciIndexInfoParser()

        with self.assertRaises(ParseError):
            list(parser.parse(xml))

    def test_parse_raisesWrongTagName(self):
        xml = """<?xml version="1.0" ?><WRONG_TAG><index id="2670" name="AC AMERICAS" /></WRONG_TAG>"""

        parser = MsciIndexInfoParser()

        with self.assertRaises(ParseError):
            list(parser.parse(xml))

    def test_parse_raisesEmptyString(self):
        xml = ''

        parser = MsciIndexInfoParser()

        with self.assertRaises(ParseError):
            list(parser.parse(xml))
