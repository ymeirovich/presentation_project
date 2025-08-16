# ===== Variables =====
GOOGLE_CLOUD_PROJECT ?= your-gcp-project-id
GOOGLE_CLOUD_REGION  ?= us-central1
PYTHON               ?= python3

# ===== Commands =====
.PHONY: smoke-test
smoke-test:
	$(PYTHON) -m pytest -q tests/test_smoke.py

.PHONY: fmt
fmt:
	$(PYTHON) -m black src tests

.PHONY: lint
lint:
	$(PYTHON) -m flake8 src tests

.PHONY: all live-smoke

all: lint test

live-smoke:
	@echo "Running live e2e smoke…"
	RUN_SMOKE=1 $(PYTHON) -m pytest -q tests/test_smoke.py::test_live_end_to_end_orchestrator

