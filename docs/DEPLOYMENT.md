# Deployment and fresh-machine notes

The supplied Compose file is a **local development stack** with loopback-bound
ports and Django's development server. A production-settings check is not a
hosting, TLS, recovery or uptime test. The exact Phase 7 check output is in
[VALIDATION.md](VALIDATION.md) and [PHASE7_CHECKS.json](results/PHASE7_CHECKS.json).

## Fresh Windows machine

Install Git and Docker Desktop; enable WSL 2 and Linux containers. Restart when
required and wait for the engine. Confirm `docker info` reports Linux and run
`docker run --rm hello-world`. Copy/clone the code into a simple D: path. This
checkout has no remote configured, so a public clone URL is not supplied.
The recorded 16 GiB laptop caps WSL at 9 GB. Size other machines for their actual
workload, retaining any original `.wslconfig` before editing it. Docker data and
model caches on this machine reside on D:; the repo does not relocate them.

```powershell
Set-Location -LiteralPath 'D:\EnviroInsights-India'
if (-not (Test-Path -LiteralPath '.env')) { Copy-Item '.env.example' '.env' }
# Edit secret placeholders before starting.
.\scripts\dev.ps1 up
.\scripts\dev.ps1 migrate
.\scripts\dev.ps1 seed
.\scripts\dev.ps1 health
.\scripts\dev.ps1 verify-worker
.\scripts\dev.ps1 test
.\scripts\dev.ps1 lint
```

Host Python/Make are unnecessary for normal development; the image supplies the
native GIS libraries. The container database address is `db:5432`; host clients
default to `127.0.0.1:5433`. Redis, Flower and MLflow are loopback-bound. Use one
Beat instance. `down` preserves volumes; do not use `down -v` on retained data.

Reference seeds do not restore observations, document bodies, weights or saved
scenarios. The committed dashboard snapshot displays historical results on a
fresh checkout. Interactive historical queries need a compatible PostgreSQL
backup and ignored `data/raw`, `data/results`, `data/models`, `data/mlflow` and
media files. Restore those artifacts, verify manifests, then rerun migration
and health checks. Do not describe an empty installation as a rerun of the
scientific experiments. [Source access gaps](DATA_SOURCES.md) remain explicit.

## Secrets and unconfigured services

Use ignored `.env` or a secret store. Set a random `DJANGO_SECRET_KEY` of at least
50 characters, unique `POSTGRES_PASSWORD`, the matching URL-encoded password in
`DATABASE_URL`, and `FLOWER_BASIC_AUTH`. Do not print a resolved Compose config
into logs: it includes secrets. Changing `.env` does not rotate an existing
PostgreSQL volume's password; perform an explicit database credential change.

Defaults are `LLM_PROVIDER=extractive`, `OLLAMA_ENABLED=false`, empty
`COMPOSE_PROFILES`. The experimental Ollama `llm` profile is opt-in and failed
its quality gate. No paid model/tile keys are needed. OpenAQ, NASA FIRMS and CDS
credentials are absent; their keyed ingestion was skipped. Remote generation,
public DNS, TLS, a reverse proxy, external authentication, alerting and managed
backups are not configured. Enabling them is a separate deployment task.

## Production settings checked

```powershell
docker compose exec -T web python manage.py check --deploy --settings=enviroinsights.settings.prod
```

The production module inherits base settings, uses `DEBUG=False`, rejects short
or placeholder secrets, redirects HTTP to HTTPS, secures session/CSRF cookies,
sets content-type protection and `X-Frame-Options: DENY`, and configures one-year
HSTS including subdomains/preload. Set real allowed hosts and trusted CSRF
origins. Enable `DJANGO_TRUST_PROXY` only behind a trusted proxy that strips
client forwarding headers. Review the checked
[Django deployment checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/).
Introduce HSTS only when the intended HTTPS/subdomain setup is ready.

Compose explicitly selects development settings; editing only `.env` does not
switch it. A hosted installation needs an override, for example:

```yaml
services:
  web:
    environment:
      DJANGO_SETTINGS_MODULE: enviroinsights.settings.prod
    command: ["gunicorn", "enviroinsights.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2"]
  worker:
    environment:
      DJANGO_SETTINGS_MODULE: enviroinsights.settings.prod
  beat:
    environment:
      DJANGO_SETTINGS_MODULE: enviroinsights.settings.prod
  rag-models:
    environment:
      DJANGO_SETTINGS_MODULE: enviroinsights.settings.prod
  rag-reranker:
    environment:
      DJANGO_SETTINGS_MODULE: enviroinsights.settings.prod
  flower:
    environment:
      DJANGO_SETTINGS_MODULE: enviroinsights.settings.prod
```

Gunicorn is already pinned. Validate the saved override with
`docker compose -f compose.yaml -f compose.production.yaml config --quiet`.
Run migrations and `collectstatic --noinput` with production settings before
switching traffic. Serve `STATIC_ROOT` through the reverse proxy; Gunicorn
alone does not serve static assets. Terminate TLS at the proxy, keep internal
services private, and restrict media/admin access appropriately. Test redirects,
cookies, static files, health and recovery. This example was not deployed here.

## Backup and recovery

Create a PostgreSQL custom-format dump without putting secrets in arguments:

```powershell
New-Item -ItemType Directory -Path '.\data\backups' -Force
docker compose exec -T db sh -c 'pg_dump -U $POSTGRES_USER -d $POSTGRES_DB -Fc -f /tmp/enviroinsights.dump'
docker compose cp db:/tmp/enviroinsights.dump .\data\backups\enviroinsights.dump
```

Keep encrypted copies separately. Back up files/media/MLflow consistently with
the database. Test restoration into an empty isolated database with compatible
extensions. No recovery drill is claimed by a deployment-settings check.
Frozen hashes and source manifests verify identity; they do not replace backups.
