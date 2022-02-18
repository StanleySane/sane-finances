""" Sources from LBMA.
"""
from . import v2021
from ..generic import InstrumentExporterRegistry, register_instrument_history_values_exporter

__all__ = ['v2021']

register_instrument_history_values_exporter(
    InstrumentExporterRegistry(
        name=v2021.exporters.LbmaExporterFactory.name,
        provider_site=v2021.exporters.LbmaExporterFactory.provider_site,
        factory=v2021.exporters.LbmaExporterFactory()
    ))
