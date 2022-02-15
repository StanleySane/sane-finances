#!/usr/bin/env python
# -*- coding: utf-8 -*-
import typing

# DO NOT IMPORT HERE ANYTHING FROM sane_finances.sources
from .common import CommonTestCases


class TestSpdjV2021Register(CommonTestCases.CommonSourceRegisterTests):

    def get_source_instrument_exporter_factory(self) -> typing.Type:
        from sane_finances.sources.spdji.v2021.exporters import SpdjExporterFactory
        return SpdjExporterFactory
