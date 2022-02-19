#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Utilities for parse data from www.bloomberg.com
"""

import datetime
import decimal
import json
import logging
import typing

from .meta import (
    HistoryFieldNames, InfoFieldNames, InstrumentPrice, BloombergInstrumentInfo)
from ...base import (
    InstrumentValuesHistoryParser, InstrumentInfoParser, ParseError)

logging.getLogger().addHandler(logging.NullHandler())


def _extract_field(
        src_dict: typing.Dict,
        field_name: str,
        type_to_check: typing.Optional[typing.Type] = None,
        required: bool = True) -> typing.Any:
    if field_name not in src_dict:
        if required:
            raise ParseError(f"Wrong JSON format. Has no '{field_name}' field.")

        return None

    result = src_dict[field_name]

    if type_to_check is not None:
        if not isinstance(result, type_to_check):
            raise ParseError(f"Wrong JSON format. Field {field_name!r} is not {type_to_check}.")

    return result


class BloombergHistoryJsonParser(InstrumentValuesHistoryParser):
    """ Parser for history data of instrument from JSON string.
    """
    date_format = '%Y-%m-%d'

    def __init__(self):
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

    # noinspection PyMethodMayBeStatic
    def convert_float_to_decimal(self, float_value: float):
        """ Convert float value to decimal value.

        :param float_value: Value to convert
        :return: Decimal value.
        """
        if isinstance(float_value, float):
            str_value = f"{float_value:.6f}"
        else:
            str_value = str(float_value)
        try:
            value = decimal.Decimal(str_value)
        except decimal.DecimalException as ex:
            raise ParseError(f"Can't convert value {float_value!r} to decimal") from ex

        return value

    def parse(  # pylint: disable=arguments-renamed
            self,
            raw_json_text: str,
            tzinfo: typing.Optional[datetime.timezone]
    ) -> typing.Iterable[InstrumentPrice]:

        try:
            raw_data = json.loads(raw_json_text)
        except json.decoder.JSONDecodeError as ex:
            raise ParseError(ex.msg) from ex

        if not isinstance(raw_data, list):
            raise ParseError("Wrong JSON format. Top level is not list.")

        has_any = False
        for item_data in raw_data:
            if not isinstance(item_data, dict):
                raise ParseError("Wrong JSON format. Data item is not dict.")

            ticker = str(_extract_field(item_data, HistoryFieldNames.TICKER.value))
            price_data = _extract_field(item_data, HistoryFieldNames.PRICE.value, list)

            for price_item in price_data:
                if not isinstance(price_item, dict):
                    raise ParseError("Wrong JSON format. Price item is not dict.")

                date_str = _extract_field(price_item, HistoryFieldNames.DATE_TIME.value)
                value_data = _extract_field(price_item, HistoryFieldNames.VALUE.value)

                try:
                    date = datetime.datetime.strptime(date_str, self.date_format).date()
                except (ValueError, TypeError, OverflowError) as ex:
                    raise ParseError(f"Wrong JSON format. Can't create date from {date_str!r}") from ex

                value = self.convert_float_to_decimal(value_data)

                has_any = True
                yield InstrumentPrice(ticker=ticker, price_date=date, price_value=value)

        if not has_any:
            raise ParseError("Wrong JSON format. Data not found.")


class BloombergInfoJsonParser(InstrumentInfoParser):
    """ Parser for info data from JSON string.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

    def parse(  # pylint: disable=arguments-renamed
            self,
            raw_json_text: str) -> typing.Iterable[BloombergInstrumentInfo]:

        try:
            raw_data = json.loads(raw_json_text)
        except json.decoder.JSONDecodeError as ex:
            raise ParseError(ex.msg) from ex

        if not isinstance(raw_data, dict):
            raise ParseError("Wrong JSON format. Top level is not dict.")

        results_data = _extract_field(raw_data, InfoFieldNames.RESULTS.value, list)
        for results_item in results_data:
            if not isinstance(results_item, dict):
                raise ParseError(f"Wrong JSON format. Items in {InfoFieldNames.RESULTS.value!r} are not dict.")

            ticker_symbol = _extract_field(results_item, InfoFieldNames.TICKER_SYMBOL.value)
            name = _extract_field(results_item, InfoFieldNames.NAME.value)
            country = _extract_field(results_item, InfoFieldNames.COUNTRY.value, required=False)
            resource_type = _extract_field(results_item, InfoFieldNames.RESOURCE_TYPE.value, required=False)
            resource_id = _extract_field(results_item, InfoFieldNames.RESOURCE_ID.value, required=False)
            security_type = _extract_field(results_item, InfoFieldNames.SECURITY_TYPE.value, required=False)
            url = _extract_field(results_item, InfoFieldNames.URL.value, required=False)

            yield BloombergInstrumentInfo(
                ticker_symbol=ticker_symbol,
                name=name,
                country=country,
                resource_type=resource_type,
                resource_id=resource_id,
                security_type=security_type,
                url=url)
