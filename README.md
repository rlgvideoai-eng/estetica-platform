# 💖 Ayudio - Plataforma Digital para Centro de Estética

Monorepo con todos los servicios para la plataforma digital de **Ayudio**, centro de estética en Santiago, Chile.

## 🏗 Arquitectura

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│   Landing   │────►│  Bot Service │────►│  Booking Service│
│  (React)    │     │  (FastAPI)   │     │   (FastAPI)     │
└─────────────┘     └──────┬───────┘     └────────┬────────┘
                           │                      │
                    ┌──────▼───────┐     ┌────────▼────────┐
                    │   RAG Mock   │     │   PostgreSQL    │
                    │  (Databricks)│     │   (Datos)       │
                    └──────────────┘     └─────────────────┘
                           │
                    ┌──────▼───────┐
                    │ Voice Mock   │
                    │ (STT/TTS)    │
                    └──────────────┘
```

## 📦 Servicios

| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| **Landing** | 3000 | Sitio estático React + Vite + Tailwind |
| **Bot Service** | 8000 | Bot Telegram + Agente LLM + RAG + Voz |
| **Booking Service** | 8001 | Agendamiento, Google Calendar, Emails |
| **RAG Mock** | 8002 | Mock de Databricks RAG para desarrollo |
| **Voice Mock** | 8003 | Mock STT/TTS para desarrollo |
| **PostgreSQL** | 5432 | Base de datos principal |
| **Redis** | 6379 | Cache y rate limiting |

## 🚀 Inicio Rápido

### Prerrequisitos
- Docker 24+ y Docker Compose 2+
- Python 3.11+ (para desarrollo local sin Docker)
- Node.js 20+ (para landing)

### 1. Clonar y configurar
```bash
git clone <repo>
cd estetica-platform

# Configurar variables de entorno
cp .env.example .env
# Editar .env con valores reales (ver sección Variables de Entorno)
```

### 2. Levantar todo con Docker Compose
```bash
# Desarrollo (con hot reload)
docker compose up -d

# Ver logs
docker compose logs -f

# Ver estado
docker compose ps
```

### 3. Verificar servicios
- **Landing**: http://localhost:3000
- **Bot Service API**: http://localhost:8000/docs
- **Booking Service API**: http://localhost:8001/docs
- **RAG Mock**: http://localhost:8002/health
- **Voice Mock**: http://localhost:8003/health

### 4. Probar el bot
1. Abrir Telegram y buscar `@ayudio` (o el username configurado)
2. Enviar `/start`
3. Probar flujo: "Quiero un masaje" → elige servicio → elige horario → confirma

## 🛠 Desarrollo Local (sin Docker)

### Landing
```bash
cd landing
npm install
npm run dev  # http://localhost:5173
```

### Bot Service
```bash
cd bot-service
pip install -r requirements-dev.txt
cp ../.env .env
uvicorn src.main:app --reload --port 8000
```

### Booking Service
```bash
cd booking-service
pip install -r requirements-dev.txt
cp ../.env .env
# Requiere PostgreSQL y Redis corriendo
alembic upgrade head
uvicorn src.main:app --reload --port 8001
```

## 🔐 Variables de Entorno (`.env`)

```bash
# -------------------------------------------
# Base de Datos
# -------------------------------------------
POSTGRES_DB=estetica
POSTGRES_USER=estetica
POSTGRES_PASSWORD=password_seguro

# -------------------------------------------
# Clave interna (comunicación entre servicios)
# -------------------------------------------
INTERNAL_API_KEY=clave_larga_y_aleatoria

# -------------------------------------------
# Telegram Bot
# -------------------------------------------
TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
TELEGRAM_WEBHOOK_SECRET=secreto_webhook
ADMIN_TELEGRAM_CHAT_ID=123456789

# -------------------------------------------
# LLM (Nemotron Nano Omni)
# -------------------------------------------
LLM_PROVIDER=nemotron
LLM_API_KEY=tu_api_key_nemotron
LLM_MODEL=nemotron-nano-omni

# -------------------------------------------
# RAG (Databricks) - En dev usa mock
# -------------------------------------------
DATABRICKS_RAG_URL=http://rag-mock:8000
DATABRICKS_TOKEN=token_databricks

# -------------------------------------------
# Booking Service
# -------------------------------------------
BOOKING_SERVICE_URL=http://booking-service:8000

# -------------------------------------------
# Google Calendar / Gmail (OAuth 2.0)
# -------------------------------------------
GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxx
GOOGLE_REFRESH_TOKEN=1//xxx

# -------------------------------------------
# Email
# -------------------------------------------
EMAIL_FROM=noreply@tudominio.cl
EMAIL_PROVIDER_KEY=tu_api_key_sendgrid_o_smtp
ADMIN_EMAIL=admin@tudominio.cl

# -------------------------------------------
# Configuración Negocio
# -------------------------------------------
TIMEZONE=America/Santiago
CANCEL_MIN_HOURS=24
BOOKING_MAX_HORIZON_DAYS=60
GRID_SIZE_MINUTES=15
MAX_ACTIVE_BOOKINGS_PER_CLIENT=3

# -------------------------------------------
# Voz (Fase 5)
# -------------------------------------------
STT_PROVIDER=mock
TTS_PROVIDER=mock

# -------------------------------------------
# Landing
# -------------------------------------------
VITE_BOT_USERNAME=ayudio
VITE_API_URL=http://localhost:8000
```

## 🧪 Tests

```bash
# Todos los tests
docker compose run --rm booking-service pytest
docker compose run --rm bot-service pytest
docker compose run --rm landing npm test

# Con coverage
docker compose run --rm booking-service pytest --cov=src --cov-report=html
```

## 📦 Despliegue a Producción (GCP VM)

### 1. Preparar VM
```bash
# En GCP Console: crear VM e2-standard-4 (4 vCPU, 16GB RAM)
# Ubuntu 22.04 LTS, permitir HTTP/HTTPS
# Agregar SSH key
```

### 2. Configurar DNS
```
A     ayudio.cl        → IP de la VM
A     api.ayudio.cl    → IP de la VM
CNAME www.ayudio.cl    → ayudio.cl
```

### 3. Deploy automático (GitHub Actions)
El workflow `.github/workflows/ci.yml` hace:
1. Lint + Type check + Tests
2. Build Docker images → GHCR
3. Deploy a VM via SSH (solo en `main`)

Configurar secrets en GitHub:
```
GCP_VM_HOST=xxx.xxx.xxx.xxx
GCP_VM_USER=ubuntu
GCP_VM_SSH_KEY=-----BEGIN OPENSSH PRIVATE KEY-----...
```

### 4. Manual (si no usas CI)
```bash
# En la VM
git clone <repo>
cd estetica-platform
cp .env.example .env
# Editar .env con valores PROD
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## 📁 Estructura del Monorepo

```
estetica-platform/
├── .github/workflows/ci.yml      # CI/CD
├── docker-compose.yml            # Orquestación dev
├── docker-compose.voice.yml      # Dev con voz real (faster-whisper + Piper)
├── docker-compose.prod.yml       # Producción con nginx + certbot
├── docker-compose.prod.yml       # Producción
├── .env.example                  # Template variables
├── .gitignore
├── landing/                      # React + Vite + Tailwind
├── bot-service/                  # FastAPI + python-telegram-bot
│   ├── src/
│   │   ├── bot/                  # Handlers Telegram
│   │   ├── agent/                # Core LLM + tools
│   │   ├── rag/                  # Cliente RAG
│   │   ├── booking/              # Cliente Booking Service
│   │   ├── notifier/             # Email + Telegram admin
│   │   └── voice/                # STT/TTS (faster-whisper + Piper)
│   ├── tests/
│   ├── Dockerfile                # Dev (mock STT/TTS)
│   ├── Dockerfile.voice          # Dev con voz real
│   ├── requirements.txt
│   └── requirements-dev.txt
├── booking-service/              # FastAPI + PostgreSQL
│   ├── src/
│   │   ├── api/routes/           # REST API
│   │   ├── services/             # Business logic (scheduler, calendar, notifications)
│   │   ├── models/               # SQLAlchemy models
│   │   └── utils/                # timezone, ics, logging
│   ├── alembic/                  # Migraciones
│   └── tests/
├── rag-mock/                     # Mock Databricks RAG
├── voice-mock/                   # Mock STT/TTS para dev
├── docker-compose.voice.yml      # Dev con STT/TTS reales
├── docker-compose.prod.yml       # Producción con nginx + certbot
├── docs/                         # Documentación
└── README.md
```

## 🎙️ Funcionalidad de Voz (Fase 5)

### Arquitectura STT/TTS
```
Usuario (Telegram) → Nota de voz (OGG/Opus)
    ↓
Bot Service → Descarga archivo
    ↓
STT Provider (faster-whisper / mock) → Texto transcrito
    ↓
Agent Core → Procesa texto → Genera respuesta
    ↓
TTS Provider (Piper / mock) → Audio OGG/Opus
    ↓
Usuario ← Nota de voz de respuesta + Texto
```

### Proveedores STT (Speech-to-Text)
| Proveedor | Descripción | Uso |
|-----------|-------------|-----|
| **mock** | Simula transcripción según tamaño de audio | Desarrollo local |
| **faster-whisper** | Modelo Whisper optimizado (CT2), CPU/GPU | Producción |
| **huggingface** | API HF Inference (whisper-medium) | Fallback cloud |

### Proveedores TTS (Text-to-Speech)
| Proveedor | Descripción | Uso |
|-----------|-------------|-----|
| **mock** | Genera silencio OGG/Opus placeholder | Desarrollo local |
| **piper** | TTS neuronal ligero, voces es-CL (carlfm) | Producción |
| **huggingface** | API HF Inference (coqui/tts-es-cl) | Fallback cloud |
| **browser** | Web Speech API (solo frontend) | Landing page |

### Configuración (.env)
```bash
# Voz (Fase 5)
STT_PROVIDER=faster-whisper    # mock | faster-whisper | huggingface
TTS_PROVIDER=piper             # mock | piper | huggingface

# Configuración faster-whisper
WHISPER_MODEL_SIZE=small       # tiny | base | small | medium | large
WHISPER_DEVICE=cpu             # cpu | cuda
WHISPER_COMPUTE_TYPE=int8      # int8 | int16 | float16 | float32

# Configuración Piper TTS
PIPER_MODEL_PATH=/models/piper/es_CL-carlfm-x_low.onnx
PIPER_CONFIG_PATH=/models/piper/es_CL-carlfm-x_low.onnx.json
PIPER_SPEAKER_ID=0
```

### Flujo de Voz Completo
1. **Usuario** envía nota de voz por Telegram (máx 60s, OGG/Opus)
2. **Bot Service** descarga el archivo
3. **STT Provider** transcribe a texto (es-CL)
4. **Agente** procesa el texto como mensaje normal
5. **Agente** genera respuesta (texto + opcional audio)
5. **TTS Provider** sintetiza audio OGG/Opus (32kbps, voip)
6. **Bot** envía respuesta: texto + nota de voz (si `/voz on`)

### Comando `/voz`
```
/voz on   → Activa respuestas de voz
/voz off  → Desactiva respuestas de voz (solo texto)
```

### Desarrollo con Voz Real
```bash
# Levantar entorno con STT/TTS reales (requiere ~4GB RAM)
docker compose -f docker-compose.yml -f docker-compose.voice.yml up -d

# Descargar modelos (primera vez)
docker compose -f docker-compose.yml -f docker-compose.voice.yml run model-downloader
```

### Tests de Voz
```bash
# Tests STT/TTS mock
cd bot-service && pytest tests/integration/test_voice_integration.py -v

# Tests integración agente + voz
cd bot-service && pytest tests/integration/test_agent_voice.py -v
```

## 📱 WhatsApp + Panel Admin (Fase 6)

### Arquitectura Multi-Canal
```
┌─────────────────┐     ┌──────────────────┐
│   Telegram      │     │    WhatsApp      │
│   (BotFather)   │     │  (Meta Cloud)    │
└────────┬────────┘     └────────┬─────────┘
         │                       │
         ▼                       ▼
┌─────────────────────────────────────────┐
│         ChannelAdapter Factory          │
│  (TelegramAdapter / WhatsAppAdapter)    │
└────────────────┬────────────────────────┘
                 │
                 ▼
        ┌─────────────────┐
        │   Agent Core    │
        │  (LLM + Tools)  │
        └────────┬────────┘
                 │
       ┌─────────┼─────────┐
       ▼         ▼         ▼
  Booking Svc  Calendar   Notifier
```

### ChannelAdapter - Abstracción Multi-Canal
| Método | Descripción |
|--------|-------------|
| `initialize()` | Inicializa conexiones y handlers |
| `start_polling()` | Inicia polling/webhook |
| `send_message(user_id, message)` | Envía texto/teclados |
| `send_voice(user_id, audio_bytes)` | Envía nota de voz |
| `process_update(update_data)` | Normaliza webhook a Message unificado |
| `verify_webhook_signature()` | Valida firma del webhook |
| `send_message()` / `send_voice()` | Envío unificado |

### WhatsApp Business API (Meta Cloud API)
| Funcionalidad | Implementación |
|---------------|----------------|
| **Mensajes de texto** | ✅ Con botones interactivos (máx 3) |
| **Notas de voz** | ✅ Subida media + envío audio |
| **Botones interactivos** | ✅ Reply buttons (máx 3) |
| **Webhook verificación** | ✅ Challenge + X-Hub-Signature-256 |
| **Media upload** | ✅ Subida media + envío por media_id |

### Configuración WhatsApp (.env)
```bash
# WhatsApp (Fase 6) - Meta Cloud API
WHATSAPP_PHONE_NUMBER_ID=tu_phone_number_id
WHATSAPP_ACCESS_TOKEN=tu_access_token
WHATSAPP_WEBHOOK_VERIFY_TOKEN=ayudio_webhook_verify
WHATSAPP_BUSINESS_ACCOUNT_ID=tu_business_account_id
```

### Panel Administrativo
| Funcionalidad | Endpoint | Descripción |
|---------------|----------|-------------|
| **Dashboard** | `GET /admin/stats` | Estadísticas generales |
| **Servicios CRUD** | `/admin/services` | CRUD completo |
| **Profesionales CRUD** | `/admin/professionals` | CRUD + asociación servicios |
| **Reservas Admin** | `/admin/bookings` | Listar, reprogramar, cancelar |
| **Estadísticas** | `/admin/stats/*` | Dashboard, popularidad, ingresos |

### Dashboard Métricas
| Métrica | Descripción |
|---------|-------------|
| `total_bookings` | Total reservas históricas |
| `bookings_today` | Reservas de hoy |
| `occupancy_rate` | Tasa de ocupación % |
| `total_revenue` | Ingresos totales |
| `by_day` | Reservas e ingresos por día |
| `by_service` | Popularidad por servicio |
| `by_professional` | Rendimiento por profesional |

### Configuración WhatsApp (.env)
```bash
# WhatsApp (Fase 6) - Meta Cloud API
WHATSAPP_PHONE_NUMBER_ID=tu_phone_number_id
WHATSAPP_ACCESS_TOKEN=tu_access_token
WHATSAPP_WEBHOOK_VERIFY_TOKEN=ayudio_webhook_verify
WHATSAPP_BUSINESS_ACCOUNT_ID=tu_business_account_id
```

### Flujo WhatsApp Completo
1. **Usuario** envía mensaje por WhatsApp
2. **Meta** envía webhook a `/webhook/whatsapp`
3. **WhatsAppAdapter** valida firma `X-Hub-Signature-256`
4. **WhatsAppAdapter** normaliza a `Message` unificado
5. **Agent Core** procesa como mensaje normal
6. **Respuesta** se envía por `WhatsAppAdapter.send_message()`
6. **Bot** responde: texto + botones + opcional nota de voz

### Desarrollo con WhatsApp
```bash
# Configurar ngrok para webhook local
ngrok http 8000

# Configurar webhook en Meta Developer Console
# URL: https://tu-ngrok.ngrok.io/webhook/whatsapp
# Verify token: ayudio_webhook_verify

# Variables de entorno necesarias
WHATSAPP_PHONE_NUMBER_ID=xxx
WHATSAPP_ACCESS_TOKEN=xxx
WHATSAPP_WEBHOOK_VERIFY_TOKEN=ayudio_webhook_verify
```

### Tests WhatsApp
```bash
# Tests adaptador WhatsApp
cd bot-service && pytest tests/integration/test_whatsapp_integration.py -v

# Tests panel admin
cd booking-service && pytest tests/integration/test_admin_panel.py -v
```

## 📋 Fases del Proyecto (según especificación)

| Fase | Estado | Descripción |
|------|--------|-------------|
| **Fase 0** | ✅ Completada | Cimientos: repo, Docker, CI, mocks, tests básicos |
| **Fase 1** | ✅ Completada | Landing page publicada con botón a bot |
| **Fase 2** | ✅ Completada | Bot informativo con RAG + derivación |
| **Fase 3** | ✅ Completada | Agendamiento completo (Calendar, emails, .ics) |
| **Fase 4** | ✅ Completada | Reprogramar/cancelar + recordatorios 24h (email + Telegram) |
| **Fase 5** | ✅ Completada | Voz (STT/TTS: faster-whisper + Piper) |
| **Fase 6** | ✅ Completada | WhatsApp + Panel admin |

## 🤝 Contribuir

1. Fork del repo
2. Crear rama: `git checkout -b feature/nueva-funcionalidad`
3. Commits con mensajes claros (Conventional Commits)
4. Push y Pull Request
4. CI debe pasar (lint, tests, build)

## 📄 Licencia

Propietario - **Ayudio Centro de Estética** - Todos los derechos reservados.

## 📞 Contacto

- **Email**: hola@ayudio.cl
- **Teléfono**: +56 2 2233 4455
- **Dirección**: Av. Providencia 1234, Providencia, Santiago
- **Instagram**: [@ayudio_cl](https://instagram.com/ayudio_cl)

---

*Construido con ❤️ para Ayudio - Tu centro de estética de confianza*

License
This project is licensed under the MIT License. See the LICENSE file for details.