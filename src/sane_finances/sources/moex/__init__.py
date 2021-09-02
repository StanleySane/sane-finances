""" Sources from Moscow Exchange.
"""
from . import v1_3
from ..generic import InstrumentExporterRegistry, register_instrument_history_values_exporter

__all__ = ['v1_3']

register_instrument_history_values_exporter(
    InstrumentExporterRegistry(
        name=v1_3.exporters.MoexIndexExporterFactory_v1_3.name,
        provider_site=v1_3.exporters.MoexIndexExporterFactory_v1_3.provider_site,
        api_url=v1_3.exporters.MoexIndexExporterFactory_v1_3.api_url,
        factory=v1_3.exporters.MoexIndexExporterFactory_v1_3()
    ))
