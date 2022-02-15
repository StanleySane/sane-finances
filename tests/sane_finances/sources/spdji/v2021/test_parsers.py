#!/usr/bin/env python
# -*- coding: utf-8 -*-
import datetime
import decimal
import json
import unittest

from sane_finances.sources.base import ParseError, InstrumentInfoEmpty
from sane_finances.sources.spdji.v2021.meta import IndexInfo, IndexLevel, IndexMetaData, Currency, ReturnType, \
    IndexFinderFilterGroup, IndexFinderFilter
from sane_finances.sources.spdji.v2021.parsers import (
    SpdjHistoryJsonParser, SpdjInfoJsonParser, SpdjMetaJsonParser, SpdjIndexFinderFiltersParser)


def get_valid_history_json() -> str:
    valid_json = '''{
    "status":true,
    "serviceMessages":["Service Ended Well"],
    "serviceConfig":"ALL_INDEX_ATTRIBUTES",
    "indexDetailHolder":{"status":true, "serviceMessages":["Success"], "serviceMessage":"Success"},
    "indexLevelsHolder":{
        "status":true,
        "serviceMessages":["Success"],
        "indexLevels":[
            {"effectiveDate":1327986000000,"indexId":340,"effectiveDateInEst":1327986000000,
             "indexValue":1312.40959743230732,"monthToDateFlag":"N","quarterToDateFlag":"N","yearToDateFlag":"N",
             "oneYearFlag":"N","threeYearFlag":"N","fiveYearFlag":"N","tenYearFlag":"Y","allYearFlag":"Y",
             "fetchedDate":1644843080736,"formattedEffectiveDate":"31-Jan-2012"},
            {"effectiveDate":1328072400000,"indexId":340,"effectiveDateInEst":1328072400000,
             "indexValue":1324.08909181957131,"monthToDateFlag":"N","quarterToDateFlag":"N","yearToDateFlag":"N",
             "oneYearFlag":"N","threeYearFlag":"N","fiveYearFlag":"N","tenYearFlag":"Y","allYearFlag":"Y",
             "fetchedDate":1644843080736,"formattedEffectiveDate":"01-Feb-2012"},
            {"effectiveDate":1328158800000,"indexId":340,"effectiveDateInEst":1328158800000,
             "indexValue":1325.54104227515965,"monthToDateFlag":"N","quarterToDateFlag":"N","yearToDateFlag":"N",
             "oneYearFlag":"N","threeYearFlag":"N","fiveYearFlag":"N","tenYearFlag":"Y","allYearFlag":"Y",
             "fetchedDate":1644843080736,"formattedEffectiveDate":"02-Feb-2012"}],
        "serviceMessage":"Success"},
    "idsIndexCurrencyHolder":[
        {"currencyCode":"EUR","fetchedDate":1644836642968},
        {"currencyCode":"GBP","fetchedDate":1644836642968},
        {"currencyCode":"USD","fetchedDate":1644836642968}],
    "idsIndexReturnTypeHolder":[
        {"returnTypeCode":"P-","returnTypeName":"PRICE RETURN","returnTypeDisplayOrder":1,
         "returnTypeNameForUI":"PRICE RETURN"},
        {"returnTypeCode":"T-","returnTypeName":"TOTAL RETURN","returnTypeDisplayOrder":3,
         "returnTypeNameForUI":"TOTAL RETURN"},
        {"returnTypeCode":"N-","returnTypeName":"NET TOTAL RETURN","returnTypeDisplayOrder":4,
         "returnTypeNameForUI":"NET TOTAL RETURN"}],
    "serviceMessage":"Service Ended Well"
    }'''
    return valid_json


def get_valid_info_json() -> str:
    valid_json = '''{
    "pagination": {
        "totalResults": 4918,
        "pageSize": 25,
        "startPageIndex": 1,
        "totalPages": 197
    },
    "response": [
        {
            "gtmTitle": "S&P 500®",
            "urlTitle": "/indices/equity/sp-500",
            "indexName": "S&P 500®",
            "assestClass": "Equity",
            "languageID": "1",
            "indexId": "340",
            "theme": "-"
        },
        {
            "gtmTitle": "S&P 500 Bond Index",
            "urlTitle": "/indices/fixed-income/sp-500-bond-index",
            "indexName": "S&P 500 Bond Index",
            "assestClass": "Fixed Income",
            "languageID": "1",
            "indexId": "92029788",
            "theme": "-"
        }]}'''
    return valid_json


class TestSpdjJsonParser(unittest.TestCase):

    def setUp(self) -> None:
        self.parser = SpdjHistoryJsonParser()

    def check_parse_raise(self, invalid_json: str, message: str):
        with self.assertRaisesRegex(ParseError, message):
            _ = list(self.parser.parse(invalid_json, tzinfo=None))

    def test_convert_float_to_decimal_Success(self):
        float_value = 42.123456789
        expected_result = decimal.Decimal('42.12345679')

        self.assertEqual(expected_result, self.parser.convert_float_to_decimal(float_value))

    def test_convert_unix_moment_to_datetime_Success(self):
        unix_moment = 0
        expected_result = datetime.datetime(1970, 1, 1, tzinfo=None)

        self.assertEqual(expected_result, self.parser.convert_unix_moment_to_datetime(unix_moment, None))

    def test_parse_Success(self):
        valid_json = get_valid_history_json()

        raw_data = json.loads(valid_json)

        expected_result = [
            IndexLevel(
                index_id=level_data['indexId'],
                effective_date=self.parser.convert_unix_moment_to_datetime(level_data['effectiveDate'], None),
                index_value=self.parser.convert_float_to_decimal(level_data['indexValue']))
            for level_data
            in raw_data['indexLevelsHolder']['indexLevels']]

        self.assertSequenceEqual(expected_result, list(self.parser.parse(valid_json, tzinfo=None)))

    def test_parse_RaiseWhenNoData(self):
        invalid_json = ''

        self.check_parse_raise(invalid_json, '')

    def test_parse_RaiseWhenNotDict(self):
        invalid_json = '[42]'

        self.check_parse_raise(invalid_json, 'is not dict')

    def test_parse_RaiseWhenNoDetailField(self):
        invalid_json = '''{
        "__indexDetailHolder":{"status":true, "serviceMessages":["Success"], "serviceMessage":"Success"}
        }'''

        self.check_parse_raise(invalid_json, 'indexDetailHolder')

    def test_parse_RaiseWhenDetailIsNotDict(self):
        invalid_json = '''{
        "indexDetailHolder":[]
        }'''

        self.check_parse_raise(invalid_json, 'indexDetailHolder')

    def test_parse_RaiseWhenSourceReturnError(self):
        invalid_json = '''{
        "indexDetailHolder":{"status":false, "serviceMessages":["ERROR_MESSAGE"], "serviceMessage":"ERROR_MESSAGE"}
        }'''

        self.check_parse_raise(invalid_json, 'Source returned errors.*ERROR_MESSAGE')

    def test_parse_RaiseWhenNoLevelsHolderField(self):
        invalid_json = '''{
        "indexDetailHolder":{"status":true, "serviceMessages":["Success"], "serviceMessage":"Success"},
        "__indexLevelsHolder":{"status":true, "serviceMessages":["Success"], "serviceMessage":"Success"}        
        }'''

        self.check_parse_raise(invalid_json, 'indexLevelsHolder')

    def test_parse_RaiseWhenLevelsHolderIsNotDict(self):
        invalid_json = '''{
        "indexDetailHolder":{"status":true, "serviceMessages":["Success"], "serviceMessage":"Success"},
        "indexLevelsHolder":[]        
        }'''

        self.check_parse_raise(invalid_json, 'indexLevelsHolder')

    def test_parse_RaiseWhenSourceReturnErrorInLevelsHolder(self):
        invalid_json = '''{
        "indexDetailHolder":{"status":true, "serviceMessages":["Success"], "serviceMessage":"Success"},
        "indexLevelsHolder":{"status":false, "serviceMessages":["ERROR_MESSAGE"], "serviceMessage":"ERROR_MESSAGE"}        
        }'''

        self.check_parse_raise(invalid_json, 'Source returned errors.*ERROR_MESSAGE')

    def test_parse_RaiseWhenNoLevelsField(self):
        invalid_json = '''{
        "indexDetailHolder":{"status":true, "serviceMessages":["Success"], "serviceMessage":"Success"},
        "indexLevelsHolder":{"status":true, "serviceMessages":["Success"],
            "__indexLevels":[], "serviceMessage":"Success"}        
        }'''

        self.check_parse_raise(invalid_json, 'indexLevels')

    def test_parse_RaiseWhenLevelsIsNotList(self):
        invalid_json = '''{
        "indexDetailHolder":{"status":true, "serviceMessages":["Success"], "serviceMessage":"Success"},
        "indexLevelsHolder":{"status":true, "serviceMessages":["Success"],
            "indexLevels":{}, "serviceMessage":"Success"}        
        }'''

        self.check_parse_raise(invalid_json, 'indexLevels')

    def test_parse_RaiseWhenLevelsItemIsNotDict(self):
        invalid_json = '''{
        "indexDetailHolder":{"status":true, "serviceMessages":["Success"], "serviceMessage":"Success"},
        "indexLevelsHolder":{"status":true, "serviceMessages":["Success"],
            "indexLevels":[42], "serviceMessage":"Success"}        
        }'''

        self.check_parse_raise(invalid_json, 'indexLevels')


class TestSpdjMetaJsonParser(unittest.TestCase):

    def setUp(self) -> None:
        self.parser = SpdjMetaJsonParser()

    def check_parse_raise(self, invalid_json: str, message: str):
        with self.assertRaisesRegex(ParseError, message):
            _ = list(self.parser.parse(invalid_json))

    def test_parse_Success(self):
        valid_json = get_valid_history_json()

        raw_data = json.loads(valid_json)

        expected_result = IndexMetaData(
            currencies=tuple(Currency.safe_create(currency_code=currency_code_data['currencyCode'])
                             for currency_code_data
                             in raw_data['idsIndexCurrencyHolder']),
            return_types=tuple(ReturnType.safe_create(return_type_code=return_type_data['returnTypeCode'],
                                                      return_type_name=return_type_data['returnTypeName'])
                               for return_type_data
                               in raw_data['idsIndexReturnTypeHolder']),
            index_finder_filters=()
        )

        self.assertSequenceEqual(expected_result, self.parser.parse(valid_json))

    def test_parse_RaiseWhenNoData(self):
        invalid_json = ''

        self.check_parse_raise(invalid_json, '')

    def test_parse_RaiseWhenNotDict(self):
        invalid_json = '[42]'

        self.check_parse_raise(invalid_json, 'is not dict')

    def test_parse_RaiseWhenNoDetailField(self):
        invalid_json = '''{
        "__indexDetailHolder":{"status":true, "serviceMessages":["Success"], "serviceMessage":"Success"}
        }'''

        self.check_parse_raise(invalid_json, 'indexDetailHolder')

    def test_parse_RaiseWhenDetailIsNotDict(self):
        invalid_json = '''{
        "indexDetailHolder":[]
        }'''

        self.check_parse_raise(invalid_json, 'indexDetailHolder')

    def test_parse_RaiseWhenSourceReturnError(self):
        invalid_json = '''{
        "indexDetailHolder":{"status":false, "serviceMessages":["ERROR_MESSAGE"], "serviceMessage":"ERROR_MESSAGE"}
        }'''

        self.check_parse_raise(invalid_json, 'Source returned errors.*ERROR_MESSAGE')

    def test_parse_RaiseWhenNoCurrencyHolderField(self):
        invalid_json = '''{
        "indexDetailHolder":{"status":true, "serviceMessages":["Success"], "serviceMessage":"Success"},
        "__idsIndexCurrencyHolder":[{"currencyCode":"EUR","fetchedDate":1644836642968}],
        "idsIndexReturnTypeHolder":[{"returnTypeCode":"P-","returnTypeName":"PRICE RETURN","returnTypeDisplayOrder":1,
         "returnTypeNameForUI":"PRICE RETURN"}]
        }'''

        self.check_parse_raise(invalid_json, 'idsIndexCurrencyHolder')

    def test_parse_RaiseWhenCurrencyHolderIsNotList(self):
        invalid_json = '''{
        "indexDetailHolder":{"status":true, "serviceMessages":["Success"], "serviceMessage":"Success"},
        "idsIndexCurrencyHolder":{},
        "idsIndexReturnTypeHolder":[{"returnTypeCode":"P-","returnTypeName":"PRICE RETURN","returnTypeDisplayOrder":1,
         "returnTypeNameForUI":"PRICE RETURN"}]
        }'''

        self.check_parse_raise(invalid_json, 'idsIndexCurrencyHolder')

    def test_parse_RaiseWhenCurrencyHolderIsEmpty(self):
        invalid_json = '''{
        "indexDetailHolder":{"status":true, "serviceMessages":["Success"], "serviceMessage":"Success"},
        "idsIndexCurrencyHolder":[],
        "idsIndexReturnTypeHolder":[{"returnTypeCode":"P-","returnTypeName":"PRICE RETURN","returnTypeDisplayOrder":1,
         "returnTypeNameForUI":"PRICE RETURN"}]
        }'''

        self.check_parse_raise(invalid_json, 'idsIndexCurrencyHolder')

    def test_parse_RaiseWhenCurrencyHolderItemIsNotDict(self):
        invalid_json = '''{
        "indexDetailHolder":{"status":true, "serviceMessages":["Success"], "serviceMessage":"Success"},
        "idsIndexCurrencyHolder":[42],
        "idsIndexReturnTypeHolder":[{"returnTypeCode":"P-","returnTypeName":"PRICE RETURN","returnTypeDisplayOrder":1,
         "returnTypeNameForUI":"PRICE RETURN"}]
        }'''

        self.check_parse_raise(invalid_json, 'idsIndexCurrencyHolder')

    def test_parse_RaiseWhenNoReturnTypeHolderField(self):
        invalid_json = '''{
        "indexDetailHolder":{"status":true, "serviceMessages":["Success"], "serviceMessage":"Success"},
        "idsIndexCurrencyHolder":[{"currencyCode":"EUR","fetchedDate":1644836642968}],
        "__idsIndexReturnTypeHolder":[{"returnTypeCode":"P-","returnTypeName":"PRICE RETURN","returnTypeDisplayOrder":1,
         "returnTypeNameForUI":"PRICE RETURN"}]
        }'''

        self.check_parse_raise(invalid_json, 'idsIndexReturnTypeHolder')

    def test_parse_RaiseWhenReturnTypeHolderIsNotList(self):
        invalid_json = '''{
        "indexDetailHolder":{"status":true, "serviceMessages":["Success"], "serviceMessage":"Success"},
        "idsIndexCurrencyHolder":[{"currencyCode":"EUR","fetchedDate":1644836642968}],
        "idsIndexReturnTypeHolder":{}
        }'''

        self.check_parse_raise(invalid_json, 'idsIndexReturnTypeHolder')

    def test_parse_RaiseWhenReturnTypeHolderIsEmpty(self):
        invalid_json = '''{
        "indexDetailHolder":{"status":true, "serviceMessages":["Success"], "serviceMessage":"Success"},
        "idsIndexCurrencyHolder":[{"currencyCode":"EUR","fetchedDate":1644836642968}],
        "idsIndexReturnTypeHolder":[]
        }'''

        self.check_parse_raise(invalid_json, 'idsIndexReturnTypeHolder')

    def test_parse_RaiseWhenReturnTypeHolderItemIsNotDict(self):
        invalid_json = '''{
        "indexDetailHolder":{"status":true, "serviceMessages":["Success"], "serviceMessage":"Success"},
        "idsIndexCurrencyHolder":[{"currencyCode":"EUR","fetchedDate":1644836642968}],
        "idsIndexReturnTypeHolder":[42]
        }'''

        self.check_parse_raise(invalid_json, 'idsIndexReturnTypeHolder')


class TestSpdjInfoJsonParser(unittest.TestCase):

    def setUp(self) -> None:
        self.parser = SpdjInfoJsonParser()

    def check_parse_raise(self, invalid_json: str, message: str):
        with self.assertRaisesRegex(ParseError, message):
            _ = list(self.parser.parse(invalid_json))

    def test_parse_success(self):
        valid_json = get_valid_info_json()

        raw_data = json.loads(valid_json)

        expected_result = [IndexInfo(index_id=response_data['indexId'],
                                     index_name=response_data['indexName'],
                                     url=response_data['urlTitle'])
                           for response_data
                           in raw_data['response']]

        self.assertSequenceEqual(expected_result, list(self.parser.parse(valid_json)))

    def test_parse_RaiseWhenNoData(self):
        invalid_json = ''

        self.check_parse_raise(invalid_json, '')

    def test_parse_RaiseWhenNotDict(self):
        invalid_json = '[42]'

        self.check_parse_raise(invalid_json, 'is not dict')

    def test_parse_RaiseWhenNoResponseField(self):
        invalid_json = '''{"__response": [{
            "gtmTitle": "S&P 500®",
            "urlTitle": "/indices/equity/sp-500",
            "indexName": "S&P 500®",
            "assestClass": "Equity",
            "languageID": "1",
            "indexId": "340",
            "theme": "-"
        }]}'''

        self.check_parse_raise(invalid_json, 'response')

    def test_parse_RaiseWhenResponseIsNotList(self):
        invalid_json = '''{"response": {}}'''

        self.check_parse_raise(invalid_json, 'response')

    def test_parse_RaiseWhenResponseItemIsNotDIct(self):
        invalid_json = '''{"response": [42]}'''

        self.check_parse_raise(invalid_json, 'response')

    def test_parse_RaiseProperErrorWhenResponseIsEmpty(self):
        valid_json = '''{"response": []}'''

        with self.assertRaises(InstrumentInfoEmpty):
            _ = list(self.parser.parse(valid_json))


class TestSpdjIndexFinderFiltersParser(unittest.TestCase):

    def setUp(self) -> None:
        self.parser = SpdjIndexFinderFiltersParser()

        self.expected_group = IndexFinderFilterGroup(name='AssetFamily', label='Asset Class')
        self.expected_result = [
            IndexFinderFilter(group=self.expected_group, label='Equity', value='equity'),
            IndexFinderFilter(group=self.expected_group, label='Fixed Income', value='all-fixed-income'),
            IndexFinderFilter(group=self.expected_group,
                              label='Fixed Income_Composite/Global',
                              value='fixed-income--composite--global'),
            IndexFinderFilter(group=self.expected_group,
                              label='Fixed Income_Treasury/Sovereign/Quasi-Government',
                              value='fixed-income--treasury-sovereign-quasi-government')
        ]

    def get_html_to_parse(self):
        expected_group = self.expected_group
        expected_result = self.expected_result

        html = f"""<!DOCTYPE html>
        <html lang="en">
        <head>
        <title>Index Finder | S&P Dow Jones Indices</title>
        </head>
        <body>
            <section class="wrapper">
            <div class="content-wrapper">		                            
        <section class="content index-finder-container">
            <form class="index-finder-form" name="index-finder" action="/spdji/en/index-finder/" autocomplete="on">
                <div class="facet-col facet-sidebar">
                    <div class="filter-wrapper">
                        <div class="finder-facets asset-class if-sidebar-wrapper"
                            data-fieldname="{expected_group.name}" >
                        <div class="finder-facets-mid">
                        <h6 class="category-group accordian" data-gtm-category="Index Finder Filter"
                            data-gtm-action="Expand"
                            data-gtm-label="{expected_group.label}">
                            <span class="category ">Asset Class</span>
                        </h6>
                        <div class="accordian-content parent" style="display: none;">
                        <div class="overview">
                            <ul class="category-list dropdown-menu-chkbox">
                                <li class="dropdown-menu-chkbox-item ">
                                    <input type="checkbox" id="asset-family-equity"
                                        name="{expected_result[0].group.name}"
                                        class="dropdown-menu-chkbox-input" data-gtm-category="Index Finder Filter"
                                        data-gtm-action="Filter"
                                        data-gtm-label="{expected_result[0].label}"
                                        value="{expected_result[0].value}"  value="{expected_result[0].value}">
                                    <label class="dropdown-chkbox-label" for="asset-family-equity" data-value="equity">
                                        <span class="criteria-name">Equity</span>
                                    </label>
                                </li>
                                <li class="dropdown-menu-chkbox-item has-sub-criteria">
                                    <span id="facet-fixed-income" data-gtm-category="Index Finder Filter"
                                        data-gtm-action="Expand" data-gtm-label="Fixed Income"
                                        class="sub-accordion accordian  "></span>   
                                    <input type="checkbox"
                                        name="{expected_result[1].group.name}"  id="all-fixed-income"
                                        data-gtm-category="Index Finder Filter" data-gtm-action="Filter"
                                        data-gtm-label="{expected_result[1].label}"
                                        value="{expected_result[1].value}"
                                        class="has-sub dropdown-menu-chkbox-input" >
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
                                            value="{expected_result[2].value}"
                                            class="dropdown-menu-chkbox-input" >
                                           <label class="dropdown-chkbox-label" for="fixed-income--composite--global"
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
                                            value="{expected_result[3].value}" 
                                            class="dropdown-menu-chkbox-input" >
                                           <label class="dropdown-chkbox-label"
                                            for="fixed-income-treasury-sovereign-quasi"
                                            data-value="fixed-income--treasury-sovereign-quasi-government">
                                            <span class="criteria-name">Treasury / Sovereign / Quasi-Government</span>
                                           </label>
                                        </li>
                                    </ul>
                                    </div>
                                </li>
                            </ul>
                        </div>
                        </div>
                    </div>
                </div>
                </div>
                </div>	    
            </form></section></div></section></body></html>"""
        return html

    def test_parse_Success(self):
        html = self.get_html_to_parse()

        result = list(self.parser.parse(html))

        self.assertSequenceEqual(self.expected_result, result)

    def test_parse_RaiseWithEmptyString(self):
        html = ""

        with self.assertRaisesRegex(ParseError, 'No data found'):
            _ = list(self.parser.parse(html))

    def test_parse_RaiseWithUnknownGroup(self):
        # corrupt HTML
        unknown_group_name = 'UNKNOWN_GROUP'
        last_filter = self.expected_result[-1]
        last_group = self.expected_group._replace(name=unknown_group_name)
        last_filter = last_filter._replace(group=last_group)
        self.expected_result[-1] = last_filter

        html = self.get_html_to_parse()

        with self.assertRaisesRegex(ParseError, f"group '{unknown_group_name}' not found"):
            _ = list(self.parser.parse(html))
