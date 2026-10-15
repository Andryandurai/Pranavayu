COMPOSE := docker compose

.PHONY: up down migrate shell test lint superuser logs seed health verify-worker schema

up:
	$(COMPOSE) up -d --build

down:
	$(COMPOSE) down

migrate:
	$(COMPOSE) exec web python manage.py migrate --noinput

shell:
	$(COMPOSE) exec web python manage.py shell

test:
	$(COMPOSE) exec -T web python manage.py check --settings=enviroinsights.settings.test
	$(COMPOSE) exec -T web python manage.py makemigrations --check --dry-run --settings=enviroinsights.settings.test
	$(COMPOSE) exec -T -e OLLAMA_ENABLED=false -e LLM_PROVIDER=extractive -e HYPOTHESIS_STORAGE_DIRECTORY=/tmp/hypothesis web pytest --ds=enviroinsights.settings.test

lint:
	$(COMPOSE) exec -T web ruff check .
	$(COMPOSE) exec -T web ruff format --check .

superuser:
	$(COMPOSE) exec web python manage.py createsuperuser

logs:
	$(COMPOSE) logs -f --tail=100

seed:
	$(COMPOSE) exec web python manage.py seed_reference

health:
	$(COMPOSE) exec -T web python -c "import json, urllib.request; print(json.dumps(json.load(urllib.request.urlopen('http://localhost:8000/api/health/')), indent=2))"

verify-worker:
	$(COMPOSE) exec -T web python manage.py verify_worker

schema:
	$(COMPOSE) exec -T web python manage.py spectacular --validate --fail-on-warn
