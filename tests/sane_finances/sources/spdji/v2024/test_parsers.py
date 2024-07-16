#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
import unittest

from sane_finances.sources.base import ParseError
from sane_finances.sources.spdji.v2021.meta import IndexFinderFilter, IndexFinderFilterGroup
from sane_finances.sources.spdji.v2024.parsers import SpdjIndexFinderFiltersParser


class TestSpdjIndexFinderFiltersParser(unittest.TestCase):

    def setUp(self) -> None:
        self.parser = SpdjIndexFinderFiltersParser()

        self.expected_groups = [
            IndexFinderFilterGroup(name='AssetFamily', label='Asset Class'),
            IndexFinderFilterGroup(name='sizeStyle', label='Size/Style'),
            IndexFinderFilterGroup(name='indexLinkedProduct', label='Index Linked Products'),
        ]

        self.expected_result = [
            # group 1
            IndexFinderFilter(group=self.expected_groups[0], label='Equity', value='equity'),
            IndexFinderFilter(group=self.expected_groups[0], label='Fixed Income', value='all-fixed-income'),
            IndexFinderFilter(group=self.expected_groups[0],
                              label='Fixed Income_Composite/Global',
                              value='fixed-income--composite--global'),
            IndexFinderFilter(group=self.expected_groups[0],
                              label='Fixed Income_Treasury/Sovereign/Quasi-Government',
                              value='fixed-income--treasury-sovereign-quasi-government'),

            # group 2
            IndexFinderFilter(group=self.expected_groups[1], label='large Cap', value='L--'),

            # group 3
            IndexFinderFilter(group=self.expected_groups[2], label='ETF', value='etf'),
        ]

        # names of groups in the HTML - they differ from expected parsed values
        self.size_group_name = "indexKeyBasedSizeFlag"
        self.linked_product_group_name = "productType"

    def build_html_to_parse(self):
        expected_groups = self.expected_groups

        expected_result = list(self.expected_result)  # copy

        # change for HTML
        for result_index, html_name in (
                (4, self.size_group_name),
                (5, self.linked_product_group_name)
        ):
            expected_result_item = expected_result[result_index]
            expected_result[result_index] = expected_result_item._replace(
                group=expected_result_item.group._replace(name=html_name))

        html = f"""<!DOCTYPE html>
<html lang="en">
<body>
<section class="wrapper">
<div class="content-wrapper">	                            
<section class="content index-finder-container">
    <form class="index-finder-form" name="index-finder"
            action="https://www.spglobal.com/spdji/en/index-finder/"
            autocomplete="on">
        <div class="facet-col facet-sidebar">
            <div class="filter-wrapper">
                <div class="finder-facets asset-class if-sidebar-wrapper"
                        data-fieldname="{expected_groups[0].name}">
                    <div class="finder-facets-mid">
                        <h6 class="category-group accordian" data-gtm-category="Index Finder Filter"
                                data-gtm-action="Expand"
                                data-gtm-label="{expected_groups[0].label}">
                            <span class="category ">Category</span>
                        </h6>
                        <div class="accordian-content parent" style="display: none;">
                            <div class="overview">
                              <ul class="category-list dropdown-menu-chkbox">
                                <li class="dropdown-menu-chkbox-item ">
                                  <input type="checkbox" id="asset-family-equity"
                                        name="{expected_result[0].group.name}"
                                        class="dropdown-menu-chkbox-input"
                                        data-gtm-category="Index Finder Filter"
                                        data-gtm-action="Filter"
                                        data-gtm-label="{expected_result[0].label}"
                                        value="{expected_result[0].value}">
                                   <label class="dropdown-chkbox-label" for="asset-family-equity"
                                        data-value="equity">
                                     <span class="criteria-name">Equity</span>
                                   </label>
                                </li>
                                <li class="dropdown-menu-chkbox-item has-sub-criteria">
                                    <span id="facet-fixed-income"
                                        data-gtm-category="Index Finder Filter"
                                        data-gtm-action="Expand"
                                        data-gtm-label="Fixed Income"></span>   
                                    <input type="checkbox"
                                        name="{expected_result[1].group.name}"
                                        id="all-fixed-income"
                                        data-gtm-category="Index Finder Filter"
                                        data-gtm-action="Filter"
                                        data-gtm-label="{expected_result[1].label}"
                                        value="{expected_result[1].value}">
                                    <label class="dropdown-chkbox-label" for="all-fixed-income"
                                            data-value="all-fixed-income">
                                        <span class="criteria-name">Fixed Income</span>
                                    </label>
                                    <div class="accordian-content child" style="display: none;">
                                      <ul class="category-list dropdown-menu-chkbox">
                                        <li class="dropdown-menu-chkbox-item">
                                          <input type="checkbox"
                                            name="{expected_result[2].group.name}"
                                            data-gtm-category="Index Finder Filter"
                                            data-gtm-action="Filter"
                                            data-gtm-label="{expected_result[2].label}"
                                            id="fixed-income--composite--global"
                                            value="{expected_result[2].value}">
                                          <label class="dropdown-chkbox-label"
                                            for="fixed-income--composite--global"
                                              data-value="fixed-income--composite--global">
                                            <span class="criteria-name">Composite/Global</span>
                                          </label>
                                        </li>
                                        <li class="dropdown-menu-chkbox-item">
                                            <input type="checkbox"
                                             name="{expected_result[3].group.name}"
                                             data-gtm-category="Index Finder Filter"
                                             data-gtm-action="Filter"
                                             data-gtm-label="{expected_result[3].label}"
                                             id="fixed-income-treasury-sovereign-quasi"
                                             value="{expected_result[3].value}">
                                            <label class="dropdown-chkbox-label"
                                                    for="fixed-income-treasury-sovereign-quasi"
                                                    data-value="fixed-income--treasury-sovereign-quasi-government">
                                                <span>Treasury / Sovereign / Quasi-Government</span>
                                            </label>
                                        </li>
                                        
                                        <!-- Duplicate value here -->
                                        <li class="dropdown-menu-chkbox-item">
                                            <input type="checkbox"
                                             name="{expected_result[3].group.name}"
                                             data-gtm-category="Index Finder Filter"
                                             data-gtm-action="Filter"
                                             data-gtm-label="{expected_result[3].label}"
                                             id="fixed-income-treasury-sovereign-quasi"
                                             value="{expected_result[3].value}">
                                            <label class="dropdown-chkbox-label"
                                                    for="fixed-income-treasury-sovereign-quasi"
                                                    data-value="fixed-income--treasury-sovereign-quasi-government">
                                                <span>Treasury / Sovereign / Quasi-Government</span>
                                            </label>
                                        </li>
                                        
                                        <!-- Empty value here -->
                                        <li class="dropdown-menu-chkbox-item">
                                            <input type="checkbox"
                                             name="{expected_result[3].group.name}"
                                             data-gtm-category="Index Finder Filter"
                                             data-gtm-action="Filter"
                                             data-gtm-label="{expected_result[3].label}"
                                             id="fixed-income-treasury-sovereign-quasi"
                                             value="">
                                            <label class="dropdown-chkbox-label"
                                                    for="fixed-income-treasury-sovereign-quasi"
                                                    data-value="fixed-income--treasury-sovereign-quasi-government">
                                                <span>Treasury / Sovereign / Quasi-Government</span>
                                            </label>
                                        </li>

                                      </ul>
                                    </div>
                                    </li>
                                </ul>
                            </div>
                        </div>
                        <div class="selected-criteria asset-class" style="display: none;">
                        </div>
                    </div>
                </div>
                <div class="finder-facets size-style if-sidebar-wrapper"
                        data-fieldname="{expected_groups[1].name}">
                    <div class="finder-facets-mid">
                        <h6 class="category-group accordian" data-gtm-category="Index Finder Filter"
                                data-gtm-action="Expand"
                                data-gtm-label="{expected_groups[1].label}">
                            <span class="category ">Size</span>
                        </h6>
                        <div class="accordian-content parent" style="display: none;">
                            <div class="overview">
                                <ul class="category-list dropdown-menu-chkbox">
                                    <li class="dropdown-menu-chkbox-item">
                                        <input type="checkbox" id="large-cap"
                                            name="{expected_result[4].group.name}"
                                            data-gtm-category="Index Finder Filter"
                                            data-gtm-action="Filter"
                                            data-gtm-label="{expected_result[4].label}"
                                            value="{expected_result[4].value}">
                                        <label class="dropdown-chkbox-label" for="large-cap">
                                            <span class="criteria-name">Large Cap</span>
                                        </label>							
                                    </li>
                                </ul>
                            </div>
                        </div>
                        <div class="selected-criteria size-style" style="display: none;">
                        </div>
                    </div>
                </div> 
                <div class="finder-facets index-linked-products"
                        data-fieldname="{expected_groups[2].name}">
                    <div class="finder-facets-mid">
                        <h6 class="category-group accordian" data-gtm-category="Index Finder Filter"
                                data-gtm-action="Expand"
                                data-gtm-label="{expected_groups[2].label}">
                            <span class="category ">Index-Linked Products</span>
                        </h6>
                        <div class="accordian-content parent" style="display: none;">
                            <div class="overview">
                                <ul class="category-list dropdown-menu-chkbox">								
                                    <li class="dropdown-menu-chkbox-item">
                                        <input type="checkbox" id="etf"
                                            name="{expected_result[5].group.name}"
                                            data-gtm-category="Index Finder Filter"
                                            data-gtm-action="Filter"
                                            data-gtm-label="{expected_result[5].label}"
                                            value="{expected_result[5].value}">
                                        <label class="dropdown-chkbox-label" for="etf">
                                            <span class="criteria-name product-type">ETF</span>
                                        </label>
                                    </li>								
                                </ul>
                            </div>
                        </div>
                        <div class="selected-criteria size-style" style="display: none;">
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </form>
</section>
</div>
</section>
</body>
</html>"""

        return html

    def test_parse_Success(self):
        html = self.build_html_to_parse()

        result = list(self.parser.parse(html))

        self.assertSequenceEqual(self.expected_result, result)

    def test_parse_RaiseWithEmptyString(self):
        html = ""

        with self.assertRaisesRegex(ParseError, 'No data found'):
            _ = list(self.parser.parse(html))

    def test_parse_RaiseWithUnknownGroup(self):
        html = self.build_html_to_parse()

        # corrupt HTML to simulate absence of any group
        html = re.sub(r"\sdata-fieldname=", " __data-fieldname=", html)

        with self.assertRaisesRegex(ParseError, "Index finder filter group .*? not found"):
            _ = list(self.parser.parse(html))

    def test_parse_RaiseWhenNoNameAttribute(self):
        html = self.build_html_to_parse()
        # corrupt HTML
        html = re.sub(r"\sname=", " __name=", html)

        with self.assertRaisesRegex(ParseError, "Not found 'name' attribute in HTML"):
            _ = list(self.parser.parse(html))

    def test_parse_RaiseWhenNoDataGtmLabelAttribute(self):
        html = self.build_html_to_parse()
        # corrupt HTML
        html = re.sub(r"\sdata-gtm-label=", " __data-gtm-label=", html)

        with self.assertRaisesRegex(ParseError, "Not found 'data-gtm-label' attribute in HTML"):
            _ = list(self.parser.parse(html))

    def test_parse_RaiseWhenNoValueAttribute(self):
        html = self.build_html_to_parse()
        # corrupt HTML
        html = re.sub(r"\svalue=", " __value=", html)

        with self.assertRaisesRegex(ParseError, "Not found 'value' attribute in HTML"):
            _ = list(self.parser.parse(html))
