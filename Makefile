SHELL := /bin/bash

.PHONY: docs docs-live docs-clean docs-multiversion

docs:
	uv run --group docs sphinx-build -b html docs docs/_build/html

docs-live:
	uv run --group docs sphinx-autobuild docs docs/_build/html

docs-clean:
	rm -rf docs/_build

docs-multiversion: docs-clean
	uv run --group docs sphinx-multiversion docs docs/_build/html
