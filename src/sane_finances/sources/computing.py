#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Classes for manipulations (computing, composing, etc.) with downloaded instruments history values
"""

import collections
import decimal
import datetime
import typing
import enum

from .base import InstrumentValue


class IntervalHistoryDataValuesType(enum.Enum):
    """ Type of history data inside some interval

    ``EVERY_DAY_VALUES`` - "Holes" in history (days without value) fill with preceding values (if exist),
    so every day inside interval has value (maybe repetitive).

    ``ONLY_INTERIOR_VALUES`` - History data contains only values with moments strictly inside interval.

    ``ALLOW_PRECEDING_VALUE`` - Same as ``ONLY_INTERIOR_VALUES`` but allows one additional value
    before interval beginning moment if that value still actual inside interval.
    """
    EVERY_DAY_VALUES = enum.auto()
    ONLY_INTERIOR_VALUES = enum.auto()
    ALLOW_PRECEDING_VALUE = enum.auto()


class ComposeType(enum.Enum):
    """ Type of composition of two history data sequences """
    MULTIPLY = 'multiply'
    DIVIDE = 'divide'
    ADD = 'add'
    SUBTRACT = 'subtract'


def _prepare_history_data(
        history_data: typing.List[InstrumentValue],
        moment_from: datetime.datetime,
        moment_to: datetime.datetime
) -> typing.Tuple[InstrumentValue, typing.Set[datetime.datetime], typing.Dict[datetime.datetime, InstrumentValue]]:
    """ Take full history data and prepare auxiliary structures for further analysis inside the interval

    :param history_data: Income history data (generally not sorted)
    :param moment_from: Interval beginning moment
    :param moment_to: Interval ending moment
    :return: Tuple (first_instrument_value_in_history,
      set_of_all_history_moments_for_the_interval,
      dictionary_of_history_values_for_the_interval)

    First instrument value is the earliest value in history between ``moment_from`` and ``moment_to``
    (or ``None`` if not found).
    If history data has no value on the exactly ``moment_from`` moment,
    then the first value of history takes from the nearest history value, previous to the ``moment_from`` (if exist).

    Examples::

        history_data = [InstrumentValue(42, datetime(2000, 1, 1)),
                        InstrumentValue(43, datetime(2000, 2, 1)),
                        InstrumentValue(44, datetime(2000, 3, 1)),
                        ]

        moment_from, moment_to = datetime(2000, 1, 1), datetime(2000, 3, 1)
        first_value, all_moments_set, history_dict = _prepare_history_data(history_data, moment_from, moment_to)
        # first_value = InstrumentValue(42, datetime(2000, 1, 1))
        # all_moments_set = {datetime(2000, 1, 1), datetime(2000, 2, 1), datetime(2000, 3, 1)}
        # history_dict = {datetime(2000, 1, 1): InstrumentValue(42, datetime(2000, 1, 1)),
        #                 datetime(2000, 2, 1): InstrumentValue(43, datetime(2000, 2, 1)),
        #                 datetime(2000, 3, 1): InstrumentValue(43, datetime(2000, 3, 1))}

        # narrower interval, but value for datetime(2000, 1, 1) is still in the interval
        moment_from, moment_to = datetime(2000, 1, 15), datetime(2000, 3, 1)
        first_value, all_moments_set, history_dict = _prepare_history_data(history_data, moment_from, moment_to)
        # first_value = InstrumentValue(42, datetime(2000, 1, 1))
        # all_moments_set = {datetime(2000, 1, 1), datetime(2000, 2, 1), datetime(2000, 3, 1)}
        # history_dict = {datetime(2000, 1, 1): InstrumentValue(42, datetime(2000, 1, 1)),
        #                 datetime(2000, 2, 1): InstrumentValue(43, datetime(2000, 2, 1)),
        #                 datetime(2000, 3, 1): InstrumentValue(43, datetime(2000, 3, 1))}

        # more narrow interval and now value for datetime(2000, 1, 1) is out of the interval
        # (because it acts only until 2000-02-01)
        moment_from, moment_to = datetime(2000, 2, 15), datetime(2000, 3, 1)
        first_value, all_moments_set, history_dict = _prepare_history_data(history_data, moment_from, moment_to)
        # first_value = InstrumentValue(43, datetime(2000, 2, 1))
        # all_moments_set = {datetime(2000, 2, 1), datetime(2000, 3, 1)}
        # history_dict = {datetime(2000, 2, 1): InstrumentValue(43, datetime(2000, 2, 1)),
        #                 datetime(2000, 3, 1): InstrumentValue(43, datetime(2000, 3, 1))}

        # wider interval, so the value for datetime(2000, 1, 1) is in the interval
        # but much latter to ``moment_from``
        moment_from, moment_to = datetime(1999, 1, 1), datetime(2000, 3, 1)
        first_value, all_moments_set, history_dict = _prepare_history_data(history_data, moment_from, moment_to)
        # first_value = InstrumentValue(42, datetime(2000, 1, 1))
        # all_moments_set = {datetime(2000, 1, 1), datetime(2000, 2, 1), datetime(2000, 3, 1)}
        # history_dict = {datetime(2000, 1, 1): InstrumentValue(42, datetime(2000, 1, 1)),
        #                 datetime(2000, 2, 1): InstrumentValue(43, datetime(2000, 2, 1)),
        #                 datetime(2000, 3, 1): InstrumentValue(43, datetime(2000, 3, 1))}

        # interval places before history data
        moment_from, moment_to = datetime(1900, 1, 1), datetime(1900, 12, 31)
        first_value, all_moments_set, history_dict = _prepare_history_data(history_data, moment_from, moment_to)
        # first_value = None
        # all_moments_set = {}
        # history_dict = {}

    """
    # find first moment ever
    first_moment = min(instrument_value.moment for instrument_value in history_data)
    # find last moment before moment_from
    first_moment = max((instrument_value.moment
                        for instrument_value
                        in history_data
                        if instrument_value.moment <= moment_from), default=first_moment)

    # cut from the history not interesting (via ``if``) and duplicated (via ``dict``) moments
    history_dict = {instrument_value.moment: instrument_value
                    for instrument_value
                    in history_data
                    if first_moment <= instrument_value.moment <= moment_to}

    return history_dict.get(first_moment, None), set(history_dict.keys()), history_dict


def _fill_gaps_in_history(
        all_history_moments: typing.Iterable[datetime.datetime],
        moment_from: datetime.datetime,
        moment_to: datetime.datetime) -> typing.List[datetime.datetime]:
    """ Take all moments in history and fill gaps (days without value) inside the interval.

    :param all_history_moments: Iterable of all moments in history.
    :param moment_from: Interval beginning moment.
    :param moment_to: Interval ending moment.
    :return: List of all moments between ``moment_from`` and ``moment_to`` without days with no value.

    Example::

        # history does not contain moments on 3, 4, 6 and 8 january.
        history = [datetime(2000, 1, 1), datetime(2000, 1, 1, 13, 00),
                   datetime(2000, 1, 2),
                   datetime(2000, 1, 5),
                   datetime(2000, 1, 7)]
        every_day_history = _fill_gaps_in_history(history, datetime(2000, 1, 1), datetime(2000, 1, 8))
        # => [datetime(2000, 1, 1), datetime(2000, 1, 1, 13, 00),
        #     datetime(2000, 1, 2),
        #     datetime(2000, 1, 3),  # added moment
        #     datetime(2000, 1, 4),  # added moment
        #     datetime(2000, 1, 5),
        #     datetime(2000, 1, 6),  # added moment
        #     datetime(2000, 1, 7),
        #     datetime(2000, 1, 8),  # added moment
        #     ]
    """
    all_moments = list(all_history_moments)  # copy

    date_from = moment_from.date()
    date_to = moment_to.date()
    one_day = datetime.timedelta(days=1)

    # add to list dates missed in history
    all_history_dates = {moment.date() for moment in all_moments}
    interval_date = date_from
    while interval_date <= date_to:
        if interval_date not in all_history_dates:
            all_moments.append(datetime.datetime.combine(
                interval_date,
                datetime.time.min,
                tzinfo=moment_from.tzinfo))
        interval_date += one_day

    return all_moments


_HistoryDataValueType = typing.Union[InstrumentValue, decimal.Decimal]


def _remove_intraday_items(
        history_items: typing.List[typing.Tuple[datetime.datetime, _HistoryDataValueType]]
) -> typing.List[typing.Tuple[datetime.datetime, _HistoryDataValueType]]:
    # leave in result only last value per day (close value)
    result_data = list(collections.OrderedDict((
        (moment.date(), (moment, value))
        for moment, value
        in history_items)).values())

    return result_data


def build_sorted_history_data(
        history_data: typing.Iterable[InstrumentValue],
        moment_from: datetime.datetime,
        moment_to: datetime.datetime,
        interval_data_type: IntervalHistoryDataValuesType = IntervalHistoryDataValuesType.ONLY_INTERIOR_VALUES,
        intraday: bool = False
) -> typing.List[typing.Tuple[datetime.datetime, InstrumentValue]]:
    """ Take full history data and build sorted list of values for the interval.

    Every history data value contain decimal value of instrument "price"
    and moment (datetime) when this value "begins". This value proceed until the next "instrument value".

    If ``history_data = [InstrumentValue(42, datetime(2000, 1, 1, 13, 0, 0))]``
    then we may say that during "1 Jan 2000" instrument has value 42 - from begin to end (close value).
    Actually, value 42 lasts till the end of time.

    If ``history_data = [InstrumentValue(42, datetime(2000, 1, 1, 13, 0, 0)),
                         InstrumentValue(256, datetime(2000, 1, 1, 20, 0, 0))]``
    then we say that from "1 Jan 2000 13:00" till "1 Jan 2000 20:00" instrument has value 42;
    from "1 Jan 2000 20:00" till "end of time" instrument has value 256.
    The daily value equal to 256 because it's the last value within the day (close value).

    Examples:

    Suppose we have such incoming history data:
    ``history_data = [IV(1, '1 Jan'), IV(2, '1 Jan, 13:00'), IV(3, '5 Jan'), IV(4, '9 Jan'),
    IV(5, '9 Jan, 13:00'), IV(6, '13 Jan'), IV(7, '15 Jan'), IV(8, '15 Jan, 13:00')]``
    where ``IV`` is ``InstrumentValue`` for short.

    Or graphically::

                +------------------------------------------------------------------------------------------+
        Moment: | 1 | 1+13h | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 9+13h | 10 | 11 | 12 | 13 | 14 | 15 | 15+13h |
                +------------------------------------------------------------------------------------------+
        Value:  | 1 | 2     |   |   |   | 3 |   |   |   | 4 | 5     |    |    |    | 6  |    | 7  | 8      |
                +------------------------------------------------------------------------------------------+

    Then::

        build_sorted_history_data(history_data, '1 Jan', '16 Jan', ONLY_INTERIOR_VALUES, intraday=True)
          => [('1 Jan', IV(1, '1 Jan')), ('1 Jan, 13:00', IV(2, '1 Jan, 13:00')), ('5 Jan', IV(3, '5 Jan')),
              ('9 Jan', IV(4, '9 Jan')), ('9 Jan, 13:00', IV(5, '9 Jan, 13:00')), ('13 Jan', IV(6, '13 Jan')),
              ('15 Jan', IV(7, '15 Jan')), ('15 Jan, 13:00', IV(8, '15 Jan, 13:00'))]
        Interval:    >------------------------------------------------------------------------------------------<
                     +------------------------------------------------------------------------------------------+
        Moment:      | 1 | 1+13h | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 9+13h | 10 | 11 | 12 | 13 | 14 | 15 | 15+13h |
                     +------------------------------------------------------------------------------------------+
        Value:       | 1 | 2     |   |   |   | 3 |   |   |   | 4 | 5     |    |    |    | 6  |    | 7  | 8      |
                     +------------------------------------------------------------------------------------------+

    ::

        build_sorted_history_data(history_data, '31 Dec', '9 Jan, 20:00', ONLY_INTERIOR_VALUES, intraday=True)
          => [('1 Jan', IV(1, '1 Jan')), ('1 Jan, 13:00', IV(2, '1 Jan, 13:00')), ('5 Jan', IV(3, '5 Jan')),
              ('9 Jan', IV(4, '9 Jan')), ('9 Jan, 13:00', IV(5, '9 Jan, 13:00'))]
        Interval: >---------------------------------------------------<
                     +---------------------------------------------------+
        Moment:      | 1 | 1+13h | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 9+13h |
                     +---------------------------------------------------+
        Value:       | 1 | 2     |   |   |   | 3 |   |   |   | 4 | 5     |
                     +---------------------------------------------------+
    Here we can see that the first value has moment '1 Jan' despite ``moment_from`` = '31 Dec'.
    Because history has no values before '1 Jan'.

    ::

        build_sorted_history_data(history_data, '1 Jan, 06:00', '9 Jan, 20:00', ONLY_INTERIOR_VALUES, intraday=True)
          => [('1 Jan, 13:00', IV(2, '1 Jan, 13:00')), ('5 Jan', IV(3, '5 Jan')),
              ('9 Jan', IV(4, '9 Jan')), ('9 Jan, 13:00', IV(5, '9 Jan, 13:00'))]
        Interval:      >----------------------------------------------<
                         +-----------------------------------------------+
        Moment:          | 1+13h | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 9+13h |
                         +-----------------------------------------------+
        Value:           | 2     |   |   |   | 3 |   |   |   | 4 | 5     |
                         +-----------------------------------------------+
    Here we not see value 1 from '1 Jan', because we ask ``ONLY_INTERIOR_VALUES`` from '1 Jan, 06:00'.

    ::

        build_sorted_history_data(history_data, '1 Jan, 06:00', '9 Jan, 20:00', ALLOW_PRECEDING_VALUE, intraday=True)
          => [('1 Jan, 06:00', IV(1, '1 Jan')), ('1 Jan, 13:00', IV(2, '1 Jan, 13:00')),
              ('5 Jan', IV(3, '5 Jan')), ('9 Jan', IV(4, '9 Jan')), ('9 Jan, 13:00', IV(5, '9 Jan, 13:00'))]
        Interval:    >---------------------------------------------------<
                     +------------------------------------------------------+
        Moment:      | 1+6h | 1+13h | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 9+13h |
                     +------------------------------------------------------+
        Value:       | 1    | 2     |   |   |   | 3 |   |   |   | 4 | 5     |
                     +------------------------------------------------------+
    Here we see value 1 from '1 Jan', because we ask ``ALLOW_PRECEDING_VALUE``.
    But first item of result tuple (moment) adjusted to ``moment_from`` value, '1 Jan, 06:00',
    though second item (interval value) still points to the original '1 Jan'.

    ::

        build_sorted_history_data(history_data, '1 Jan, 06:00', '9 Jan, 20:00', EVERY_DAY_VALUES, intraday=True)
          => [('1 Jan, 06:00', IV(1, '1 Jan')), ('1 Jan, 13:00', IV(2, '1 Jan, 13:00')),
              ('2 Jan', IV(2, '1 Jan, 13:00')), ('3 Jan', IV(2, '1 Jan, 13:00')), ('4 Jan', IV(2, '1 Jan, 13:00')),
              ('5 Jan', IV(3, '5 Jan')), ('6 Jan', IV(3, '5 Jan')), ('7 Jan', IV(3, '5 Jan')),
              ('8 Jan', IV(3, '5 Jan')),
              ('9 Jan', IV(4, '9 Jan')), ('9 Jan, 13:00', IV(5, '9 Jan, 13:00'))]
        Interval:    >---------------------------------------------------<
                     +------------------------------------------------------+
        Moment:      | 1+6h | 1+13h | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 9+13h |
                     +------------------------------------------------------+
        Value:       | 1    | 2     | 2 | 2 | 2 | 3 | 3 | 3 | 3 | 4 | 5     |
                     +------------------------------------------------------+
        Added items:                  ^   ^   ^       ^   ^   ^
    Here we see value 1 from '1 Jan', because we ask ``EVERY_DAY_VALUES``.
    But first item of result tuple (moment) adjusted to ``moment_from`` value, '1 Jan, 06:00',
    though second item (interval value) still points to the original '1 Jan'.
    Also, we see values in days that were not in the original history data: 2, 3, 4, 6, 7 and 8 Jan.

    ::

        build_sorted_history_data(history_data, '31 Dec', '9 Jan, 20:00', ONLY_INTERIOR_VALUES, intraday=False)
          => [('1 Jan, 13:00', IV(2, '1 Jan, 13:00')), ('5 Jan', IV(3, '5 Jan')),
              ('9 Jan, 13:00', IV(5, '9 Jan, 13:00'))]
        Interval: >---------------------------------------------------<
                         +-----------------------------------------------+
        Moment:          | 1+13h | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 9+13h |
                         +-----------------------------------------------+
        Value:           | 2     |   |   |   | 3 |   |   |   |   | 5     |
                         +-----------------------------------------------+
    Here we not see value 1 from '1 Jan' and value 4 from '9 Jan',
    because we ask ``intraday=False``, but that values are not last (close) during their days.

    ::

        build_sorted_history_data(history_data, '1 Jan, 06:00', '9 Jan, 20:00', EVERY_DAY_VALUES, intraday=False)
          => [('1 Jan, 13:00', IV(2, '1 Jan, 13:00')),
              ('2 Jan', IV(2, '1 Jan, 13:00')), ('3 Jan', IV(2, '1 Jan, 13:00')), ('4 Jan', IV(2, '1 Jan, 13:00')),
              ('5 Jan', IV(3, '5 Jan')), ('6 Jan', IV(3, '5 Jan')), ('7 Jan', IV(3, '5 Jan')),
              ('8 Jan', IV(3, '5 Jan')),
              ('9 Jan, 13:00', IV(5, '9 Jan, 13:00'))]
        Interval:    >---------------------------------------------------<
                            +-----------------------------------------------+
        Moment:             | 1+13h | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 9+13h |
                            +-----------------------------------------------+
        Value:              | 2     | 2 | 2 | 2 | 3 | 3 | 3 | 3 |   | 5     |
                            +-----------------------------------------------+
        Added items:                  ^   ^   ^       ^   ^   ^
    Here we not see value 1 from '1 Jan' and value 4 from '9 Jan',
    because we ask ``intraday=False``, but that values are not last (close) during their days.
    But also, we see values in days that were not in the original history data: 2, 3, 4, 6, 7 and 8 Jan.


    :param history_data: Income history data (generally not sorted)
    :param moment_from: Interval beginning moment
    :param moment_to: Interval ending moment
    :param interval_data_type: Type of built result history data
    :param intraday: Should result history data contain all values within a day (``True``)
     or only "close" values (``False``).
     Sometimes intraday values calls "ticks" and contains values for every hour, every minute, etc.
     If ``intraday`` is ``False`` then we take only single value from the several intraday values - the last one.
    :return: List of sorted (by the datetime) history data values
     in form of [(``value_moment``, ``original_instrument_value``), ...].
     ``value_moment`` is the moment (datetime) when correspondent ``original_instrument_value`` is actual.
     ``value_moment`` is always between ``moment_from`` and ``moment_to``.
     ``original_instrument_value`` is item from ``history_data``.
     ``original_instrument_value.moment`` can be less than ``moment_from``, but only for the first item
     (when ``interval_data_type`` is ``ALLOW_PRECEDING_VALUE`` or ``EVERY_DAY_VALUES``).
    """
    if not isinstance(interval_data_type, IntervalHistoryDataValuesType):
        raise ValueError(f"Unknown 'interval_data_type' value: {interval_data_type}")

    history_data_list = list(history_data)
    if moment_from > moment_to or not history_data_list:
        return []

    first_value, all_moments_set, history_dict = _prepare_history_data(history_data_list, moment_from, moment_to)

    if interval_data_type == IntervalHistoryDataValuesType.EVERY_DAY_VALUES:
        all_moments = _fill_gaps_in_history(list(all_moments_set), moment_from, moment_to)
        all_moments.sort()

        result_data = []
        result_dict = {}  # already worked items
        prev_value = first_value if (first_value is not None and first_value.moment < moment_from) else None
        for moment in all_moments:
            prev_value = current_value = history_dict.get(moment, prev_value)
            if current_value is not None:
                # adjust first_value (which is prior to moment_from value) to moment_from
                result_moment = max(moment, moment_from)
                assert result_moment not in result_dict or result_dict[result_moment] == current_value, \
                    f"Moment {result_moment} already added to result but with different value " \
                    f"({result_dict[result_moment]} vs current_value)"

                if result_moment not in result_dict:
                    result_data.append((result_moment, current_value))
                    result_dict[result_moment] = current_value

    else:
        # if instrument_value.moment is before moment_from, then use moment_from
        result_data = [(max(instrument_value.moment, moment_from), instrument_value)
                       for instrument_value
                       in history_dict.values()
                       if (interval_data_type == IntervalHistoryDataValuesType.ALLOW_PRECEDING_VALUE or
                           instrument_value.moment >= moment_from)]
        result_data.sort(key=lambda it: it[0])

    if not intraday:
        result_data = _remove_intraday_items(result_data)

    return result_data


def build_composed_sorted_history_data(
        history_data1: typing.Iterable[InstrumentValue],
        history_data2: typing.Iterable[InstrumentValue],
        compose_type: ComposeType,
        moment_from: datetime.datetime,
        moment_to: datetime.datetime,
        interval_data_type: IntervalHistoryDataValuesType = IntervalHistoryDataValuesType.ONLY_INTERIOR_VALUES,
        intraday: bool = False,
        compose_error_handler: typing.Callable[
            [Exception, ComposeType, datetime.datetime, InstrumentValue, InstrumentValue],
            decimal.Decimal] = None
) -> typing.List[typing.Tuple[datetime.datetime, decimal.Decimal]]:
    """ Take full history data and build sorted list of values for the interval.

    See additional information in ``build_sorted_history_data`` docstring.

    ``compose_error_handler`` has signature::

        _return_stub_error_handler(
            ex: Exception,
            compose_type: ComposeType,
            moment: datetime.datetime,
            left_value: InstrumentValue,
            right_value: InstrumentValue) -> decimal.Decimal

    Suppose we have such incoming history data:
    ``history_data1 = [IV(10, '1 Jan'), IV(20, '1 Jan, 13:00'), IV(30, '5 Jan'), IV(40, '7 Jan'),
    IV(50, '7 Jan, 13:00'), IV(60, '10 Jan')]``
    ``history_data2 = [IV(1, '2 Jan, 13:00'), IV(2, '6 Jan'), IV(3, '7 Jan'), IV(4, '8 Jan'), IV(5, '8 Jan, 13:00'),
    IV(6, '10 Jan'), IV(7, '11 Jan')]``
    where ``IV`` is ``InstrumentValue`` for short.

    Or graphically::

                    +----------------------------------------------------------------------------------+
        Moment:     | 1  | 1+13h | 2 | 2+13h | 3 | 4 | 5  | 6  | 7  | 7+13h | 8  | 8+13h | 9 | 10 | 11 |
                    +----------------------------------------------------------------------------------+
        History 1:  | 10 | 20    |   |       |   |   | 30 |    | 40 | 50    |    |       |   | 60 |    |
                    +----------------------------------------------------------------------------------+
        History 2:  |    |       |   | 1     |   |   |    | 2  | 3  |       | 4  | 5     |   | 6  | 7  |
                    +----------------------------------------------------------------------------------+

    Then::

        build_composed_sorted_history_data(
            history_data1, history_data2,
            ADD,
            '1 Jan', '11 Jan',
            ONLY_INTERIOR_VALUES,
            intraday=True)
          => [('2 Jan, 13:00', 21), ('5 Jan', 31), ('6 Jan', 32), ('7 Jan', 43), ('7 Jan, 13:00', 53),
              ('8 Jan', 54), ('8 Jan, 13:00', 55), ('10 Jan', 66), ('11 Jan', 67)]
        Interval:    >----------------------------------------------------------------------------------<
                                      +-----------------------------------------------------------------+
        Moment:                       | 2+13h | 3 | 4 | 5  | 6  | 7  | 7+13h | 8  | 8+13h | 9 | 10 | 11 |
                                      +-----------------------------------------------------------------+
        Composed:                     | 21    |   |   | 31 | 32 | 43 | 53    | 54 | 55    |   | 66 | 67 |
                                      +-----------------------------------------------------------------+

    :param history_data1: Income first history data (generally not sorted)
    :param history_data2: Income second history data (generally not sorted)
    :param compose_type: Type of composition of two history data sequences
    :param moment_from: Interval beginning moment
    :param moment_to: Interval ending moment
    :param interval_data_type: Type of built result history data
    :param intraday: Should result history data contain all values within a day (``True``)
     or only "close" values (``False``).
     Sometimes intraday values calls "ticks" and contains values for every hour, every minute, etc.
     If ``intraday`` is ``False`` then we take only single value from the several intraday values - the last one.
    :param compose_error_handler: Callable that called on every arithmetic error during composing.
     Should reraise exception or return adjusted composed value.
    :return: List of sorted (by the datetime) history data values
     in form of [(``value_moment``, ``composed_value``), ...].
     ``value_moment`` is the moment (datetime) when correspondent ``composed_value`` is actual.
     ``value_moment`` is always between ``moment_from`` and ``moment_to``.
     ``composed_value`` is computed value for item from ``history_data1`` as left operand
     and item from ``history_data2`` as right operand.
    """
    if not isinstance(compose_type, ComposeType):
        raise ValueError(f"Unknown 'compose_type' value: {compose_type}")
    if not isinstance(interval_data_type, IntervalHistoryDataValuesType):
        raise ValueError(f"Unknown 'interval_data_type' value: {interval_data_type}")
    if compose_error_handler is not None and not callable(compose_error_handler):
        raise ValueError(f"Not callable 'compose_error_handler' value: {compose_error_handler}")

    history_data1_list = list(history_data1)
    history_data2_list = list(history_data2)
    if moment_from > moment_to or not history_data1_list or not history_data2_list:
        return []

    composer = {ComposeType.MULTIPLY: lambda v1, v2: v1 * v2,
                ComposeType.DIVIDE: lambda v1, v2: v1 / v2,
                ComposeType.ADD: lambda v1, v2: v1 + v2,
                ComposeType.SUBTRACT: lambda v1, v2: v1 - v2}[compose_type]

    first_value1, all_moments_set1, history_dict1 = _prepare_history_data(history_data1_list, moment_from, moment_to)
    first_value2, all_moments_set2, history_dict2 = _prepare_history_data(history_data2_list, moment_from, moment_to)

    if not history_dict1 or not history_dict2:
        # no common data in requested interval
        return []

    # make merge of two histories
    all_moments = [moment
                   for moment
                   in (all_moments_set1 |
                       all_moments_set2 |
                       (set()
                        if interval_data_type == IntervalHistoryDataValuesType.ONLY_INTERIOR_VALUES
                        # moment_from not needed for ONLY_INTERIOR_VALUES
                        else {moment_from})
                       )
                   if moment >= moment_from]

    if interval_data_type == IntervalHistoryDataValuesType.EVERY_DAY_VALUES:
        all_moments = _fill_gaps_in_history(all_moments, moment_from, moment_to)

    all_moments.sort()

    prev_value1 = first_value1 if first_value1.moment < moment_from else None
    prev_value2 = first_value2 if first_value2.moment < moment_from else None

    composed_data: typing.List[typing.Tuple[datetime.datetime, decimal.Decimal]] = []

    for moment in all_moments:
        prev_value1 = current_value1 = history_dict1.get(moment, prev_value1)
        prev_value2 = current_value2 = history_dict2.get(moment, prev_value2)

        # current values can be None only at the beginning of the interval
        # after first not None value all following values will be not None
        if current_value1 is not None and current_value2 is not None:
            if compose_error_handler is None:
                value = composer(current_value1.value, current_value2.value)

            else:
                try:
                    value = composer(current_value1.value, current_value2.value)
                except ArithmeticError as ex:
                    # try to handle error
                    value = compose_error_handler(ex, compose_type, moment, current_value1, current_value2)

            composed_data.append((moment, value))

    if not intraday:
        composed_data = _remove_intraday_items(composed_data)

    return composed_data
