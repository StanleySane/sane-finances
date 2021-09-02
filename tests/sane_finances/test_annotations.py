#!/usr/bin/python
# -*- coding: utf-8 -*-

import unittest

from sane_finances.annotations import Volatile


class TestVolatile(unittest.TestCase):

    def test_generate_Success(self):
        expected_result = 'OK'
        volatile = Volatile(generator=lambda _context: expected_result)

        result = volatile.generate({})

        self.assertEqual(expected_result, result)

    def test_generate_raiseWrongGenerator(self):

        with self.assertRaises(TypeError):
            # noinspection PyTypeChecker
            _ = Volatile(generator=None)
