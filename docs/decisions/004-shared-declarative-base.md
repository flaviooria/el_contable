# 004 - Shared Declarative Base

## Context

Initially, each feature defined its own ``DeclarativeBase`` subclass:

- ``features/movements/models.py`` → ``Base`` (own DeclarativeBase)
- ``features/account_balance/models.py`` → ``Base`` (own DeclarativeBase)

This prevented cross-feature foreign key relationships because SQLAlchemy requires a single ``Base`` for all tables involved in FK constraints.

We needed to introduce ``account_id`` FK from ``movements`` to ``accounts`` and from ``account_balances`` to ``accounts``, which requires all models to share the same ``Base``.

## Decision

We move the ``Base`` to ``database.py`` and have all feature models import it from there.

**Before:**

```python
# features/movements/models.py
class Base(DeclarativeBase):
    pass
```

**After:**

```python
# database.py
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

```python
# features/movements/models.py
from el_contable.database import Base
```

## Why

### Single Base for FK constraints

SQLAlchemy's ``declarative_base`` (or ``DeclarativeBase``) creates a metaclass that tracks all mapped classes. All tables that participate in foreign key relationships must use the same ``Base`` instance.

### Centralizing in ``database.py``

``database.py`` is already the canonical location for database-wide configuration (engine, session). Adding ``Base`` there is a natural extension and avoids creating a new file purely for this purpose.

## Alternatives Considered

### Feature-specific bases with aliased tables

Using ``table_args`` to define FKs across features was considered but adds complexity and obscures the relationship intent.

### Separate base per feature with cross-feature models in a shared module

Would require importing models across features in a non-hierarchical way, increasing coupling.

## Status

Accepted - 2026-08-28
