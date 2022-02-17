#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Utilities for parse data from www.ishares.com
"""

import datetime
import decimal
import json
import logging
import re
import typing

from .meta import ProductInfo, PerformanceValue, InfoFieldNames
from ...base import InstrumentValuesHistoryParser, InstrumentInfoParser, ParseError

logging.getLogger().addHandler(logging.NullHandler())


def make_date_from_iso_int(date_as_int: int) -> datetime.date:
    """ Make date from ISO format number

    Example::

        d = make_date_from_iso_int(20201231)
        # d == datetime.date(2020, 12, 31)

    :param date_as_int: Integer value of date
    :return: Date object
    """
    year = int(date_as_int / 10000)
    month = int((date_as_int - year * 10000) / 100)
    day = date_as_int - year * 10000 - month * 100

    result = datetime.date(year, month, day)
    return result


def _extract_field(
        src_dict: typing.Dict,
        field_name: str,
        type_to_check: typing.Optional[typing.Type] = None) -> typing.Any:
    if field_name not in src_dict:
        raise ParseError(f"Wrong JSON format. Has no '{field_name}' field.")

    result = src_dict[field_name]

    if type_to_check is not None:
        if not isinstance(result, type_to_check):
            raise ParseError(f"Wrong JSON format. Field {field_name!r} is not {type_to_check}.")

    return result


class ISharesHistoryHtmlParser(InstrumentValuesHistoryParser):
    """ Parser for history data of instrument from HTML string.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

    def _convert_to_int(self, str_to_convert: str, field_name: str) -> int:
        try:
            int_value = int(str_to_convert)
        except ValueError as ex:
            self.logger.error(f"Can't convert {field_name!r} value {str_to_convert!r} to int")
            raise ParseError(f"Unexpected HTML format. "
                             f"Can't convert {field_name!r} value {str_to_convert!r} to int") from ex

        return int_value

    def parse(  # pylint: disable=arguments-renamed
            self,
            html: str,
            tzinfo: typing.Optional[datetime.timezone]
    ) -> typing.Iterable[PerformanceValue]:

        performance_data_pattern = re.compile(
            r'var\s*?performanceData\s*?=\s*?\[(?P<performanceData>.*?)]\s*?;',
            re.IGNORECASE | re.MULTILINE | re.DOTALL
        )
        performance_data_item_pattern = re.compile(
            r'{.*?}',
            re.IGNORECASE | re.MULTILINE | re.DOTALL
        )
        date_pattern = re.compile(
            r'Date.UTC\s*?\(\s*?(?P<year>\d*?)\s*?,\s*?(?P<month>\d*?)\s*?,\s*?(?P<day>\d*?)\s*?\)',
            re.IGNORECASE | re.MULTILINE | re.DOTALL
        )
        value_pattern = re.compile(
            r'Number\s*?\(\s*?\(\s*?(?P<value>.*?)\s*?\)',
            re.IGNORECASE | re.MULTILINE | re.DOTALL
        )

        has_any = False
        m_performance_data = performance_data_pattern.search(html)
        if m_performance_data is not None:
            performance_data_str = m_performance_data.group()
            for m_performance_data_item in performance_data_item_pattern.finditer(performance_data_str):
                performance_data_item_str = m_performance_data_item.group()

                m_date_pattern = date_pattern.search(performance_data_item_str)
                if m_date_pattern is None:
                    self.logger.error(f"Not found date in HTML {performance_data_item_str!r}")
                    raise ParseError(f"Unexpected HTML format. "
                                     f"Not found date in HTML {performance_data_item_str!r}")

                m_value_pattern = value_pattern.search(performance_data_item_str)
                if m_value_pattern is None:
                    self.logger.error(f"Not found value in HTML {performance_data_item_str!r}")
                    raise ParseError(f"Unexpected HTML format. "
                                     f"Not found value in HTML {performance_data_item_str!r}")

                year_str = m_date_pattern.group('year')
                month_str = m_date_pattern.group('month')
                day_str = m_date_pattern.group('day')
                value_str = m_value_pattern.group('value')

                year = self._convert_to_int(year_str, 'year')
                month = self._convert_to_int(month_str, 'month') + 1
                day = self._convert_to_int(day_str, 'day')

                try:
                    value_date = datetime.date(year, month, day)
                except (ValueError, OverflowError) as ex:
                    self.logger.error(f"Can't create date from {m_date_pattern.group()!r}")
                    raise ParseError(f"Unexpected HTML format. "
                                     f"Can't create date from {m_date_pattern.group()!r}") from ex

                try:
                    value = decimal.Decimal(value_str)
                except decimal.DecimalException as ex:
                    self.logger.error(f"Can't convert value {value_str!r} to decimal")
                    raise ParseError(f"Unexpected HTML format. "
                                     f"Can't convert value {value_str!r} to decimal") from ex

                has_any = True
                yield PerformanceValue(date=value_date, value=value)

        if not has_any:
            self.logger.error(f"No data found in HTML:\n{html}")
            raise ParseError("Unexpected HTML format. No data found")


class ISharesInfoJsonParser(InstrumentInfoParser):
    """ Parser for info data from JSON string.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

    def parse(self, raw_json_text: str) -> typing.Iterable[ProductInfo]:  # pylint: disable=arguments-renamed

        try:
            raw_data = json.loads(raw_json_text)
        except json.decoder.JSONDecodeError as ex:
            raise ParseError(ex.msg) from ex

        if not isinstance(raw_data, dict):
            # can be Inf etc., but we accept only {}
            raise ParseError("Wrong JSON format. Top level is not dict.")

        for instrument_item in raw_data.values():
            if not isinstance(instrument_item, dict):
                raise ParseError("Wrong JSON format. Items are not dict.")

            local_exchange_ticker = _extract_field(instrument_item, InfoFieldNames.LOCAL_EXCHANGE_TICKER.value)
            isin = _extract_field(instrument_item, InfoFieldNames.ISIN.value)
            fund_name = _extract_field(instrument_item, InfoFieldNames.FUND_NAME.value)
            product_page_url = _extract_field(instrument_item, InfoFieldNames.PRODUCT_PAGE_URL.value)

            inception_date_data = _extract_field(instrument_item, InfoFieldNames.INCEPTION_DATE.value, dict)
            inception_date_r = _extract_field(inception_date_data, InfoFieldNames.INCEPTION_DATE_R.value)
            try:
                inception_date_as_int = int(inception_date_r)
            except (ValueError, TypeError) as ex:
                self.logger.error(f"Can't convert {inception_date_r!r} to int")
                raise ParseError(f"Unexpected HTML format. "
                                 f"Can't convert {inception_date_r!r} to int") from ex

            try:
                inception_date = make_date_from_iso_int(inception_date_as_int)
            except ValueError as ex:
                self.logger.error(f"Can't create date from {inception_date_r}")
                raise ParseError(f"Unexpected HTML format. "
                                 f"Can't create date from {inception_date_r}") from ex

            yield ProductInfo(
                local_exchange_ticker=local_exchange_ticker,
                isin=isin,
                fund_name=fund_name,
                inception_date=inception_date,
                product_page_url=product_page_url)
