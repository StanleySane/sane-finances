""" Sources from Central Bank of Russia.
"""
from . import v2016
from ..generic import InstrumentExporterRegistry, register_instrument_history_values_exporter

__all__ = ['v2016']

register_instrument_history_values_exporter(
    InstrumentExporterRegistry(
        name=v2016.exporters.CbrCurrencyRatesExporterFactory.name,
        provider_site=v2016.exporters.CbrCurrencyRatesExporterFactory.provider_site,
        api_url=v2016.exporters.CbrCurrencyRatesExporterFactory.api_url,
        factory=v2016.exporters.CbrCurrencyRatesExporterFactory()
    ))
