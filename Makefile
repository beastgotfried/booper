PYTHON ?= python
SOURCE_PATHS := apps/cli/src:apps/server/src:packages/backends/src:packages/core/src:packages/evaluators/src:packages/languages/src:packages/mutations/src:packages/profiles/src:packages/protocol/src:packages/providers/src:packages/sdk/src:packages/skills/src:packages/testing/src:packages/tools/src
TEST_DIRS := packages/protocol/test packages/providers/test packages/tools/test packages/core/test packages/backends/test packages/languages/test packages/profiles/test packages/sdk/test packages/testing/test apps/cli/test tests/integration tests/e2e

.PHONY: install test smoke live-groq live-codx build

install:
	$(PYTHON) -m pip install --editable .

test:
	@set -e; \
	for directory in $(TEST_DIRS); do \
		PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$(SOURCE_PATHS)" \
			$(PYTHON) -m unittest discover -s $$directory -p '*_test.py'; \
	done

smoke:
	PYTHONDONTWRITEBYTECODE=1 enshittify doctor
	PYTHONDONTWRITEBYTECODE=1 enshittify tools list >/dev/null
	PYTHONDONTWRITEBYTECODE=1 enshittify profiles list >/dev/null

live-groq:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) scripts/live_groq_smoke.py

live-codx:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) scripts/live_codx_smoke.py

build:
	$(PYTHON) -m build
