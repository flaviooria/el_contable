# 🎯 Python Code Style

## 💡 Convention

This project uses modern Python with strict static typing, explicit framework conventions, and consistent tooling.

The minimum supported Python version is defined in `pyproject.toml`, which is the source of truth for runtime and dependency versions.

## 🌍 Language

- All code, comments, docstrings, identifiers, exceptions, and developer-facing messages must be written in English.
- Keep terminology consistent with the project's domain language.
- Avoid unnecessary abbreviations and ambiguous names.

## 🏷️ Naming Conventions

Use standard Python naming conventions:

- `snake_case` for functions, methods, variables, parameters, and modules.
- `UPPER_SNAKE_CASE` for constants.
- `PascalCase` for classes and exceptions.
- Names should be concise, descriptive, and domain-oriented.

Prefer:

```python
movement_amount
transaction_date
calculate_available_balance()
```

over vague names such as:

```python
data
value
process()
```

## 🧩 Modern Typing — PEP 585 & PEP 604

Use modern Python type annotations.

Prefer native collection generics:

```python
list[str]
dict[str, int]
tuple[str, int]
set[str]
```

Prefer PEP 604 unions:

```python
str | None
int | float
```

Do not use legacy collection or union aliases from `typing`:

```python
List
Dict
Tuple
Set
Union
Optional
```

Utilities from `typing` that do not have native equivalents are allowed when appropriate, including:

```python
Annotated
Literal
Protocol
TypeGuard
Never
```

- Public functions, methods, and application boundaries should have explicit type annotations.
- Avoid `Any` unless interacting with genuinely dynamic or untyped data.
- Do not add `# type: ignore` merely to silence a typing error. Fix the underlying type issue whenever practical.

## 🐍 Modern Python Syntax

Use modern Python syntax when it improves clarity and reduces unnecessary boilerplate.

Features such as:

- assignment expressions (`:=`)
- structural pattern matching (`match`)
- comprehensions
- generator expressions

should only be used when they make the code easier to understand.

- Do not use modern syntax solely for novelty or to make code shorter.
- Prefer simple control flow when it is clearer.

## 📖 Documentation

Google-style docstrings are required for non-trivial public:

- modules
- classes
- functions
- methods

- Docstrings should explain behaviour, constraints, or intent that is not already obvious from the implementation.
- Do not add docstrings that merely repeat the function name or type signature.
- Trivial private functions and self-explanatory getters or setters do not require docstrings.
- Comments should primarily explain *why*, not repeat *what* the code already expresses.

## ⚡ FastAPI

Use FastAPI's native APIs and dependency injection system.

- Use `Depends` for dependency injection.
- Keep HTTP concerns inside endpoints and routers.
- Keep business logic outside route handlers.
- Keep route handlers focused on request parsing, dependency orchestration, and response construction.
- Use Pydantic models for request and response schemas.
- Do not pass FastAPI-specific objects into business logic unless they are genuinely required.

Prefer typed dependencies when they improve readability:

```python
from typing import Annotated

from fastapi import Depends

DatabaseSession = Annotated[Session, Depends(get_session)]
```

## ✅ Pydantic v2

Use Pydantic v2 APIs and conventions exclusively.

Prefer:

- `model_validate()`
- `model_dump()`
- `model_dump_json()`
- `ConfigDict`
- `field_validator`
- `model_validator`

Do not introduce deprecated Pydantic v1 APIs such as:

- `parse_obj()`
- `dict()`
- `json()`
- `validator`
- `root_validator`

- Do not use legacy inner `Config` classes when `ConfigDict` is appropriate.
- Pydantic models should represent validated application or API data.
- Do not use Pydantic models as database models.

## 🗄️ SQLAlchemy 2.x

Use SQLAlchemy 2.x APIs and conventions exclusively.

Use always name of the table in plural form:

```python
class User(Base):
    __tablename__ = "users"
```

Use modern declarative mappings:

- `Mapped[str]`
- `mapped_column()`

Use SQLAlchemy 2.x statements:

- `select()`
- `insert()`
- `update()`
- `delete()`

Do not use:

- the legacy Query API
- SQLAlchemy 1.x query patterns
- deprecated ORM APIs

- Keep feature-specific persistence logic inside the feature that owns the data whenever possible.
- Do not accumulate feature-specific queries inside shared database infrastructure.
- Keep transaction boundaries explicit.
- Services use `flush()` to validate and persist within a transaction, but do not commit. This keeps them testable and reusable.
- The router (FastAPI endpoint) is the proper place to call `commit()` after a service operation succeeds. If the operation fails, the router should not commit.
- Avoid hidden commits inside low-level persistence functions unless committing is explicitly part of their contract.

## 🔄 Models and Schemas

Keep persistence models and validation schemas conceptually separate.

- SQLAlchemy models represent persisted database entities.
- Pydantic models represent validated application or API data.
- Do not couple API schemas directly to persistence behaviour.
- Conversions between database entities and schemas should remain explicit and predictable.

## 🧹 Ruff

Ruff is the project's only formatter and linter.

Use Ruff for:

- formatting
- linting
- import ordering according to project configuration

Do not introduce alternative tooling such as:

- Black
- Flake8
- isort
- autopep8

unless explicitly requested and adopted as a project-level decision.

The Ruff configuration in `pyproject.toml` is the source of truth.

## 🔍 mypy

- mypy is the project's static type checker.
- Code should pass the configured mypy checks.
- Do not weaken global mypy configuration to work around a local typing issue.
- Prefer fixing the type model, narrowing values correctly, or improving the relevant interface.

## 📦 Dependencies

Use `uv` for dependency and environment management.

Before introducing a new dependency:

- Check whether the standard library already provides the required functionality.
- Check whether an existing project dependency already solves the problem.
- Ensure the new dependency has a clear and justified purpose.
- Avoid introducing overlapping libraries.

- Do not introduce alternative dependency managers unless explicitly requested.
- Dependency versions are defined in `pyproject.toml`.

## 🏛️ Architecture

Follow the architecture defined in `docs/ARCHITECTURE.md`.

In particular:

- organize business functionality by feature
- keep HTTP concerns separate from business logic
- keep feature-specific persistence logic inside its owning feature
- avoid unnecessary cross-feature dependencies
- prefer explicit dependencies
- avoid premature abstractions

Do not introduce alternative architectural patterns, frameworks, libraries, or abstraction layers unless explicitly requested or documented through an architectural decision.

## ⚠️ Error Handling

Use exceptions deliberately.

- Raise specific exceptions instead of generic `Exception`.
- Do not silently swallow errors.
- Do not catch exceptions unless they can be handled meaningfully.
- Preserve the original exception when wrapping errors when appropriate.
- Keep HTTP-specific exceptions at the HTTP or application boundary whenever possible.
- Business logic should not depend unnecessarily on FastAPI-specific exceptions.

## 🧪 Testing

Code should be designed so business logic can be tested independently from FastAPI and external infrastructure whenever practical.

Tests should:

- be deterministic
- focus on observable behaviour
- use descriptive names
- avoid unnecessary coupling to implementation details
- avoid excessive mocking when simpler dependency boundaries are available

Bug fixes should include a regression test when practical.

## ✅ Validation

After modifying Python code, run:

```bash
make checks
```

The validation suite should cover:

- Ruff linting
- Ruff formatting
- mypy
- tests

Implementation work should not be considered complete while relevant checks are failing.

## 🏆 Benefits

### ✨ Modern Python

Modern type annotations and language features keep the code concise without relying on deprecated syntax.

### 🔒 Strong Typing

mypy helps detect invalid assumptions and interface mismatches before runtime.

### 🧭 Explicit Conventions

Clear rules for FastAPI, Pydantic, SQLAlchemy, and project architecture reduce inconsistent implementation choices.

### 🧹 Consistent Formatting

Using Ruff as the single formatter and linter prevents conflicting formatting and linting tools.

### 🧱 Clear Boundaries

Separating HTTP concerns, schemas, business logic, and persistence keeps features easier to understand and test.

### 🌍 Consistent Language

Using English throughout the codebase avoids language switching and keeps terminology consistent across developers and AI agents.

### 🚫 Reduced Tooling Drift

The established stack must be followed instead of introducing alternative libraries, frameworks, or architectural patterns without a concrete reason.

## 👀 Examples

### ✅ Good: Modern typing, clear naming, and simple control flow

```python
from dataclasses import dataclass

MAX_BATCH_SIZE: int = 100


@dataclass(frozen=True)
class UserProfile:
    user_id: int
    username: str
    is_active: bool = True


def fetch_users(user_ids: list[int]) -> dict[int, UserProfile | None]:
    """Fetch user profiles for the provided user IDs."""
    if len(user_ids) > MAX_BATCH_SIZE:
        raise ValueError(f"Batch size {len(user_ids)} exceeds limit of {MAX_BATCH_SIZE}")

    results: dict[int, UserProfile | None] = {}

    for user_id in user_ids:
        if user_id == 0:
            results[user_id] = None
            continue

        results[user_id] = UserProfile(
            user_id=user_id,
            username=f"user_{user_id}",
        )

    return results
```

### ❌ Bad: Legacy typing, unclear naming, and inconsistent conventions

```python
from typing import Dict, List, Optional

TAMANO_MAXIMO = 100


def obtenerUsuarios(
    lista_ids: List[int],
) -> Dict[int, Optional[UserProfile]]:
    res = {}

    for i in lista_ids:
        if i == 0:
            res[i] = None
        else:
            res[i] = UserProfile(
                user_id=i,
                username="user_" + str(i),
            )

    return res
```

Problems with this example:

- Uses deprecated typing aliases.
- Uses Spanish identifiers.
- Uses vague variable names.
- Does not declare the constant type.
- Uses inconsistent naming conventions.
- Does not follow the project's English-only rule.