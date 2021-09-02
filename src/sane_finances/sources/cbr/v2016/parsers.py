#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Utilities for parse data from cbr.ru.
"""

import decimal
import logging
import typing
from xml.etree import ElementTree
import datetime

from .meta import CurrencyRateValue, CurrencyInfo
from ...base import InstrumentValuesHistoryParser, InstrumentInfoParser, ParseError

logging.getLogger().addHandler(logging.NullHandler())


def _get_xml_last_item_text(element: ElementTree.Element, path: str) -> typing.Optional[str]:
    # get last item
    text = None
    for value in element.iterfind(path):
        text = value.text
    return text


class CbrCurrencyHistoryXmlParser(InstrumentValuesHistoryParser):
    """ Parser for history data of currency from XML string.

    E.g.::

        <ValCurs ID="R01235" DateRange1="02.03.2001" DateRange2="14.03.2001" name="Foreign Currency Market Dynamic">
            <Record Date="02.03.2001" Id="R01235">
                <Nominal>1</Nominal>
                <Value>28,6200</Value>
            </Record>
            ...
        </ValCurs>
    """
    RootTag = 'ValCurs'
    date_format = '%d.%m.%Y'

    def __init__(self):
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

    def parse(  # pylint: disable=arguments-renamed
            self,
            raw_xml_text: str,
            tzinfo: typing.Optional[datetime.timezone]
    ) -> typing.Iterable[CurrencyRateValue]:

        try:
            root = ElementTree.fromstring(raw_xml_text)
        except ElementTree.ParseError as ex:
            raise ParseError(ex.msg) from ex

        expected_tag = self.RootTag
        if root.tag != expected_tag:
            raise ParseError(f"Wrong XML format. Root ('{root.tag}') is not '{expected_tag}'.")

        id_tag = 'Id'
        date_tag = 'Date'

        for record_element in root.iterfind('./Record'):
            if id_tag not in record_element.attrib:
                raise ParseError(f"Wrong XML format. "
                                 f"Not found {id_tag} attrib in\n{ElementTree.tostring(record_element)}")
            if date_tag not in record_element.attrib:
                raise ParseError(f"Wrong XML format. "
                                 f"Not found {date_tag} attrib in\n{ElementTree.tostring(record_element)}")

            currency_id: str = record_element.attrib[id_tag]
            self.logger.debug(f"Got currency '{currency_id}'")

            date_raw_text: str = record_element.attrib[date_tag]
            value_raw_text = _get_xml_last_item_text(record_element, './Value')
            nominal_raw_text = _get_xml_last_item_text(record_element, './Nominal')

            self.logger.debug(f"Got {date_raw_text!r} -> {value_raw_text!r}/{nominal_raw_text!r}")

            if nominal_raw_text is None:
                raise ParseError(f"Wrong XML format. "
                                 f"Not found Nominal tag in\n{ElementTree.tostring(record_element)}")
            if value_raw_text is None:
                raise ParseError(f"Wrong XML format. "
                                 f"Not found Value tag in\n{ElementTree.tostring(record_element)}")

            value_date = datetime.datetime.strptime(date_raw_text, self.date_format).date()
            value = decimal.Decimal(value_raw_text.replace(',', '.'))
            nominal = int(nominal_raw_text)

            yield CurrencyRateValue(date=value_date, value=value, nominal=nominal, currency_id=currency_id)


class CbrCurrencyInfoParser(InstrumentInfoParser):
    """ Parser for indexes info list from XML.

    E.g.::

        <Valuta name="Foreign Currency Market Lib">
            <Item ID="R01010">
                <Name>Австралийский доллар</Name>
                <EngName>Australian Dollar</EngName>
                <Nominal>1</Nominal>
                <ParentCode>R01010 </ParentCode>
            </Item>
            ...
        </Valuta>
    """

    RootTag = 'Valuta'

    def __init__(self):
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

    def parse(self, raw_xml_text: str) -> typing.Iterable[CurrencyInfo]:  # pylint: disable=arguments-renamed
        try:
            root = ElementTree.fromstring(raw_xml_text)
        except ElementTree.ParseError as ex:
            raise ParseError(ex.msg) from ex

        expected_tag = self.RootTag
        if root.tag != expected_tag:
            raise ParseError(f"Wrong XML format. Root ('{root.tag}') is not '{expected_tag}'.")

        id_tag = 'ID'

        has_any = False
        for item_element in root.iterfind('./Item'):

            if id_tag not in item_element.attrib:
                self.logger.error(f"Currency ID not found in\n{ElementTree.tostring(item_element)}")
                raise ParseError("Unexpected XML format. Currency ID not found")

            currency_id = item_element.attrib[id_tag]
            name = _get_xml_last_item_text(item_element, './Name')
            eng_name = _get_xml_last_item_text(item_element, './EngName')
            nominal_raw_text = _get_xml_last_item_text(item_element, './Nominal')
            parent_code = _get_xml_last_item_text(item_element, './ParentCode')

            if name is None:
                raise ParseError(f"Wrong XML format. "
                                 f"Not found Name tag in\n{ElementTree.tostring(item_element)}")
            if eng_name is None:
                raise ParseError(f"Wrong XML format. "
                                 f"Not found EngName tag in\n{ElementTree.tostring(item_element)}")
            if nominal_raw_text is None:
                raise ParseError(f"Wrong XML format. "
                                 f"Not found Nominal tag in\n{ElementTree.tostring(item_element)}")
            if parent_code is None:
                raise ParseError(f"Wrong XML format. "
                                 f"Not found ParentCode tag in\n{ElementTree.tostring(item_element)}")

            parent_code = parent_code.strip()
            nominal = int(nominal_raw_text)

            has_any = True
            yield CurrencyInfo(
                currency_id=currency_id,
                name=name,
                eng_name=eng_name,
                nominal=nominal,
                parent_code=parent_code)

        if not has_any:
            self.logger.error(f"No data found in XML:\n{raw_xml_text}")
            raise ParseError("Unexpected XML format. No data found")
