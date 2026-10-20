.PHONY: install install-engine test lint run

install:
	pip install -r requirements-dev.txt

install-engine:
	pip install -r requirements-engine.txt

test:
	pytest

lint:
	ruff check .
	ruff format --check .

run:
	uvicorn app.main:app --reload
