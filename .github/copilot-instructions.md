# GitHub Copilot Instructions

## Project Overview

This is a **production-ready FastAPI backend template** designed as a generic, high-performance solution for commercial applications. It provides enterprise-grade features including authentication, team management, 2FA, async task processing, and comprehensive security measures.

## Purpose and Goals

- **Generic Template Solution**: Serve as a reusable, customizable foundation for FastAPI projects
- **Production-Ready**: Built for high-performance commercial deployments
- **Full-Featured**: Include common enterprise requirements out-of-the-box
- **Security-First**: Implement industry-standard security practices
- **Scalable Architecture**: Support async operations and background task processing

## Tech Stack

### Core Technologies
- **Framework**: FastAPI 0.109+ (Python 3.12+)
- **Database**: MySQL 8.0 with async support (aiomysql)
- **ORM**: SQLAlchemy 2.0 (async mode)
- **Cache/Queue**: Redis 7.0
- **Task Queue**: Celery with Flower for monitoring
- **Authentication**: JWT (python-jose) with bcrypt password hashing
- **2FA**: PyOTP with QR code generation
- **Validation**: Pydantic v2
- **Migrations**: Alembic
- **Containerization**: Docker & Docker Compose

### Key Dependencies
- `fastapi[all]` - Web framework with OpenAPI support
- `sqlalchemy` - ORM with async capabilities
- `redis` - Caching and message broker
- `celery[redis]` - Distributed task queue
- `pyotp` & `qrcode[pil]` - Two-factor authentication
- `python-jose` & `bcrypt` - Security and authentication
- `alembic` - Database migrations

## Architecture

### Project Structure
```
app/
├── main.py                    # FastAPI application entry point
├── api/
│   ├── dependencies.py        # Dependency injection (DB, auth, Redis)
│   └── endpoints/
│       ├── auth.py            # Authentication endpoints
│       └── teams.py           # Team management endpoints
├── core/
│   ├── config.py              # Settings and environment variables
│   └── security.py            # JWT, password hashing, OTP, TOTP
├── db/
│   ├── base.py                # SQLAlchemy Base
│   └── session.py             # Database session management
├── models/
│   ├── user.py                # User model with 2FA fields
│   ├── team.py                # Team model
│   └── password_reset.py     # Password reset tracking
├── schemas/
│   ├── auth.py                # Pydantic schemas for auth
│   ├── user.py                # User schemas
│   └── team.py                # Team schemas
├── mycelery/
│   ├── app.py                 # Celery configuration
│   └── worker.py              # Async tasks (email, notifications)
└── helpers/
    ├── getters.py             # Utility functions
    ├── rate_limit.py          # Rate limiting with Redis
    └── qrcode_generator.py    # QR code generation for 2FA
```

### Design Patterns

1. **Async/Await Throughout**: All database operations and I/O are async
2. **Dependency Injection**: Use FastAPI's dependency injection for DB sessions, auth, and Redis
3. **Repository Pattern**: Database operations are abstracted through models
4. **Service Layer**: Business logic separated from endpoints
5. **Schema Validation**: Pydantic models for request/response validation

## Code Style and Conventions

### Python Style
- Follow **PEP 8** style guidelines
- Use **type hints** for all function parameters and return values
- Use **async/await** for all I/O operations
- Prefer **async with** for context managers (DB sessions, Redis connections)

### Naming Conventions
- **Files**: lowercase with underscores (e.g., `password_reset.py`)
- **Classes**: PascalCase (e.g., `UserModel`, `TeamSchema`)
- **Functions/Variables**: snake_case (e.g., `get_current_user`, `user_email`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `SECRET_KEY`, `DATABASE_URL`)
- **Private attributes**: prefix with underscore (e.g., `_internal_method`)

### FastAPI Patterns

#### Endpoint Definition
```python
@router.post("/endpoint", response_model=ResponseSchema)
async def endpoint_name(
    data: RequestSchema,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ResponseSchema:
    """
    Clear docstring describing the endpoint's purpose.
    
    Args:
        data: Description of the input data
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Description of the response
        
    Raises:
        HTTPException: Description of when this is raised
    """
    # Implementation
```

#### Database Operations
```python
# Always use async with for sessions
async with get_db_session() as db:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
```

#### Error Handling
```python
from fastapi import HTTPException, status

# Use appropriate HTTP status codes
raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Resource not found"
)
```

### Security Best Practices

1. **Password Handling**
   - Always hash passwords with bcrypt
   - Never log or return passwords in responses
   - Use password strength validation

2. **JWT Tokens**
   - Include token versioning for instant invalidation
   - Use short expiration times (15-30 minutes recommended)
   - Implement refresh token mechanism
   - Store token blacklist in Redis for logout

3. **Rate Limiting**
   - Apply rate limits to authentication endpoints
   - Use Redis for distributed rate limiting
   - Implement anti-enumeration measures

4. **Input Validation**
   - Use Pydantic schemas for all inputs
   - Validate and sanitize user inputs
   - Use parameterized queries (SQLAlchemy handles this)

5. **2FA Implementation**
   - Generate secure secrets with `pyotp.random_base32()`
   - Validate TOTP codes server-side
   - Implement backup codes for account recovery

### Database Patterns

#### Model Definition
```python
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from app.db.base import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    teams = relationship("Team", back_populates="owner")
```

#### Migrations
```bash
# Create migration after model changes
alembic revision --autogenerate -m "description of changes"

# Apply migrations
alembic upgrade head

# Rollback if needed
alembic downgrade -1
```

### Celery Tasks

```python
from app.mycelery.app import celery_app

@celery_app.task
def send_email_task(to_email: str, subject: str, body: str):
    """
    Background task to send email.
    """
    # Implementation
```

## Development Workflow

### Environment Setup
1. Copy `.env.example` to `.env` and configure variables
2. Use Docker Compose for local development: `docker-compose -f docker-compose.dev.yaml up -d`
3. Access API docs at http://localhost:8006/docs

### Making Changes
1. Create feature branch from main
2. Make minimal, focused changes
3. Test locally with `pytest` (if tests exist)
4. Run migrations if models changed
5. Update documentation if API changes
6. Commit with clear, descriptive messages

### Testing
- Place tests in `tests/` directory (if not exists, create it)
- Use `pytest` and `pytest-asyncio` for async tests
- Mock external services (email, Redis, etc.)
- Test both success and failure paths

### Docker Development
- **Development mode**: `docker-compose -f docker-compose.dev.yaml up -d` (hot reload enabled)
- **Production mode**: `docker-compose up -d`
- **View logs**: `docker logs -f app_backend`
- **Access MySQL**: `localhost:3384` (external port)
- **Access Redis**: `localhost:6398` (external port)

## Key Features to Maintain

### Authentication System
- JWT with token versioning
- Secure login/logout flow
- Password reset with OTP via email
- 2FA/TOTP support with QR code generation
- Anti-enumeration protection

### Team Management
- Multi-tenancy with team switching
- Automatic personal team creation on registration
- Team invitation and member management

### Async Task Processing
- Celery for background jobs
- Redis as message broker
- Flower for monitoring at http://localhost:5596

### Performance
- Async database operations
- Connection pooling
- Redis caching where appropriate
- Optimized Docker images with multi-stage builds

## Common Tasks

### Adding a New Endpoint
1. Define Pydantic schemas in `app/schemas/`
2. Add endpoint to appropriate router in `app/api/endpoints/`
3. Implement business logic
4. Add authentication/authorization if needed
5. Update OpenAPI docs (automatic with FastAPI)

### Adding a New Model
1. Create model in `app/models/`
2. Import in `app/db/base.py`
3. Generate migration: `alembic revision --autogenerate -m "add new model"`
4. Review and apply migration: `alembic upgrade head`
5. Create corresponding Pydantic schemas

### Adding a Background Task
1. Define task in `app/mycelery/worker.py`
2. Use `@celery_app.task` decorator
3. Call with `.delay()` or `.apply_async()`
4. Monitor in Flower dashboard

## Important Notes

### Configuration
- All configuration should use environment variables
- Use `app/core/config.py` for settings management
- Separate internal (Docker network) and external (localhost) URLs
- Never commit `.env` files with real credentials

### Database URLs
- **Internal (Docker)**: `mysql+aiomysql://root:password@mysql_app_backend:3306/dbname`
- **External (localhost)**: `mysql+aiomysql://root:password@localhost:3384/dbname`
- Use `MYSQL_INTERNAL_URL` in production, `MYSQL_EXTERNAL_URL` for local dev

### Redis URLs
- **Internal**: `redis://redis_app_backend:6379/0`
- **External**: `redis://localhost:6398/0`

## Anti-Patterns to Avoid

1. **Don't** use synchronous I/O in async functions
2. **Don't** commit sensitive data or credentials
3. **Don't** bypass Pydantic validation
4. **Don't** use raw SQL queries (use SQLAlchemy)
5. **Don't** hardcode configuration values
6. **Don't** return raw exceptions to clients
7. **Don't** skip rate limiting on public endpoints
8. **Don't** implement custom crypto (use established libraries)

## Resources

- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **SQLAlchemy Async**: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- **Celery**: https://docs.celeryq.dev/
- **Pydantic**: https://docs.pydantic.dev/
- **API Documentation**: http://localhost:8006/docs (when running)

## Contribution Guidelines

See [CONTRIBUTING.md](../CONTRIBUTING.md) for detailed architecture and development guidelines.

---

**Remember**: This is a production-ready template. Maintain high code quality, comprehensive security, and clear documentation for all changes.
