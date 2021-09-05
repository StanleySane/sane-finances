# Sane Finances 

[pypi_project]: https://pypi.org/project/sane-finances/
[pypi_badge]: https://img.shields.io/pypi/v/sane-finances.svg
[![pypi badge][pypi_badge]][pypi_project]
![tests](https://github.com/StanleySane/sane-finances/actions/workflows/tests.yml/badge.svg)

A library for download and parse financial data from various sources.

Library provides unified interface for access to various sources of financial data.
Such as stocks or bonds historical values.

## Disclaimer

This library acts like some sort of "middleware" between financial source API and user.
It does not store or analyze data.
So in many (or most) cases you may need legal permission for access to source API and usage of downloaded data.
This library does not provide any of such permission by design.

Before use of this library you have to examine user agreement of each source independently.
If you have no special permission or breach user agreement then use library on you own responsibility.