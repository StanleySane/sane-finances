""" Sources from MSCI.
"""
from . import v1, v2021
from ..generic import InstrumentExporterRegistry, register_instrument_history_values_exporter

__all__ = ['v1', 'v2021']

register_instrument_history_values_exporter(
    InstrumentExporterRegistry(
        name=v1.exporters.MsciIndexExporterFactory.name,
        provider_site=v1.exporters.MsciIndexExporterFactory.provider_site,
        api_url=v1.exporters.MsciIndexExporterFactory.api_url,
        factory=v1.exporters.MsciIndexExporterFactory()
    ))

register_instrument_history_values_exporter(
    InstrumentExporterRegistry(
        name=v2021.exporters.MsciIndexExporterFactory.name,
        provider_site=v2021.exporters.MsciIndexExporterFactory.provider_site,
        api_url=v2021.exporters.MsciIndexExporterFactory.api_url,
        factory=v2021.exporters.MsciIndexExporterFactory()
    ))
