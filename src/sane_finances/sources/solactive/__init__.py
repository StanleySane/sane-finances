""" Sources from Solactive.
"""
from . import v2018
from ..generic import InstrumentExporterRegistry, register_instrument_history_values_exporter

__all__ = ['v2018']

register_instrument_history_values_exporter(
    InstrumentExporterRegistry(
        name=v2018.exporters.SolactiveExporterFactory.name,
        provider_site=v2018.exporters.SolactiveExporterFactory.provider_site,
        factory=v2018.exporters.SolactiveExporterFactory()
    ))
