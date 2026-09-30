# Author & builder: Juan-louw Greyling <juanlouw.greyling@gmail.com>
venv:
	python3 -m venv .venv && .venv/bin/pip install -e .[dev]
native:
	.venv/bin/python setup.py build_ext --inplace
test:
	.venv/bin/pytest -v
bench:
	.venv/bin/python bench/run_benchmark.py
ab:
	.venv/bin/python bench/ab_native.py
test-plain:
	python3 tools/run_tests.py
