#!/usr/bin/python
# -*- coding: utf-8 -*-

import unittest

from sane_finances.sources.inspection import InstrumentInfoParameter


class TestInstrumentInfoParameter(unittest.TestCase):

    def test_Success(self):
        _ = InstrumentInfoParameter()
        _ = InstrumentInfoParameter(instrument_identity=True)
