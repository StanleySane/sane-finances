#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import unittest

from sane_finances.communication.cachers import ExpiryCalculator, DummyCacher, InMemoryCacher

from .fakes import FakeExpiryCalculator


class TestExpiryCalculator(unittest.TestCase):

    def test_is_expired_Success(self):
        yesterday = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=1)
        tomorrow = datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(days=1)
        calculator = ExpiryCalculator()

        self.assertTrue(calculator.is_expired(yesterday))
        self.assertFalse(calculator.is_expired(tomorrow))

    def test_get_revive_moment_Success(self):
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        calculator = ExpiryCalculator()

        revive_moment = calculator.get_revive_moment()

        self.assertGreaterEqual(revive_moment, now)

    def test_get_expiry_moment_Success(self):
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        delta = datetime.timedelta(days=1)
        expected_result = now + delta
        calculator = ExpiryCalculator()

        result = calculator.get_expiry_moment(delta, now)

        self.assertEqual(result, expected_result)

    def test_get_expiry_moment_ShiftFromNow(self):
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        delta = datetime.timedelta(days=1)
        expected_result = now + delta
        calculator = ExpiryCalculator()

        result = calculator.get_expiry_moment(delta)  # no start_from

        self.assertGreaterEqual(result, expected_result)


class TestDummyCacher(unittest.TestCase):

    def setUp(self):
        self.dummy_reviver_count = 0
        self.success_string = 'OK'

    def dummy_reviver(self):
        self.dummy_reviver_count += 1
        return self.success_string

    def test_retrieve_Success(self):
        cacher = DummyCacher()

        (got_from_cache, result) = cacher.retrieve('', [], {}, self.dummy_reviver)

        self.assertFalse(got_from_cache)
        self.assertEqual(result, self.success_string)
        self.assertEqual(self.dummy_reviver_count, 1)

    def test_drop_NeverDrop(self):
        cacher = DummyCacher()

        result = cacher.drop('', [], {})

        self.assertFalse(result)

    def test_has_NeverHas(self):
        cacher = DummyCacher()

        result = cacher.has('', [], {})

        self.assertFalse(result)

    def test_is_empty_AlwaysEmpty(self):
        cacher = DummyCacher()

        result = cacher.is_empty()

        self.assertTrue(result)

    def test_full_clear_AlwaysSuccess(self):
        cacher = DummyCacher()
        cacher.full_clear()


class TestInMemoryCacher(unittest.TestCase):

    def setUp(self) -> None:
        self.expected_result = 'OK'
        self.retriever_count = 0
        self.expiry_calculator = FakeExpiryCalculator(datetime.datetime(2000, 1, 1))
        self.cacher = InMemoryCacher(expiry_calculator=self.expiry_calculator)

    def retriever(self):
        self.retriever_count += 1
        return self.expected_result

    def test_expiry_DefaultExpiry(self):
        default_expiry = self.cacher.expiry

        self.assertEqual(default_expiry, self.cacher.default_expiry)

    def test_expiry_ExpiryChanges(self):
        new_expiry = datetime.timedelta(days=1)
        self.cacher.expiry = new_expiry

        self.assertEqual(self.cacher.expiry, new_expiry)

    def test_CahersHasNoCommonState(self):
        expiry_days = 1
        self.cacher.expiry = datetime.timedelta(days=expiry_days)

        # create second cacher
        another_cacher = InMemoryCacher(expiry_calculator=self.expiry_calculator)
        another_cacher.expiry = datetime.timedelta(days=expiry_days)

        # add items in first cache
        got_from_cache, result = self.cacher.retrieve('', [], {}, self.retriever)

        self.assertFalse(got_from_cache)
        self.assertEqual(result, self.expected_result)
        self.assertEqual(self.retriever_count, 1)
        self.assertTrue(self.cacher.has('', [], {}))
        self.assertFalse(self.cacher.is_empty())

        # second cache should stay empty
        self.assertFalse(another_cacher.has('', [], {}))
        self.assertTrue(another_cacher.is_empty())

    def test_ExpiresSuccess(self):
        now = self.expiry_calculator.now
        expiry_days = 1
        self.cacher.expiry = datetime.timedelta(days=expiry_days)

        # add items in cache
        got_from_cache, result = self.cacher.retrieve('', [], {}, self.retriever)

        self.assertFalse(got_from_cache)
        self.assertEqual(result, self.expected_result)
        self.assertEqual(self.retriever_count, 1)
        self.assertTrue(self.cacher.has('', [], {}))
        self.assertFalse(self.cacher.is_empty())

        # test that it's inside
        got_from_cache, result = self.cacher.retrieve('', [], {}, self.retriever)

        self.assertTrue(got_from_cache)
        self.assertEqual(result, self.expected_result)
        self.assertEqual(self.retriever_count, 1)  # didn't changed
        self.assertTrue(self.cacher.has('', [], {}))
        self.assertFalse(self.cacher.is_empty())

        # two days later
        now += datetime.timedelta(days=expiry_days*2)
        self.expiry_calculator.now = now

        # cache should be cleaned
        self.assertEqual(self.retriever_count, 1)  # didn't changed
        self.assertFalse(self.cacher.has('', [], {}))
        self.assertTrue(self.cacher.is_empty())

    def test_NotExpiresSuccess(self):
        now = self.expiry_calculator.now
        expiry_days = 4
        self.cacher.expiry = datetime.timedelta(days=expiry_days)

        # add items in cache
        got_from_cache, result = self.cacher.retrieve('', [], {}, self.retriever)

        self.assertFalse(got_from_cache)
        self.assertEqual(result, self.expected_result)
        self.assertEqual(self.retriever_count, 1)
        self.assertTrue(self.cacher.has('', [], {}))
        self.assertFalse(self.cacher.is_empty())

        # test that it's inside
        got_from_cache, result = self.cacher.retrieve('', [], {}, self.retriever)

        self.assertTrue(got_from_cache)
        self.assertEqual(result, self.expected_result)
        self.assertEqual(self.retriever_count, 1)  # didn't changed
        self.assertTrue(self.cacher.has('', [], {}))
        self.assertFalse(self.cacher.is_empty())

        # two days later
        now += datetime.timedelta(days=expiry_days/2)
        self.expiry_calculator.now = now

        # items should persist
        self.assertEqual(self.retriever_count, 1)  # didn't changed
        self.assertTrue(self.cacher.has('', [], {}))
        self.assertFalse(self.cacher.is_empty())

    def test_expiry_CleanedWhenChanged(self):
        now = self.expiry_calculator.now
        self.cacher.expiry = datetime.timedelta(days=1)

        # add items in cache
        got_from_cache, result = self.cacher.retrieve('', [], {}, self.retriever)

        self.assertFalse(got_from_cache)
        self.assertEqual(result, self.expected_result)
        self.assertEqual(self.retriever_count, 1)
        self.assertTrue(self.cacher.has('', [], {}))
        self.assertFalse(self.cacher.is_empty())

        # test that it's inside
        got_from_cache, result = self.cacher.retrieve('', [], {}, self.retriever)

        self.assertTrue(got_from_cache)
        self.assertEqual(result, self.expected_result)
        self.assertEqual(self.retriever_count, 1)  # didn't changed
        self.assertTrue(self.cacher.has('', [], {}))
        self.assertFalse(self.cacher.is_empty())

        # another parameters - another cache item
        got_from_cache, result = self.cacher.retrieve('', [], {'a': 'a'}, self.retriever)

        self.assertFalse(got_from_cache)
        self.assertEqual(result, self.expected_result)
        self.assertEqual(self.retriever_count, 2)  # incremented
        self.assertTrue(self.cacher.has('', [], {'a': 'a'}))
        self.assertFalse(self.cacher.is_empty())

        # one hour later
        minutes_spent = 60
        now += datetime.timedelta(minutes=minutes_spent)
        self.expiry_calculator.now = now

        # change expiry to half hour
        self.cacher.expiry = datetime.timedelta(minutes=minutes_spent/2)

        # cache should be cleaned
        self.assertEqual(self.retriever_count, 2)  # didn't changed
        self.assertFalse(self.cacher.has('', [], {}))
        self.assertTrue(self.cacher.is_empty())

    def test_drop_Success(self):
        self.cacher.expiry = datetime.timedelta(days=1)

        # add items in cache
        got_from_cache, result = self.cacher.retrieve('', [], {}, self.retriever)

        self.assertFalse(got_from_cache)
        self.assertEqual(result, self.expected_result)
        self.assertEqual(self.retriever_count, 1)
        self.assertTrue(self.cacher.has('', [], {}))
        self.assertFalse(self.cacher.is_empty())

        # test that it's inside
        got_from_cache, result = self.cacher.retrieve('', [], {}, self.retriever)

        self.assertTrue(got_from_cache)
        self.assertEqual(result, self.expected_result)
        self.assertEqual(self.retriever_count, 1)  # didn't changed
        self.assertTrue(self.cacher.has('', [], {}))
        self.assertFalse(self.cacher.is_empty())

        # drop it
        was_in_cache = self.cacher.drop('', [], {})

        self.assertTrue(was_in_cache)
        self.assertEqual(self.retriever_count, 1)  # didn't changed
        self.assertFalse(self.cacher.has('', [], {}))
        self.assertTrue(self.cacher.is_empty())

        # drop again
        was_in_cache = self.cacher.drop('', [], {})

        self.assertFalse(was_in_cache)
        self.assertEqual(self.retriever_count, 1)  # didn't changed
        self.assertFalse(self.cacher.has('', [], {}))
        self.assertTrue(self.cacher.is_empty())

    def test_full_clear_Success(self):
        self.cacher.expiry = datetime.timedelta(days=1)

        # add items in cache
        got_from_cache, result = self.cacher.retrieve('', [], {}, self.retriever)

        self.assertFalse(got_from_cache)
        self.assertEqual(result, self.expected_result)
        self.assertEqual(self.retriever_count, 1)
        self.assertTrue(self.cacher.has('', [], {}))
        self.assertFalse(self.cacher.is_empty())

        # test that it's inside
        got_from_cache, result = self.cacher.retrieve('', [], {}, self.retriever)

        self.assertTrue(got_from_cache)
        self.assertEqual(result, self.expected_result)
        self.assertEqual(self.retriever_count, 1)  # didn't changed
        self.assertTrue(self.cacher.has('', [], {}))
        self.assertFalse(self.cacher.is_empty())

        # clear all
        self.cacher.full_clear()

        self.assertEqual(self.retriever_count, 1)  # didn't changed
        self.assertFalse(self.cacher.has('', [], {}))
        self.assertTrue(self.cacher.is_empty())
