#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Cachers for downloaders
"""

import abc
import logging
import datetime
import typing

logging.getLogger().addHandler(logging.NullHandler())


class ExpiryCalculator:
    """ Uses for calculations of expiry and revive moments.
    """

    def is_expired(self, expiry_moment: datetime.datetime) -> bool:
        """ Verify `expiry_moment` for expiration.

        :param expiry_moment: Moment to verify.
        :return: ``True`` if 'expiry_moment' was in past (i.e. expired).
        """
        return datetime.datetime.now(tz=datetime.timezone.utc) > expiry_moment

    def get_expiry_moment(self, delta: datetime.timedelta, start_from: datetime.datetime = None) -> datetime.datetime:
        """ Calculate and return moment shifted on `delta` time from `start_from` moment.
            If `start_from` is ``None`` then moment shifts from current moment (from now).

        :param delta: Timedelta for calculation.
        :param start_from: Start moment for calculation.
        :return: Calculated expiry moment relatively to `start_from` on `delta` time.
        """
        if start_from is None:
            start_from = datetime.datetime.now(tz=datetime.timezone.utc)
        return start_from + delta

    def get_revive_moment(self) -> datetime.datetime:
        """ Usually return current moment (now).

        :return: Moment of this method invoking.
        """
        return datetime.datetime.now(tz=datetime.timezone.utc)


class BaseCacher(abc.ABC):
    """ Base class (interface) for all cachers.
    """

    @abc.abstractmethod
    def retrieve(
            self,
            url: str,
            parameters: typing.List[typing.Tuple[str, str]],
            headers: typing.Dict[str, str],
            reviver: typing.Callable[[], str]) -> typing.Tuple[bool, str]:
        """ Try to find previously downloaded string by arguments inside the internal storage.
        If not found, then call `reviver` and store it result.

        :param url: URL of request.
        :param parameters: Parameters of request.
        :param headers: Headers of request.
        :param reviver: Function that returns downloaded string if such not found in cache yet.
        :return: Pair: (got_from_cache, result)
        """
        raise NotImplementedError

    @abc.abstractmethod
    def drop(
            self,
            url: str,
            parameters: typing.List[typing.Tuple[str, str]],
            headers: typing.Dict[str, str]) -> bool:
        """ Drop items from internal storage by parameters.

        :param url: URL of request.
        :param parameters: Parameters of request.
        :param headers: Headers of request.
        :return: ``True`` if any item was dropped. ``False`` if no items was in storage by that parameters.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def has(
            self,
            url: str,
            parameters: typing.List[typing.Tuple[str, str]],
            headers: typing.Dict[str, str]) -> bool:
        """ Verify that cache contains items with such parameters.

        :param url: URL of request.
        :param parameters: Parameters of request.
        :param headers: Headers of request.
        :return: ``True`` if there are any item is in storage by that parameters.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def is_empty(self) -> bool:
        """ Verify that cache is empty.

        :return: ``True`` if cache is empty
        """
        raise NotImplementedError

    @abc.abstractmethod
    def full_clear(self):
        """ Full clear of internal storage.
        """
        raise NotImplementedError


class ExpirableCacher(BaseCacher, abc.ABC):
    """ Base class for cachers that can expire their stored items.
    """
    @property
    @abc.abstractmethod
    def expiry(self) -> datetime.timedelta:
        """ Current timedelta value of expiry.
        """
        raise NotImplementedError

    @expiry.setter
    @abc.abstractmethod
    def expiry(self, delta: datetime.timedelta):
        """ Set new value of timedelta for expiry.

        Usually calls `clean` for revisiting stored items due to new expiry value.

        :param delta: New value.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def clean(self):
        """ Revisit all cached items, drop expired, update expiry moment if needed.
        """
        raise NotImplementedError


class DummyCacher(BaseCacher):
    """ Cacher without cache.
    """

    def retrieve(
            self,
            url: str,
            parameters: typing.List[typing.Tuple[str, str]],
            headers: typing.Dict[str, str],
            reviver: typing.Callable[[], str]) -> typing.Tuple[bool, str]:
        return False, reviver()

    def drop(
            self,
            url: str,
            parameters: typing.List[typing.Tuple[str, str]],
            headers: typing.Dict[str, str]) -> bool:
        return False

    def has(
            self,
            url: str,
            parameters: typing.List[typing.Tuple[str, str]],
            headers: typing.Dict[str, str]) -> bool:
        return False

    def is_empty(self) -> bool:
        return True

    def full_clear(self):
        pass


class _InMemoryCacheKey(typing.NamedTuple):
    url: str
    parameters: typing.Tuple[typing.Tuple[str, str]]
    headers: typing.Tuple[typing.Tuple[str, str]]


class _InMemoryCacheItem(typing.NamedTuple):
    key: _InMemoryCacheKey
    result: str
    revive_moment: datetime.datetime
    expiry_moment: datetime.datetime


class InMemoryCacher(ExpirableCacher):
    """ In-memory cacher based on dictionary.
    """
    default_expiry: datetime.timedelta = datetime.timedelta()  # zero delta

    _expiry: datetime.timedelta
    _storage: typing.Dict[_InMemoryCacheKey, _InMemoryCacheItem]

    def __init__(self,
                 initial_expiry: datetime.timedelta = None,
                 expiry_calculator: ExpiryCalculator = None):
        """ Initialize cacher.

        :param initial_expiry: Initial value of expiry.
        :param expiry_calculator: Expiry calculator used for such calculations.
        """
        self.expiry_calculator = ExpiryCalculator() if expiry_calculator is None else expiry_calculator

        self._expiry = self.default_expiry if initial_expiry is None else initial_expiry
        self._storage = {}

    @property
    def expiry(self) -> datetime.timedelta:
        return self._expiry

    @expiry.setter
    def expiry(self, delta: datetime.timedelta):
        self._expiry = delta
        self.clean()

    @staticmethod
    def _build_key(
            url: str,
            parameters: typing.List[typing.Tuple[str, str]],
            headers: typing.Dict[str, str]):
        key = _InMemoryCacheKey(
            url=str(url),
            parameters=tuple((str(param_name), str(param_value)) for param_name, param_value in parameters),
            headers=tuple((str(header_name), str(header_value)) for header_name, header_value in headers.items())
        )
        return key

    def clean(self):
        items = tuple(self._storage.values())
        for item in items:
            new_expiry_moment = self.expiry_calculator.get_expiry_moment(
                self.expiry,
                start_from=item.revive_moment)

            if (self.expiry_calculator.is_expired(item.expiry_moment)
                    or self.expiry_calculator.is_expired(new_expiry_moment)):
                del self._storage[item.key]

            else:
                self._storage[item.key] = item._replace(expiry_moment=new_expiry_moment)

    def retrieve(
            self,
            url: str,
            parameters: typing.List[typing.Tuple[str, str]],
            headers: typing.Dict[str, str],
            reviver: typing.Callable[[], str]) -> typing.Tuple[bool, str]:

        self.clean()

        key = self._build_key(url, parameters, headers)
        got_from_cache, cache_item = True, self._storage.get(key, None)
        if cache_item is None or self.expiry_calculator.is_expired(cache_item.expiry_moment):
            got_from_cache, result = False, reviver()
            revive_moment = self.expiry_calculator.get_revive_moment()
            expiry_moment = self.expiry_calculator.get_expiry_moment(self.expiry)
            self._storage[key] = cache_item = _InMemoryCacheItem(
                key=key,
                result=result,
                revive_moment=revive_moment,
                expiry_moment=expiry_moment)

        return got_from_cache, cache_item.result

    def drop(
            self,
            url: str,
            parameters: typing.List[typing.Tuple[str, str]],
            headers: typing.Dict[str, str]) -> bool:

        self.clean()

        key = self._build_key(url, parameters, headers)
        if key in self._storage:
            del self._storage[key]
            return True

        return False

    def has(
            self,
            url: str,
            parameters: typing.List[typing.Tuple[str, str]],
            headers: typing.Dict[str, str]) -> bool:

        self.clean()

        key = self._build_key(url, parameters, headers)
        return key in self._storage

    def is_empty(self) -> bool:
        self.clean()

        return len(self._storage) == 0

    def full_clear(self):
        self._storage.clear()
