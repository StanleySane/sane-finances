#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Utilities for parse data from https://finance.yahoo.com/
"""

import datetime
import decimal
import json
import logging
import typing

from .meta import InstrumentQuoteInfo, InstrumentQuoteValue, SearchInfoFieldNames, QuoteHistoryFieldNames
from ...base import InstrumentValuesHistoryParser, InstrumentInfoParser, ParseError

logging.getLogger().addHandler(logging.NullHandler())


class YahooQuotesJsonParser(InstrumentValuesHistoryParser):
    """ Parser for history data of instrument from JSON string.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

    @staticmethod
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

    def parse(  # pylint: disable=arguments-renamed
            self,
            raw_json_text: str,
            tzinfo: typing.Optional[datetime.timezone]
    ) -> typing.Iterable[InstrumentQuoteValue]:

        try:
            raw_data = json.loads(raw_json_text)
        except json.decoder.JSONDecodeError as ex:
            raise ParseError(ex.msg) from ex

        if not isinstance(raw_data, dict):
            # can be Inf etc., but we accept only dict
            raise ParseError("Wrong JSON format. Top level is not dict.")

        raw_data = self._extract_field(raw_data, QuoteHistoryFieldNames.CHART.value)

        error_data = raw_data.get(QuoteHistoryFieldNames.ERROR.value, None)
        if error_data is not None:
            error_code = error_data.get(QuoteHistoryFieldNames.ERROR_CODE.value, '')
            error_description = error_data.get(QuoteHistoryFieldNames.ERROR_DESCRIPTION.value, '')
            raise ParseError(f"Source returned error: {error_code} {error_description}")

        result_data = self._extract_field(raw_data, QuoteHistoryFieldNames.RESULT.value, type_to_check=list)
        if len(result_data) == 0:
            raise ParseError(f"Wrong JSON format. Field {QuoteHistoryFieldNames.RESULT.value!r} is empty.")

        result_data = result_data[0]
        if not isinstance(result_data, dict):
            raise ParseError(f"Wrong JSON format. Items in {QuoteHistoryFieldNames.RESULT.value!r} are not dict.")

        meta_dict = self._extract_field(result_data, QuoteHistoryFieldNames.META.value, type_to_check=dict)
        symbol = self._extract_field(meta_dict, QuoteHistoryFieldNames.SYMBOL.value)

        timestamps = self._extract_field(result_data, QuoteHistoryFieldNames.TIMESTAMP.value, type_to_check=list)
        indicators = self._extract_field(result_data, QuoteHistoryFieldNames.INDICATORS.value, type_to_check=dict)

        quote_data = self._extract_field(indicators, QuoteHistoryFieldNames.QUOTE.value, type_to_check=list)
        if len(quote_data) == 0:
            raise ParseError(f"Wrong JSON format. Field {QuoteHistoryFieldNames.QUOTE.value!r} is empty.")

        quote_data = quote_data[0]
        if not isinstance(quote_data, dict):
            raise ParseError(f"Wrong JSON format. Items in {QuoteHistoryFieldNames.QUOTE.value!r} are not dict.")

        closes = self._extract_field(quote_data, QuoteHistoryFieldNames.CLOSE.value, type_to_check=list)

        if len(timestamps) != len(closes):
            raise ParseError(
                f"Wrong JSON format. "
                f"Length of timestamps ({len(timestamps)}) not equals to length of close values ({len(closes)})")

        first_date = datetime.datetime(1970, 1, 1, tzinfo=tzinfo)

        for timestamp, close_value in zip(timestamps, closes):
            moment = first_date + datetime.timedelta(seconds=timestamp)

            # convert from float to Decimal
            str_value = f"{close_value:.8f}"
            close_value = decimal.Decimal(str_value)

            yield InstrumentQuoteValue(symbol=symbol, timestamp=moment, close=close_value)


class YahooInstrumentInfoParser(InstrumentInfoParser):
    """ Parser for instruments info list from JSON.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

    def parse(self, raw_json_text: str, ) -> typing.Iterable[InstrumentQuoteInfo]:  # pylint: disable=arguments-renamed

        try:
            raw_data = json.loads(raw_json_text)
        except json.decoder.JSONDecodeError as ex:
            raise ParseError(ex.msg) from ex

        if not isinstance(raw_data, dict):
            raise ParseError("Wrong JSON format. Top level is not dict.")

        if SearchInfoFieldNames.FINANCE.value in raw_data:
            finance_data = raw_data[SearchInfoFieldNames.FINANCE.value]

            error_data = finance_data.get(SearchInfoFieldNames.ERROR.value, None)
            if error_data is not None:
                error_code = error_data.get(SearchInfoFieldNames.ERROR_CODE.value, '')
                error_description = error_data.get(SearchInfoFieldNames.ERROR_DESCRIPTION.value, '')
                raise ParseError(f"Source returned error: {error_code} {error_description}")

        if SearchInfoFieldNames.QUOTES.value not in raw_data:
            raise ParseError(f"Wrong JSON format. Has no '{SearchInfoFieldNames.QUOTES.value}' field.")

        quotes_data = raw_data[SearchInfoFieldNames.QUOTES.value]
        if not isinstance(quotes_data, list):
            raise ParseError(f"Wrong JSON format. Field {SearchInfoFieldNames.QUOTES.value!r} is not list.")

        for quote in quotes_data:
            if not isinstance(quote, dict):
                raise ParseError(f"Wrong JSON format. Item in {SearchInfoFieldNames.QUOTES.value!r} is not dict.")

            if SearchInfoFieldNames.SYMBOL.value not in quote:
                raise ParseError(f"Wrong JSON format. Has no '{SearchInfoFieldNames.SYMBOL.value}' field.")
            if SearchInfoFieldNames.EXCHANGE.value not in quote:
                raise ParseError(f"Wrong JSON format. Has no '{SearchInfoFieldNames.EXCHANGE.value}' field.")
            if SearchInfoFieldNames.SHORT_NAME.value not in quote:
                raise ParseError(f"Wrong JSON format. Has no '{SearchInfoFieldNames.SHORT_NAME.value}' field.")

            symbol = quote[SearchInfoFieldNames.SYMBOL.value]
            exchange = quote[SearchInfoFieldNames.EXCHANGE.value]
            short_name = quote[SearchInfoFieldNames.SHORT_NAME.value]
            long_name = quote.get(SearchInfoFieldNames.LONG_NAME.value, None)
            type_disp = quote.get(SearchInfoFieldNames.TYPE_DISP.value, None)
            exchange_disp = quote.get(SearchInfoFieldNames.EXCHANGE_DISP.value, None)
            is_yahoo_finance = quote.get(SearchInfoFieldNames.IS_YAHOO_FINANCE.value, False)

            yield InstrumentQuoteInfo(
                symbol=symbol,
                exchange=exchange,
                short_name=short_name,
                long_name=long_name,
                type_disp=type_disp,
                exchange_disp=exchange_disp,
                is_yahoo_finance=is_yahoo_finance)
