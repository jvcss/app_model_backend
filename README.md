# 🚀 FastAPI Backend Boilerplate

> Enterprise-grade FastAPI application with authentication, teams, 2FA, and async task processing

<div align="center">

![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688?style=for-the-badge&logo=fastapi)
![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python)
![MySQL](https://img.shields.io/badge/MySQL-8.0+-4479A1?style=for-the-badge&logo=mysql)
![Redis](https://img.shields.io/badge/Redis-7.0+-DC382D?style=for-the-badge&logo=redis)
![Celery](https://img.shields.io/badge/Celery-5.3+-37814A?style=for-the-badge&logo=celery)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker)

</div>

## ✨ Features

### 🔐 Authentication & Security
- **JWT Authentication** with token versioning for instant token invalidation
- **2FA (TOTP)** with QR code generation for authenticator apps
- **Password Reset Flow** with OTP via email and optional TOTP verification
- **Rate Limiting** to prevent brute-force and enumeration attacks
- **Anti-Enumeration** measures with uniform error responses
- **Bcrypt** password hashing with configurable salt rounds

### 👥 User & Team Management
- User registration with automatic personal team creation
- Multi-tenancy support with team switching
- Team creation and management
- Current user context with automatic token refresh

### ⚡ Async Architecture
- **Async/Await** throughout with SQLAlchemy async sessions
- **Celery** for background task processing
- **Redis** as message broker and result backend
- **Flower** for real-time task monitoring

### 🗄️ Database
- **MySQL** with async driver (aiomysql)
- **SQLAlchemy** ORM with declarative models
- **Alembic** for database migrations
- Automatic table creation on startup

### 🐳 DevOps Ready
- **Docker Compose** for local development
- Multi-stage build with optimized layers
- Health checks for all services
- Resource limits and logging configuration
- Separate configurations for dev/prod environments

## 📁 Project Structure

```
backend/
├── app/
│   ├── api/
│   │   ├── dependencies.py      # Dependency injection (DB, auth, redis)
│   │   └── endpoints/
│   │       ├── auth.py          # Auth endpoints (login, register, 2FA, password reset)
│   │       └── teams.py         # Team management endpoints
│   ├── core/
│   │   ├── config.py            # Settings and environment variables
│   │   └── security.py          # JWT, password hashing, OTP, TOTP
│   ├── db/
│   │   ├── base.py              # SQLAlchemy Base
│   │   └── session.py           # Database session management
│   ├── models/
│   │   ├── user.py              # User model with 2FA fields
│   │   ├── team.py              # Team model
│   │   └── password_reset.py   # Password reset tracking
│   ├── schemas/
│   │   ├── auth.py              # Pydantic schemas for auth
│   │   ├── user.py              # Pydantic schemas for users
│   │   └── team.py              # Pydantic schemas for teams
│   ├── mycelery/
│   │   ├── app.py               # Celery configuration
│   │   └── worker.py            # Async tasks (email, etc)
│   ├── helpers/
│   │   ├── getters.py           # Utility functions
│   │   ├── rate_limit.py        # Rate limiting with Redis
│   │   └── qrcode_generator.py  # QR code generation for 2FA
│   └── main.py                  # FastAPI application entry point
├── docker-compose.yaml          # Production Docker Compose
├── docker-compose.dev.yaml      # Development Docker Compose
├── Dockerfile                   # Multi-stage Docker build
├── docker-entrypoint.sh         # Container entrypoint script
├── requirements.txt             # Python dependencies
└── .env.example                 # Environment variables template
```

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.12+ (for local development)
- MySQL 8.0+
- Redis 7.0+

### Installation

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd backend
```

2. **Configure environment variables**
```bash
cp .env.example .env
```

Edit `.env` with your configuration:
```env
MODE=development
KEY=your-secret-key-here

# MySQL (internal Docker network)
MYSQL_INTERNAL_URL=mysql+aiomysql://root:password@mysql_app_backend:3306/dbname
MYSQL_INTERNAL_URL_SYNC=mysql+pymysql://root:password@mysql_app_backend:3306/dbname

# MySQL (external localhost)
MYSQL_EXTERNAL_URL=mysql+aiomysql://root:password@localhost:3384/dbname
MYSQL_EXTERNAL_URL_SYNC=mysql+pymysql://root:password@localhost:3384/dbname

# Redis
CELERY_BROKER_URL=redis://redis_app_backend:6379/0
CELERY_BROKER_URL_EXTERNAL=redis://localhost:6398/0

# SMTP (for password reset emails)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

3. **Start with Docker Compose**

**Development (with hot reload):**
```bash
docker-compose -f docker-compose.dev.yaml up -d
```

**Production:**
```bash
docker-compose up -d
```

4. **Access the services**

- **API:** http://localhost:8006
- **API Docs:** http://localhost:8006/docs
- **Flower (Task Monitor):** http://localhost:5596
- **MySQL:** localhost:3384
- **Redis:** localhost:6398

### Local Development (without Docker)

1. **Create virtual environment**
 ```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Start services** (MySQL and Redis)
```bash
docker-compose -f docker-compose.dev.yaml up -d mysql_app_backend redis_app_backend
```

4. **Run the API**
```bash
 uvicorn app.main:app --reload
-```
\ No newline at end of file
```

5. **Run Celery worker** (in another terminal)
```bash
celery -A app.mycelery.app:celery_app worker --loglevel=info
```

6. **Run Flower** (optional, for task monitoring)
```bash
celery -A app.mycelery.app:celery_app flower --port=5555
```

## 🗄️ Database Migrations

### Create a new migration
```bash
alembic revision --autogenerate -m "description of changes"
```

### Apply migrations
```bash
alembic upgrade head
```

### Rollback migration
```bash
alembic downgrade -1
```

## 📚 API Documentation

Once the server is running, access the interactive API documentation:

- **Swagger UI:** http://localhost:8006/docs
- **ReDoc:** http://localhost:8006/redoc

### Key Endpoints

- `POST /api/auth/register` - Create new user account
- `POST /api/auth/login` - Authenticate and get JWT token
- `GET /api/auth/me` - Get current user info
- `POST /api/auth/logout` - Logout (blacklist token)
- `POST /api/auth/forgot-password/start` - Request password reset OTP
- `POST /api/auth/forgot-password/verify` - Verify OTP and get reset token
- `POST /api/auth/forgot-password/confirm` - Confirm password reset
- `POST /api/auth/2fa/setup` - Generate 2FA QR code
- `POST /api/auth/2fa/verify` - Enable 2FA with TOTP code
- `GET /api/teams/` - List user teams
- `POST /api/teams/` - Create new team

## 🔧 Tech Stack

- **Framework:** FastAPI 0.109+
- **Language:** Python 3.12+
- **Database:** MySQL 8.0 with aiomysql (async)
- **Cache/Queue:** Redis 7.0
- **Task Queue:** Celery with Flower
- **ORM:** SQLAlchemy 2.0 (async)
- **Migrations:** Alembic
- **Authentication:** JWT (python-jose), bcrypt
- **2FA:** PyOTP with QR code generation
- **Validation:** Pydantic v2
- **Containerization:** Docker & Docker Compose

## 🛡️ Security Features

### Authentication Flow
1. User registers → Personal team created automatically
2. User logs in → JWT token issued with token version
3. Token versioning allows instant invalidation on password change
4. Optional 2FA with TOTP for enhanced security

### Password Reset Flow
1. User requests reset → OTP sent to email
2. User verifies OTP (and TOTP if 2FA enabled) → Reset session token issued
3. User confirms new password → Token version incremented (all old tokens invalidated)

### Rate Limiting
- **Login attempts:** Prevent brute-force attacks
- **Password reset:** Limit OTP requests per email/IP
- **Anti-enumeration:** Uniform responses don't leak user existence

## 📦 Docker Services

| Service | Container Name | Port | Description |
|---------|---------------|------|-------------|
| API | app_backend | 8006 | FastAPI application |
| Worker | celery_app_backend_worker | - | Celery async tasks |
| Beat | celery_app_backend_beat | - | Celery scheduler |
| Flower | celery_app_backend_flower | 5596 | Task monitoring UI |
| MySQL | mysql_app_backend | 3384 | Database |
| Redis | redis_app_backend | 6398 | Cache & message broker |

## 🔍 Monitoring

### Flower Dashboard
Access Celery task monitoring at http://localhost:5596

- Real-time task progress
- Worker status
- Task history and results
- Retry and error tracking

### Logs
```bash
# View API logs
docker logs -f app_backend

# View worker logs
docker logs -f celery_app_backend_worker

# View all services
docker-compose logs -f
```

## 🧪 Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest
```

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for architecture details and development guidelines.

## 📄 License

This project is private and proprietary.

## 🙏 Acknowledgments

Built with [FastAPI](https://fastapi.tiangolo.com/), [SQLAlchemy](https://www.sqlalchemy.org/), [Celery](https://docs.celeryq.dev/), and [Docker](https://www.docker.com/)

---

<div align="center">

**[Documentation](http://localhost:8006/docs)** • **[Issues](../../issues)** • **[Contributing](CONTRIBUTING.md)**

Made with 🔥 by JVCSS

</div>
