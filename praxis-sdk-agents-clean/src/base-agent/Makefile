.PHONY: run-locally	test

export PYTHONPATH := $(shell pwd)/src
export ENV_FILE := .env

run-locally:
	@echo "Running FastAPI app locally with .env loaded..."
	env $$(cat .env | xargs) python entrypoint.py

test:
	ENVIRONMENT=test pytest -v