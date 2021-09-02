#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Utilities for parse data from app2.msci.com
"""

import decimal
import json
import logging
import typing
import datetime

from .meta import (
    IndexValue, IndexInfo, Market, Size, Style, IndexSuite, IndexSuiteGroup, Frequency,
    Scopes, IndexLevel, Currency, IndexPanelData)
from ...base import (
    InstrumentValuesHistoryParser, InstrumentInfoParser, ParseError, SourceDownloadError,
    DownloadParameterValuesStorage, InstrumentValuesHistoryEmpty)

logging.getLogger().addHandler(logging.NullHandler())


class MsciHistoryJsonParser(InstrumentValuesHistoryParser):
    """ Parser for history data of index from JSON string.

    https://app2.msci.com/products/service/index/indexmaster/getLevelDataForGraph?currency_symbol=USD&index_variant=STRD&start_date=20170813&end_date=20210813&data_frequency=DAILY&index_codes=990300

    E.g.::

        {
            "msci_index_code":"990300",
            "index_variant_type":"STRD",
            "ISO_currency_symbol":"USD",
            "indexes":{
                "INDEX_LEVELS":[
                    {"level_eod":1892.970699,"calc_date":20170609},
                    {"level_eod":1886.335805,"calc_date":20170612},
                    ...
                    ]
            }
        }

    On error may return

    ::

     {
      "timestamp":"Aug 14, 2021 4:20:12 PM",
      "user":"sys_x_bmapip01",
      "error_code":" 100",
      "error_message":" null Invalid Parameter end_date : '19691231. Calculation date cannot be earlier than 19970101'"
     }

    Or

    ::

        {
            "timestamp":"Aug 14, 2021 4:23:16 PM",
            "user":"sys_x_bmapip01",
            "error_code":"  300",
            "error_message":"  Invalid Parameter data_frequency : 'DAYLY'"
        }
    """
    date_format = '%Y%m%d'

    def __init__(self, parameter_values_storage: DownloadParameterValuesStorage):
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

        self.parameter_values_storage = parameter_values_storage

    def parse(  # pylint: disable=arguments-renamed
            self,
            raw_json_text: str,
            tzinfo: typing.Optional[datetime.timezone]
    ) -> typing.Iterable[IndexValue]:

        try:
            raw_data = json.loads(raw_json_text)
        except json.decoder.JSONDecodeError as ex:
            raise ParseError(ex.msg) from ex

        if not isinstance(raw_data, dict):
            # can be Inf etc., but we accept only {}
            raise ParseError("Wrong JSON format. Top level is not dictionary.")

        error_message = raw_data.get('error_message', None)
        if error_message is not None:
            raise SourceDownloadError(f"JSON contains error message: {error_message}")

        msci_index_code = raw_data.get('msci_index_code', None)
        if msci_index_code is None:
            raise ParseError("Wrong JSON format. 'msci_index_code' not found.")

        index_variant_type = raw_data.get('index_variant_type', None)
        if index_variant_type is None:
            raise ParseError("Wrong JSON format. 'index_variant_type' not found.")

        iso_currency_symbol = raw_data.get('ISO_currency_symbol', None)
        if iso_currency_symbol is None:
            raise ParseError("Wrong JSON format. 'ISO_currency_symbol' not found.")

        indexes_block = raw_data.get('indexes', None)
        if indexes_block is None:
            raise ParseError("Wrong JSON format. 'indexes' block not found.")

        if not isinstance(indexes_block, dict):
            raise ParseError("Wrong JSON format. 'indexes' block is not dictionary.")

        index_levels_block = indexes_block.get('INDEX_LEVELS', None)
        if index_levels_block is None:
            raise ParseError("Wrong JSON format. 'INDEX_LEVELS' block not found.")

        if not index_levels_block:
            raise InstrumentValuesHistoryEmpty()

        index_values_pairs: typing.List[typing.Tuple[decimal.Decimal, datetime.date]] = []
        for index_value_block in index_levels_block:
            if not isinstance(index_value_block, dict):
                raise ParseError("Wrong JSON format. Item inside 'INDEX_LEVELS' block is not dictionary.")

            level_eod = index_value_block.get('level_eod', None)
            if level_eod is None:
                raise ParseError("Wrong JSON format. 'level_eod' not found.")

            calc_date = index_value_block.get('calc_date', None)
            if calc_date is None:
                raise ParseError("Wrong JSON format. 'calc_date' not found.")

            if isinstance(level_eod, float):
                # hack to adjust floating point digits
                level_eod = repr(level_eod)

            try:
                level_eod = decimal.Decimal(level_eod)
            except (ValueError, TypeError, decimal.DecimalException) as ex:
                raise ParseError(f"Wrong JSON format. Can't convert {level_eod} to decimal.") from ex

            try:
                calc_date = datetime.datetime.strptime(str(calc_date), self.date_format)
            except (ValueError, TypeError) as ex:
                raise ParseError(f"Wrong JSON format. Can't convert {calc_date} to datetime.") from ex

            index_values_pairs.append((level_eod, calc_date.date()))

        index_level = self.parameter_values_storage.get_dynamic_enum_value_by_key(IndexLevel, index_variant_type)
        if index_level is None:
            raise ParseError(f"Index level {index_variant_type!r} not found")

        currency = self.parameter_values_storage.get_dynamic_enum_value_by_key(Currency, iso_currency_symbol)
        if currency is None:
            raise ParseError(f"Currency {iso_currency_symbol!r} not found")

        return (
            IndexValue(calc_date=calc_date,
                       level_eod=level_eod,
                       msci_index_code=msci_index_code,
                       index_variant_type=index_level,
                       currency=currency)
            for level_eod, calc_date
            in index_values_pairs)


class MsciIndexInfoParser(InstrumentInfoParser):
    """ Parser for indexes info list from JSON.

    https://app2.msci.com/products/service/index/indexmaster/searchIndexes?index_market=24576&index_scope=Region&index_size=12&index_style=None&index_suite=C

    E.g.::

        {
            "indexes":[
                {"msci_index_code":903600,"index_name":"AUSTRALIA"},
                {"msci_index_code":904000,"index_name":"AUSTRIA"},
                ...
                ]
        }
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
            raise ParseError("Wrong JSON format. Top level is not dictionary.")

        indexes_block = raw_data.get('indexes', None)
        if indexes_block is None:
            raise ParseError("Wrong JSON format. 'indexes' block not found.")

        index_info_pairs: typing.List[typing.Tuple[str, str]] = []
        for index_info_block in indexes_block:
            if not isinstance(index_info_block, dict):
                raise ParseError("Wrong JSON format. Item inside 'indexes' block is not dictionary.")

            msci_index_code = index_info_block.get('msci_index_code', None)
            if msci_index_code is None:
                raise ParseError("Wrong JSON format. 'msci_index_code' not found.")

            index_name = index_info_block.get('index_name', None)
            if index_name is None:
                raise ParseError("Wrong JSON format. 'index_name' not found.")

            index_info_pairs.append((msci_index_code, index_name))

        return (
            IndexInfo(msci_index_code=msci_index_code,
                      index_name=index_name)
            for msci_index_code, index_name
            in index_info_pairs)


class MsciIndexPanelDataJsonParser:
    """ Parser for index panel data from JSON.
    """

    all_country_market_id = '24576'
    daily_frequency_id = 'DAILY'
    monthly_frequency_id = 'END_OF_MONTH'

    def __init__(self):
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

        self._index_suite_groups = {}

    @staticmethod
    def _parse_block(
            block_name: str,
            src_block: typing.Dict[str, typing.List]) -> typing.Iterable[typing.Tuple[str, str]]:

        target_block = src_block.get(block_name, None)
        if target_block is None:
            raise ParseError(f"Wrong JSON format. {block_name!r} block not found.")

        for pair_block in target_block:
            if not isinstance(pair_block, dict):
                raise ParseError(f"Wrong JSON format. Item inside {block_name!r} block is not dictionary.")

            identity = pair_block.get('id', None)
            if identity is None:
                raise ParseError("Wrong JSON format. 'id' not found.")

            name = pair_block.get('name', None)
            if name is None:
                raise ParseError("Wrong JSON format. 'name' not found.")

            yield identity, name

    def parse(self, raw_json_text: str) -> IndexPanelData:
        """ Parse index panel data from JSON and return it.

        :param raw_json_text: JSON string with index panel data.
        :return: ``IndexPanelData`` instance.
        """
        try:
            raw_data = json.loads(raw_json_text)
        except json.decoder.JSONDecodeError as ex:
            raise ParseError(ex.msg) from ex

        if not isinstance(raw_data, dict):
            # can be Inf etc., but we accept only {}
            raise ParseError("Wrong JSON format. Top level is not dictionary.")

        markets = tuple(
            Market.safe_create(
                identity=identity,
                name=name,
                # 'All Country (DM+EM)' market available only in regional scope
                scope=Scopes.REGIONAL if str(identity) == self.all_country_market_id else None)
            for identity, name
            in self._parse_block('market', raw_data))
        currencies = tuple(
            Currency.safe_create(identity=identity, name=name)
            for identity, name
            in self._parse_block('currency', raw_data))
        index_levels = tuple(
            IndexLevel.safe_create(identity=identity, name=name)
            for identity, name
            in self._parse_block('indexLevels', raw_data))
        frequencies = tuple(
            Frequency.safe_create(identity=identity, name=name)
            for identity, name
            in self._parse_block('frequency', raw_data))
        sizes = tuple(
            Size.safe_create(identity=identity, name=name)
            for identity, name
            in self._parse_block('size', raw_data))
        styles = tuple(
            Style.safe_create(identity=identity, name=name)
            for identity, name
            in self._parse_block('style', raw_data))

        index_suites_block = raw_data.get('indexSuite', None)
        if index_suites_block is None:
            raise ParseError("Wrong JSON format. 'indexSuite' block not found.")

        index_suite_groups: typing.List[IndexSuiteGroup] = []
        index_suites: typing.List[IndexSuite] = []

        for index_suites_block_item in index_suites_block:
            optgroup = index_suites_block_item.get('optgroup', None)
            if optgroup is None:
                index_suites.extend(
                    IndexSuite.safe_create(identity=identity, name=name)
                    for identity, name
                    in self._parse_block('DUMMY', {'DUMMY': [index_suites_block_item]}))

            else:
                group = IndexSuiteGroup.safe_create(name=optgroup)
                index_suite_groups.append(group)
                index_suites.extend(
                    IndexSuite.safe_create(identity=identity, name=name, group=group)
                    for identity, name
                    in self._parse_block('options', index_suites_block_item))

        # unfortunately, daily and monthly frequencies hard-coded in site scripts
        # so we forced to assume their codes here
        frequencies_dict = {frequency.identity: frequency for frequency in frequencies}
        if self.daily_frequency_id not in frequencies_dict:
            raise ParseError(f"Frequency with id {self.daily_frequency_id!r} not found.")
        if self.monthly_frequency_id not in frequencies_dict:
            raise ParseError(f"Frequency with id {self.monthly_frequency_id!r} not found.")

        return IndexPanelData(
            markets=markets,
            currencies=currencies,
            index_levels=index_levels,
            frequencies=frequencies,
            index_suite_groups=tuple(index_suite_groups),
            index_suites=tuple(index_suites),
            sizes=sizes,
            styles=styles,
            daily_frequency=frequencies_dict[self.daily_frequency_id],
            monthly_frequency=frequencies_dict[self.monthly_frequency_id])
