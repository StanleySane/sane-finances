#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Generic functionality for sources.
"""

import datetime
import inspect
import typing
import logging

from ..communication.downloader import DownloadError
from .base import (
    InstrumentStringDataDownloader, SourceDownloadError,
    InstrumentValuesHistoryParser, InstrumentInfoParser, InstrumentHistoryValuesExporter,
    InstrumentInfoProvider, InstrumentValueProvider,
    InstrumentExporterRegistry, InstrumentExporterFactory, InstrumentsInfoExporter,
    InstrumentHistoryDownloadParameters, InstrumentValuesHistoryEmpty, MaxPagesLimitExceeded)

logging.getLogger().addHandler(logging.NullHandler())


class GenericInstrumentHistoryValuesExporter(InstrumentHistoryValuesExporter):
    """ Generic, used by default, instrument history exporter.
    """
    max_paged_parameters = 10000  # limit of paged parameters

    def __init__(
            self,
            string_data_downloader: InstrumentStringDataDownloader,
            history_values_parser: InstrumentValuesHistoryParser):
        """ Initialize exporter.

        :param string_data_downloader: Used instrument string data downloader.
        :param history_values_parser: Used instrument values history parser.
        """
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

        self.string_data_downloader = string_data_downloader
        self.history_values_parser = history_values_parser

    def export_instrument_history_values(
            self,
            parameters: InstrumentHistoryDownloadParameters,
            moment_from: datetime.datetime,
            moment_to: datetime.datetime) -> typing.Iterable[InstrumentValueProvider]:

        if moment_from > moment_to:
            raise ValueError(f"Moment from ({moment_from}) is greater then moment to ({moment_to})")

        self.logger.info(f"Begin to export instrument history values "
                         f"in [{moment_from.isoformat(), moment_to.isoformat()}] "
                         f"by parameters: {parameters}")

        parameters, moment_from, moment_to = self.string_data_downloader.adjust_download_instrument_history_parameters(
            parameters=parameters,
            moment_from=moment_from,
            moment_to=moment_to)
        self.logger.info(f"Parameters was adjusted to: {parameters}")
        self.logger.info(f"Interval was adjusted to: {moment_from.isoformat()}..{moment_to.isoformat()}")

        paged_parameters_index = 0
        for paged_parameters, paged_moment_from, paged_moment_to in \
                self.string_data_downloader.paginate_download_instrument_history_parameters(
                    parameters=parameters,
                    moment_from=moment_from,
                    moment_to=moment_to):
            self.logger.info(f"Begin to export instrument history values "
                             f"by paged parameters: {paged_parameters}, "
                             f"paged interval: {paged_moment_from}..{paged_moment_to}")

            paged_parameters_index += 1
            if paged_parameters_index >= self.max_paged_parameters:
                raise MaxPagesLimitExceeded(self.max_paged_parameters)

            try:
                history_data_string_result = \
                    self.string_data_downloader.download_instrument_history_string(
                        parameters=paged_parameters,
                        moment_from=paged_moment_from,
                        moment_to=paged_moment_to)

            except DownloadError as ex:
                raise SourceDownloadError(f"Download error {ex} for parameters '{parameters}', "
                                          f"moment from '{moment_from.isoformat()}', "
                                          f"moment to '{moment_to.isoformat()}'") from ex

            try:
                values_providers = self.history_values_parser.parse(
                    history_data_string_result.downloaded_string,
                    moment_from.tzinfo)

                all_values = ((value_provider.get_instrument_value(moment_from.tzinfo), value_provider)
                              for value_provider
                              in values_providers)
                value_providers = (value_provider
                                   for value, value_provider
                                   in all_values
                                   if moment_from <= value.moment <= moment_to)

                yield from value_providers

            except InstrumentValuesHistoryEmpty:
                # history data exhausted
                history_data_string_result.set_correctness(True)
                return

            except Exception:
                history_data_string_result.set_correctness(False)
                raise

            history_data_string_result.set_correctness(True)


class GenericInstrumentsInfoExporter(InstrumentsInfoExporter):
    """ Generic, used by default, instrument info exporter.
    """

    def __init__(
            self,
            string_data_downloader: InstrumentStringDataDownloader,
            info_parser: InstrumentInfoParser):
        """ Initialize exporter.

        :param string_data_downloader: Used instrument string data downloader.
        :param info_parser: Used instrument info parser.
        """
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

        self.string_data_downloader = string_data_downloader
        self.info_parser = info_parser

    def export_instruments_info(self, parameters) -> typing.Iterator[InstrumentInfoProvider]:
        self.logger.info(f"Begin to export instruments info "
                         f"by parameters: {parameters}")

        info_data_string_result = \
            self.string_data_downloader.download_instruments_info_string(parameters=parameters)

        try:
            info_providers = self.info_parser.parse(info_data_string_result.downloaded_string)

            yield from info_providers

        except Exception:
            info_data_string_result.set_correctness(False)
            raise

        info_data_string_result.set_correctness(True)


# Global registry for all available sources and theirs factories
_GlobalInstrumentExporterRegistry: \
    typing.Dict[typing.Type[InstrumentExporterFactory], InstrumentExporterRegistry] = {}


def register_instrument_history_values_exporter(registry: InstrumentExporterRegistry):
    """ Register instrument data exporter. Validate `registry` and store it in internal global cache.

    :param registry: Instrument exporter to register.
    """
    if registry is None:
        raise ValueError("'registry' is None")
    if not isinstance(registry, InstrumentExporterRegistry):
        raise TypeError(f"'registry' is not {InstrumentExporterRegistry.__name__}: {registry!r}")

    if registry.factory is None:
        raise ValueError("'registry.factory' is None")
    if not isinstance(registry.factory, InstrumentExporterFactory):
        raise TypeError(f"'registry.factory' is not {InstrumentExporterFactory.__name__}: {registry.factory!r}")

    if registry.factory.__class__ in _GlobalInstrumentExporterRegistry:
        raise ValueError(f"Factory {registry.factory!r} already registered")

    if registry.name is None:
        raise ValueError("'registry.name' is None")
    if not str(registry.name).strip():
        raise ValueError("'registry.name' is empty or whitespace only")

    _GlobalInstrumentExporterRegistry[registry.factory.__class__] = registry


def get_all_instrument_exporters() -> typing.Tuple[InstrumentExporterRegistry, ...]:
    """ Get all available (registered) instrument data exporters.

    :return: Tuple of all available (registered) instrument data exporters
    """
    return tuple(_GlobalInstrumentExporterRegistry.values())


def get_instrument_exporter_by_factory(
        factory: typing.Union[typing.Type[InstrumentExporterFactory], InstrumentExporterFactory]) \
        -> typing.Optional[InstrumentExporterRegistry]:
    """ Find registered instrument data exporter by its factory (instance or class) and return it.

    :param factory: Factory instance or class of registered data exporter.
    :return: ``None`` if not found.
    """
    if inspect.isclass(factory):
        return _GlobalInstrumentExporterRegistry.get(factory, None)

    factory: InstrumentExporterFactory
    return _GlobalInstrumentExporterRegistry.get(factory.__class__, None)
