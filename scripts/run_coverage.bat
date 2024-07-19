
set PYTHONPATH=src

coverage run -m unittest discover

coverage html
coverage report --fail-under 95