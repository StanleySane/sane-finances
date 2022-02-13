#!/usr/bin/env python
# -*- coding: utf-8 -*-
import typing

# DO NOT IMPORT HERE ANYTHING FROM sane_finances.sources
from .common import CommonTestCases


class TestYahooV8Register(CommonTestCases.CommonSourceRegisterTests):

    def get_source_instrument_exporter_factory(self) -> typing.Type:
        from sane_finances.sources.cbr.v2016.exporters import CbrCurrencyRatesExporterFactory
        return CbrCurrencyRatesExporterFactory
