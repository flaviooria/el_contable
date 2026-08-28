# 🧮 El Contable

> *App web que te ayuda a gestionar tus cuentas sin morir en el intento.* 💸

**El Contable** es una aplicación web de contabilidad personal que te permite **importar tus movimientos bancarios** desde archivos Excel/CSV, validarlos automáticamente contra tus datos existentes y **mantener tu saldo disponible siempre al día** para futuras visualizaciones.

---

## 🚀 ¿Qué hace?

- 📥 **Importación de movimientos** desde archivos `.xlsx` y `.csv` con un formato estándar de banco.
- 🔍 **Deduplicación inteligente** por clave única `(fecha_movimiento, importe, disponible)`, evitando duplicados tanto dentro del mismo archivo como entre subidas repetidas.
- 📅 **Ordenación automática** por fecha (de más reciente a más antiguo), sin importar el orden en que vengan las filas del archivo.
- 💰 **Seguimiento del saldo disponible** real mediante una tabla dedicada que se actualiza en cada subida.
- 📊 **Base para visualizaciones** del saldo y los movimientos en el frontend.

---

## 🏗️ Arquitectura

Proyecto en **Python 3.12+** con arquitectura **modular basada en features** (vertical slicing), donde cada feature agrupa su capa HTTP, lógica de aplicación y persistencia.

```
src/el_contable/
├── database.py                  # Configuración de la base de datos (SQLAlchemy)
├── features/
│   ├── account_balance/         # Saldo disponible autoritativo (models, service)
│   └── movements/               # Importación y validación de movimientos
└── templates/                   # Plantilla Excel oficial
```

**Stack principal:**

| Componente | Tecnología |
|------------|------------|
| Framework web | [FastAPI](https://fastapi.tiangolo.com/) ⚡ |
| ORM | SQLAlchemy 2.x |
| Base de datos | PostgreSQL 16 (vía Docker) 🐘 |
| Procesamiento de datos | Polars 📊 |
| Reading de Excel | fastexcel / openpyxl |
| Migraciones | Alembic |
| Gestión de dependencias | uv |
| Linter/Formato | Ruff |
| Type checking | mypy |
| Tests | pytest |

---

## 🗺️ Estructura de documentación

El proyecto sigue un flujo **OpenSpec** para el diseño de features:

```
openspec/
├── specs/                       # Especificaciones formales de cada feature
│   ├── upload_movements/
│   └── account_balance/
└── changes/                     # Propuestas y tareas de cambios
    ├── upload-movements/
    └── account-balance/

docs/
├── ARCHITECTURE.md              # Arquitectura y límites de módulos
├── FUNCTIONAL.md                # Reglas de negocio
├── code_style.md                # Convenciones de código
└── decisions/                   # ADRs (Records de Decisiones de Arquitectura)
    ├── 001-movements-upload-strategy.md
    └── 002-account-balance.md
```

---

## 📋 Requisitos previos

- 🐍 **Python 3.12+** (el proyecto usa [uv](https://docs.astral.sh/uv/) como gestor)
- 🐳 **Docker** + **Docker Compose** (para PostgreSQL)
- ⚙️ **mise** (opcional, permite ejecutar tareas con `mise run <task>`)

---

## ⚙️ Configuración

### 1️⃣ Instalar dependencias

```bash
make install
# o
uv sync --group dev
```

### 2️⃣ Levantar la base de datos PostgreSQL 🐘

```bash
make db-up
```

Esto levanta un contenedor `postgres:16-alpine` con las credenciales por defecto.

### 3️⃣ Aplicar las migraciones de base de datos

```bash
make migrate
```

### 4️⃣ Arrancar el servidor de desarrollo 🚀

```bash
make dev
```

---

## 🔐 Variables de entorno

Actualmente la conexión a la base de datos está **definida directamente** en el código. Los valores por defecto son:

| Variable | Valor por defecto | Descripción |
|----------|-------------------|-------------|
| `DATABASE_URL` | `postgresql+psycopg://el_contable:el_contable@localhost:5432/el_contable` | Cadena de conexión de SQLAlchemy (definida en `src/el_contable/database.py` y `alembic.ini`) |

> 💡 **Nota:** A día de hoy los valores de conexión están hardcodeados. Cuando se introduzca el soporte de `.env`, `DATABASE_URL` (y las credenciales de PostgreSQL del contenedor) pasarán a resolverse desde variables de entorno.

---

## 🛠️ Comandos

### Gestión de la base de datos 🐘

| Comando | Descripción |
|---------|-------------|
| `make db-up` | Levanta el contenedor PostgreSQL |
| `make db-down` | Apaga el contenedor PostgreSQL |
| `make migrate` | Aplica las migraciones (`alembic upgrade head`) |
| `make revision m="mensaje"` | Genera una migración nueva (autogenerate) |
| `make downgrade` | Revierte la última migración |

### Desarrollo y calidad 🧑‍💻

| Comando | Descripción |
|---------|-------------|
| `make dev` | Arranca el servidor de desarrollo FastAPI |
| `make lint` | Ejecuta Ruff (lint) |
| `make format` | Formatea el código con Ruff |
| `make format-check` | Verifica el formato |
| `make typecheck` | Ejecuta mypy |
| `make test` | Ejecuta pytest |
| `make checks` | Suite completa: lint + formato + typecheck + tests ✅ |
| `make clean` | Limpia cachés y temporales |

> Todos los comandos también están disponibles vía **mise**: `mise run dev`, `mise run checks`, etc.

---

## 🧪 Estilo y calidad

- **Ruff** como linter y formateador (line-length 100, indent 4).
- **mypy** para comprobación de tipos estática.
- **pytest** para la suite de pruebas.
- Toda la lógica de negocio se implementa dentro de la feature correspondiente bajo `src/el_contable/features/`.
- Las tablas SQLAlchemy se nombran **siempre en plural** (ej. `movements`, `account_balances`).

---

## 📌 Alcance actual

**Incluido:**
- ✅ Subida de archivos `.xlsx`/`.csv` de movimientos
- ✅ Validación y deduplicación de movimientos
- ✅ Ordenación descendente por fecha
- ✅ Almacenamiento del saldo disponible (tabla `account_balances`)
- ✅ Migraciones gestionadas con Alembic

**Pendiente / futuro:**
- 🔒 Autenticación de usuarios
- 📊 Visualizaciones y gráficos del saldo en el frontend
- 💳 Soporte de múltiples cuentas
- 🔄 Cálculo y reconciliación de saldos

---

<p align="center">Hecho con ❤️ y muchos ☕ para no perder el hilo de tus finanzas.</p>
