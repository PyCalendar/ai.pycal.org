.DEFAULT_GOAL = help
SHELL         = bash
PYTHONVERSION = >=3.13,<3.15
PORT         ?= 5000
DOCS_PORT    ?= 8000
# the tests run on all processors (pytest-xdist); JOBS=0 runs them in one process
JOBS         ?= auto
# the settings of .env are used by make run, if it exists
ENV_FILE      = $(if $(wildcard .env),--env-file .env)
DEV_COMMAND   = uv run $(ENV_FILE) python -m ai_pycal.development --port "$(PORT)" --docs-port "$(DOCS_PORT)"

.PHONY: help
help:  ## This help message
	@grep -E '^[a-zA-Z_.-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: dev
dev:  ## Set up the development environment: Python, packages, git hooks, prompt recording, database
	@uv python install "$(PYTHONVERSION)"
	@uv sync --python "$(PYTHONVERSION)" --group dev --extra docs
	@uv run pre-commit install
	@uv run pre-commit run --hook-stage manual prepare-ai-repository
	@uv run $(ENV_FILE) python manage.py migrate
	@echo "Ready. Start the site with: make run"

.venv:
	@$(MAKE) --no-print-directory dev

.PHONY: migrate
migrate: .venv  ## Create or update the database
	@uv run $(ENV_FILE) python manage.py migrate

.PHONY: run
run: migrate  ## Run the site on http://localhost:$(PORT) with the settings of .env
	@$(DEV_COMMAND) runserver "$(PORT)"

.PHONY: app-manifest
app-manifest: .venv  ## Print the GitHub App manifest with the same local defaults as make run
	@$(DEV_COMMAND) app_manifest

.PHONY: test
test: .venv  ## Run the tests on all processors with coverage and check that no migration is missing
	@uv run python manage.py makemigrations --check --dry-run
	@uv run pytest -n "$(JOBS)" --cov=ai_pycal --cov-branch --cov-report=term --cov-report=xml

.PHONY: lint
lint: .venv  ## Check the code style
	@uv run ruff check .
	@uv run ruff format --check .

.PHONY: browser-test
browser-test: .venv docs  ## Test the setup docs and manifest form in Chromium without external requests
	@uv run --group browser pytest -o addopts= tests/browser

.PHONY: docs
docs:  ## Build the documentation; warnings fail
	@uv run --extra docs sphinx-build -W -n --keep-going -b html docs docs/_build/html

.PHONY: livehtml
livehtml:  ## Show the documentation on http://localhost:$(DOCS_PORT) while editing it
	@uv run --extra docs sphinx-autobuild --port "$(DOCS_PORT)" docs docs/_build/html

.PHONY: linkcheck
linkcheck:  ## Check the links of the documentation (needs the internet)
	@uv run --extra docs sphinx-build -b linkcheck docs docs/_build/linkcheck

.PHONY: changelog
changelog:  ## Check that there is a news fragment
	@uv run --extra docs towncrier check --compare-with origin/main

.PHONY: prose
prose:  ## Check the prose of the documentation with Vale (.vale.ini)
	@uv run --extra docs --with vale==3.26.0.1 vale docs/*.rst docs/*/*.rst README.md CONTRIBUTING.md

.PHONY: workflows
workflows:  ## Check the GitHub workflows for security problems with zizmor
	@uvx zizmor==1.32.0 --offline .github/workflows

.PHONY: reuse
reuse:  ## Check the licensing (REUSE)
	@uvx --quiet reuse lint

.PHONY: build
build:  ## Build the package into dist/
	@uv build -o dist

.PHONY: docker-build
docker-build:  ## Build the container
	docker build -t ai-pycal .

.PHONY: docker-test
docker-test: docker-build  ## Run the container and check that Docker sees it healthy
	@docker rm -f ai-pycal-test >/dev/null 2>&1 || true
	@docker run -d --name ai-pycal-test -p 5098:5000 -e ALLOWED_HOSTS=ai.example.org ai-pycal >/dev/null
	@for i in $$(seq 60); do [ "$$(docker inspect -f '{{.State.Health.Status}}' ai-pycal-test)" = healthy ] && break; sleep 1; done; \
	status=$$(docker inspect -f '{{.State.Health.Status}}' ai-pycal-test); echo $$status; \
	[ "$$status" = healthy ] || docker logs ai-pycal-test; docker rm -f ai-pycal-test >/dev/null; [ "$$status" = healthy ]

TRIVY = aquasec/trivy:0.58.1
.PHONY: docker-scan
docker-scan: docker-build  ## Scan the image with Trivy: fails on critical vulnerabilities that have a fix
	@# the image is saved to a file, so Trivy needs no access to the socket of Docker
	@mkdir -p build && docker save ai-pycal -o build/ai-pycal-image.tar
	@docker run --rm -v "$(CURDIR)/build:/scan:ro" $(TRIVY) image --input /scan/ai-pycal-image.tar \
		--exit-code 1 --severity CRITICAL --ignore-unfixed --no-progress; \
		status=$$?; rm -f build/ai-pycal-image.tar; exit $$status

.PHONY: docker-run
docker-run: docker-build  ## Run the container on $(PORT) with ./data
	@mkdir -p data
	docker run --rm -p "$(PORT):5000" -v "$(CURDIR)/data:/app/data" --user "$$(id -u):$$(id -g)" \
		$(if $(wildcard .env),--env-file .env) ai-pycal
