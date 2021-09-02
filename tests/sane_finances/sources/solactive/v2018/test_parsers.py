#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest

from sane_finances.sources.base import ParseError
from sane_finances.sources.solactive.v2018.meta import IndexInfo
from sane_finances.sources.solactive.v2018.parsers import SolactiveJsonParser, SolactiveIndexInfoParser


class TestSolactiveJsonParser(unittest.TestCase):

    def setUp(self) -> None:
        self.parser = SolactiveJsonParser()

    def check_parse_raise(self, invalid_json: str):
        with self.assertRaises(ParseError):
            _ = list(self.parser.parse(invalid_json, tzinfo=None))

    def test_parse_Success(self):
        valid_json = '[{"indexId":"DE000SLA4YD9","timestamp":1147046400000,"value":466.44}]'

        _ = list(self.parser.parse(valid_json, tzinfo=None))

    def test_parse_raisesWhenNoData(self):
        invalid_json = ''

        self.check_parse_raise(invalid_json)

    def test_parse_raisesWhenEmptyList(self):
        invalid_json = '[]'

        self.check_parse_raise(invalid_json)

    def test_parse_raisesWhenNotList(self):
        invalid_json = '{}'

        self.check_parse_raise(invalid_json)

    def test_parse_raisesWhenNotDict(self):
        invalid_json = '[[]]'

        self.check_parse_raise(invalid_json)

    def test_parse_raisesWhenNoIndexIDField(self):
        invalid_json = '[{"indexId__":"DE000SLA4YD9","timestamp":1147046400000,"value":466.44}]'

        self.check_parse_raise(invalid_json)

    def test_parse_raisesWhenNoTimestampField(self):
        invalid_json = '[{"indexId":"DE000SLA4YD9","timestamp__":1147046400000,"value":466.44}]'

        self.check_parse_raise(invalid_json)

    def test_parse_raisesWhenNoValueField(self):
        invalid_json = '[{"indexId":"DE000SLA4YD9","timestamp":1147046400000,"value__":466.44}]'

        self.check_parse_raise(invalid_json)


class TestSolactiveIndexInfoParser(unittest.TestCase):
    
    def test_parse_success(self):
        expected_result = [IndexInfo(name='11USA Index', isin='DE000SLA3E30'),
                           IndexInfo(name='ABCD', isin='DETEST104000')]
        
        first_name, first_isin = expected_result[0].name, expected_result[0].isin
        second_name, second_isin = expected_result[1].name, expected_result[1].isin
        
        html = f"""
<!doctype html>
<html lang="en-US">
  <head>
  <meta charset="utf-8">
  <meta http-equiv="x-ua-compatible" content="ie=edge">
  <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
  <title>Solactive | Indices</title>

</script>  <script src='https://www.google.com/recaptcha/api.js?hl=en'></script>
</head>


  <body class="page-template page-template-template-indices template-indices page page-id-11 page-parent ">
        <header class="header navbar navbar-inverse">

</header>
        <table class="groups table table-hover datatable-indices dataTable no-footer" data-pagelength="15">
        <thead>
            <tr>
                <th class="name">Name</th>
                <th class="isin">ISIN</th>
                <th class="level">Level</th>
            </tr>
        </thead>
        <tbody>
                            <tr>
                    <td class="name">
                        <a href="?index=DE000SLA3E30">{first_name}</a>
                    </td>
                    <td class="isin">{first_isin}</td>
                    <td class="level">603.12</td>
                </tr>
                            <tr>
                    <td class="name">
                        <a href="?index=DETEST104000">{second_name}</a>
                    </td>
                    <td class="isin">{second_isin}</td>
                    <td class="level">101.18</td>
                </tr>
                    </tbody>
    </table>

    </div>
</section>


        </main>
<script type='text/javascript' src='https://www.solactive.com/wp-includes/js/wp-embed.min.js?ver=5.2.5'></script>
  </body>
</html>
        """
        
        parser = SolactiveIndexInfoParser()
        
        result = list(parser.parse(html))
        
        self.assertSequenceEqual(result, expected_result)
    
    def test_parse_raisesWithoutName(self):
        html = """
        <table class="groups table table-hover datatable-indices dataTable no-footer" data-pagelength="15">
        <thead>
            <tr>
                <th class="name">Name</th>
                <th class="isin">ISIN</th>
                <th class="level">Level</th>
            </tr>
        </thead>
        <tbody>
                            <tr>
                    <td class="">
                        <a href="?index=DE000SLA3E30">11USA Index</a>
                    </td>
                    <td class="isin">DE000SLA3E30</td>
                    <td class="level">603.12</td>
                </tr>
                    </tbody>
    </table>
        """

        parser = SolactiveIndexInfoParser()

        with self.assertRaises(ParseError):
            list(parser.parse(html))

    def test_parse_raisesWithEmptyName(self):
        html = """
        <table class="groups table table-hover datatable-indices dataTable no-footer" data-pagelength="15">
        <thead>
            <tr>
                <th class="name">Name</th>
                <th class="isin">ISIN</th>
                <th class="level">Level</th>
            </tr>
        </thead>
        <tbody>
                            <tr>
                    <td class="name">
                    </td>
                    <td class="isin">DE000SLA3E30</td>
                    <td class="level">603.12</td>
                </tr>
                    </tbody>
    </table>
        """

        parser = SolactiveIndexInfoParser()

        with self.assertRaises(ParseError):
            list(parser.parse(html))

    def test_parse_raisesWithoutIsin(self):
        html = """
        <table class="groups table table-hover datatable-indices dataTable no-footer" data-pagelength="15">
        <thead>
            <tr>
                <th class="name">Name</th>
                <th class="isin">ISIN</th>
                <th class="level">Level</th>
            </tr>
        </thead>
        <tbody>
                            <tr>
                    <td class="name">
                        <a href="?index=DE000SLA3E30">11USA Index</a>
                    </td>
                    <td class="">DE000SLA3E30</td>
                    <td class="level">603.12</td>
                </tr>
                    </tbody>
    </table>
        """

        parser = SolactiveIndexInfoParser()
        
        with self.assertRaises(ParseError):
            list(parser.parse(html))
    
    def test_parse_raisesEmptyString(self):
        html = ""

        parser = SolactiveIndexInfoParser()
        
        with self.assertRaises(ParseError):
            list(parser.parse(html))
