#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Tools for download (export) currency rates data from cbr.ru
"""
import logging
import typing
import decimal
import datetime
import inspect

from .meta import (
    RateFrequencies, CbrDownloadParametersFactory,
    CbrCurrenciesInfoDownloadParameters, CbrCurrencyHistoryDownloadParameters)
from .parsers import CbrCurrencyHistoryXmlParser, CbrCurrencyInfoParser
from ...base import (
    ApiActualityChecker, InstrumentStringDataDownloader, ParseError,
    InstrumentExporterFactory, InstrumentHistoryValuesExporter, InstrumentsInfoExporter,
    DownloadParameterValuesStorage, CheckApiActualityError)
from ...generic import GenericInstrumentHistoryValuesExporter, GenericInstrumentsInfoExporter
from ....communication.downloader import Downloader, DownloadStringResult

logging.getLogger().addHandler(logging.NullHandler())


class CbrStringDataDownloader(InstrumentStringDataDownloader):
    """ Data downloader from cbr.ru.

    See http://www.cbr.ru/development/sxml/ for details.

    The list of all currencies can be obtained from
    https://www.cbr.ru/scripts/XML_val.asp?d=0
    and
    https://www.cbr.ru/scripts/XML_val.asp?d=1
    """

    CurrenciesListUrl = 'https://www.cbr.ru/scripts/XML_val.asp'
    RatesHistoryUrl = 'https://www.cbr.ru/scripts/XML_dynamic.asp'

    encoding = 'cp1251'
    query_date_format = '%d/%m/%Y'

    def __init__(self, downloader: Downloader):
        """ Initialize downloader.

        :param downloader: Used string downloader.
        """
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

        self.downloader = downloader

        # headers for HTTP
        self.headers: typing.Dict[str, str] = {}

    def download_instrument_history_string(
            self,
            parameters: CbrCurrencyHistoryDownloadParameters,
            moment_from: datetime.datetime,
            moment_to: datetime.datetime) -> DownloadStringResult:

        date_from = moment_from.date()
        date_to = moment_to.date()
        if moment_to.time() != datetime.time.min:
            date_to += datetime.timedelta(days=1)

        return self.download_currency_history_string(parameters.currency_id, date_from, date_to)

    def download_instruments_info_string(
            self,
            parameters: CbrCurrenciesInfoDownloadParameters) -> DownloadStringResult:
        return self.download_currencies_info_string(parameters.rate_frequency)

    def download_currency_history_string(
            self,
            currency_id: str,
            date_from: datetime.date,
            date_to: datetime.date) -> DownloadStringResult:
        """ Downloads data for one currency as string.

        :param currency_id: Currency ID.
        :param date_from: Download interval beginning.
        :param date_to: Download interval ending.
        :return: Container with downloaded string.
        """
        params = [
            ('date_req1', date_from.strftime(self.query_date_format)),
            ('date_req2', date_to.strftime(self.query_date_format)),
            ('VAL_NM_RQ', currency_id)
        ]

        self.downloader.parameters = params
        self.downloader.headers = self.headers

        return self.downloader.download_string(self.RatesHistoryUrl, self.encoding)

    def download_currencies_info_string(self, rate_frequency: RateFrequencies) -> DownloadStringResult:
        """ Downloads the list of all available currencies by specified parameters.

        :param rate_frequency: ``RateFrequencies`` value.
        :return: Container with downloaded string.
        """
        self.downloader.headers = {}
        self.downloader.parameters = [
            ('d', rate_frequency.value)
        ]

        return self.downloader.download_string(self.CurrenciesListUrl, self.encoding)


class CbrApiActualityChecker(ApiActualityChecker):
    """ Verifies actuality and accessibility of REST API of cbr.ru.
    """

    _currencyToCheck = 'R01235'  # US Dollar
    _expectedFirstDate = datetime.date(2000, 1, 1)
    _expectedFirstNominal = 1
    _expectedFirstValue = decimal.Decimal('27')

    def __init__(self,
                 string_data_downloader: CbrStringDataDownloader,
                 history_xml_parser: CbrCurrencyHistoryXmlParser,
                 index_info_parser: CbrCurrencyInfoParser):
        """ Initialize checker.

        :param string_data_downloader: Used string data downloader.
        :param history_xml_parser: Used history xml parser.
        :param index_info_parser: Used index info parser.
        """
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

        self.string_data_downloader = string_data_downloader
        self.history_xml_parser = history_xml_parser
        self.index_info_parser = index_info_parser

    def check(self):
        self.logger.info("Check actuality via currencies list")

        rate_frequency = RateFrequencies.DAILY
        history_date_from = self._expectedFirstDate
        history_date_to = self._expectedFirstDate + datetime.timedelta(days=10)

        xml_list_result = self.string_data_downloader.download_currencies_info_string(rate_frequency)
        self.logger.debug(f"Got XML data:\n{xml_list_result.downloaded_string}")

        try:
            info_list = list(self.index_info_parser.parse(xml_list_result.downloaded_string))
        except ParseError as ex:
            xml_list_result.set_correctness(False)
            raise CheckApiActualityError(f"Unexpected currency info XML: {ex.message}") from ex
        except Exception:
            xml_list_result.set_correctness(False)
            raise

        if len(info_list) == 0:
            xml_list_result.set_correctness(False)
            raise CheckApiActualityError("Unexpected currency info list. No data")

        # here we know that check via index list was successful

        self.logger.info(f"Check actuality via currency {self._currencyToCheck!r}")

        xml_history_result = self.string_data_downloader.download_currency_history_string(
            self._currencyToCheck,
            history_date_from,
            history_date_to
        )

        try:
            history = list(self.history_xml_parser.parse(xml_history_result.downloaded_string, tzinfo=None))
        except ParseError as ex:
            xml_history_result.set_correctness(False)
            raise CheckApiActualityError(f"Unexpected currency history XML: {ex.message}") from ex
        except Exception:
            xml_history_result.set_correctness(False)
            raise

        history.sort(key=lambda v: v.date)

        first_value = history[0]  # for actuality checking one record is enough

        if first_value.currency_id != self._currencyToCheck:
            xml_history_result.set_correctness(False)
            raise CheckApiActualityError(f"Unexpected currency ID. "
                                         f"{first_value.currency_id!r} != {self._currencyToCheck!r}")

        if first_value.date != self._expectedFirstDate:
            xml_history_result.set_correctness(False)
            raise CheckApiActualityError(f"Unexpected first date. "
                                         f"{first_value.date} != {self._expectedFirstDate}")

        if first_value.nominal != self._expectedFirstNominal:
            xml_history_result.set_correctness(False)
            raise CheckApiActualityError(f"Unexpected first nominal. "
                                         f"{first_value.nominal} != {self._expectedFirstNominal}")

        if first_value.value != self._expectedFirstValue:
            xml_history_result.set_correctness(False)
            raise CheckApiActualityError(f"Unexpected first value. "
                                         f"{first_value.value} != {self._expectedFirstValue}")

        self.logger.info("Actuality check was successful")


class CbrCurrencyDownloadParameterValuesStorage(DownloadParameterValuesStorage):
    """ Storage of currency download parameters.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

        self._special_handlers: typing.Dict[type, typing.Callable] = {
            RateFrequencies: self._get_rate_frequency_choices
        }

    def is_dynamic_enum_type(self, cls: type) -> bool:
        return False

    def get_all_managed_types(self) -> typing.Iterable[typing.Type]:
        return ()

    def get_dynamic_enum_key(self, instance):
        return None

    def get_parameter_type_choices(self, cls: type) \
            -> typing.Optional[
                typing.List[typing.Tuple[typing.Any, typing.Union[str, typing.List[typing.Tuple[typing.Any, str]]]]]
            ]:

        if not inspect.isclass(cls):
            return None

        if cls not in self._special_handlers:
            return None

        return self._special_handlers[cls]()

    @staticmethod
    def _get_rate_frequency_choices():
        rate_frequency: RateFrequencies

        return [(rate_frequency.value, rate_frequency.description)
                for rate_frequency
                in RateFrequencies]


class CbrCurrencyRatesExporterFactory(InstrumentExporterFactory):
    """ Factory class for create instances of Bank of Russia data exporter.
    """
    name: str = 'Bank of Russia Foreign Currency Market Lib. Version 1.4, 2016.'
    provider_site: str = 'http://www.cbr.ru/'
    api_url: str = 'http://www.cbr.ru/development/sxml/'

    def __init__(self):
        self._dynamic_enum_type_manager = None
        self._download_parameters_factory = None

    def create_history_values_exporter(self, downloader: Downloader) -> InstrumentHistoryValuesExporter:
        string_data_downloader = CbrStringDataDownloader(downloader)
        history_values_parser = CbrCurrencyHistoryXmlParser()

        return GenericInstrumentHistoryValuesExporter(string_data_downloader, history_values_parser)

    def create_info_exporter(self, downloader: Downloader) -> InstrumentsInfoExporter:
        string_data_downloader = CbrStringDataDownloader(downloader)
        info_parser = CbrCurrencyInfoParser()

        return GenericInstrumentsInfoExporter(string_data_downloader, info_parser)

    def create_download_parameter_values_storage(
            self,
            downloader: Downloader) -> CbrCurrencyDownloadParameterValuesStorage:
        return CbrCurrencyDownloadParameterValuesStorage()

    def create_api_actuality_checker(self, downloader: Downloader) -> CbrApiActualityChecker:
        string_data_downloader = CbrStringDataDownloader(downloader)
        history_values_parser = CbrCurrencyHistoryXmlParser()
        info_parser = CbrCurrencyInfoParser()

        return CbrApiActualityChecker(string_data_downloader, history_values_parser, info_parser)

    @property
    def dynamic_enum_type_manager(self) -> CbrCurrencyDownloadParameterValuesStorage:
        if self._dynamic_enum_type_manager is None:
            self._dynamic_enum_type_manager = CbrCurrencyDownloadParameterValuesStorage()

        return self._dynamic_enum_type_manager

    @property
    def download_parameters_factory(self) -> CbrDownloadParametersFactory:
        if self._download_parameters_factory is None:
            self._download_parameters_factory = CbrDownloadParametersFactory()

        return self._download_parameters_factory
