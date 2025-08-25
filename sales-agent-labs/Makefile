# ===== Variables =====
GOOGLE_CLOUD_PROJECT ?= presgen
GOOGLE_CLOUD_REGION  ?= us-central1
PYTHON               ?= python3

# ===== Commands =====
.PHONY: smoke-test
smoke-test:
	$(PYTHON) -m pytest -q tests/test_cache_unit.py

.PHONY: fmt
fmt:
	$(PYTHON) -m black src tests

.PHONY: lint
lint:
	$(PYTHON) -m flake8 src tests

.PHONY: all

all: lint test

.PHONY: run-orchestrator live-smoke

run-orchestrator:
	@$(PYTHON) -m src.mcp_lab ./examples/report_demo.txt

live-smoke:
	@echo "Running live e2e smoke…"
	@RUN_SMOKE=1 python3 -m pytest -q tests/test_orchestrator_live.py tests/test_batch_live.py

.PHONY: run-batch
run-batch:
	@python3 -m src.mcp_lab ./examples ./examples/more_reports
