#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Utilities for parse data from https://www.spglobal.com/spdji/
"""

import json
import decimal
import datetime
import logging
import re
import typing

from .meta import (
    IndexInfo, IndexLevel, Currency, ReturnType, HistoryFieldNames, InfoFieldNames, IndexMetaData,
    IndexFinderFilterGroup, IndexFinderFilter)
from ...base import (
    InstrumentValuesHistoryParser, InstrumentInfoParser, ParseError, InstrumentInfoEmpty)

logging.getLogger().addHandler(logging.NullHandler())


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


class SpdjHistoryJsonParser(InstrumentValuesHistoryParser):
    """ Parser for history data of index from JSON string.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

    # noinspection PyMethodMayBeStatic
    def convert_float_to_decimal(self, float_value: float):
        """ Convert float value to decimal value.

        :param float_value: Value to convert
        :return: Decimal value.
        """
        if isinstance(float_value, float):
            str_value = f"{float_value:.8f}"
        else:
            str_value = str(float_value)
        try:
            value = decimal.Decimal(str_value)
        except decimal.DecimalException as ex:
            raise ParseError(f"Can't convert value {float_value!r} to decimal") from ex

        return value

    # noinspection PyMethodMayBeStatic
    def convert_unix_moment_to_datetime(self, unix_moment: int, tzinfo: typing.Optional[datetime.timezone]):
        """ Convert UNIX epoch moment to Python datetime

        :param unix_moment: UNIX epoch moment
        :param tzinfo: Timezone of result datetime
        :return: Python datetime
        """
        first_date = datetime.datetime(1970, 1, 1, tzinfo=tzinfo)
        try:
            moment = first_date + datetime.timedelta(milliseconds=unix_moment)
        except (TypeError, OverflowError) as ex:
            raise ParseError(f"Can't convert value {unix_moment!r} to timedelta milliseconds") from ex
        return moment

    def parse(  # pylint: disable=arguments-renamed
            self,
            raw_json_text: str,
            tzinfo: typing.Optional[datetime.timezone]
    ) -> typing.Iterable[IndexLevel]:

        try:
            raw_data = json.loads(raw_json_text)
        except json.decoder.JSONDecodeError as ex:
            raise ParseError(ex.msg) from ex

        if not isinstance(raw_data, dict):
            # can be Inf etc., but we accept only {}
            raise ParseError("Wrong JSON format. Top level is not dict.")

        detail_holder = _extract_field(raw_data, HistoryFieldNames.DETAIL_HOLDER.value, dict)
        status = _extract_field(detail_holder, HistoryFieldNames.STATUS.value)
        if not status:
            service_messages = _extract_field(detail_holder, HistoryFieldNames.SERVICE_MESSAGES.value) or []
            error_message = ','.join(service_messages)
            raise ParseError(f"Source returned errors: {error_message}")

        levels_holder = _extract_field(raw_data, HistoryFieldNames.LEVELS_HOLDER.value, dict)
        status = _extract_field(levels_holder, HistoryFieldNames.STATUS.value)
        if not status:
            service_messages = _extract_field(levels_holder, HistoryFieldNames.SERVICE_MESSAGES.value) or []
            error_message = ','.join(service_messages)
            raise ParseError(f"Source returned errors: {error_message}")

        levels = _extract_field(levels_holder, HistoryFieldNames.LEVELS.value, list)
        for level_dict in levels:
            if not isinstance(level_dict, dict):
                raise ParseError(f"Wrong JSON format. Items in {HistoryFieldNames.LEVELS.value!r} are not dict.")

            effective_date = _extract_field(level_dict, HistoryFieldNames.EFFECTIVE_DATE.value)
            index_id = _extract_field(level_dict, HistoryFieldNames.INDEX_ID.value)
            index_value = _extract_field(level_dict, HistoryFieldNames.INDEX_VALUE.value)

            moment = self.convert_unix_moment_to_datetime(effective_date, tzinfo)
            value = self.convert_float_to_decimal(index_value)

            yield IndexLevel(index_id=index_id, effective_date=moment, index_value=value)


class SpdjMetaJsonParser:
    """ Parser for meta information from JSON string.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

    def parse(self, raw_json_text: str) -> IndexMetaData:
        """ Parse JSON with metadata

        :param raw_json_text: JSON with metadata
        :return: ``IndexMetaData`` with ``currencies`` and ``return_types`` members filled.
         ``index_finder_filters`` remains empty because JSON not contains such data.
         Use ``SpdjIndexFinderFiltersParser`` to get ``index_finder_filters`` member.
        """

        try:
            raw_data = json.loads(raw_json_text)
        except json.decoder.JSONDecodeError as ex:
            raise ParseError(ex.msg) from ex

        if not isinstance(raw_data, dict):
            # can be Inf etc., but we accept only {}
            raise ParseError("Wrong JSON format. Top level is not dict.")

        detail_holder = _extract_field(raw_data, HistoryFieldNames.DETAIL_HOLDER.value, dict)
        status = _extract_field(detail_holder, HistoryFieldNames.STATUS.value)
        if not status:
            service_messages = _extract_field(detail_holder, HistoryFieldNames.SERVICE_MESSAGES.value) or []
            error_message = ','.join(service_messages)
            self.logger.error(f"Source returned errors: {error_message}")
            raise ParseError(f"Source returned errors: {error_message}")

        currency_holder = _extract_field(raw_data, HistoryFieldNames.CURRENCY_HOLDER.value, list)
        if len(currency_holder) == 0:
            raise ParseError(f"Wrong JSON format. Field {HistoryFieldNames.CURRENCY_HOLDER.value!r} is empty.")

        currencies: typing.List[Currency] = []
        for currency_data in currency_holder:
            if not isinstance(currency_data, dict):
                raise ParseError(f"Wrong JSON format. "
                                 f"Items in {HistoryFieldNames.CURRENCY_HOLDER.value!r} are not dict.")

            currency_code = _extract_field(currency_data, HistoryFieldNames.CURRENCY_CODE.value)
            currency = Currency.safe_create(currency_code=currency_code)
            currencies.append(currency)

        return_type_holder = _extract_field(raw_data, HistoryFieldNames.RETURN_TYPE_HOLDER.value, list)
        if len(return_type_holder) == 0:
            raise ParseError(f"Wrong JSON format. Field {HistoryFieldNames.RETURN_TYPE_HOLDER.value!r} is empty.")

        return_types: typing.List[ReturnType] = []
        for return_type_data in return_type_holder:
            if not isinstance(return_type_data, dict):
                raise ParseError(f"Wrong JSON format. "
                                 f"Items in {HistoryFieldNames.RETURN_TYPE_HOLDER.value!r} are not dict.")

            return_type_code = _extract_field(return_type_data, HistoryFieldNames.RETURN_TYPE_CODE.value)
            return_type_name = _extract_field(return_type_data, HistoryFieldNames.RETURN_TYPE_NAME.value)
            return_type = ReturnType.safe_create(return_type_code=return_type_code, return_type_name=return_type_name)
            return_types.append(return_type)

        return IndexMetaData(
            currencies=tuple(currencies),
            return_types=tuple(return_types),
            index_finder_filters=())


class SpdjInfoJsonParser(InstrumentInfoParser):
    """ Parser for info data from JSON string.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

    def parse(self, raw_json_text: str) -> typing.Iterable[IndexInfo]:  # pylint: disable=arguments-renamed

        try:
            raw_data = json.loads(raw_json_text)
        except json.decoder.JSONDecodeError as ex:
            raise ParseError(ex.msg) from ex

        if not isinstance(raw_data, dict):
            # can be Inf etc., but we accept only {}
            raise ParseError("Wrong JSON format. Top level is not dict.")

        response_data = _extract_field(raw_data, InfoFieldNames.RESPONSE.value, list)
        if len(response_data) == 0:
            raise InstrumentInfoEmpty()

        for response_item in response_data:
            if not isinstance(response_item, dict):
                raise ParseError(f"Wrong JSON format. Items in {InfoFieldNames.RESPONSE.value!r} are not dict.")

            index_id = _extract_field(response_item, InfoFieldNames.INDEX_ID.value)
            index_name = _extract_field(response_item, InfoFieldNames.INDEX_NAME.value)
            url = _extract_field(response_item, InfoFieldNames.URL_TITLE.value)

            yield IndexInfo(index_id=index_id, index_name=index_name, url=url)


class SpdjIndexFinderFiltersParser:
    """ Parser for indexes finder filters from HTML.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

    def parse(self, html: str) -> typing.Iterable[IndexFinderFilter]:
        """ Parse HTML and return index finder filters

        :param html: HTML to parse.
        :return: Iterable of ``IndexFinderFilter``.
        """

        group_pattern = re.compile(
            r'<div[^>]*?\sdata-fieldname\s*?=\s*?"(?P<field_name>[^"]*?)".*?>.*?'
            r'<\w*?[^>]*?\sdata-gtm-category\s*?=\s*?"Index Finder Filter".*?'
            r'\sdata-gtm-label\s*?=\s*?"(?P<label>[^"]*?)".*?>',
            re.IGNORECASE | re.MULTILINE | re.DOTALL
        )
        checkbox_pattern = re.compile(
            r'<input[^>]*?data-gtm-category\s*?=\s*?"Index Finder Filter"[^>]*?>',
            re.IGNORECASE | re.MULTILINE | re.DOTALL
        )
        checkbox_name_pattern = re.compile(
            r'\sname\s*?=\s*?"(?P<field_name>[^"]*?)"',
            re.IGNORECASE | re.MULTILINE | re.DOTALL
        )
        checkbox_label_pattern = re.compile(
            r'\sdata-gtm-label\s*?=\s*?"(?P<label>[^"]*?)"',
            re.IGNORECASE | re.MULTILINE | re.DOTALL
        )
        checkbox_value_pattern = re.compile(
            r'\svalue\s*?=\s*?"(?P<value>[^"]*?)"',
            re.IGNORECASE | re.MULTILINE | re.DOTALL
        )

        groups = {}
        for m_group in group_pattern.finditer(html):
            field_name = m_group.group('field_name')
            label = m_group.group('label')

            groups[field_name] = IndexFinderFilterGroup.safe_create(name=field_name, label=label)

        worked_values = {}
        has_any = False
        for m_checkbox in checkbox_pattern.finditer(html):
            checkbox_str = m_checkbox.group()

            m_checkbox_name_pattern = checkbox_name_pattern.search(checkbox_str)
            if m_checkbox_name_pattern is None:
                self.logger.error(f"Not found 'name' attribute in HTML {checkbox_str!r}")
                raise ParseError(f"Unexpected HTML format. "
                                 f"Not found 'name' attribute in HTML {checkbox_str!r}")

            m_checkbox_label_pattern = checkbox_label_pattern.search(checkbox_str)
            if m_checkbox_label_pattern is None:
                self.logger.error(f"Not found 'data-gtm-label' attribute in HTML {checkbox_str!r}")
                raise ParseError(f"Unexpected HTML format. "
                                 f"Not found 'data-gtm-label' attribute in HTML {checkbox_str!r}")

            m_checkbox_value_pattern = checkbox_value_pattern.search(checkbox_str)
            if m_checkbox_value_pattern is None:
                self.logger.error(f"Not found 'value' attribute in HTML {checkbox_str!r}")
                raise ParseError(f"Unexpected HTML format. "
                                 f"Not found 'value' attribute in HTML {checkbox_str!r}")

            field_name = m_checkbox_name_pattern.group('field_name')
            label = m_checkbox_label_pattern.group('label')
            value = m_checkbox_value_pattern.group('value')

            if not value:
                self.logger.info(f"'value' attribute in empty in HTML: {checkbox_str!r}")
                continue

            if field_name not in groups:
                self.logger.error(f"Index finder filter group {field_name!r} not found in HTML")
                raise ParseError(f"Unexpected HTML format. Index finder filter group {field_name!r} not found")

            if value in worked_values:
                self.logger.info(f"Index finder filter with value {value!r} for label {label} "
                                 f"already worked for label {worked_values[value]!r}")
                continue

            has_any = True
            worked_values[value] = label
            yield IndexFinderFilter.safe_create(group=groups[field_name], label=label, value=value)

        if not has_any:
            self.logger.error(f"No data found in HTML:\n{html}")
            raise ParseError("Unexpected HTML format. No data found")
