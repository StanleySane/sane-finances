#!/usr/bin/python
# -*- coding: utf-8 -*-

""" Inspection utilities for sources.
"""


class InstrumentInfoParameter:
    """ Describes attribute of instrument's history download parameters class
    which value comes from instrument's info download parameters
    and should not be changed without changing instrument itself.

    For example: some sources provide API for searching instruments by parameters;
    such API returns info about instrument (unique code, name, etc.).
    In spite of this other API (e.g. download values history of instrument) may need same parameters
    in addition to other specific parameters.

    ::

        class InfoParams:
            ''' This params uses for searching of instruments list.
                Such searching returns unique ISIN of instruments.
            '''
            region: str
            country: str

        class HistoryParams:
            ''' Despite the fact that ISIN uniquely identifies concrete instrument
                this API demands region and country codes for instrument values history.
                So we mark them properly.
            '''
            region: typing.Annotated[str, InstrumentInfoParameter()]
            country: typing.Annotated[str, InstrumentInfoParameter()]
            isin: typing.Annotated[str, InstrumentInfoParameter(instrument_identity=True)]
            currency: str
    """
    instrument_identity: bool

    def __init__(self, instrument_identity: bool = False):
        """ Initialize annotation.

        :param instrument_identity: ``True`` if annotated attribute represents instrument identity value.
        """
        self.instrument_identity = bool(instrument_identity)
