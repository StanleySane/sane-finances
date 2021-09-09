#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Tools for download (export) index data from moex.com
"""
import collections
import dataclasses
import decimal
import itertools
import logging
import typing
import datetime
import inspect

from .meta import (
    TradeEngine, Market, Board, ResponseFormats, JsonFormats, Limits,
    GlobalIndexData,
    MoexSecurityHistoryDownloadParameters, MoexSecuritiesInfoDownloadParameters,
    MoexDownloadParametersFactory)
from .parsers import MoexGlobalIndexJsonParser, MoexHistoryJsonParser, MoexSecurityInfoJsonParser
from ...base import (
    ApiActualityChecker, InstrumentStringDataDownloader, ParseError,
    InstrumentExporterFactory, InstrumentHistoryValuesExporter, InstrumentsInfoExporter,
    DownloadParameterValuesStorage, DynamicEnumTypeManager, DownloadStringResult,
    SourceError, CheckApiActualityError)
from ...generic import GenericInstrumentHistoryValuesExporter, GenericInstrumentsInfoExporter
from ....communication.downloader import Downloader

logging.getLogger().addHandler(logging.NullHandler())


class MoexStringDataDownloader(InstrumentStringDataDownloader):
    """ Data downloader from moex.com.
    """

    BaseUrl = 'https://iss.moex.com/iss'

    def __init__(self, downloader: Downloader):
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

        self.downloader = downloader

        # headers for HTTP
        self.headers: typing.Dict[str, str] = {}

        self.iss_meta = False
        self.iss_data = True
        self.iss_json = JsonFormats.COMPACT
        self.limit = Limits.HUNDRED
        self.response_format = ResponseFormats.JSON
        self.history_columns = ['BOARDID', 'TRADEDATE', 'SECID', 'CLOSE', 'LEGALCLOSEPRICE', 'FACEVALUE']

    def paginate_download_instrument_history_parameters(
            self,
            parameters: MoexSecurityHistoryDownloadParameters,
            moment_from: datetime.datetime,
            moment_to: datetime.datetime
    ) -> typing.Iterable[typing.Tuple[MoexSecurityHistoryDownloadParameters, datetime.datetime, datetime.datetime]]:

        for start in itertools.count(start=0, step=self.limit.value):
            parameters = dataclasses.replace(parameters, start=start)
            yield parameters, moment_from, moment_to

    def download_instrument_history_string(
            self,
            parameters: MoexSecurityHistoryDownloadParameters,
            moment_from: datetime.datetime,
            moment_to: datetime.datetime) -> DownloadStringResult:
        date_from = moment_from.date()
        date_to = moment_to.date()
        if moment_to.time() != datetime.time.min:
            date_to += datetime.timedelta(days=1)

        return self.download_security_history_string(
            parameters.board,
            parameters.sec_id,
            parameters.start,
            date_from,
            date_to)

    def download_instruments_info_string(
            self,
            parameters: MoexSecuritiesInfoDownloadParameters) -> DownloadStringResult:
        return self.download_securities_info_string(
            parameters.board)

    def download_security_history_string(
            self,
            board: Board,
            sec_id: str,
            start: int,
            date_from: datetime.date,
            date_to: datetime.date) -> DownloadStringResult:
        """ Downloads history data for one security as string.

        :param board: Board.
        :param sec_id: Security ID.
        :param start: Start value.
        :param date_from: Download interval beginning.
        :param date_to: Download interval ending.
        :return: Container with downloaded string.
        """
        params = [
            ('iss.meta', 'on' if self.iss_meta else 'off'),
            ('iss.data', 'on' if self.iss_data else 'off'),
            ('iss.json', str(self.iss_json.value)),
            ('limit', str(self.limit.value)),
            ('start', str(start)),
            ('history.columns', ','.join(self.history_columns)),
            ('from', date_from.strftime('%Y-%m-%d')),
            ('till', date_to.strftime('%Y-%m-%d'))
        ]

        url = f"{self.BaseUrl}/history/engines/{board.trade_engine.name}/" \
              f"markets/{board.market.name}/" \
              f"boards/{board.boardid}/" \
              f"securities/{sec_id}.{self.response_format.value}"

        self.downloader.parameters = params
        self.downloader.headers = self.headers

        return self.downloader.download_string(url)

    def download_securities_info_string(
            self,
            board: Board) -> DownloadStringResult:
        """ Downloads the list of all available securities by specified parameters.

        :param board: Board.
        :return: Container with downloaded string.
        """
        self.downloader.headers = self.headers
        self.downloader.parameters = []
        url = f"{self.BaseUrl}/engines/{board.trade_engine.name}/" \
              f"markets/{board.market.name}/" \
              f"boards/{board.boardid}/" \
              f"securities.{self.response_format.value}"

        return self.downloader.download_string(url)


class MoexDynamicEnumTypeManager(DynamicEnumTypeManager):
    """ MOEX dynamic enum types manager.
    """

    def __init__(self):
        self._managed_types: typing.Dict[typing.Type, typing.Tuple[str, typing.Callable]] = {
            TradeEngine: ('trade_engines', lambda it: it.identity),
            Market: ('markets', lambda it: it.identity),
            Board: ('boards', lambda it: it.identity)
        }

    def is_dynamic_enum_type(self, cls: type) -> bool:
        if not inspect.isclass(cls):
            return False

        return cls in self._managed_types

    def get_all_managed_types(self) -> typing.Iterable[typing.Type]:
        return self._managed_types.keys()

    def get_dynamic_enum_key(self, instance):
        for managed_type, (_, key_getter, *_) in self._managed_types.items():
            if isinstance(instance, managed_type):
                return key_getter(instance)

        return None


class MoexDownloadParameterValuesStorage(MoexDynamicEnumTypeManager, DownloadParameterValuesStorage):
    """ Storage of instrument download parameters.
    """

    def __init__(
            self,
            downloader: Downloader,
            global_index_json_parser: MoexGlobalIndexJsonParser):
        super().__init__()
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

        self.downloader = downloader
        self.global_index_json_parser = global_index_json_parser

        # headers for HTTP
        self.headers: typing.Dict[str, str] = {}

        self._extended_managed_types: typing.Dict[typing.Type, typing.Tuple] = {
            TradeEngine: (self._get_trade_engines_choices,),
            Market: (self._get_markets_choices,),
            Board: (self._get_boards_choices,)
        }
        assert set(self._extended_managed_types.keys()) == set(self._managed_types.keys()), \
            ("MoexDynamicEnumTypeManager and MoexDownloadParameterValuesStorage "
             "has different managed types.")

        self.global_index_data: typing.Optional[GlobalIndexData] = None

    def reload(self) -> None:
        self.downloader.headers = self.headers
        self.downloader.parameters = []
        url = f"{MoexStringDataDownloader.BaseUrl}/index.json"

        json_string_result = self.downloader.download_string(url)

        try:
            global_index_data = self.global_index_json_parser.parse(json_string_result.downloaded_string)

        except Exception:
            json_string_result.set_correctness(False)
            raise

        json_string_result.set_correctness(True)
        self.global_index_data = global_index_data

    def _ensure_loaded(self):
        if self.global_index_data is None:
            self.reload()

    def get_dynamic_enum_value_by_key(self, cls: type, key) -> typing.Any:
        if not self.is_dynamic_enum_type(cls):
            return None

        self._ensure_loaded()

        global_index_data_attr_name, key_getter, *_ = self._managed_types[cls]
        enum_values = getattr(self.global_index_data, global_index_data_attr_name)

        for enum_value in enum_values:
            if key == key_getter(enum_value):
                return enum_value

        return None

    def get_dynamic_enum_value_by_choice(self, cls: type, choice: str) -> typing.Any:
        if not self.is_dynamic_enum_type(cls):
            return None

        self._ensure_loaded()

        try:
            # here we know that all choices from get_parameter_type_choices
            # was made by converting identities to strings,
            # so we convert them back
            key = int(choice)
        except (ValueError, TypeError) as ex:
            raise SourceError(f"Can't get enum value key from {choice!r}") from ex

        global_index_data_attr_name, key_getter, *_ = self._managed_types[cls]
        enum_values = getattr(self.global_index_data, global_index_data_attr_name)

        for enum_value in enum_values:
            if key == key_getter(enum_value):
                return enum_value

        return None

    def get_all_parameter_values_for(self, cls: type) -> typing.Optional[typing.Iterable]:
        if not self.is_dynamic_enum_type(cls):
            return None

        self._ensure_loaded()

        global_index_data_attr_name, *_ = self._managed_types[cls]
        return getattr(self.global_index_data, global_index_data_attr_name)

    def get_parameter_type_choices(self, cls: type) \
            -> typing.Optional[
                typing.List[typing.Tuple[typing.Any, typing.Union[str, typing.List[typing.Tuple[typing.Any, str]]]]]
            ]:
        if not self.is_dynamic_enum_type(cls):
            return None

        self._ensure_loaded()

        choices_getter, *_ = self._extended_managed_types[cls]
        return choices_getter()

    def _get_trade_engines_choices(self):
        return [(str(trade_engine.identity), trade_engine.title)
                for trade_engine
                in self.global_index_data.trade_engines]

    def _get_markets_choices(self):
        market: Market

        grouped_markets = collections.OrderedDict()
        for market in self.global_index_data.markets:
            if market.trade_engine not in grouped_markets:
                grouped_markets[market.trade_engine] = []
            grouped_markets[market.trade_engine].append(market)

        return [(f"Available for trade engine {trade_engine.title!r}:",
                 [(str(market.identity), market.title) for market in markets])
                for trade_engine, markets
                in grouped_markets.items()]

    def _get_boards_choices(self):
        board: Board

        grouped_boards = collections.OrderedDict()
        for board in self.global_index_data.boards:
            key = (board.trade_engine, board.market)
            if key not in grouped_boards:
                grouped_boards[key] = []
            grouped_boards[key].append(board)

        return [(f"Available for {trade_engine.title!r}, {market.title!r}:",
                 [(str(board.identity), board.title) for board in boards])
                for (trade_engine, market), boards
                in grouped_boards.items()]


class MoexApiActualityChecker(ApiActualityChecker):
    """ Verifies actuality and accessibility of REST API of moex.com.
    """

    _trade_engine_name_to_test = 'stock'
    _market_name_to_test = 'index'
    _boardid_to_test = 'TQTF'
    _sec_id_to_test = 'FXJP'
    _history_date_to_test = datetime.date(2014, 6, 10)
    _expected_close_value = decimal.Decimal('1000')

    def __init__(
            self,
            parameter_values_storage: MoexDownloadParameterValuesStorage,
            string_data_downloader: MoexStringDataDownloader,
            info_parser: MoexSecurityInfoJsonParser,
            history_values_parser: MoexHistoryJsonParser):
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

        self.parameter_values_storage = parameter_values_storage
        self.string_data_downloader = string_data_downloader
        self.history_values_parser = history_values_parser
        self.info_parser = info_parser

    def check(self):
        self.logger.info("Check actuality via security list")

        all_boards: typing.Tuple[Board] = tuple(self.parameter_values_storage.get_all_parameter_values_for(Board))
        if not all_boards:
            raise CheckApiActualityError("Not found any board")

        # try to find any board for stock indexes
        all_stock_index_boards = [board
                                  for board
                                  in all_boards
                                  if (board.trade_engine.name == self._trade_engine_name_to_test
                                      and board.market.name == self._market_name_to_test)]

        if not all_stock_index_boards:
            # else get any other board
            all_stock_index_boards = [all_boards[0]]

        target_board = all_stock_index_boards[0]
        securities_info_string_result = self.string_data_downloader.download_securities_info_string(target_board)
        self.logger.debug(f"Got JSON data:\n{securities_info_string_result.downloaded_string}")
        # read all available securities
        try:
            _ = tuple(self.info_parser.parse(securities_info_string_result.downloaded_string))
        except ParseError as ex:
            securities_info_string_result.set_correctness(False)
            raise CheckApiActualityError(f"Unexpected securities info JSON: {ex.message}") from ex
        except Exception:
            securities_info_string_result.set_correctness(False)
            raise

        # now test history data
        self.logger.info(f"Check actuality via security {self._sec_id_to_test!r}")

        target_board = ([board
                         for board
                         in all_boards
                         if board.boardid == self._boardid_to_test] or [None])[0]

        if target_board is None:
            securities_info_string_result.set_correctness(False)
            raise CheckApiActualityError(f"Not found board with boardid {self._boardid_to_test!r}")

        history_data_string_result = self.string_data_downloader.download_security_history_string(
            target_board,
            self._sec_id_to_test,
            0,
            self._history_date_to_test,
            self._history_date_to_test
        )
        self.logger.debug(f"Got JSON data:\n{history_data_string_result.downloaded_string}")
        try:
            history_data = tuple(self.history_values_parser.parse(
                history_data_string_result.downloaded_string,
                tzinfo=None))
        except ParseError as ex:
            history_data_string_result.set_correctness(False)
            raise CheckApiActualityError(f"Unexpected securities history JSON: {ex.message}") from ex
        except Exception:
            history_data_string_result.set_correctness(False)
            raise

        if not history_data:
            history_data_string_result.set_correctness(False)
            raise CheckApiActualityError(
                f"Not found history values for {self._sec_id_to_test!r} "
                f"on {self._history_date_to_test.isoformat()}")

        value_to_test = history_data[0]

        if value_to_test.trade_date != self._history_date_to_test:
            history_data_string_result.set_correctness(False)
            raise CheckApiActualityError(
                f"Unexpected trade date. {value_to_test.trade_date!r} != {self._history_date_to_test!r}")

        if value_to_test.close != self._expected_close_value:
            history_data_string_result.set_correctness(False)
            raise CheckApiActualityError(
                f"Unexpected close value. {value_to_test.close!r} != {self._expected_close_value!r}")

        self.logger.info("Actuality check was successful")


# noinspection PyPep8Naming
class MoexIndexExporterFactory_v1_3(InstrumentExporterFactory):  # pylint: disable=invalid-name
    """ Factory class for create instances of Moscow Exchange data exporter.
    """
    name: str = 'Moscow Exchange ISS data exporter. ' \
                'X-Micex-ISS-Query-Version: 1.0. ' \
                'X-Micex-ISS-Statement-Version: history=3.0'
    provider_site: str = 'https://www.moex.com/'
    api_url: str = 'http://iss.moex.com/iss/reference/'

    def __init__(self):
        self._dynamic_enum_type_manager = None
        self._download_parameters_factory = None

    def create_history_values_exporter(self, downloader: Downloader) -> InstrumentHistoryValuesExporter:
        string_data_downloader = MoexStringDataDownloader(downloader)
        history_values_parser = MoexHistoryJsonParser()

        return GenericInstrumentHistoryValuesExporter(string_data_downloader, history_values_parser)

    def create_info_exporter(self, downloader: Downloader) -> InstrumentsInfoExporter:
        string_data_downloader = MoexStringDataDownloader(downloader)
        global_index_json_parser = MoexGlobalIndexJsonParser()
        parameter_values_storage = MoexDownloadParameterValuesStorage(downloader, global_index_json_parser)
        info_parser = MoexSecurityInfoJsonParser(parameter_values_storage)

        return GenericInstrumentsInfoExporter(string_data_downloader, info_parser)

    def create_download_parameter_values_storage(self, downloader: Downloader) -> MoexDownloadParameterValuesStorage:
        global_index_json_parser = MoexGlobalIndexJsonParser()

        return MoexDownloadParameterValuesStorage(downloader, global_index_json_parser)

    def create_api_actuality_checker(self, downloader: Downloader) -> MoexApiActualityChecker:
        string_data_downloader = MoexStringDataDownloader(downloader)
        history_values_parser = MoexHistoryJsonParser()
        global_index_json_parser = MoexGlobalIndexJsonParser()
        parameter_values_storage = MoexDownloadParameterValuesStorage(downloader, global_index_json_parser)
        info_parser = MoexSecurityInfoJsonParser(parameter_values_storage)

        return MoexApiActualityChecker(
            parameter_values_storage,
            string_data_downloader,
            info_parser,
            history_values_parser)

    @property
    def dynamic_enum_type_manager(self) -> MoexDynamicEnumTypeManager:
        if self._dynamic_enum_type_manager is None:
            self._dynamic_enum_type_manager = MoexDynamicEnumTypeManager()

        return self._dynamic_enum_type_manager

    @property
    def download_parameters_factory(self) -> MoexDownloadParametersFactory:
        if self._download_parameters_factory is None:
            self._download_parameters_factory = MoexDownloadParametersFactory()

        return self._download_parameters_factory
