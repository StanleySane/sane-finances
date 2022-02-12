""" Sources from Yahoo Finance.
"""
from . import v8
from ..generic import InstrumentExporterRegistry, register_instrument_history_values_exporter

__all__ = ['v8']

register_instrument_history_values_exporter(
    InstrumentExporterRegistry(
        name=v8.exporters.YahooFinanceExporterFactory.name,
        provider_site=v8.exporters.YahooFinanceExporterFactory.provider_site,
        factory=v8.exporters.YahooFinanceExporterFactory()
    ))
