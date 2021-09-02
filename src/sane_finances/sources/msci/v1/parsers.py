#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Utilities for parse data from app2.msci.com
"""

import decimal
import logging
import typing
from xml.etree import ElementTree
import datetime

from .meta import IndexValue, IndexInfo, Styles, Sizes
from ...base import InstrumentValuesHistoryParser, InstrumentInfoParser, ParseError


logging.getLogger().addHandler(logging.NullHandler())


class MsciHistoryXmlParser(InstrumentValuesHistoryParser):
    """ Parser for history data of index from XML string.

    E.g.::

      <?xml version="1.0" ?>
      <performance>
        <index id="EAFE,C,36">
          <asOf>
            <date>03/11/2016</date>
            <value>1,644.941</value>
          </asOf>
          ...
        </index>
      </performance>
    """
    RootTag = 'performance'
    date_format = '%m/%d/%Y'

    def __init__(self):
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

    def parse(  # pylint: disable=arguments-renamed
            self,
            raw_xml_text: str,
            tzinfo: typing.Optional[datetime.timezone]
    ) -> typing.Iterable[IndexValue]:

        try:
            root = ElementTree.fromstring(raw_xml_text)
        except ElementTree.ParseError as ex:
            raise ParseError(ex.msg) from ex

        expected_tag = self.RootTag
        if root.tag != expected_tag:
            raise ParseError(f"Wrong XML format. Root ('{root.tag}') is not '{expected_tag}'.")

        has_any = False
        for index_element in root.iterfind('./index'):
            str_id: str = index_element.attrib['id']

            self.logger.debug(f"Got index '{str_id}'")

            index_id_parts = str_id.split(',')
            if len(index_id_parts) != 3:
                raise ParseError(f"Wrong XML format. Unexpected index ID: '{str_id}'.")

            index_name, index_style, index_size = index_id_parts

            # see https://github.com/PyCQA/pylint/issues/1801 for pylint disable hint details
            index_style, index_size = Styles(index_style), Sizes(index_size)  # pylint: disable=no-value-for-parameter

            for data_element in index_element.iterfind('./asOf'):

                # get last item
                date_raw_text = None
                for date_element in data_element.iterfind('./date'):
                    date_raw_text = date_element.text

                # get last item
                value_raw_text = None
                for value in data_element.iterfind('./value'):
                    value_raw_text = value.text

                self.logger.debug(f"Got {date_raw_text!r} -> {value_raw_text!r}")

                if date_raw_text is None:
                    raise ParseError(f"Wrong XML format. Not found date tag in\n{ElementTree.tostring(data_element)}")
                if value_raw_text is None:
                    raise ParseError(f"Wrong XML format. Not found value tag in\n{ElementTree.tostring(data_element)}")

                try:
                    value_date = datetime.datetime.strptime(date_raw_text, self.date_format)
                except (ValueError, TypeError) as ex:
                    raise ParseError(f"Wrong XML format."
                                     f"Not valid date: {date_raw_text!r}") from ex

                value_date = value_date.date()

                try:
                    value = decimal.Decimal(value_raw_text.replace(',', '').replace(' ', ''))
                except (ValueError, TypeError, decimal.DecimalException) as ex:
                    raise ParseError(f"Wrong XML format."
                                     f"Not valid value: {value_raw_text!r}") from ex

                has_any = True
                yield IndexValue(
                    date=value_date,
                    value=value,
                    index_name=index_name,
                    style=index_style,
                    size=index_size)

        if not has_any:
            # empty sequence make no sense: there always must be history
            raise ParseError("Wrong XML format. Data not found.")


class MsciIndexInfoParser(InstrumentInfoParser):
    """ Parser for indexes info list from XML.

    E.g.::

        <?xml version="1.0" ?><indices><index id="2670" name="AC AMERICAS" />...</indices>
    """

    RootTag = 'indices'

    def __init__(self):
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

    def parse(self, raw_xml_text: str) -> typing.Iterable[IndexInfo]:  # pylint: disable=arguments-renamed
        raw_xml_text = raw_xml_text.replace('&', '&amp;')  # yes, it can contain symbol & inside 'name' attribute
        try:
            root = ElementTree.fromstring(raw_xml_text)
        except ElementTree.ParseError as ex:
            raise ParseError(ex.msg) from ex

        expected_tag = self.RootTag
        if root.tag != expected_tag:
            raise ParseError(f"Wrong XML format. Root ('{root.tag}') is not '{expected_tag}'.")

        id_tag = 'id'
        name_tag = 'name'

        has_any = False
        for data_element in root.iterfind('./index'):

            if id_tag not in data_element.attrib:
                self.logger.error(f"Index ID not found in\n{ElementTree.tostring(data_element)}")
                raise ParseError("Unexpected XML format. Index ID not found")

            if name_tag not in data_element.attrib:
                self.logger.error(f"Index name not found in\n{ElementTree.tostring(data_element)}")
                raise ParseError("Unexpected XML format. Index name not found")

            index_id = data_element.attrib[id_tag]
            index_name = data_element.attrib[name_tag]

            has_any = True
            yield IndexInfo(index_id=index_id, name=index_name)

        if not has_any:
            self.logger.error(f"No data found in XML:\n{raw_xml_text}")
            raise ParseError("Unexpected XML format. No data found")
