.PHONY: up down kit dev test test-unit acceptance clean secrets-check

up:
	docker compose up --build -d

down:
	docker compose down

kit:
	python scripts/run_starter_kit.py

acceptance:
	python scripts/acceptance.py

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
	python scripts/secrets_check.py

clean:
	@powershell -Command "Remove-Item -Recurse -Force -ErrorAction SilentlyContinue .pytest_cache, __pycache__, tests\__pycache__, src\pulse\__pycache__"
