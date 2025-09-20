# WeaveFeed
Open source Social Media platform

## Dependencies

### Pip Libraries required:
* Quart

### First Time Alembic Setup

NOTE: For WeaveFeed this has already been done, but for reference
      this is how it's done.

** Required PIP library **

pip install alembic

** Initialising Alembic **

* First change into service directory (e.g. services/accounts)
* Run `alembic init alembic`
* Edit the alembic.ini file and update the sqlalchemy.url field, e.g. postgresql+psycopg2://weavefeed:password@db:5432/weavefeed)

### Database Management
