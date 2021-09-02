#!/usr/bin/python
# -*- coding: utf-8 -*-

import unittest

from sane_finances.retry_policy import wait_and_retry


class TestWaitAndRetry(unittest.TestCase):

    def setUp(self):
        self.alwaysRaisingActionCount = 0
        self.properRaisingActionCount = 0

    def alwaysRaisingAction(self, x):
        self.alwaysRaisingActionCount += 1
        raise x

    def properRaisingAction(self, x, num_of_raised):
        """
        - *x* - Exception to be raised
        - *num_of_raised* - Number of calls (not only retries) when exception *x* raises
        """
        self.properRaisingActionCount += 1
        if self.properRaisingActionCount <= num_of_raised:
            raise x

    def test_raisedForNotValidAction(self):
        with self.assertRaises(ValueError):
            # noinspection PyTypeChecker
            wait_and_retry(None, lambda: True)

    def test_raisedForNotValidTransientValidator(self):
        with self.assertRaises(ValueError):
            # noinspection PyTypeChecker
            wait_and_retry(lambda: None, None)

    def test_actionCallsProperCountOfTimesWIthSleep(self):
        retry_count = 2
        estimated_action_calls = retry_count + 1

        with self.assertRaises(StopIteration):
            wait_and_retry(
                action=lambda: self.alwaysRaisingAction(StopIteration),
                transient_validator=lambda x, n: True,
                max_retry_count=retry_count,
                sleep_duration_factor=0.01,
                first_sleep_duration=0.01  # sleep a little
            )

        self.assertEqual(
            self.alwaysRaisingActionCount,
            estimated_action_calls,
            "Action called not proper num of times"
        )

    def test_actionCallsProperCountOfTimesAndAdjustParams(self):
        estimated_action_calls = 1

        with self.assertRaises(StopIteration):
            wait_and_retry(
                action=lambda: self.alwaysRaisingAction(StopIteration),
                transient_validator=lambda x, n: True,
                max_retry_count=-1,
                sleep_duration_factor=-1.0,
                first_sleep_duration=-1.0
            )

        self.assertEqual(
            self.alwaysRaisingActionCount,
            estimated_action_calls,
            "Action called not proper num of times"
        )

    def test_actionCallsProperCountOfTimesNeverRetry(self):
        retry_count = 0
        estimated_action_calls = retry_count + 1

        with self.assertRaises(StopIteration):
            wait_and_retry(
                action=lambda: self.alwaysRaisingAction(StopIteration),
                transient_validator=lambda x, n: True,
                max_retry_count=retry_count,
                first_sleep_duration=0.0  # do not sleep
            )

        self.assertEqual(
            self.alwaysRaisingActionCount,
            estimated_action_calls,
            "Action called not proper num of times"
        )

    def test_actionCallsProperCountOfTimes(self):
        retry_count = 5
        estimated_action_calls = retry_count + 1

        with self.assertRaises(StopIteration):
            wait_and_retry(
                action=lambda: self.alwaysRaisingAction(StopIteration),
                transient_validator=lambda x, n: True,
                max_retry_count=retry_count,
                first_sleep_duration=0.0  # do not sleep
            )

        self.assertEqual(
            self.alwaysRaisingActionCount,
            estimated_action_calls,
            "Action called not proper num of times"
        )

    def test_actionCallsProperCountOfTimesIfTransient(self):
        transient_retry_count = 5  # num of retries when exception is supposed to be transient;
        # after that every exception is critical

        retry_count = transient_retry_count * 2  # retry much more than *transient_retry_count* admits
        estimated_action_calls = transient_retry_count + 1

        self.assertGreater(retry_count, transient_retry_count, "Wrong test setting")

        with self.assertRaises(StopIteration):
            wait_and_retry(
                action=lambda: self.alwaysRaisingAction(StopIteration),
                transient_validator=lambda x, n: n <= transient_retry_count,
                max_retry_count=retry_count,
                first_sleep_duration=0.0  # do not sleep
            )

        self.assertEqual(
            self.alwaysRaisingActionCount,
            estimated_action_calls,
            "Action called not proper num of times for transient exception"
        )

    def test_successAfterFailedActions(self):
        failed_calls = 5
        retry_count = failed_calls + 1
        estimated_action_calls = failed_calls + 1

        self.assertGreater(retry_count, failed_calls, "Wrong test setting")

        wait_and_retry(
            action=lambda: self.properRaisingAction(StopIteration, failed_calls),
            transient_validator=lambda x, n: True,
            max_retry_count=retry_count,
            first_sleep_duration=0.0  # do not sleep
        )

        self.assertEqual(
            self.properRaisingActionCount,
            estimated_action_calls,
            "Action called not proper num of times before success"
        )
