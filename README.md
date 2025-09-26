# BAES Flask Application with MSSQL

This project contains a Flask application containerized with Docker, connected to a Microsoft SQL Server 2017 database.

## Project Structure

- `api/`: Directory containing all API-related code
  - `app.py`: The Flask application
  - `models/`: Directory for database models
  - `routes/`: Directory for API routes
  - `templates/`: Directory for HTML templates
  - `static/`: Directory for static assets (CSS, JS, images)
- `Dockerfile`: Instructions for building the Flask application container
- `docker-compose.yml`: Configuration for orchestrating the Flask and MSSQL containers
- `init-db.sql`: SQL script to initialize the database user
- `mssql-entrypoint.sh`: Entrypoint script for the MSSQL container
- `pyproject.toml`: Python project dependencies

## Prerequisites

- Docker
- Docker Compose

ODBC Driver 17: https://go.microsoft.com/fwlink/?linkid=2266337
Or : https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server?view=sql-server-ver17

## Getting Started

1. Clone the repository
2. Navigate to the project directory
3. Build and start the containers:

```bash
docker-compose up -d
```

This will:
- Start a MSSQL 2017 container
- Create a user (username: Externe, password: Secur3P@ssw0rd!)
- Display a confirmation message when the database initialization is complete
- Start the Flask application container
- Connect the Flask application to the MSSQL database

## Accessing the Application

- Flask application: http://localhost:5000
- Database connection test: http://localhost:5000/db-test

## Database Connection Details

- Host: localhost (or mssql from within the Docker network)
- Port: 1433
- Username: Externe
- Password: Secur3P@ssw0rd!
- Database: master

## Stopping the Application

To stop the containers:

```bash
docker-compose down
```

To stop the containers and remove the volumes (this will delete all database data):

```bash
docker-compose down -v
```

## Development

To make changes to the application:

1. Modify the code as needed
2. Rebuild and restart the containers:

```bash
docker-compose up -d --build
```


## Schema change notice

As of 2025-09-26, the field is_ignored has been moved from the status table to the baes table.

- Code now reads/writes the ignore flag at BAES level. Existing API responses still include is_ignored on status payloads for backward compatibility.
- If you already have a running database, you must migrate your schema manually (MSSQL examples below). Adjust constraint names to your environment if needed.

MSSQL migration example:

```sql
-- Add column to BAES (with default 0 = false)
ALTER TABLE baes ADD is_ignored BIT NOT NULL CONSTRAINT DF_baes_is_ignored DEFAULT (0);

-- Optional: initialize BAES.is_ignored from any existing Status rows if applicable
-- (example: set BAES.is_ignored to 1 if any Status for that BAES was ignored)
UPDATE b
SET b.is_ignored = 1
FROM baes b
WHERE EXISTS (
    SELECT 1 FROM status s WHERE s.baes_id = b.id AND s.is_ignored = 1
);

-- Remove is_ignored from Status once BAES column is in place
ALTER TABLE status DROP COLUMN is_ignored;
```

Rebuild containers after migration if needed:

```bash
docker-compose up -d --build
```


## Modifications effectuées (26/09/2025)

Contexte
- Suite à la demande « enléve le champs ignorer de la table status et mets le dans la table baes ».

Changements principaux
- Déplacement du champ is_ignored de la table status vers la table baes.
- api/models/baes.py : ajout de la colonne is_ignored = db.Column(db.Boolean, default=False, nullable=False).
- api/models/status.py : suppression de la colonne is_ignored (côté modèle) et ajout d’une propriété proxy is_ignored qui lit/écrit baes.is_ignored pour conserver la compatibilité.
- api/routes/status_routes.py : ajustements mineurs pour retourner is_ignored à partir de BAES dans certaines réponses (la lecture/écriture via Status.is_ignored reste possible grâce au proxy).
- README.md : ajout d’une notice de changement de schéma et des instructions de migration MSSQL.

Impact API
- Les endpoints Status continuent d’accepter et de renvoyer le champ is_ignored ; la valeur est désormais stockée au niveau du BAES associé.
- Aucune modification n’est requise côté client (rétrocompatibilité maintenue).

Migration base de données (MSSQL)
- Voir la section « Schema change notice » ci-dessus pour le script de migration d’exemple (ajout de baes.is_ignored, éventuelle initialisation, suppression de status.is_ignored).
- Adaptez les noms de contraintes à votre environnement si nécessaire.

Fichiers modifiés
- api/models/baes.py
- api/models/status.py
- api/routes/status_routes.py
- README.md

Déploiement
- Après migration, reconstruire et redémarrer les conteneurs :
  
  docker-compose up -d --build

Vérifications rapides
- GET /status et GET /status/{id} renvoient bien is_ignored basé sur BAES.
- POST /status et les PUT de mise à jour de statut acceptent toujours is_ignored et le persistent via BAES.
