#!/usr/bin/env python
# -*- coding: utf-8 -*-
import typing

from sane_finances.inspection.analyzers import (
    FlattenedInstanceAnalyzer, FlattenedAnnotatedInstanceAnalyzer, InstanceAttributeInfo)

from ..sources.fakes import FakeDownloadParameterValuesStorage  # noqa # proxy for import from upper directories


class FakeFlattenedInstanceAnalyzer(FlattenedInstanceAnalyzer):

    def __init__(
            self,
            fake_root_data_class: typing.Type,
            fake_flattened_attrs_info: typing.Dict[str, InstanceAttributeInfo],
            fake_dynamic_enum_types: typing.Tuple[typing.Type, ...]):
        self.fake_root_data_class = fake_root_data_class
        self.fake_flattened_attrs_info = fake_flattened_attrs_info
        self.fake_dynamic_enum_types = fake_dynamic_enum_types

    def get_flattened_attrs_info(self) -> typing.Dict[str, InstanceAttributeInfo]:
        return self.fake_flattened_attrs_info

    @property
    def dynamic_enum_types(self) -> typing.Iterable[typing.Type]:
        return self.fake_dynamic_enum_types

    @property
    def root_data_class(self) -> typing.Type:
        return self.fake_root_data_class

    @property
    def primitive_types(self) -> typing.Tuple[typing.Type, ...]:
        # noinspection PyProtectedMember
        return FlattenedAnnotatedInstanceAnalyzer._primitive_types
