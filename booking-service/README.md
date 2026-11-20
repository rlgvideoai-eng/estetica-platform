# Booking Service - Ayudio

Servicio de agendamiento para el centro de estética Ayudio, construido con FastAPI, SQLAlchemy 2.0 (async), PostgreSQL y Alembic.

## 🚀 Características

- **CRUD completo** de servicios, profesionales, horarios, bloqueos
- **Cálculo de disponibilidad** en tiempo real (horario local ∩ profesional − reservas − bloqueos − Google Calendar)
- **Reservas idempotentes** con clave única
- **Sincronización bidireccional** con Google Calendar (OAuth 2.0)
- **Emails transaccionales** (confirmación, recordatorio 24h, cancelación, reprogramación) con archivo .ics
- **Notificaciones a admin** por Telegram
- **Políticas configurables**: anticipación mínima, horizonte máximo, grid, límite reservas/cliente
- **Zona horaria America/Santiago** en todo el sistema (almacena UTC, muestra Santiago)
- **Migraciones** con Alembic
- **Tests** con pytest + PostgreSQL test container

## 📁 Estructura

```
booking-service/
├── src/
│   ├── main.py                 # FastAPI app + lifespan
│   ├── config.py               # Pydantic Settings
│   ├── db/
│   │   ├── session.py          # SQLAlchemy async engine/session
│   │   └── base.py             # DeclarativeBase + mixins
│   ├── models/                 # SQLAlchemy models
│   │   ├── service.py
│   │   ├── professional.py
│   │   ├── business_hours.py
│   │   ├── time_block.py
│   │   ├── client.py
│   │   ├── booking.py
│   │   └── conversation_log.py
│   ├── schemas/                # Pydantic models (API)
│   ├── api/
│   │   ├── deps.py             # Auth internal API key
│   │   └── routes/
│   │       ├── services.py
│   │       ├── availability.py
│   │       ├── bookings.py
│   │       └── clients.py
│   ├── services/               # Business logic
│   │   ├── service_service.py
│   │   ├── professional_service.py
│   │   ├── availability_service.py  # Core AG-2
│   │   ├── booking_service.py
│   │   ├── client_service.py
│   │   ├── calendar_service.py      # Google Calendar
│   │   └── notification_service.py  # Email + Telegram admin
│   └── utils/
│       ├── logging.py
│       ├── timezone.py
│       └── ics.py              # Generador .ics
├── alembic/                    # Migraciones
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── requirements.txt
├── requirements-dev.txt
├── Dockerfile
└── README.md
```

## 🛠 Desarrollo Local

```bash
# 1. Variables de entorno
cp ../.env.example ../.env
# Editar .env con valores reales

# 2. Levantar servicios (PostgreSQL, Redis, etc.)
docker compose up -d postgres redis

# 3. Instalar dependencias
pip install -r requirements-dev.txt

# 4. Ejecutar migraciones
alembic upgrade head

# 5. Ejecutar servidor (hot reload)
uvicorn src.main:app --reload --port 8000

# 6. Tests
pytest --cov=src --cov-report=html
```

## 🐳 Docker

```bash
# Desarrollo (con hot reload)
docker compose up booking-service

# Producción
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d booking-service
```

## 📋 API Endpoints (Internos - X-Internal-Api-Key)

### Servicios
- `GET /services` - Lista paginada
- `GET /services/{id}` - Detalle
- `POST /services` - Crear
- `PATCH /services/{id}` - Actualizar
- `DELETE /services/{id}` - Soft delete

### Disponibilidad
- `GET /availability?service_id=&from=&to=&professional_id=` - Slots libres

### Reservas
- `POST /bookings` - Crear (idempotente)
- `GET /bookings` - Lista con filtros
- `GET /bookings/{id}` - Detalle
- `PATCH /bookings/{id}` - Actualizar (reprogramar, cancelar)
- `DELETE /bookings/{id}` - Cancelar (soft)

### Clientes
- `POST /clients` - Crear
- `GET /clients/by-telegram/{telegram_user_id}` - Buscar por Telegram ID
- `GET /clients/{id}` - Detalle

## ⚙️ Variables de Entorno

| Variable | Descripción | Requerida |
|----------|-------------|-----------|
| `DATABASE_URL` | PostgreSQL async URL | Sí |
| `INTERNAL_API_KEY` | Clave auth entre servicios | Sí |
| `GOOGLE_CLIENT_ID` | OAuth2 Client ID | Para Calendar |
| `GOOGLE_CLIENT_SECRET` | OAuth2 Secret | Para Calendar |
| `GOOGLE_REFRESH_TOKEN` | OAuth2 Refresh Token | Para Calendar |
| `GOOGLE_CALENDAR_ID` | Calendar ID (default: primary) | Para Calendar |
| `EMAIL_FROM` | Remitente emails | Sí |
| `EMAIL_PROVIDER_KEY` | SMTP/API Key (Gmail, SendGrid, etc.) | Sí |
| `ADMIN_EMAIL` | Email admin para notificaciones | Sí |
| `TIMEZONE` | Zona horaria (default: America/Santiago) | No |
| `CANCEL_MIN_HOURS` | Anticipación cancelación sin cargo (default: 24) | No |
| `BOOKING_MAX_HORIZON_DAYS` | Horizonte máx reservas (default: 60) | No |
| `GRID_SIZE_MINUTES` | Grid disponibilidad (default: 15) | No |
| `MAX_ACTIVE_BOOKINGS_PER_CLIENT` | Límite reservas activas/cliente (default: 3) | No |

## 🧪 Tests

```bash
# Unit tests
pytest tests/unit -v

# Integration tests (requiere PostgreSQL test container)
pytest tests/integration -v

# Con coverage
pytest --cov=src --cov-report=html
```

## 📦 Migraciones

```bash
# Crear migración
alembic revision --autogenerate -m "descripción"

# Aplicar migraciones
alembic upgrade head

# Rollback
alembic downgrade -1
```

## 📄 Licencia

Propietario - Ayudio Centro de Estética