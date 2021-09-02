#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest

from sane_finances.communication.downloader import DownloadStringResult


class TestDownloadStringResult(unittest.TestCase):

    def test_Success(self):
        expected_string = 'OK'
        result = DownloadStringResult(expected_string)

        self.assertEqual(result.downloaded_string, expected_string)

        result.set_correctness(True)

        self.assertEqual(result.downloaded_string, expected_string)
        self.assertTrue(result.is_correct)

        result.set_correctness(False)

        self.assertEqual(result.downloaded_string, expected_string)
        self.assertFalse(result.is_correct)
