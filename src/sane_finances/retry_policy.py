#!/usr/bin/python
# -*- coding: utf-8 -*-

""" Simplified utility for retry strategy with exponential backoff.
"""

import logging
import time
import typing

logging.getLogger().addHandler(logging.NullHandler())


def wait_and_retry(action: typing.Callable[[], typing.Any],
                   transient_validator: typing.Callable[[Exception, int], bool],
                   max_retry_count: int = 10,
                   first_sleep_duration: float = 1.0,
                   sleep_duration_factor: float = 2.0):
    """ Implements a policy that will wait and retry `max_retry_count` times calling `action`
    on each retry with the raised exception and the current sleep duration.

    The duration of wait (sleep) between retries calculates as
    ``first_sleep_duration * (sleep_duration_factor ^ retry_attempt)``,
    where `retry_attempt` is zero based count of `action` calls.

    :param action: The action to call on each try.
    :param transient_validator: Determine if the exception is transient, i.e. available for retry.
    :param max_retry_count: The max retry count (not including first call).
    :param first_sleep_duration: Duration in seconds to wait for a first retry attempt
      (right after first failed `action`).
    :param sleep_duration_factor: Factor for the duration to wait before next (second, etc.) retries.
    :return:
    """
    logger = logging.getLogger(__name__ + '.wait_and_retry')

    if not callable(action):
        logger.error(f"Action '{action}' is not callable")
        raise ValueError(f"Action '{action}' is not callable")

    if not callable(transient_validator):
        logger.error(f"Transient validator '{transient_validator}' is not callable")
        raise ValueError(f"Transient validator '{transient_validator}' is not callable")

    min_max_retry_count = 0
    if max_retry_count < min_max_retry_count:
        logger.debug(f"max_retry_count adjusted from {max_retry_count} to {min_max_retry_count}")
        max_retry_count = min_max_retry_count
    del min_max_retry_count

    min_first_sleep_duration = 0.0
    if first_sleep_duration < min_first_sleep_duration:
        logger.debug(f"first_sleep_duration adjusted from {first_sleep_duration} to {min_first_sleep_duration}")
        first_sleep_duration = min_first_sleep_duration
    del min_first_sleep_duration

    adjusted_sleep_duration_factor = 1.0
    if sleep_duration_factor < 0.0:
        logger.debug(f"sleep_duration_factor adjusted from {sleep_duration_factor} to {adjusted_sleep_duration_factor}")
        sleep_duration_factor = adjusted_sleep_duration_factor
    del adjusted_sleep_duration_factor

    pause_in_seconds = first_sleep_duration

    retry_attempt = 0

    while retry_attempt <= max_retry_count:  # always do at least one attempt # pragma: no branch

        logger.log(retry_attempt > 0 and logging.INFO or logging.DEBUG, f"Attempt #{retry_attempt}...")

        try:
            action()

        except Exception as ex:  # pylint: disable=broad-except
            logger.exception("Attempt failed")

            if retry_attempt >= max_retry_count or not transient_validator(ex, retry_attempt + 1):
                raise

            pause_in_seconds *= sleep_duration_factor

        else:
            # success
            logger.info("Attempt succeeded")

            return

        if pause_in_seconds > 0.0:
            logger.debug(f"Wait for {pause_in_seconds} seconds before next attempt...")
            time.sleep(pause_in_seconds)

        retry_attempt += 1
