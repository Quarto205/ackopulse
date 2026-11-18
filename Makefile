.PHONY: up down kit dev test test-unit clean secrets-check

up:
	docker compose up --build -d

down:
	docker compose down

kit:
	python scripts/run_starter_kit.py

dev:
	@echo "Starting Pulse app with Uvicorn..."
	uvicorn src.pulse.main:app --host 0.0.0.0 --port 8000 --reload

test:
ifdef U
	pytest -m unit_$(U) -v
else
	pytest -v
endif

test-unit:
	pytest tests/unit -v

secrets-check:
	@echo "Checking for secrets in tracked files..."
	@powershell -Command "if (Select-String -Path @('*.py','*.md','*.sql','*.json') -Pattern 'sk-[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{20,}|password\s*=\s*[\"\''][^\"\'']+[\"\'']' -Quiet) { Write-Error 'Secrets found!'; exit 1 } else { Write-Host 'No secrets found.' }"

clean:
	@powershell -Command "Remove-Item -Recurse -Force -ErrorAction SilentlyContinue .pytest_cache, __pycache__, tests\__pycache__, src\pulse\__pycache__"
