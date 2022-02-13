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

        if QuoteHistoryFieldNames.CHART.value not in raw_data:
            raise ParseError(f"Wrong JSON format. Has no '{QuoteHistoryFieldNames.CHART.value}' field.")

        raw_data = raw_data[QuoteHistoryFieldNames.CHART.value]

        error_data = raw_data.get(QuoteHistoryFieldNames.ERROR.value, None)
        if error_data is not None:
            error_code = raw_data.get(QuoteHistoryFieldNames.ERROR_CODE.value, '')
            error_description = raw_data.get(QuoteHistoryFieldNames.ERROR_DESCRIPTION.value, '')
            raise ParseError(f"Source returned error: {error_code} {error_description}")

        if QuoteHistoryFieldNames.RESULT.value not in raw_data:
            raise ParseError(f"Wrong JSON format. Has no '{QuoteHistoryFieldNames.RESULT.value}' field.")

        result_data = raw_data[QuoteHistoryFieldNames.RESULT.value]
        if not isinstance(result_data, list):
            raise ParseError(f"Wrong JSON format. Field {QuoteHistoryFieldNames.RESULT.value!r} is not list.")
        if len(result_data) == 0:
            raise ParseError(f"Wrong JSON format. Field {QuoteHistoryFieldNames.RESULT.value!r} is empty.")

        result_data = result_data[0]
        if not isinstance(result_data, dict):
            raise ParseError(f"Wrong JSON format. Items in {QuoteHistoryFieldNames.RESULT.value!r} are not dict.")

        if QuoteHistoryFieldNames.META.value not in result_data:
            raise ParseError(f"Wrong JSON format. Has no '{QuoteHistoryFieldNames.META.value}' field.")
        meta_dict = result_data[QuoteHistoryFieldNames.META.value]
        if not isinstance(meta_dict, dict):
            raise ParseError(f"Wrong JSON format. Items in {QuoteHistoryFieldNames.META.value!r} are not dict.")
        if QuoteHistoryFieldNames.SYMBOL.value not in meta_dict:
            raise ParseError(f"Wrong JSON format. Has no '{QuoteHistoryFieldNames.SYMBOL.value}' field.")
        symbol = meta_dict[QuoteHistoryFieldNames.SYMBOL.value]

        if QuoteHistoryFieldNames.TIMESTAMP.value not in result_data:
            raise ParseError(f"Wrong JSON format. Has no '{QuoteHistoryFieldNames.TIMESTAMP.value}' field.")

        timestamps = result_data[QuoteHistoryFieldNames.TIMESTAMP.value]
        if not isinstance(timestamps, list):
            raise ParseError(f"Wrong JSON format. Field {QuoteHistoryFieldNames.TIMESTAMP.value!r} is not list.")

        if QuoteHistoryFieldNames.INDICATORS.value not in result_data:
            raise ParseError(f"Wrong JSON format. Has no '{QuoteHistoryFieldNames.INDICATORS.value}' field.")

        indicators = result_data[QuoteHistoryFieldNames.INDICATORS.value]
        if not isinstance(indicators, dict):
            raise ParseError(f"Wrong JSON format. Field {QuoteHistoryFieldNames.INDICATORS.value!r} is not dict.")

        if QuoteHistoryFieldNames.QUOTE.value not in indicators:
            raise ParseError(f"Wrong JSON format. Has no '{QuoteHistoryFieldNames.QUOTE.value}' field.")
        quote_data = indicators[QuoteHistoryFieldNames.QUOTE.value]
        if not isinstance(quote_data, list):
            raise ParseError(f"Wrong JSON format. Field {QuoteHistoryFieldNames.QUOTE.value!r} is not list.")
        if len(quote_data) == 0:
            raise ParseError(f"Wrong JSON format. Field {QuoteHistoryFieldNames.QUOTE.value!r} is empty.")

        quote_data = quote_data[0]
        if not isinstance(quote_data, dict):
            raise ParseError(f"Wrong JSON format. Items in {QuoteHistoryFieldNames.QUOTE.value!r} are not dict.")
        if QuoteHistoryFieldNames.CLOSE.value not in quote_data:
            raise ParseError(f"Wrong JSON format. Has no '{QuoteHistoryFieldNames.CLOSE.value}' field.")

        closes = quote_data[QuoteHistoryFieldNames.CLOSE.value]
        if not isinstance(closes, list):
            raise ParseError(f"Wrong JSON format. Field {QuoteHistoryFieldNames.CLOSE.value!r} is not list.")

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
                error_code = finance_data.get(SearchInfoFieldNames.ERROR_CODE.value, '')
                error_description = finance_data.get(SearchInfoFieldNames.ERROR_DESCRIPTION.value, '')
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
