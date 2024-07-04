#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Tools for download (export) index data from https://www.spglobal.com/spdji/
"""
import collections
import datetime
import inspect
import itertools
import logging
import typing

from .meta import (
    IndexFinderFilterGroup, IndexFinderFilter, Currency, ReturnType,
    SpdjIndexHistoryDownloadParameters, SpdjIndexesInfoDownloadParameters, SpdjDownloadParametersFactory, IndexMetaData)
from .parsers import SpdjHistoryJsonParser, SpdjInfoJsonParser, SpdjMetaJsonParser, SpdjIndexFinderFiltersParser
from ...base import (
    ApiActualityChecker, InstrumentStringDataDownloader, ParseError,
    InstrumentExporterFactory, InstrumentHistoryValuesExporter, InstrumentsInfoExporter,
    DownloadParameterValuesStorage, DynamicEnumTypeManager, DownloadStringResult,
    CheckApiActualityError)
from ...generic import GenericInstrumentHistoryValuesExporter, GenericInstrumentsInfoExporter
from ....communication.downloader import Downloader

logging.getLogger().addHandler(logging.NullHandler())


class SpdjStringDataDownloader(InstrumentStringDataDownloader):
    """ Data downloader from https://www.spglobal.com/spdji/
    """

    history_url = 'https://www.spglobal.com/spdji/en/util/redesign/index-data/' \
                  'get-performance-data-for-datawidget-redesign.dot'
    info_url = 'https://www.spglobal.com/spdji/en/util/redesign/index-finder/index-finder-json.dot'
    index_finder_url = 'https://www.spglobal.com/spdji/en/index-finder/'

    def __init__(self, downloader: Downloader):
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

        self.downloader = downloader

        # headers for HTTP
        self.headers: typing.Dict[str, str] = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;'
                      'q=0.9,image/avif,image/webp,image/apng,*/*;'
                      'q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'no-cache',
            'Sec-Ch-Ua': '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/126.0.0.0 Safari/537.36',
        }

        self.language_id = '1'
        self.get_child_index = True
        self.info_results_per_page = 100

    def download_instrument_history_string(
            self,
            parameters: SpdjIndexHistoryDownloadParameters,
            moment_from: datetime.datetime,
            moment_to: datetime.datetime) -> DownloadStringResult:
        return self.download_index_history_string(parameters.index_id, parameters.currency, parameters.return_type)

    def paginate_download_instruments_info_parameters(
            self,
            parameters: SpdjIndexesInfoDownloadParameters) -> typing.Iterable[SpdjIndexesInfoDownloadParameters]:

        for page_number in itertools.count(start=1, step=1):
            # noinspection PyProtectedMember
            parameters = parameters._replace(page_number=page_number)
            yield parameters

    def download_instruments_info_string(
            self,
            parameters: SpdjIndexesInfoDownloadParameters) -> DownloadStringResult:
        return self.download_index_info_string(
            page_number=parameters.page_number,
            index_finder_filter=parameters.index_finder_filter)

    def download_index_history_string(
            self,
            index_id: str,
            currency: typing.Optional[Currency],
            return_type: typing.Optional[ReturnType]) -> DownloadStringResult:
        """ Downloads history data for one index as string.

        :param index_id: Index ID.
        :param currency: Currency or ``None``
        :param return_type: Return type or ``None``
        :return: Container with downloaded string.
        """
        params = [
            ('indexId', str(index_id)),
            ('getchildindex', 'true' if self.get_child_index else 'false'),
            ('language_id', str(self.language_id))
        ]
        if currency is not None:
            params.append(('currencycode', currency.currency_code))
        if return_type is not None:
            params.append(('returntype', return_type.return_type_code))

        self.downloader.parameters = params
        self.downloader.headers = self.headers

        return self.downloader.download_string(self.history_url)

    def download_index_info_string(
            self,
            page_number: int,
            index_finder_filter: typing.Optional[IndexFinderFilter]) -> DownloadStringResult:
        """ Downloads the list of all available indexes by specified parameters.

        :param page_number: Number of page to download
        :param index_finder_filter: Index finder filter or ``None``
        :return: Container with downloaded string.
        """
        self.downloader.headers = self.headers
        self.downloader.parameters = [
            ('pageNumber', page_number),
            ('resultsPerPage', self.info_results_per_page),
            ('language_id', str(self.language_id))
        ]
        if index_finder_filter is not None:
            self.downloader.parameters.append((index_finder_filter.group.name, index_finder_filter.value))

        return self.downloader.download_string(self.info_url)


class SpdjDynamicEnumTypeManager(DynamicEnumTypeManager):
    """ S&P Dow Jones dynamic enum types manager.
    """

    def __init__(self):
        self._managed_types: typing.Dict[typing.Type, typing.Tuple[str, typing.Callable]] = {
            Currency: ('currencies', lambda it: it.currency_code),
            ReturnType: ('return_types', lambda it: it.return_type_code),
            IndexFinderFilter: ('index_finder_filters', lambda it: it.value)
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


class SpdjDownloadParameterValuesStorage(SpdjDynamicEnumTypeManager, DownloadParameterValuesStorage):
    """ Storage of instrument download parameters.
    """

    def __init__(
            self,
            downloader: Downloader,
            meta_json_parser: SpdjMetaJsonParser,
            index_finder_filters_parser: SpdjIndexFinderFiltersParser):
        super().__init__()
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

        self.downloader = downloader
        self.meta_json_parser = meta_json_parser
        self.index_finder_filters_parser = index_finder_filters_parser

        self.meta_json_index_id = '340'  # S&P 500
        self.meta_json_language_id = '1'

        # headers for HTTP
        self.headers: typing.Dict[str, str] = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/39.0.2171.95 Safari/537.36'
        }

        self._extended_managed_types: typing.Dict[typing.Type, typing.Tuple] = {
            Currency: (self._get_currency_choices,),
            ReturnType: (self._get_return_type_choices,),
            IndexFinderFilter: (self._get_index_finder_filter_choices,)
        }
        assert set(self._extended_managed_types.keys()) == set(self._managed_types.keys()), \
            ("SpdjDynamicEnumTypeManager and SpdjDownloadParameterValuesStorage "
             "has different managed types.")

        self.index_meta_data: typing.Optional[IndexMetaData] = None

    def _reload_meta_from_history(self) -> IndexMetaData:
        self.downloader.headers = self.headers
        self.downloader.parameters = [
            ('indexId', str(self.meta_json_index_id)),
            ('language_id', str(self.meta_json_language_id))
        ]

        json_string_result = self.downloader.download_string(SpdjStringDataDownloader.history_url)

        try:
            index_meta_data = self.meta_json_parser.parse(json_string_result.downloaded_string)

        except Exception:
            json_string_result.set_correctness(False)
            raise

        json_string_result.set_correctness(True)
        return index_meta_data

    def _reload_meta_from_index_finder(self) -> typing.Tuple[IndexFinderFilter, ...]:
        self.downloader.headers = self.headers
        self.downloader.parameters = []

        json_string_result = self.downloader.download_string(SpdjStringDataDownloader.index_finder_url)

        try:
            index_finder_filters = tuple(self.index_finder_filters_parser.parse(json_string_result.downloaded_string))

        except Exception:
            json_string_result.set_correctness(False)
            raise

        json_string_result.set_correctness(True)
        return index_finder_filters

    def reload(self) -> None:
        index_meta_data = self._reload_meta_from_history()
        index_finder_filters = self._reload_meta_from_index_finder()
        index_meta_data = index_meta_data._replace(index_finder_filters=index_finder_filters)

        self.index_meta_data = index_meta_data

    def _ensure_loaded(self):
        if self.index_meta_data is None:
            self.reload()

    def get_dynamic_enum_value_by_key(self, cls: type, key) -> typing.Any:
        if not self.is_dynamic_enum_type(cls):
            return None

        self._ensure_loaded()

        index_meta_data_attr_name, key_getter, *_ = self._managed_types[cls]
        enum_values = getattr(self.index_meta_data, index_meta_data_attr_name)

        for enum_value in enum_values:
            if key == key_getter(enum_value):
                return enum_value

        return None

    def get_dynamic_enum_value_by_choice(self, cls: type, choice: str) -> typing.Any:
        if not self.is_dynamic_enum_type(cls):
            return None

        self._ensure_loaded()

        index_meta_data_attr_name, key_getter, *_ = self._managed_types[cls]
        enum_values = getattr(self.index_meta_data, index_meta_data_attr_name)

        for enum_value in enum_values:
            if choice == key_getter(enum_value):
                return enum_value

        return None

    def get_all_parameter_values_for(self, cls: type) -> typing.Optional[typing.Iterable]:
        if not self.is_dynamic_enum_type(cls):
            return None

        self._ensure_loaded()

        index_meta_data_attr_name, *_ = self._managed_types[cls]
        return getattr(self.index_meta_data, index_meta_data_attr_name)

    def get_parameter_type_choices(self, cls: type) \
            -> typing.Optional[
                typing.List[typing.Tuple[typing.Any, typing.Union[str, typing.List[typing.Tuple[typing.Any, str]]]]]
            ]:
        if not self.is_dynamic_enum_type(cls):
            return None

        self._ensure_loaded()

        choices_getter, *_ = self._extended_managed_types[cls]
        return choices_getter()

    def _get_currency_choices(self):
        return [(str(currency.currency_code), currency.currency_code)
                for currency
                in self.index_meta_data.currencies]

    def _get_return_type_choices(self):
        return [(str(return_type.return_type_code), return_type.return_type_name)
                for return_type
                in self.index_meta_data.return_types]

    def _get_index_finder_filter_choices(self):
        group: IndexFinderFilterGroup  # pylint: disable=unused-variable

        grouped_filters = collections.OrderedDict()
        for index_finder_filter in self.index_meta_data.index_finder_filters:
            if index_finder_filter.group not in grouped_filters:
                grouped_filters[index_finder_filter.group] = []
            grouped_filters[index_finder_filter.group].append(index_finder_filter)

        return [(group.label,
                 [(str(index_finder_filter.value), index_finder_filter.label)
                  for index_finder_filter
                  in index_finder_filters])
                for group, index_finder_filters
                in grouped_filters.items()]


class SpdjApiActualityChecker(ApiActualityChecker):
    """ Verifies actuality and accessibility of REST API of https://www.spglobal.com/spdji/
    """

    _history_index_id_to_test = '340'  # S&P 500

    def __init__(
            self,
            string_data_downloader: SpdjStringDataDownloader,
            info_parser: SpdjInfoJsonParser,
            history_values_parser: SpdjHistoryJsonParser):
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

        self.string_data_downloader = string_data_downloader
        self.history_values_parser = history_values_parser
        self.info_parser = info_parser

    def check(self):
        self.logger.info("Check actuality via indexes list")

        self.string_data_downloader.info_results_per_page = 1  # to minimize traffic
        indexes_info_string_result = self.string_data_downloader.download_index_info_string(
            page_number=1,
            index_finder_filter=None)
        self.logger.debug(f"Got JSON data:\n{indexes_info_string_result.downloaded_string}")
        # read all available indexes
        try:
            _ = tuple(self.info_parser.parse(indexes_info_string_result.downloaded_string))
        except ParseError as ex:
            indexes_info_string_result.set_correctness(False)
            raise CheckApiActualityError(f"Unexpected indexes info JSON: {ex.message}") from ex
        except Exception:
            indexes_info_string_result.set_correctness(False)
            raise

        # now test history data
        self.logger.info(f"Check actuality via security {self._history_index_id_to_test!r}")

        self.string_data_downloader.get_child_index = False  # needed if currency and return type are None
        history_data_string_result = self.string_data_downloader.download_index_history_string(
            index_id=self._history_index_id_to_test,
            currency=None,
            return_type=None)
        self.logger.debug(f"Got JSON data:\n{history_data_string_result.downloaded_string}")
        try:
            history_data = tuple(self.history_values_parser.parse(
                history_data_string_result.downloaded_string,
                tzinfo=None))
        except ParseError as ex:
            history_data_string_result.set_correctness(False)
            raise CheckApiActualityError(f"Unexpected indexes history JSON: {ex.message}") from ex
        except Exception:
            history_data_string_result.set_correctness(False)
            raise

        if not history_data:
            history_data_string_result.set_correctness(False)
            raise CheckApiActualityError(
                f"Not found history values for {self._history_index_id_to_test!r}")

        self.logger.info("Actuality check was successful")


class SpdjExporterFactory(InstrumentExporterFactory):
    """ Factory class for create instances of S&P Dow Jones data exporter.
    """
    name: str = 'S&P Dow Jones Indices. Version 2021'
    provider_site: str = 'https://www.spglobal.com/spdji/en/'
    api_url: str = 'https://www.spglobal.com/spdji/en/index-finder/'

    def __init__(self):
        self._dynamic_enum_type_manager = None
        self._download_parameters_factory = None

    def create_history_values_exporter(self, downloader: Downloader) -> InstrumentHistoryValuesExporter:
        string_data_downloader = SpdjStringDataDownloader(downloader)
        history_values_parser = SpdjHistoryJsonParser()

        return GenericInstrumentHistoryValuesExporter(string_data_downloader, history_values_parser)

    def create_info_exporter(self, downloader: Downloader) -> InstrumentsInfoExporter:
        string_data_downloader = SpdjStringDataDownloader(downloader)
        info_parser = SpdjInfoJsonParser()

        return GenericInstrumentsInfoExporter(string_data_downloader, info_parser)

    def create_download_parameter_values_storage(self, downloader: Downloader) -> SpdjDownloadParameterValuesStorage:
        meta_json_parser = SpdjMetaJsonParser()
        index_finder_filters_parser = SpdjIndexFinderFiltersParser()

        return SpdjDownloadParameterValuesStorage(downloader, meta_json_parser, index_finder_filters_parser)

    def create_api_actuality_checker(self, downloader: Downloader) -> SpdjApiActualityChecker:
        string_data_downloader = SpdjStringDataDownloader(downloader)
        history_values_parser = SpdjHistoryJsonParser()
        info_parser = SpdjInfoJsonParser()

        return SpdjApiActualityChecker(
            string_data_downloader,
            info_parser,
            history_values_parser)

    @property
    def dynamic_enum_type_manager(self) -> SpdjDynamicEnumTypeManager:
        if self._dynamic_enum_type_manager is None:
            self._dynamic_enum_type_manager = SpdjDynamicEnumTypeManager()

        return self._dynamic_enum_type_manager

    @property
    def download_parameters_factory(self) -> SpdjDownloadParametersFactory:
        if self._download_parameters_factory is None:
            self._download_parameters_factory = SpdjDownloadParametersFactory()

        return self._download_parameters_factory
