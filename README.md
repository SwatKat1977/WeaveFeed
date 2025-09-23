# WeaveFeed
Open source Social Media platform

## Dependencies

### Pip Libraries required:
* Quart
* asyncpg

### First Time Alembic Setup

NOTE: For WeaveFeed this has already been done, but for reference
      this is how it's done.

** Required PIP library **

pip install:
* alembic
* psycopg2
* passlib[bcrypt]
* pydantic
* pydantic[email]

** Initialising Alembic **

* First change into service directory (e.g. services/accounts)
* Run `alembic init alembic`
* Edit the alembic.ini file and update the sqlalchemy.url field,
  e.g. postgresql+psycopg2://weavefeed:password@db:5432/weavefeed)

** Create First Migration **

Run `alembic revision --autogenerate -m "init schema"` to generate
your first migration.

Alembic will compare your models (Base.metadata) against the DB.

Since the DB is empty, it will generate alembic/versions/xxxx_init_schema.py
with CREATE TABLE statements for users, profiles, and auth_providers etc.

Next you will need to add any data seeding into the schema. This only
needs to be done once.

To do this edit the xxxx_init_schema.py and update the upgrade() method.
Below is an example how to seed a user into the database:

```
from datetime import datetime
import uuid
from passlib.hash import bcrypt

    # seed admin user
    admin_id = str(uuid.uuid4())
    password_hash = bcrypt.hash("WeaveFeed_Admin")
    now = datetime.utcnow()

    op.execute(
        f"""
        INSERT INTO users (id, username, email, password_hash, is_verified, is_active, created_at, updated_at)
        VALUES ('{admin_id}', 'admin', 'admin@weavefeed.local', '{password_hash}', true, true, '{now}', '{now}')
        ON CONFLICT (username) DO NOTHING
        """
    )

    op.execute(
        f"""
        INSERT INTO user_profiles (id, user_id, display_name, created_at, updated_at)
        VALUES ('{uuid.uuid4()}', '{admin_id}', 'Administrator', '{now}', '{now}')
        ON CONFLICT (user_id) DO NOTHING
        """
    )
```

### Database Management

To perform a migration you need to run `alembic upgrade head`

To recreate the database

```
DROP DATABASE accounts;
CREATE DATABASE accounts;
```