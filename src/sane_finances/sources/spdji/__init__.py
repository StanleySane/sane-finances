""" Sources from Yahoo Finance.
"""
from . import v2021, v2024
from ..generic import InstrumentExporterRegistry, register_instrument_history_values_exporter

__all__ = ['v2021', 'v2024']

register_instrument_history_values_exporter(
    InstrumentExporterRegistry(
        name=v2021.exporters.SpdjExporterFactory.name,
        provider_site=v2021.exporters.SpdjExporterFactory.provider_site,
        factory=v2021.exporters.SpdjExporterFactory()
    ))

register_instrument_history_values_exporter(
    InstrumentExporterRegistry(
        name=v2024.exporters.SpdjExporterFactory.name,
        provider_site=v2024.exporters.SpdjExporterFactory.provider_site,
        factory=v2024.exporters.SpdjExporterFactory()
    ))
