# AI-CFD-V2 Makefile
# Phase 0 bootstrap targets only. Do NOT add real-OpenFOAM execution here yet.

PY ?= python3
PIP ?= $(PY) -m pip
PYTEST ?= $(PY) -m pytest
CASE ?= cases/flat_plate_rans_sst

.PHONY: help install test validate audit run report trust-loop cockpit status-event bootstrap-check clean

help:
	@echo "AI-CFD-V2 Phase 0 targets:"
	@echo "  make install         install package editable"
	@echo "  make test            run pytest"
	@echo "  make validate        validate sample case manifest"
	@echo "  make audit           run audits on sample case"
	@echo "  make run             run (possibly mocked) solver on sample case"
	@echo "  make report          generate trust_report.json for sample case"
	@echo "  make trust-loop      validate + audit + run + report"
	@echo "  make cockpit         generate project_status.json + COCKPIT.md/html"
	@echo "  make status-event    show an example CWOS event command"
	@echo "  make bootstrap-check end-to-end: validate, trust-loop, cockpit, test"

install:
	$(PIP) install -e .

test:
	PYTHONPATH=src $(PYTEST) -q

validate:
	PYTHONPATH=src $(PY) -m cfdtrust.cli validate-manifest $(CASE)

audit:
	PYTHONPATH=src $(PY) -m cfdtrust.cli audit $(CASE)

run:
	PYTHONPATH=src $(PY) -m cfdtrust.cli run $(CASE)

report:
	PYTHONPATH=src $(PY) -m cfdtrust.cli report $(CASE)

trust-loop: validate audit run report

cockpit:
	PYTHONPATH=src $(PY) tools/cwos_status.py
	PYTHONPATH=src $(PY) tools/cwos_render_dashboard.py

status-event:
	@echo "Example CWOS event:"
	@echo ""
	@echo "  python tools/cwos_event.py \\"
	@echo "    --agent backend-engineer \\"
	@echo "    --task-id PH0-CLI-001 \\"
	@echo "    --status PASS \\"
	@echo "    --summary 'Implemented cfdtrust CLI skeleton' \\"
	@echo "    --evidence src/cfdtrust/cli.py tests/test_manifest.py \\"
	@echo "    --tests 'pytest -q'"

bootstrap-check: validate trust-loop cockpit test
	@echo ""
	@echo "==> bootstrap-check complete."
	@echo "    Inspect: docs/status/COCKPIT.md"
	@echo "    Inspect: cases/flat_plate_rans_sst/artifacts/trust_report.json"

clean:
	rm -rf .pytest_cache **/__pycache__ build dist *.egg-info
	rm -f docs/status/project_status.json docs/status/COCKPIT.html
	rm -f cases/*/artifacts/*.json cases/*/artifacts/*.csv cases/*/artifacts/*.log
