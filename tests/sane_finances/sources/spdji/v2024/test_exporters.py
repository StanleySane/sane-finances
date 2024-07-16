#!/usr/bin/env python
# -*- coding: utf-8 -*-

from sane_finances.sources.base import InstrumentExporterFactory
from sane_finances.sources.spdji.v2024.exporters import SpdjExporterFactory

from .common import CommonTestCases
from ..v2021 import test_exporters


class TestSpdjStringDataDownloader(test_exporters.TestSpdjStringDataDownloader):
    """
    Logic is absolutely the same as for the 2021 version
    """
    pass


class TestSpdjExporterFactory(CommonTestCases.CommonInstrumentExporterFactoryTests):

    def get_exporter_factory(self) -> InstrumentExporterFactory:
        return SpdjExporterFactory()

    def is_dynamic_enum_type_manager_singleton(self):
        return True

    def is_download_parameters_factory_singleton(self):
        return True
