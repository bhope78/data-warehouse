.PHONY: setup up down ingest dbt-run dbt-test lint test refresh

setup:             ## First-time local setup
	cp .env.example .env
	pip install -r requirements.txt
	cd dbt_project && dbt deps
	docker compose -f docker/docker-compose.yml up -d

up:                ## Start local services (Postgres, Superset)
	docker compose -f docker/docker-compose.yml up -d

down:              ## Stop local services
	docker compose -f docker/docker-compose.yml down

ingest:            ## Run all ingestion scripts
	python scripts/run_ingestion.py --all

ingest-%:          ## Run single ingestor (e.g. make ingest-bls)
	python scripts/run_ingestion.py --source $*

dbt-run:           ## Run dbt models
	cd dbt_project && dbt run --target dev

dbt-test:          ## Run dbt tests
	cd dbt_project && dbt test --target dev

lint:              ## Lint Python code
	ruff check ingestion/ frontend/ scripts/

test:              ## Run Python tests
	pytest ingestion/tests/ -v

refresh:           ## Full pipeline: ingest + transform + test
	$(MAKE) ingest
	$(MAKE) dbt-run
	$(MAKE) dbt-test
