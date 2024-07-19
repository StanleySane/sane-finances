#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Utilities for parse data from https://www.spglobal.com/spdji/
"""

import logging
import re
import typing

from ..v2021.meta import IndexFinderFilter, IndexFinderFilterGroup
from ...base import ParseError

logging.getLogger().addHandler(logging.NullHandler())


class SpdjIndexFinderFiltersParser:
    """ Parser for indexes finder filters from HTML.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

    def parse(self, html: str) -> typing.Iterable[IndexFinderFilter]:
        """ Parse HTML and return index finder filters

        :param html: HTML to parse.
        :return: Iterable of ``IndexFinderFilter``.
        """

        group_pattern = re.compile(
            r'<div[^>]*?\sdata-fieldname\s*?=\s*?"(?P<field_name>[^"]*?)".*?>.*?'
            r'<\w*?[^>]*?\sdata-gtm-category\s*?=\s*?"Index Finder Filter".*?'
            r'\sdata-gtm-label\s*?=\s*?"(?P<label>[^"]*?)".*?>',
            re.IGNORECASE | re.MULTILINE | re.DOTALL
        )
        checkbox_pattern = re.compile(
            r'<input[^>]*?data-gtm-category\s*?=\s*?"Index Finder Filter"[^>]*?>',
            re.IGNORECASE | re.MULTILINE | re.DOTALL
        )
        checkbox_name_pattern = re.compile(
            r'\sname\s*?=\s*?"(?P<field_name>[^"]*?)"',
            re.IGNORECASE | re.MULTILINE | re.DOTALL
        )
        checkbox_label_pattern = re.compile(
            r'\sdata-gtm-label\s*?=\s*?"(?P<label>[^"]*?)"',
            re.IGNORECASE | re.MULTILINE | re.DOTALL
        )
        checkbox_value_pattern = re.compile(
            r'\svalue\s*?=\s*?"(?P<value>[^"]*?)"',
            re.IGNORECASE | re.MULTILINE | re.DOTALL
        )

        groups_by_field_name = {}
        groups_by_position = {}
        for m_group in group_pattern.finditer(html):
            field_name = m_group.group('field_name')
            label = m_group.group('label')

            group_instance = IndexFinderFilterGroup.safe_create(name=field_name, label=label)
            groups_by_field_name[field_name] = group_instance
            groups_by_position[m_group.start()] = group_instance

        worked_values = {}
        has_any = False
        for m_checkbox in checkbox_pattern.finditer(html):
            checkbox_str = m_checkbox.group()

            m_checkbox_name = checkbox_name_pattern.search(checkbox_str)
            if m_checkbox_name is None:
                self.logger.error(f"Not found 'name' attribute in HTML {checkbox_str!r}")
                raise ParseError(f"Unexpected HTML format. "
                                 f"Not found 'name' attribute in HTML {checkbox_str!r}")

            m_checkbox_label = checkbox_label_pattern.search(checkbox_str)
            if m_checkbox_label is None:
                self.logger.error(f"Not found 'data-gtm-label' attribute in HTML {checkbox_str!r}")
                raise ParseError(f"Unexpected HTML format. "
                                 f"Not found 'data-gtm-label' attribute in HTML {checkbox_str!r}")

            m_checkbox_value = checkbox_value_pattern.search(checkbox_str)
            if m_checkbox_value is None:
                self.logger.error(f"Not found 'value' attribute in HTML {checkbox_str!r}")
                raise ParseError(f"Unexpected HTML format. "
                                 f"Not found 'value' attribute in HTML {checkbox_str!r}")

            field_name = m_checkbox_name.group('field_name')
            label = m_checkbox_label.group('label')
            value = m_checkbox_value.group('value')

            if not value:
                self.logger.info(f"'value' attribute in empty in HTML: {checkbox_str!r}")
                continue

            if field_name in groups_by_field_name:
                filter_group = groups_by_field_name[field_name]

            else:
                # try to find last parsed group by position
                checkbox_position = m_checkbox.start()
                current_group_pos = max(
                    (group_pos for group_pos in groups_by_position if group_pos <= checkbox_position),
                    default=-1)

                if current_group_pos < 0:
                    self.logger.error(f"Index finder filter group {field_name!r} not found in HTML "
                                      f"and current group position {checkbox_position} is useless")
                    raise ParseError(f"Unexpected HTML format. Index finder filter group {field_name!r} not found "
                                     f"and current group position {checkbox_position} is useless")

                filter_group = groups_by_position[current_group_pos]

            if value in worked_values:
                self.logger.info(f"Index finder filter with value {value!r} for label {label} "
                                 f"already worked for label {worked_values[value]!r}")
                continue

            has_any = True
            worked_values[value] = label
            yield IndexFinderFilter.safe_create(group=filter_group, label=label, value=value)

        if not has_any:
            self.logger.error(f"No data found in HTML:\n{html}")
            raise ParseError("Unexpected HTML format. No data found")
