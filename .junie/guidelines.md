# Project Guidelines – BAES Flask API

## Overview
This repository hosts a Flask-based REST API connected to a Microsoft SQL Server 2017 database. The application is containerized using Docker and orchestrated with docker-compose. It includes database models, route handlers, and utility scripts (e.g., an MQTT bridge) to support BAES-related operations.

Primary goals:
- Provide HTTP endpoints for managing BAES entities (sites, buildings, floors, cards, users, roles, status, etc.).
- Persist and query data via MSSQL.
- Offer a reproducible, containerized local environment for development and demo.

Tech stack:
- Python (Flask)
- Microsoft SQL Server 2017
- Docker and docker-compose
- uWSGI/supervisord for containerized runtime (see uwsgi.ini, supervisord.conf)

## Project Structure
- api/
  - app.py – Flask application factory / setup
  - models/ – SQLAlchemy-like data models (baes, batiment, etage, site, user, role, status, …)
  - routes/ – REST endpoints (auth, user, site, role, status, etc.)
  - templates/ – Shared mixins/utilities (e.g., TimestampMixin.py)
  - openapi.json – API schema/definition
- app.py – Entrypoint that may run the API (root-level convenience)
- Dockerfile – Build instructions for the API container
- docker-compose.yml – Orchestrates API and MSSQL containers
- init-db.sql – Initializes DB user/permissions
- mssql-entrypoint.sh – MSSQL container entrypoint script
- scripts/mqtt_to_baesapi.py – MQTT to API bridge utility
- pyproject.toml, uv.lock, requirements – Dependencies
- uwsgi.ini, supervisord.conf – Runtime configuration inside container
- documentation_api.md – API documentation notes

## How to Run Locally (containers)
- Prerequisites: Docker, Docker Compose, and (for direct DB access) ODBC Driver 17 for SQL Server.
- Start services:
  - docker-compose up -d
- What this does:
  - Starts MSSQL 2017
  - Creates a user Externe / Secur3P@ssw0rd!
  - Builds and starts the Flask API and connects it to MSSQL
- Access:
  - API: http://localhost:5000
  - Optional DB test route (if enabled): http://localhost:5000/db-test
- Stop services:
  - docker-compose down
  - Remove volumes (DB data loss): docker-compose down -v

Database connection details (default, from README):
- Host: localhost (or service name mssql within Docker network)
- Port: 1433
- Username: Externe
- Password: Secur3P@ssw0rd!
- Database: master (or configured DB as per environment)

## Development Workflow for Junie
- For code changes that affect runtime, prefer verifying docker builds locally with docker-compose up -d --build when feasible.
- Keep changes minimal and scoped to the issue at hand.
- If endpoints, models, or configs change, scan related route and model modules to ensure consistency.
- If touching deployment/runtime files (Dockerfile, uwsgi.ini, supervisord.conf), ensure syntax is valid and image builds.

## Testing
- There are currently no automated tests in this repository.
- Junie should NOT attempt to run tests unless tests are added in the future.
- If you add tests later, document how to run them here and in README.

## Code Style
- Follow PEP 8 for Python style (4-space indentation, clear naming).
- Add type hints where practical; keep functions small and readable.
- Minimize external API surface changes unless required by the issue.
- Keep configuration/secrets out of source code (use env vars / compose where possible).

## Submission Checklist for Junie
- Updated the minimal set of files to satisfy the issue.
- Verified that changes don’t obviously break container build (when relevant to the change).
- Updated docs as necessary (README, documentation_api.md, or this guidelines file).

## Notes
- Use Windows-style backslashes in paths when referencing files in this environment.
- When editing, prefer specialized tools provided by the interface (search/replace, file open) over raw shell operations.
