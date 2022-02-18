#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Utilities for parse data from www.lbma.org.uk
"""

import datetime
import decimal
import json
import logging
import typing

from .meta import (
    PreciousMetalPrice, PreciousMetalInfo, HistoryFieldNames, LbmaPreciousMetalHistoryDownloadParameters,
    PreciousMetals)
from ...base import InstrumentValuesHistoryParser, ParseError, InstrumentInfoParser

logging.getLogger().addHandler(logging.NullHandler())


class LbmaInfoParser(InstrumentInfoParser):
    """ Parser for instrument info list from meta-string.
    """
    def __init__(self):
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

    def parse(self, raw_text: str) -> typing.Iterable[PreciousMetalInfo]:
        return (PreciousMetalInfo(metal=metal) for metal in PreciousMetals)


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


class LbmaHistoryJsonParser(InstrumentValuesHistoryParser):
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
            str_value = f"{float_value:.2f}"
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
    ) -> typing.Iterable[PreciousMetalPrice]:

        if not isinstance(self.download_parameters, LbmaPreciousMetalHistoryDownloadParameters):
            raise ParseError(f"Wrong 'download_parameters' attribute value: {self.download_parameters}")
        currency = self.download_parameters.currency
        value_index = currency.history_position

        try:
            raw_data = json.loads(raw_json_text)
        except json.decoder.JSONDecodeError as ex:
            raise ParseError(ex.msg) from ex

        if not isinstance(raw_data, list):
            raise ParseError("Wrong JSON format. Top level is not list.")

        for item_data in raw_data:
            if not isinstance(item_data, dict):
                raise ParseError("Wrong JSON format. Data item is not dict.")

            date_str = _extract_field(item_data, HistoryFieldNames.DATE.value)
            values_data = _extract_field(item_data, HistoryFieldNames.VALUE.value, list)

            try:
                date = datetime.datetime.strptime(date_str, self.date_format).date()
            except (ValueError, TypeError, OverflowError) as ex:
                raise ParseError(f"Wrong JSON format. Can't create date from {date_str!r}") from ex

            if len(values_data) < value_index + 1:
                raise ParseError(f"Wrong JSON format. Values list has not enough values: {values_data!r}")

            value = self.convert_float_to_decimal(values_data[value_index])
            if value == 0:
                continue

            yield PreciousMetalPrice(date=date, value=value)
