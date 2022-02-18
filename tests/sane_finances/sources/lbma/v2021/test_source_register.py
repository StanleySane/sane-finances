#!/usr/bin/env python
# -*- coding: utf-8 -*-
import typing

# DO NOT IMPORT HERE ANYTHING FROM sane_finances.sources
from .common import CommonTestCases


class TestISharesV2021Register(CommonTestCases.CommonSourceRegisterTests):

    def get_source_instrument_exporter_factory(self) -> typing.Type:
        from sane_finances.sources.lbma.v2021.exporters import LbmaExporterFactory
        return LbmaExporterFactory
