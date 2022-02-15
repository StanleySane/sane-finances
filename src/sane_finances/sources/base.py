#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Base classes for data sources
"""

import abc
import decimal
import datetime
import typing

from ..communication.downloader import Downloader, DownloadStringResult

T = typing.TypeVar('T')  # pylint: disable=invalid-name


class SourceError(Exception):
    """ Base exception for all exceptions generated by sources. """

    def __init__(self, message: str):
        """ Initialize exception.

        :param message: Error message.
        """
        super().__init__(message)
        self.message = message


class SourceDownloadError(SourceError):
    """ Error happened while download data from source.
    """
    pass


class ParseError(SourceError):
    """ Error happened while parse downloaded data from source.
    """
    pass


class CheckApiActualityError(SourceError):
    """ Error happened while check API actuality of source.

        Uses as negative API actuality check result.
    """
    pass


class MaxPagesLimitExceeded(SourceError):
    """ Raise when limit of paged parameters intervals exceeded.
        Helps to prevent cycling.
    """
    def __init__(self, max_paged_parameters: int):
        """ Initialize exception.

        :param max_paged_parameters: Value of exceeded limit.
        """
        super().__init__(f"Limit of maximum paged parameters ({max_paged_parameters}) exceed.")


class InstrumentValuesHistoryEmpty(SourceError):
    """ Used by ``InstrumentValuesHistoryParser.parse`` to signal about empty history data
        if such data is acceptable.

        This is not signal about error but signal about acceptable empty sequence.
    """
    def __init__(self):
        """ Initialize exception.
        """
        super().__init__("Empty history data")


class InstrumentInfoEmpty(SourceError):
    """ Used by ``InstrumentInfoParser.parse`` to signal about empty info data
        if such data is acceptable.

        This is not signal about error but signal about acceptable empty sequence.
    """
    def __init__(self):
        """ Initialize exception.
        """
        super().__init__("Empty info data")


class InstrumentValue(typing.NamedTuple):
    """ Contains minimum (generic) data for value (e.g. price) representation
        of some financial instrument (stock, index etc.) on a moment in time.
    """
    value: decimal.Decimal
    moment: datetime.datetime


class InstrumentValueProvider(abc.ABC):
    """ Provides property for `InstrumentValue`
    """

    @abc.abstractmethod
    def get_instrument_value(self, tzinfo: typing.Optional[datetime.timezone]) -> InstrumentValue:
        """ Get generalized instrument history value.

        :param tzinfo: Expected time zone of moment inside instrument value.
        :return: `InstrumentValue` instance.
        """
        raise NotImplementedError


AnyInstrumentValueProvider = typing.TypeVar('AnyInstrumentValueProvider', bound=InstrumentValueProvider)


class InstrumentInfo(typing.NamedTuple):
    """ Contains minimum (generic) data for information (description)
        about some financial instrument (stock, index etc.).
    """
    code: str
    name: str


class InstrumentInfoProvider(abc.ABC):
    """ Provides property for `InstrumentInfo`
    """

    @property
    @abc.abstractmethod
    def instrument_info(self) -> InstrumentInfo:
        """ Get generalized instrument info.

        :return: Returns `InstrumentInfo`
        """
        raise NotImplementedError


AnyInstrumentInfoProvider = typing.TypeVar('AnyInstrumentInfoProvider', bound=InstrumentInfoProvider)


class InstrumentHistoryDownloadParameters(abc.ABC):
    """ Base class for instrument history download parameters
    """

    @abc.abstractmethod
    def clone_with_instrument_info_parameters(
            self,
            info_download_parameters: typing.Any,
            instrument_info: typing.Optional[InstrumentInfoProvider]) -> 'InstrumentHistoryDownloadParameters':
        """ Clones this history download parameters instance with replace some data
        with instrument info data.

        :param info_download_parameters: Optional instrument info download parameters for cloning.
        :param instrument_info: Optional instrument info for cloning.
        :return: Cloned history download parameters instance (self) with replacing some attributes from
                 `info_download_parameters` and `instrument_info`.
        """
        raise NotImplementedError


AnyInstrumentHistoryDownloadParameters = typing.TypeVar(
    'AnyInstrumentHistoryDownloadParameters',
    bound=InstrumentHistoryDownloadParameters)


class DynamicEnumTypeManager(abc.ABC):
    """ Base class for any dynamic enum types manager.

        Uses for static treatment of enum types, i.e. without web trips.
    """

    @abc.abstractmethod
    def is_dynamic_enum_type(self, cls: type) -> bool:
        """ Check whether ``cls`` is managed dynamic enum type.

        :param cls: Type (usually class) to check.
        :return: True if `cls` is managed dynamic enum type.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_all_managed_types(self) -> typing.Iterable[typing.Type]:
        """ Get all managed dynamic enum types.

        :return: All managed dynamic enum types.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_dynamic_enum_key(self, instance: typing.Any) -> typing.Any:
        """ Get dynamic enum key of instance.

        Returned key must be immutable and simply serializable,
        i.e. string, int, tuple, tuple of strings or ints, etc.

        :param instance: Instance of any managed dynamic enum type.
        :return: Dynamic enum key of `instance` or ``None`` if `instance` is not dynamic enum.
        """
        raise NotImplementedError


class DownloadParameterValuesStorage(DynamicEnumTypeManager, abc.ABC):
    """ Base class for storage of instrument download parameters.

        Uses for dynamically changing enum types, usually via web trips.
    """

    def reload(self) -> None:
        """ Force reload stored dynamic enum values, may be from external source.

        Method may access web.
        """
        pass

    def get_dynamic_enum_value_by_key(self, cls: type, key) -> typing.Any:
        """ Get value of dynamic enum type by its key.

        Key may be any value, uniquely identifying dynamic enum value of type 'cls'.
        Usually it's a some attribute ID.

        :param cls: Dynamic enum type (usually class) which value need to get.
        :param key: Key of required dynamic enum value.
        :return: Return value of dynamic enum type by its key.
                 `None` if 'cls' is not managed dynamic enum type.
        """
        return None

    def get_dynamic_enum_value_by_choice(self, cls: type, choice: str) -> typing.Any:
        """ Get value of dynamic enum type by its choice.

        Choice is stringified value of dynamic enum key.
        Usually uses in select inputs in HTML or any other API demanding string values
        (see `get_parameter_type_choices`).

        :param cls: Dynamic enum type (usually class) which value need to get.
        :param choice: Choice of required dynamic enum value.
        :return: Return value of dynamic enum type by its choice.
                 `None` if 'cls' is not managed dynamic enum type.
        """
        return None

    def get_all_parameter_values_for(self, cls: type) -> typing.Optional[typing.Iterable]:
        """ Get all values of dynamic enum type.

        :param cls: Dynamic enum type (usually class) which values need to get.
        :return: Return all values of dynamic enum type.
                 `None` if `cls` is not managed dynamic enum type.
        """
        return None

    def get_parameter_type_choices(self, cls: type) \
            -> typing.Optional[
                typing.List[typing.Tuple[typing.Any, typing.Union[str, typing.List[typing.Tuple[typing.Any, str]]]]]
            ]:
        """ If download parameters class contains attribute (maybe nested),
        which type allows only limited set of valid values,
        this function returns such set in form of sequence
        consisting itself of iterables of exactly two items
        (e.g. ``[(A, B), (A, B) ...]`` - a value ``A`` and a human-readable name ``B``)
        to use as choices for this attribute.

        You can also collect your available choices into named groups
        that can be used for organizational purposes::

            [('Audio', [('vinyl', 'Vinyl'), ('cd', 'CD'))],
             ('Video', [('vhs', 'VHS Tape'), ('dvd', 'DVD'))],
             ('unknown', 'Unknown')]

        The first element in each tuple is the name to apply to the group.
        The second element is an iterable of 2-tuples,
        with each 2-tuple containing a value and a human-readable name for an option.
        Grouped options may be combined with ungrouped options within a single list
        (such as the 'unknown' option in this example).

        Thus, choices treats like select tag options (with optgroups) in HTML,
        or like the choices option for field in ``Django`` model API.

        :param cls: Dynamic enum type (usually class) which choices need to get.
        :return: Return all choices of dynamic enum type.
                 `None` if `cls` is unknown or doesn't need any special treatment.
        """
        return None


class InstrumentStringDataDownloader(abc.ABC):
    """ Base class for instrument data downloader.
    """

    @classmethod
    def adjust_date_from_to_holidays(cls, date_from: datetime.datetime) -> datetime.datetime:
        """ Utility function for adjusting `date from` value due to well known holidays.

        If `date from` locates into any holiday's interval, then shift it to the nearest previous working day.
        The point is not to lose instrument history moment if its value calculates only at working days.

        Supports Christmas holidays and New Year's Eve.

        :param date_from: Date to adjust.
        :return: Adjusted `date from` value.
        """
        if date_from.month == 12 and date_from.day >= 25:
            # consider Christmas holidays: take last working day
            date_from = datetime.datetime(year=date_from.year, month=date_from.month, day=24, tzinfo=date_from.tzinfo)

        if date_from.month == 1 and date_from.day <= 10:
            # consider New Year's Eve: take last working day in previous year
            date_from = datetime.datetime(year=date_from.year - 1, month=12, day=24, tzinfo=date_from.tzinfo)

        return date_from

    def adjust_download_instrument_history_parameters(
            self,
            parameters: InstrumentHistoryDownloadParameters,
            moment_from: datetime.datetime,
            moment_to: datetime.datetime
    ) -> typing.Tuple[InstrumentHistoryDownloadParameters, datetime.datetime, datetime.datetime]:
        """ Takes parameters value and interval, analyzes it and returns similar parameters and interval,
        but adjusted to export interval dates
        (used in `InstrumentHistoryValuesExporter.export_instrument_history_values`)

        For instance, if 'moment_from' equals to 01-01-2000 (New Year holiday),
        then this method may adjust it to the nearest working day, i.e. 24-12-1999,
        when instrument history value was set.

        Or, if downloader got interval of many years in parameters,
        but exporter need only a couple of months,
        then this method will return similar parameters,
        but with smaller interval of dates in it, required to download requested data::

            adjust_download_instrument_history_parameters(
                {df='1967-01-01', dt='2020-12-31', ...},
                '2005-01-01',
                '2005-03-01'
                ) -> {df='2004-12-01', dt='2005-03-01', ...}, '2004-12-24', '2005-03-01'

        Notice that returned parameters interval may differ from requested by exporter interval
        (in this example ['2005-01-01', '2005-03-01'] vs ['2004-12-01', '2005-03-01'])
        It depends on downloader policy and dates themselves.

        :param parameters: Source specific history download parameters to adjust.
        :param moment_from: Moment from to adjust.
        :param moment_to: Moment to adjust.
        :return: Tuple of adjusted arguments.
        """
        if moment_from > moment_to:
            raise ValueError(f"Moment from ({moment_from}) is greater then moment to ({moment_to})")

        moment_from = self.adjust_date_from_to_holidays(moment_from)

        return parameters, moment_from, moment_to

    def paginate_download_instrument_history_parameters(
            self,
            parameters: InstrumentHistoryDownloadParameters,
            moment_from: datetime.datetime,
            moment_to: datetime.datetime
    ) -> typing.Iterable[typing.Tuple[InstrumentHistoryDownloadParameters, datetime.datetime, datetime.datetime]]:
        """ Takes parameters value and interval, analyzes it and returns sequence of similar parameters and interval,
        but paginated for downloading of most granular data in interval (daily usually).

        For instance, if downloader got interval of several years in parameters,
        but daily data can be downloaded only in one-year interval,
        then this method will return sequence of similar parameters,
        but with one-year interval of dates in them::

            paginate_download_instrument_history_parameters({df=2000, dt=2005, ...}) ->
                ({df=2000, dt=2000, ...}, {df=2001, dt=2001, ...}, {df=2002, dt=2002, ...},
                 {df=2003, dt=2003, ...}, {df=2004, dt=2004, ...}, {df=2005, dt=2005, ...})

        Default implementation does nothing and returns its arguments without modification.

        :param parameters: Source specific history download parameters to paginate.
        :param moment_from: Moment from to paginate.
        :param moment_to: Moment to paginate.
        :return: Iterable of tuples of paginated arguments.
        """
        yield parameters, moment_from, moment_to

    @abc.abstractmethod
    def download_instrument_history_string(
            self,
            parameters: InstrumentHistoryDownloadParameters,
            moment_from: datetime.datetime,
            moment_to: datetime.datetime) -> DownloadStringResult:
        """ Downloads data of some instrument history as string and returns it.

        :param parameters: Source specific instrument history download parameters.
        :param moment_from: Download interval beginning.
        :param moment_to: Download interval ending.
        :return: Container with downloaded string.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def download_instruments_info_string(self, parameters) -> DownloadStringResult:
        """ Downloads data for set of instruments as string and returns it.

        :param parameters: Source specific instruments info download parameters.
        :return: Container with downloaded string.
        """
        raise NotImplementedError


class InstrumentValuesHistoryParser(abc.ABC):
    """ Parser for ``InstrumentValue`` history.
    """

    @abc.abstractmethod
    def parse(
            self,
            raw_text: str,
            tzinfo: typing.Optional[datetime.timezone]) -> typing.Iterable[InstrumentValueProvider]:
        """ Parses `raw_text` and returns `InstrumentValue` history.

        If `raw_text` is incorrect then raises ``ParseException``.
        If `raw_text` is correct, but contains unexpected or error-signalling content then raises ``DownloadError``.
        If parsed history data is empty (zero items) then raises ``InstrumentValuesHistoryEmpty``.

        :param raw_text: String to parse.
        :param tzinfo: Expected time zone of moment inside instrument value provider.
        :return: Iterable instrument values history.
        """
        raise NotImplementedError


class InstrumentInfoParser(abc.ABC):
    """ Parser for ``InstrumentInfo``.
    """

    @abc.abstractmethod
    def parse(self, raw_text: str) -> typing.Iterable[InstrumentInfoProvider]:
        """ Parses `raw_text` and returns ``InstrumentInfo`` sequence.

        If `raw_text` is incorrect then raises ``ParseException``.

        :param raw_text: String to parse.
        :return: Iterable instruments info.
        """
        raise NotImplementedError


class ApiActualityChecker(abc.ABC):
    """ Verifies actuality and accessibility of source API.
    """

    @abc.abstractmethod
    def check(self):
        """ Verifies actuality and accessibility of source API.

        Reads some data from source and verifies the result.
        If result is not expected or not relevant, then ``CheckApiActualityException`` raises.
        When success nothing happens (returns ``None``).
        """
        raise NotImplementedError


class InstrumentHistoryValuesExporter(abc.ABC):
    """ Base class for instrument history values exporter.
    """

    @abc.abstractmethod
    def export_instrument_history_values(
            self,
            parameters: InstrumentHistoryDownloadParameters,
            moment_from: datetime.datetime,
            moment_to: datetime.datetime
    ) -> typing.Iterable[InstrumentValueProvider]:
        """ Downloads data of some instrument history and returns it.

        :param parameters: Source specific instrument history download parameters.
        :param moment_from: Download interval beginning.
        :param moment_to: Download interval ending.
        :return: Iterable of instrument history values.
        """
        raise NotImplementedError


class InstrumentsInfoExporter(abc.ABC):
    """ Base class for instruments info exporter.
    """

    @abc.abstractmethod
    def export_instruments_info(self, parameters) -> typing.Iterator[InstrumentInfoProvider]:
        """ Downloads data for set of instruments info and returns it.

        :param parameters: Source specific instruments info download parameters.
        :return: Iterable of instruments info.
        """
        raise NotImplementedError


class DownloadParametersFactory(abc.ABC):
    """ Class for download parameters factories and generators.
    """

    @property
    @abc.abstractmethod
    def download_history_parameters_class(self) -> typing.Type[AnyInstrumentHistoryDownloadParameters]:
        """
        :return: Source specific class for download history parameters.
        """
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def download_history_parameters_factory(self) -> typing.Callable[..., AnyInstrumentHistoryDownloadParameters]:
        """
        :return: Factory for source specific download history parameters.
        """
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def download_info_parameters_class(self):
        """
        :return: Source specific class for download info parameters.
        """
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def download_info_parameters_factory(self) -> typing.Callable[..., typing.Any]:
        """
        :return: Factory for source specific download info parameters.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def generate_history_download_parameters_from(
            self,
            history_download_parameters: typing.Optional[AnyInstrumentHistoryDownloadParameters],
            info_download_parameters: typing.Any,
            instrument_info: typing.Optional[AnyInstrumentInfoProvider]) -> InstrumentHistoryDownloadParameters:
        """ Generate source specific history download parameters instance.

        :param history_download_parameters: Optional source specific history download parameters.
        :param info_download_parameters: Optional source specific info download parameters.
        :param instrument_info: Optional source specific instrument info.
        :return: New instance (cloned) of source specific history download parameters
                 with some attributes replaced from arguments.
        """
        raise NotImplementedError


class InstrumentExporterFactory(abc.ABC):
    """ Factory class for create instances of instrument data exporter.
    """

    @abc.abstractmethod
    def create_history_values_exporter(self, downloader: Downloader) -> InstrumentHistoryValuesExporter:
        """ Create new instance of source specific instrument history values exporter.

        :param downloader: Downloader used for get instrument data.
        :return: New instance of source specific instrument history values exporter.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def create_info_exporter(self, downloader: Downloader) -> InstrumentsInfoExporter:
        """ Create new instance of source specific instruments info exporter.

        :param downloader: Downloader used for get instrument data.
        :return: New instance of source specific instruments info exporter.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def create_download_parameter_values_storage(self, downloader: Downloader) -> DownloadParameterValuesStorage:
        """ Create new instance of source specific instrument download parameters storage.

        :param downloader: Downloader used for get storage data.
        :return: New instance of source specific instrument download parameters storage.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def create_api_actuality_checker(self, downloader: Downloader) -> ApiActualityChecker:
        """ Create new instance of source specific API actuality checker.

        :param downloader: Downloader used for get API data.
        :return: New instance of source specific API actuality checker.
        """
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def dynamic_enum_type_manager(self) -> DynamicEnumTypeManager:
        """ Get source specific dynamic enum type manager.

        :return: Instance of source specific dynamic enum type manager.
        """
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def download_parameters_factory(self) -> DownloadParametersFactory:
        """ Get source specific download parameters factory.

        :return: Source specific download parameters factory.
        """
        raise NotImplementedError


class InstrumentExporterRegistry(typing.NamedTuple):
    """ Container for information about registered ``InstrumentHistoryValuesExporterFactory``.
    """
    factory: InstrumentExporterFactory
    name: str
    provider_site: typing.Optional[str] = None
    api_url: typing.Optional[str] = None
