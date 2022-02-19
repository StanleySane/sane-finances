@rem Upload package to pypi.org using [sane-finances] sector from local .pypirc

py -m twine upload --repository sane-finances --verbose dist/*
