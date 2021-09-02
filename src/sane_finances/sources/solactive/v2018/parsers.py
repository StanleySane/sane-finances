#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Utilities for parse data from solactive.com
"""

import json
import decimal
import datetime
import logging
import re
import typing

from .meta import IndexInfo, IndexValue, FieldNames
from ...base import InstrumentValuesHistoryParser, InstrumentInfoParser, ParseError

logging.getLogger().addHandler(logging.NullHandler())


class SolactiveJsonParser(InstrumentValuesHistoryParser):
    """ Parser for history data of index from JSON string.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

    def parse(  # pylint: disable=arguments-renamed
            self,
            raw_json_text: str,
            tzinfo: typing.Optional[datetime.timezone]
    ) -> typing.Iterable[IndexValue]:

        try:
            raw_data = json.loads(raw_json_text)
        except json.decoder.JSONDecodeError as ex:
            raise ParseError(ex.msg) from ex

        if not isinstance(raw_data, list):
            # can be Inf etc., but we accept only []
            raise ParseError("Wrong JSON format. Top level is not list.")

        if len(raw_data) == 0:
            # empty list make no sense: there always must be history
            raise ParseError("Empty JSON")

        first_date = datetime.datetime(1970, 1, 1, tzinfo=tzinfo)

        for json_item in raw_data:
            if not isinstance(json_item, dict):
                raise ParseError("Wrong JSON format. Item level is not dict.")

            for field_name in (FieldNames.INDEX_ID.value, FieldNames.TIMESTAMP.value, FieldNames.VALUE.value):
                if field_name not in json_item:
                    raise ParseError(f"Wrong JSON format. Has no '{field_name}' field.")

            moment = first_date + datetime.timedelta(milliseconds=json_item[FieldNames.TIMESTAMP.value])

            # convert from float to Decimal
            str_value = "%.4f" % json_item[FieldNames.VALUE.value]
            value = decimal.Decimal(str_value)

            self.logger.debug(f"Converted value from {json_item[FieldNames.VALUE.value]} to {value}")

            yield IndexValue(index_id=json_item[FieldNames.INDEX_ID.value], moment=moment, value=value)


class SolactiveIndexInfoParser(InstrumentInfoParser):
    """ Parser for indexes info list from HTML.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

    def parse(self, html: str) -> typing.Iterable[IndexInfo]:  # pylint: disable=arguments-renamed
        table_pattern = re.compile(
            r"<tbody.*?>(?P<table>.*?)</tbody.*?>",
            re.IGNORECASE | re.MULTILINE | re.DOTALL
        )
        row_pattern = re.compile(
            r".*?<tr.*?>(?P<row>.*?)</tr.*?>.*?",
            re.IGNORECASE | re.MULTILINE | re.DOTALL
        )
        cell_pattern = re.compile(
            r"<td.*?class=\"(?P<class_name>.*?)\".*?>(?P<cell>.*?)</td.*?>",
            re.IGNORECASE | re.MULTILINE | re.DOTALL
        )
        name_cell_pattern = re.compile(
            r".*?<a.*?>(?P<name>.*?)</a.*?>.*?",
            re.IGNORECASE | re.MULTILINE | re.DOTALL
        )

        has_any = False
        for m_table in table_pattern.finditer(html):
            for m_row in row_pattern.finditer(m_table.group("table")):
                row = m_row.group("row")

                name = None
                isin = None

                for m_cell in cell_pattern.finditer(row):
                    class_name = m_cell.group("class_name")
                    cell = m_cell.group("cell")

                    if class_name == "name":
                        m_name = name_cell_pattern.match(cell)
                        if m_name:
                            name = m_name.group("name")

                    elif class_name == "isin":
                        isin = cell

                if name is None:
                    self.logger.error(f"Index name not found in {row!r}")
                    raise ParseError("Unexpected HTML format. Index name not found")

                if isin is None:
                    self.logger.error(f"Index ISIN not found in {row!r}")
                    raise ParseError("Unexpected HTML format. Index ISIN not found")

                has_any = True
                yield IndexInfo(name=name, isin=isin)

        if not has_any:
            self.logger.error(f"No data found in HTML:\n{html}")
            raise ParseError("Unexpected HTML format. No data found")
