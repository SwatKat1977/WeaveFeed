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
* Edit the alembic.ini file and update the sqlalchemy.url field,
  e.g. postgresql+psycopg2://weavefeed:password@db:5432/weavefeed) or
  replace with an environment variable (e.g. ${DATABASE_URL})

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
    # seed admin user
    admin_id = str(uuid.uuid4())
    password_hash = bcrypt.hash("WeaveFeed_Admin")

    op.execute(
        sa.text(
            "INSERT INTO users (id, username, email, password_hash, is_verified) "
            "VALUES (:id, :username, :email, :password_hash, true)"
        ),
        {
            "id": admin_id,
            "username": "admin",
            "email": "admin@weavefeed.local",
            "password_hash": password_hash,
        },
    )

    op.execute(
        sa.text(
            "INSERT INTO profiles (id, user_id, display_name, bio) "
            "VALUES (:id, :user_id, :display_name, :bio)"
        ),
        {
            "id": str(uuid.uuid4()),
            "user_id": admin_id,
            "display_name": "Administrator",
            "bio": "Default admin account",
        },
    )
```

### Database Management
