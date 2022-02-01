#!/usr/bin/python
# -*- coding: utf-8 -*-
import collections
import datetime
import decimal
import itertools
import typing
import unittest
import random

from sane_finances.sources.base import InstrumentValue
from sane_finances.sources.computing import (
    build_sorted_history_data, build_composed_sorted_history_data, ComposeType, IntervalHistoryDataValuesType)


class TestBuildSortedHistoryData(unittest.TestCase):

    def setUp(self) -> None:
        n_years = 5
        moment_from = datetime.datetime(2000, 1, 1)
        moment_to = moment_from + datetime.timedelta(days=365 * n_years)
        self.history_data = [
            InstrumentValue(moment=datetime.datetime(year, 1, 1), value=decimal.Decimal(year) / 100)
            for year
            in range(moment_from.year, moment_to.year + 1)]

        # add intraday values
        self.history_data.extend([
            InstrumentValue(moment=iv.moment + datetime.timedelta(hours=13), value=iv.value * decimal.Decimal('1.1'))
            for iv
            in self.history_data
            if iv.moment.year % 2 == 0])

        self.history_data.sort(key=lambda iv: iv.moment)  # ensure that list is sorted

        self.history_moment_from = min(iv.moment for iv in self.history_data)
        self.history_moment_to = max(iv.moment for iv in self.history_data)

        # leave in history data only last value per day (close value)
        self.close_values_history_data = list(collections.OrderedDict((
            (iv.moment.date(), iv)
            for iv
            in self.history_data)).values())
        self.close_values_history_moment_from = min(iv.moment for iv in self.close_values_history_data)

        self.shuffled_history_data = list(self.history_data)  # copy
        random.shuffle(self.shuffled_history_data)  # disrupt sort order for testing purposes

    def get_all_days_between(
            self,
            moment_from: datetime.datetime,
            moment_to: datetime.datetime) -> typing.List[datetime.datetime]:
        """ Get sorted list of every day date in interval """
        self.assertLessEqual(moment_from, moment_to)

        all_days = []

        date_from = moment_from.date()
        date_to = moment_to.date()
        one_day = datetime.timedelta(days=1)

        interval_date = date_from
        while interval_date <= date_to:
            all_days.append(datetime.datetime.combine(
                interval_date,
                datetime.time.min,
                tzinfo=moment_from.tzinfo))
            interval_date += one_day

        return all_days

    def test_build_sorted_history_data_RaiseWithWrongIntervalDataType(self):
        build_moment_from = self.history_moment_from
        build_moment_to = self.history_moment_to

        self.assertGreaterEqual(build_moment_to, build_moment_from)

        for intraday in (True, False):
            with self.assertRaises(ValueError):
                # noinspection PyTypeChecker
                _ = build_sorted_history_data(
                    history_data=self.shuffled_history_data,
                    moment_from=build_moment_from,
                    moment_to=build_moment_to,
                    interval_data_type=None,
                    intraday=intraday)

    def test_build_sorted_history_data_ReturnEmptyWithWrongInterval(self):
        build_moment_from = self.history_moment_from
        build_moment_to = build_moment_from - datetime.timedelta(days=30)

        self.assertGreater(build_moment_from, build_moment_to)

        for interval_data_type in IntervalHistoryDataValuesType:
            for intraday in (True, False):
                sorted_history_data = build_sorted_history_data(
                    history_data=self.shuffled_history_data,
                    moment_from=build_moment_from,
                    moment_to=build_moment_to,
                    interval_data_type=interval_data_type,
                    intraday=intraday)

                self.assertSequenceEqual([], sorted_history_data)

    def test_build_sorted_history_data_ReturnEmptyBeforeHistoryBegin(self):
        build_moment_from = self.history_moment_from - datetime.timedelta(days=30)
        build_moment_to = self.history_moment_from - datetime.timedelta(microseconds=1)

        self.assertGreaterEqual(build_moment_to, build_moment_from)
        self.assertLess(build_moment_to, self.history_moment_from)

        for interval_data_type in IntervalHistoryDataValuesType:
            for intraday in (True, False):
                sorted_history_data = build_sorted_history_data(
                    history_data=self.shuffled_history_data,
                    moment_from=build_moment_from,
                    moment_to=build_moment_to,
                    interval_data_type=interval_data_type,
                    intraday=intraday)

                self.assertSequenceEqual([], sorted_history_data)

    def test_build_sorted_history_data_ReturnSingleItemOnHistoryBegin(self):
        build_moment_from = self.history_moment_from - datetime.timedelta(days=30)
        build_moment_to = self.history_moment_from

        self.assertGreaterEqual(build_moment_to, build_moment_from)
        self.assertEqual(build_moment_to, self.history_moment_from)

        expected_history_data = [(iv.moment, iv) for iv in self.history_data[:1]]
        self.assertEqual(len(expected_history_data), 1)

        for interval_data_type in IntervalHistoryDataValuesType:
            for intraday in (True, False):
                sorted_history_data = build_sorted_history_data(
                    history_data=self.shuffled_history_data,
                    moment_from=build_moment_from,
                    moment_to=build_moment_to,
                    interval_data_type=interval_data_type,
                    intraday=intraday)

                self.assertSequenceEqual(expected_history_data, sorted_history_data)

    def test_build_sorted_history_data_ReturnSingleOrNoneItemAfterHistoryEnd(self):
        build_moment_from = self.history_moment_to + datetime.timedelta(days=30)
        build_moment_to = build_moment_from

        self.assertEqual(build_moment_to, build_moment_from)  # to enforce only one item in result
        self.assertGreater(build_moment_from, self.history_moment_to)

        for interval_data_type in IntervalHistoryDataValuesType:

            # return only last item in history or empty list
            expected_history_data = (
                []
                if interval_data_type == IntervalHistoryDataValuesType.ONLY_INTERIOR_VALUES
                else [(build_moment_from, iv) for iv in self.history_data[-1:]])

            for intraday in (True, False):
                sorted_history_data = build_sorted_history_data(
                    history_data=self.shuffled_history_data,
                    moment_from=build_moment_from,
                    moment_to=build_moment_to,
                    interval_data_type=interval_data_type,
                    intraday=intraday)

                self.assertSequenceEqual(expected_history_data, sorted_history_data)

    def test_build_sorted_history_data_ReturnSingleItemOnHistoryEnd(self):
        build_moment_from = self.history_moment_to
        build_moment_to = build_moment_from

        self.assertEqual(build_moment_to, build_moment_from)  # to enforce only one item in result
        self.assertEqual(build_moment_from, self.history_moment_to)

        for interval_data_type in IntervalHistoryDataValuesType:

            # return only last item in history
            expected_history_data = [(build_moment_from, iv) for iv in self.history_data[-1:]]
            self.assertEqual(len(expected_history_data), 1)

            for intraday in (True, False):
                sorted_history_data = build_sorted_history_data(
                    history_data=self.shuffled_history_data,
                    moment_from=build_moment_from,
                    moment_to=build_moment_to,
                    interval_data_type=interval_data_type,
                    intraday=intraday)

                self.assertSequenceEqual(expected_history_data, sorted_history_data)

    def test_build_sorted_history_data_ReturnEmptyWithEmptyData(self):
        build_moment_from = self.history_moment_from
        build_moment_to = self.history_moment_to

        self.assertGreaterEqual(build_moment_to, build_moment_from)

        for interval_data_type in IntervalHistoryDataValuesType:
            for intraday in (True, False):
                sorted_history_data = build_sorted_history_data(
                    history_data=[],
                    moment_from=build_moment_from,
                    moment_to=build_moment_to,
                    interval_data_type=interval_data_type,
                    intraday=intraday)

                self.assertSequenceEqual([], sorted_history_data)

    def test_build_sorted_history_data_SuccessSameInterval(self):
        build_moment_from = self.history_moment_from
        build_moment_to = self.history_moment_to

        for intraday in (True, False):
            expected_history_data = [(iv.moment, iv) for iv in (self.history_data
                                                                if intraday
                                                                else self.close_values_history_data)]

            for interval_data_type in (IntervalHistoryDataValuesType.ONLY_INTERIOR_VALUES,
                                       IntervalHistoryDataValuesType.ALLOW_PRECEDING_VALUE):
                sorted_history_data = build_sorted_history_data(
                    history_data=self.shuffled_history_data,
                    moment_from=build_moment_from,
                    moment_to=build_moment_to,
                    interval_data_type=interval_data_type,
                    intraday=intraday)

                self.assertGreaterEqual(min(moment for moment, _ in sorted_history_data), build_moment_from)
                self.assertLessEqual(max(moment for moment, _ in sorted_history_data), build_moment_to)
                self.assertEqual(len(sorted_history_data), len({moment for moment, _ in sorted_history_data}))  # unique

                self.assertSequenceEqual(expected_history_data, sorted_history_data)
                self.assertSequenceEqual([moment for moment, _ in sorted_history_data],
                                         [iv.moment for _, iv in sorted_history_data])

    def test_build_sorted_history_data_SuccessWiderInterval(self):
        build_moment_from = self.history_moment_from - datetime.timedelta(days=30)
        build_moment_to = self.history_moment_to + datetime.timedelta(days=30)

        self.assertLessEqual(build_moment_from, self.history_moment_from)
        self.assertGreaterEqual(build_moment_to, self.history_moment_to)

        for intraday in (True, False):
            expected_history_data = [(iv.moment, iv) for iv in (self.history_data
                                                                if intraday
                                                                else self.close_values_history_data)]

            for interval_data_type in (IntervalHistoryDataValuesType.ONLY_INTERIOR_VALUES,
                                       IntervalHistoryDataValuesType.ALLOW_PRECEDING_VALUE):
                sorted_history_data = build_sorted_history_data(
                    history_data=self.shuffled_history_data,
                    moment_from=build_moment_from,
                    moment_to=build_moment_to,
                    interval_data_type=interval_data_type,
                    intraday=intraday)

                self.assertGreaterEqual(min(moment for moment, _ in sorted_history_data), build_moment_from)
                self.assertLessEqual(max(moment for moment, _ in sorted_history_data), build_moment_to)
                self.assertEqual(len(sorted_history_data), len({moment for moment, _ in sorted_history_data}))  # unique

                self.assertSequenceEqual(expected_history_data, sorted_history_data)
                self.assertSequenceEqual([moment for moment, _ in sorted_history_data],
                                         [iv.moment for _, iv in sorted_history_data])

    def test_build_sorted_history_data_SuccessNarrowerIntervalPreceding(self):
        for intraday in (True, False):
            history_moment_from = self.history_moment_from if intraday else self.close_values_history_moment_from
            history_data_source = self.history_data if intraday else self.close_values_history_data

            build_moment_from = history_moment_from + datetime.timedelta(hours=1)  # delta for the first item only
            build_moment_to = self.history_moment_to

            self.assertGreater(build_moment_from, history_moment_from)
            self.assertGreaterEqual(build_moment_to, self.history_moment_to)
            # ensure that there only one value from history is outside the interval (just for simpler testing):
            self.assertEqual(1, len([iv for iv in history_data_source if iv.moment < build_moment_from]))

            # first value moment shifted to the interval beginning:
            expected_history_data = ([(build_moment_from, history_data_source[0])] +
                                     [(iv.moment, iv) for iv in history_data_source[1:]])

            sorted_history_data = build_sorted_history_data(
                history_data=self.shuffled_history_data,
                moment_from=build_moment_from,
                moment_to=build_moment_to,
                interval_data_type=IntervalHistoryDataValuesType.ALLOW_PRECEDING_VALUE,
                intraday=intraday)

            self.assertGreaterEqual(min(moment for moment, _ in sorted_history_data), build_moment_from)
            self.assertLessEqual(max(moment for moment, _ in sorted_history_data), build_moment_to)
            self.assertEqual(len(sorted_history_data), len({moment for moment, _ in sorted_history_data}))  # unique

            self.assertSequenceEqual(expected_history_data, sorted_history_data)
            # here we know that the first item of result sorted data is preceding to the interval beginning
            # so its result moment must be strictly greater than actual history moment (because of adjustment):
            self.assertGreater(sorted_history_data[0][0], sorted_history_data[0][1].moment)
            self.assertSequenceEqual([moment for moment, _ in sorted_history_data[1:]],
                                     [iv.moment for _, iv in sorted_history_data[1:]])

    def test_build_sorted_history_data_SuccessNarrowerIntervalOnlyInterior(self):
        for intraday in (True, False):
            history_moment_from = self.history_moment_from if intraday else self.close_values_history_moment_from
            history_data_source = self.history_data if intraday else self.close_values_history_data

            build_moment_from = history_moment_from + datetime.timedelta(days=30)
            build_moment_to = self.history_moment_to - datetime.timedelta(days=30)

            self.assertGreater(build_moment_from, history_moment_from)
            self.assertLess(build_moment_to, self.history_moment_to)

            # for interior values we expect only values from inside the interval:
            expected_history_data = [(iv.moment, iv)
                                     for iv
                                     in history_data_source
                                     if build_moment_from <= iv.moment <= build_moment_to]

            sorted_history_data = build_sorted_history_data(
                history_data=self.shuffled_history_data,
                moment_from=build_moment_from,
                moment_to=build_moment_to,
                interval_data_type=IntervalHistoryDataValuesType.ONLY_INTERIOR_VALUES,
                intraday=intraday)

            self.assertGreaterEqual(min(moment for moment, _ in sorted_history_data), build_moment_from)
            self.assertLessEqual(max(moment for moment, _ in sorted_history_data), build_moment_to)
            self.assertEqual(len(sorted_history_data), len({moment for moment, _ in sorted_history_data}))  # unique

            self.assertSequenceEqual(expected_history_data, sorted_history_data)
            self.assertSequenceEqual([moment for moment, _ in sorted_history_data],
                                     [iv.moment for _, iv in sorted_history_data])

    def test_build_sorted_history_data_SuccessEveryDayWithIntraday(self):
        for intraday in (True, False):
            history_moment_from = self.history_moment_from if intraday else self.close_values_history_moment_from
            history_data_source = self.history_data if intraday else self.close_values_history_data

            intervals = (
                # same interval:
                (history_moment_from,
                 self.history_moment_to),
                # wider interval:
                (history_moment_from - datetime.timedelta(days=30),
                 self.history_moment_to + datetime.timedelta(days=30)),
                # narrower interval:
                (history_moment_from + datetime.timedelta(hours=1),  # delta for the first item only
                 self.history_moment_to),
                (history_moment_from + datetime.timedelta(days=30),
                 self.history_moment_to - datetime.timedelta(days=30))
            )

            for build_moment_from, build_moment_to in intervals:
                # list of all dates in interval:
                expected_all_days = [
                    d.date()
                    for d
                    in self.get_all_days_between(max(build_moment_from, history_moment_from), build_moment_to)]
                # list of all unique items:
                expected_history_items = [
                    iv
                    for iv, iv_next
                    in itertools.zip_longest(history_data_source, history_data_source[1:])
                    if (iv_next is None or build_moment_from < iv_next.moment) and iv.moment <= build_moment_to]

                sorted_history_data = build_sorted_history_data(
                    history_data=self.shuffled_history_data,
                    moment_from=build_moment_from,
                    moment_to=build_moment_to,
                    interval_data_type=IntervalHistoryDataValuesType.EVERY_DAY_VALUES,
                    intraday=intraday)

                result_history_items = list(collections.OrderedDict([
                    (iv.moment, iv)
                    for _, iv
                    in sorted_history_data]).values())

                self.assertGreaterEqual(min(moment for moment, _ in sorted_history_data), build_moment_from)
                self.assertLessEqual(max(moment for moment, _ in sorted_history_data), build_moment_to)
                self.assertEqual(len(sorted_history_data), len({moment for moment, _ in sorted_history_data}))  # unique

                # has same items:
                self.assertSequenceEqual(expected_history_items, result_history_items)
                # has item on every day:
                self.assertEqual(set(expected_all_days), set(moment.date() for moment, _ in sorted_history_data))
                # has no items with values from future:
                self.assertSequenceEqual([], [None for moment, iv in sorted_history_data if moment < iv.moment])
                # is sorted (has no not sorted items):
                self.assertSequenceEqual(
                    [],
                    [None
                     for (moment_prev, iv_prev), (moment, iv)
                     in zip(sorted_history_data, sorted_history_data[1:])  # itertools.pairwise analog
                     if moment < moment_prev or iv.moment < iv_prev.moment])


class TestBuildComposedSortedHistoryData(unittest.TestCase):

    def setUp(self) -> None:
        n_days = 10  # approximate count of days
        moment_from = datetime.datetime(2000, 1, 1)
        one_day = datetime.timedelta(days=1)

        self.history_data1, self.history_data2 = [], []
        history_data_value1, history_data_value2 = 1, 1
        for day_num in range(1, n_days + 1):
            current_moment = moment_from + datetime.timedelta(days=day_num - 1)

            if day_num == 1 or day_num % 7 == 0 or day_num % 5 == 0:
                self.history_data1.append(InstrumentValue(
                    moment=current_moment,
                    value=decimal.Decimal(history_data_value1 * 10)))
                history_data_value1 += 1

            if day_num == 1 or day_num % 7 == 0:
                self.history_data1.append(InstrumentValue(
                    moment=current_moment + datetime.timedelta(hours=13),
                    value=decimal.Decimal(history_data_value1 * 10)))
                history_data_value1 += 1

            if day_num % 7 == 0 or day_num % 10 == 0:
                self.history_data2.append(InstrumentValue(
                    moment=current_moment,
                    value=decimal.Decimal(history_data_value2)))
                history_data_value2 += 1

            if day_num % 7 == 0 or day_num % 5 == 0:
                self.history_data2.append(InstrumentValue(
                    moment=current_moment + one_day,
                    value=decimal.Decimal(history_data_value2)))
                history_data_value2 += 1

            if day_num == 1 or day_num % 7 == 0:
                self.history_data2.append(InstrumentValue(
                    moment=current_moment + one_day + datetime.timedelta(hours=13),
                    value=decimal.Decimal(history_data_value2)))
                history_data_value2 += 1

        self.history_data1.sort(key=lambda iv: iv.moment)  # ensure that list is sorted
        self.history_data2.sort(key=lambda iv: iv.moment)  # ensure that list is sorted

        self.history1_moment_from = min(iv.moment for iv in self.history_data1)
        self.history1_moment_to = max(iv.moment for iv in self.history_data1)

        self.history2_moment_from = min(iv.moment for iv in self.history_data2)
        self.history2_moment_to = max(iv.moment for iv in self.history_data2)

        # history 2 always latter (shifted to right in time) than history 1
        self.assertGreater(self.history2_moment_from, self.history1_moment_from)

        self.history_min_moment = min(self.history1_moment_from, self.history2_moment_from)
        self.history_max_moment = max(self.history1_moment_to, self.history2_moment_to)

        self.shuffled_history_data1 = list(self.history_data1)  # copy
        random.shuffle(self.shuffled_history_data1)  # disrupt sort order for testing purposes

        self.shuffled_history_data2 = list(self.history_data2)  # copy
        random.shuffle(self.shuffled_history_data2)  # disrupt sort order for testing purposes

    def _calculate_composed_data(
            self,
            moment_from: datetime.datetime,
            moment_to: datetime.datetime,
            compose_type: ComposeType,
            interval_data_type: IntervalHistoryDataValuesType,
            intraday: bool):
        self.assertLessEqual(moment_from, moment_to)

        composer = {ComposeType.MULTIPLY: lambda v1, v2: v1 * v2,
                    ComposeType.DIVIDE: lambda v1, v2: v1 / v2,
                    ComposeType.ADD: lambda v1, v2: v1 + v2,
                    ComposeType.SUBTRACT: lambda v1, v2: v1 - v2}[compose_type]

        # adjust moment_from to maximum of first dates in histories
        moment_from = max(moment_from, self.history1_moment_from, self.history2_moment_from)
        if moment_from > moment_to:
            return []

        history1_moments = {iv.moment for iv in self.history_data1 if moment_from <= iv.moment <= moment_to}
        history2_moments = {iv.moment for iv in self.history_data2 if moment_from <= iv.moment <= moment_to}
        all_history_moments = history1_moments | history2_moments
        if interval_data_type != IntervalHistoryDataValuesType.ONLY_INTERIOR_VALUES:
            all_history_moments |= {moment_from}

        all_moments = list(all_history_moments)
        if interval_data_type == IntervalHistoryDataValuesType.EVERY_DAY_VALUES:
            date_from = moment_from.date()
            date_to = moment_to.date()
            one_day = datetime.timedelta(days=1)

            # add to list dates missed in history
            all_history_dates = {moment.date() for moment in all_history_moments}
            interval_date = date_from
            while interval_date <= date_to:
                if interval_date not in all_history_dates:
                    all_moments.append(datetime.datetime.combine(
                        interval_date,
                        datetime.time.min,
                        tzinfo=moment_from.tzinfo))
                interval_date += one_day

        all_moments.sort()

        composed_data: typing.List[typing.Tuple[datetime.datetime, decimal.Decimal]] = []
        for moment in all_moments:
            history1_item = [iv for iv in self.history_data1 if iv.moment <= moment][-1]
            history2_item = [iv for iv in self.history_data2 if iv.moment <= moment][-1]

            composed_value = composer(history1_item.value, history2_item.value)

            composed_data.append((moment, composed_value))

        if not intraday:
            # leave in result only last value per day (close value)
            composed_data = list(collections.OrderedDict((
                (moment.date(), (moment, value))
                for moment, value
                in composed_data)).values())

        return composed_data

    def make_common_verifications(
            self,
            build_moment_from: datetime.datetime,
            build_moment_to: datetime.datetime,
            composed_sorted_history_data: typing.List[typing.Tuple[datetime.datetime, decimal.Decimal]]):
        self.assertGreaterEqual(min(moment for moment, _ in composed_sorted_history_data),
                                build_moment_from)
        self.assertLessEqual(max(moment for moment, _ in composed_sorted_history_data),
                             build_moment_to)
        self.assertEqual(len(composed_sorted_history_data),
                         len({moment for moment, _ in composed_sorted_history_data}))  # unique

        # is sorted (has no not sorted items):
        self.assertSequenceEqual(
            [],
            [None
             for (moment_prev, _), (moment, _)
             # itertools.pairwise analog:
             in zip(composed_sorted_history_data, composed_sorted_history_data[1:])
             if moment < moment_prev])

    def test_build_composed_sorted_history_data_RaiseWithWrongComposeType(self):
        build_moment_from = self.history_min_moment
        build_moment_to = self.history_max_moment

        self.assertLessEqual(build_moment_from, build_moment_to)

        for interval_data_type in IntervalHistoryDataValuesType:
            for intraday in (True, False):
                with self.assertRaisesRegex(ValueError, "'compose_type'"):
                    # noinspection PyTypeChecker
                    _ = build_composed_sorted_history_data(
                        history_data1=self.shuffled_history_data1,
                        history_data2=self.shuffled_history_data2,
                        compose_type=None,
                        moment_from=build_moment_from,
                        moment_to=build_moment_to,
                        interval_data_type=interval_data_type,
                        intraday=intraday)

    def test_build_composed_sorted_history_data_RaiseWithWrongIntervalDataType(self):
        build_moment_from = self.history_min_moment
        build_moment_to = self.history_max_moment

        self.assertLessEqual(build_moment_from, build_moment_to)

        for compose_type in ComposeType:
            for intraday in (True, False):
                with self.assertRaisesRegex(ValueError, "'interval_data_type'"):
                    # noinspection PyTypeChecker
                    _ = build_composed_sorted_history_data(
                        history_data1=self.shuffled_history_data1,
                        history_data2=self.shuffled_history_data2,
                        compose_type=compose_type,
                        moment_from=build_moment_from,
                        moment_to=build_moment_to,
                        interval_data_type=None,
                        intraday=intraday)

    def test_build_composed_sorted_history_data_RaiseWithWrongComposeErrorHandler(self):
        build_moment_from = self.history_min_moment
        build_moment_to = self.history_max_moment

        self.assertLessEqual(build_moment_from, build_moment_to)

        for compose_type in ComposeType:
            for interval_data_type in IntervalHistoryDataValuesType:
                for intraday in (True, False):
                    with self.assertRaisesRegex(ValueError, "'compose_error_handler'"):
                        # noinspection PyTypeChecker
                        _ = build_composed_sorted_history_data(
                            history_data1=self.shuffled_history_data1,
                            history_data2=self.shuffled_history_data2,
                            compose_type=compose_type,
                            moment_from=build_moment_from,
                            moment_to=build_moment_to,
                            interval_data_type=interval_data_type,
                            intraday=intraday,
                            compose_error_handler=42)  # not callable handler

    def test_build_composed_sorted_history_data_ProperExceptionHandling(self):
        build_moment_from = build_moment_to = datetime.datetime(2000, 1, 1)
        history_data1 = [InstrumentValue(moment=build_moment_from, value=decimal.Decimal(42))]
        history_data2 = [InstrumentValue(moment=build_moment_from, value=decimal.Decimal(0))]  # zero

        self.assertLessEqual(build_moment_from, build_moment_to)
        self.assertEqual(history_data2[0].value, decimal.Decimal(0))

        class SomeError(Exception):
            pass

        # noinspection PyUnusedLocal,PyTypeChecker
        def _reraise_error_handler(
                ex: Exception,
                compose_operation_type: ComposeType,
                moment: datetime.datetime,
                left_value: InstrumentValue,
                right_value: InstrumentValue) -> decimal.Decimal:
            self.assertIsInstance(ex, ArithmeticError)
            raise SomeError() from ex

        for interval_data_type in IntervalHistoryDataValuesType:
            for intraday in (True, False):
                with self.assertRaises(SomeError):
                    _ = build_composed_sorted_history_data(
                        history_data1=history_data1,
                        history_data2=history_data2,
                        compose_type=ComposeType.DIVIDE,  # divide on zero to fire error
                        moment_from=build_moment_from,
                        moment_to=build_moment_to,
                        interval_data_type=interval_data_type,
                        intraday=intraday,
                        compose_error_handler=_reraise_error_handler)

        error_stub_value = decimal.Decimal(0)
        expected_result = [(build_moment_from, error_stub_value)]

        # noinspection PyUnusedLocal
        def _return_stub_error_handler(
                ex: Exception,
                compose_operation_type: ComposeType,
                moment: datetime.datetime,
                left_value: InstrumentValue,
                right_value: InstrumentValue) -> decimal.Decimal:
            self.assertIsInstance(ex, ArithmeticError)
            return error_stub_value

        for interval_data_type in IntervalHistoryDataValuesType:
            for intraday in (True, False):
                composed_sorted_history_data = build_composed_sorted_history_data(
                    history_data1=history_data1,
                    history_data2=history_data2,
                    compose_type=ComposeType.DIVIDE,  # divide on zero to fire error
                    moment_from=build_moment_from,
                    moment_to=build_moment_to,
                    interval_data_type=interval_data_type,
                    intraday=intraday,
                    compose_error_handler=_return_stub_error_handler)

                self.assertSequenceEqual(expected_result, composed_sorted_history_data)

    def test_build_composed_sorted_history_data_ReturnEmptyWithWrongInterval(self):
        build_moment_from = self.history_min_moment
        build_moment_to = build_moment_from - datetime.timedelta(days=30)

        self.assertGreater(build_moment_from, build_moment_to)

        for compose_type in ComposeType:
            for interval_data_type in IntervalHistoryDataValuesType:
                for intraday in (True, False):
                    composed_sorted_history_data = build_composed_sorted_history_data(
                        history_data1=self.shuffled_history_data1,
                        history_data2=self.shuffled_history_data2,
                        compose_type=compose_type,
                        moment_from=build_moment_from,
                        moment_to=build_moment_to,
                        interval_data_type=interval_data_type,
                        intraday=intraday)

                    self.assertSequenceEqual([], composed_sorted_history_data)

    def test_build_composed_sorted_history_data_ReturnEmptyWithEmptyData(self):
        build_moment_from = self.history_min_moment
        build_moment_to = self.history_max_moment

        self.assertLessEqual(build_moment_from, build_moment_to)

        for compose_type in ComposeType:
            for interval_data_type in IntervalHistoryDataValuesType:
                for intraday in (True, False):
                    composed_sorted_history_data = build_composed_sorted_history_data(
                        history_data1=[],  # empty
                        history_data2=self.shuffled_history_data2,
                        compose_type=compose_type,
                        moment_from=build_moment_from,
                        moment_to=build_moment_to,
                        interval_data_type=interval_data_type,
                        intraday=intraday)

                    self.assertSequenceEqual([], composed_sorted_history_data)

                    composed_sorted_history_data = build_composed_sorted_history_data(
                        history_data1=self.shuffled_history_data1,
                        history_data2=[],  # empty
                        compose_type=compose_type,
                        moment_from=build_moment_from,
                        moment_to=build_moment_to,
                        interval_data_type=interval_data_type,
                        intraday=intraday)

                    self.assertSequenceEqual([], composed_sorted_history_data)

                    composed_sorted_history_data = build_composed_sorted_history_data(
                        history_data1=[],  # empty
                        history_data2=[],  # empty
                        compose_type=compose_type,
                        moment_from=build_moment_from,
                        moment_to=build_moment_to,
                        interval_data_type=interval_data_type,
                        intraday=intraday)

                    self.assertSequenceEqual([], composed_sorted_history_data)

    def test_build_composed_sorted_history_data_ReturnEmptyBeforeHistoryBegin(self):
        build_moment_from = self.history_min_moment - datetime.timedelta(days=30)
        build_moment_to = self.history_min_moment - datetime.timedelta(microseconds=1)

        self.assertLessEqual(build_moment_from, build_moment_to)
        self.assertLess(build_moment_to, self.history_min_moment)

        for compose_type in ComposeType:
            for interval_data_type in IntervalHistoryDataValuesType:
                for intraday in (True, False):
                    composed_sorted_history_data = build_composed_sorted_history_data(
                        history_data1=self.shuffled_history_data1,
                        history_data2=self.shuffled_history_data2,
                        compose_type=compose_type,
                        moment_from=build_moment_from,
                        moment_to=build_moment_to,
                        interval_data_type=interval_data_type,
                        intraday=intraday)

                    self.assertSequenceEqual([], composed_sorted_history_data)

    def test_build_composed_sorted_history_data_ReturnEmptyBeforeLatterHistoryBegin(self):
        build_moment_from = self.history_min_moment - datetime.timedelta(days=30)
        # take "moment to" little less than beginning of the latter (shifted) history
        # i.e. "moment to" is inside one of the histories
        build_moment_to = self.history2_moment_from - datetime.timedelta(microseconds=1)

        self.assertLessEqual(build_moment_from, build_moment_to)
        self.assertGreaterEqual(build_moment_to, self.history_min_moment)
        self.assertLess(build_moment_to, self.history2_moment_from)

        for compose_type in ComposeType:
            for interval_data_type in IntervalHistoryDataValuesType:
                for intraday in (True, False):
                    composed_sorted_history_data = build_composed_sorted_history_data(
                        history_data1=self.shuffled_history_data1,
                        history_data2=self.shuffled_history_data2,
                        compose_type=compose_type,
                        moment_from=build_moment_from,
                        moment_to=build_moment_to,
                        interval_data_type=interval_data_type,
                        intraday=intraday)

                    self.assertSequenceEqual([], composed_sorted_history_data)

    def test_build_composed_sorted_history_data_ReturnSingleItemOnHistoryBegin(self):
        build_moment_from = self.history_min_moment - datetime.timedelta(days=30)
        # take "moment to" as beginning of the latter (shifted) history
        # i.e. "moment to" is inside one of the histories
        build_moment_to = self.history2_moment_from

        self.assertLessEqual(build_moment_from, build_moment_to)
        self.assertGreaterEqual(build_moment_to, self.history_min_moment)
        self.assertEqual(build_moment_to, self.history2_moment_from)

        for compose_type in ComposeType:
            for interval_data_type in IntervalHistoryDataValuesType:
                for intraday in (True, False):
                    composed_sorted_history_data = build_composed_sorted_history_data(
                        history_data1=self.shuffled_history_data1,
                        history_data2=self.shuffled_history_data2,
                        compose_type=compose_type,
                        moment_from=build_moment_from,
                        moment_to=build_moment_to,
                        interval_data_type=interval_data_type,
                        intraday=intraday)

                    self.assertEqual(len(composed_sorted_history_data), 1)

    def test_build_composed_sorted_history_data_ReturnSingleOrNoneItemAfterHistoryEnd(self):
        build_moment_from = self.history_max_moment + datetime.timedelta(days=30)
        build_moment_to = build_moment_from

        self.assertEqual(build_moment_from, build_moment_to)  # to enforce only one item in result
        self.assertGreater(build_moment_from, self.history_max_moment)

        for compose_type in ComposeType:
            for interval_data_type in IntervalHistoryDataValuesType:
                expected_result_length = (0
                                          if interval_data_type == IntervalHistoryDataValuesType.ONLY_INTERIOR_VALUES
                                          else 1)

                for intraday in (True, False):
                    composed_sorted_history_data = build_composed_sorted_history_data(
                        history_data1=self.shuffled_history_data1,
                        history_data2=self.shuffled_history_data2,
                        compose_type=compose_type,
                        moment_from=build_moment_from,
                        moment_to=build_moment_to,
                        interval_data_type=interval_data_type,
                        intraday=intraday)

                    self.assertEqual(len(composed_sorted_history_data), expected_result_length)

    def test_build_composed_sorted_history_data_ReturnSingleItemOnHistoryEnd(self):
        build_moment_from = self.history_max_moment
        build_moment_to = build_moment_from

        self.assertEqual(build_moment_from, build_moment_to)  # to enforce only one item in result
        self.assertEqual(build_moment_from, self.history_max_moment)

        for compose_type in ComposeType:
            for interval_data_type in IntervalHistoryDataValuesType:
                for intraday in (True, False):
                    composed_sorted_history_data = build_composed_sorted_history_data(
                        history_data1=self.shuffled_history_data1,
                        history_data2=self.shuffled_history_data2,
                        compose_type=compose_type,
                        moment_from=build_moment_from,
                        moment_to=build_moment_to,
                        interval_data_type=interval_data_type,
                        intraday=intraday)

                    self.assertEqual(len(composed_sorted_history_data), 1)

    def test_build_composed_sorted_history_data_SuccessSameInterval(self):
        build_moment_from = self.history_min_moment
        build_moment_to = self.history_max_moment

        self.assertLess(build_moment_from, build_moment_to)

        for compose_type in ComposeType:
            for interval_data_type in IntervalHistoryDataValuesType:
                for intraday in (True, False):
                    expected_data = self._calculate_composed_data(
                        moment_from=build_moment_from,
                        moment_to=build_moment_to,
                        compose_type=compose_type,
                        interval_data_type=interval_data_type,
                        intraday=intraday)

                    composed_sorted_history_data = build_composed_sorted_history_data(
                        history_data1=self.shuffled_history_data1,
                        history_data2=self.shuffled_history_data2,
                        compose_type=compose_type,
                        moment_from=build_moment_from,
                        moment_to=build_moment_to,
                        interval_data_type=interval_data_type,
                        intraday=intraday)

                    self.assertSequenceEqual(expected_data, composed_sorted_history_data)

                    self.make_common_verifications(build_moment_from, build_moment_to, composed_sorted_history_data)

    def test_build_composed_sorted_history_data_SuccessWiderInterval(self):
        build_moment_from = self.history_min_moment - datetime.timedelta(days=30)
        build_moment_to = self.history_max_moment + datetime.timedelta(days=30)

        self.assertLessEqual(build_moment_from, self.history_min_moment)
        self.assertGreaterEqual(build_moment_to, self.history_max_moment)

        for compose_type in ComposeType:
            for interval_data_type in IntervalHistoryDataValuesType:
                for intraday in (True, False):
                    expected_data = self._calculate_composed_data(
                        moment_from=build_moment_from,
                        moment_to=build_moment_to,
                        compose_type=compose_type,
                        interval_data_type=interval_data_type,
                        intraday=intraday)

                    composed_sorted_history_data = build_composed_sorted_history_data(
                        history_data1=self.shuffled_history_data1,
                        history_data2=self.shuffled_history_data2,
                        compose_type=compose_type,
                        moment_from=build_moment_from,
                        moment_to=build_moment_to,
                        interval_data_type=interval_data_type,
                        intraday=intraday)

                    self.assertSequenceEqual(expected_data, composed_sorted_history_data)

                    self.make_common_verifications(build_moment_from, build_moment_to, composed_sorted_history_data)

    def test_build_composed_sorted_history_data_SuccessNarrowerInterval(self):
        intervals = (
            (self.history_min_moment + datetime.timedelta(microseconds=1),
             self.history_max_moment),
            (self.history_min_moment + datetime.timedelta(days=3),
             self.history_max_moment - datetime.timedelta(days=2)),

            (self.history2_moment_from + datetime.timedelta(microseconds=1),
             self.history_max_moment),
            (self.history2_moment_from + datetime.timedelta(days=3),
             self.history_max_moment - datetime.timedelta(days=2))
        )

        for build_moment_from, build_moment_to in intervals:
            self.assertGreater(build_moment_from, self.history_min_moment)
            self.assertLessEqual(build_moment_from, build_moment_to)

            for compose_type in ComposeType:
                for interval_data_type in IntervalHistoryDataValuesType:
                    for intraday in (True, False):
                        expected_data = self._calculate_composed_data(
                            moment_from=build_moment_from,
                            moment_to=build_moment_to,
                            compose_type=compose_type,
                            interval_data_type=interval_data_type,
                            intraday=intraday)

                        composed_sorted_history_data = build_composed_sorted_history_data(
                            history_data1=self.shuffled_history_data1,
                            history_data2=self.shuffled_history_data2,
                            compose_type=compose_type,
                            moment_from=build_moment_from,
                            moment_to=build_moment_to,
                            interval_data_type=interval_data_type,
                            intraday=intraday)

                        self.assertSequenceEqual(expected_data, composed_sorted_history_data)

                        self.make_common_verifications(build_moment_from, build_moment_to, composed_sorted_history_data)
