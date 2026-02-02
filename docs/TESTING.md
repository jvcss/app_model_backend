# Guia de Testes

Este documento descreve a estratégia e práticas de testes do projeto.

## 📚 Índice

1. [Visão Geral](#visão-geral)
2. [Estrutura de Testes](#estrutura-de-testes)
3. [Tipos de Testes](#tipos-de-testes)
4. [Executando Testes](#executando-testes)
5. [Escrevendo Testes](#escrevendo-testes)
6. [Coverage](#coverage)
7. [CI/CD](#cicd)
8. [Troubleshooting](#troubleshooting)

---

## Visão Geral

**Objetivo:** 80% de cobertura de código com testes automatizados.

**Stack de Testes:**
- pytest 8.0+ (framework)
- pytest-asyncio (async support)
- httpx (HTTP client)
- factory-boy (data factories)
- fakeredis (Redis mock)
- freezegun (time mocking)

**Total de Testes:** 882+ testes

---

## Estrutura de Testes

```
tests/
├── conftest.py              # Fixtures globais
├── pytest.ini               # Configuração pytest
├── .coveragerc              # Configuração coverage
│
├── unit/                    # Testes unitários (265+ testes)
│   ├── test_security.py     # JWT, bcrypt, OTP, TOTP
│   ├── test_permissions.py  # RBAC
│   └── test_schemas_validation.py
│
├── integration/             # Testes de integração (590+ testes)
│   ├── auth/               # Endpoints de autenticação
│   ├── teams/              # Endpoints de teams
│   ├── organizations/      # Endpoints de organizations
│   └── logs/               # Endpoints de logs
│
├── e2e/                     # End-to-end (16 testes)
│   ├── test_user_registration_flow.py
│   ├── test_password_reset_flow.py
│   ├── test_2fa_setup_flow.py
│   └── test_team_collaboration_flow.py
│
├── smoke/                   # Smoke tests (11 testes)
│   └── test_critical_endpoints.py
│
└── factories/               # Data factories
    ├── user.py
    ├── team.py
    ├── organization.py
    ├── team_member.py
    └── organization_member.py
```

---

## Tipos de Testes

### 1. Unit Tests (Whitebox)

**Características:**
- Sem banco de dados
- Testa lógica isolada
- Muito rápidos (<1s para 265 testes)

**Alvos:**
- `app/core/security.py` - JWT, hashing, OTP, TOTP
- `app/core/permissions.py` - RBAC completo
- `app/schemas/*.py` - Validações Pydantic

**Exemplo:**
```python
def test_admin_can_delete_team():
    assert has_permission(TeamRole.ADMIN, Resource.TEAM, Action.DELETE) is True
```

**Executar:**
```bash
pytest tests/unit -v
```

---

### 2. Integration Tests (Blackbox)

**Características:**
- Com banco de dados real (PostgreSQL)
- Testa endpoints completos
- Isolamento por transação (rollback)

**Alvos:**
- Todos os 26 endpoints da API
- Validação de schemas
- RBAC enforcement
- Edge cases

**Matriz de casos por endpoint:**
- ✅ Happy path (200/201)
- ❌ Schema inválido (422)
- 🔒 Sem autenticação (401)
- 🚫 Sem permissão (403)
- 📭 Recurso não encontrado (404)
- ⚠️ Edge cases

**Exemplo:**
```python
async def test_login_success(client, db_session):
    user = await UserFactory.create_with_team_async(
        db_session, email="test@example.com", password="Test123!"
    )
    await db_session.commit()

    response = await client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "Test123!"}
    )

    assert response.status_code == 200
    assert "access_token" in response.json()
```

**Executar:**
```bash
pytest tests/integration -v
```

---

### 3. Smoke Tests

**Características:**
- Testes críticos mais rápidos
- <10 segundos total
- Detecta quebras graves

**Alvos:**
- Endpoints essenciais: login, register, me
- Validação de JWT
- Criação de personal team

**Uso:**
- CI rápido em Pull Requests
- Verificação pré-deploy

**Executar:**
```bash
pytest tests/smoke -v
```

---

### 4. End-to-End Tests

**Características:**
- Fluxos completos de usuário
- Multi-step workflows
- Simula uso real

**Fluxos cobertos:**
1. **Registration Flow**
   - Registro → Personal Team → Criar Org → Criar Team → Colaboração

2. **Password Reset Flow**
   - Start (OTP) → Verify → Confirm → Login com nova senha

3. **2FA Setup Flow**
   - Setup → Verify TOTP → Login com 2FA

4. **Team Collaboration Flow**
   - Multi-user → Convites → Org membership → Permissions

**Exemplo:**
```python
async def test_complete_registration_flow(client):
    # 1. Register
    register_resp = await client.post("/api/auth/register", json={...})
    token = register_resp.json()["access_token"]

    # 2. Create organization
    org_resp = await client.post("/api/organizations/", headers={...}, json={...})

    # 3. Create team
    team_resp = await client.post("/api/teams/", headers={...}, json={...})

    # 4. Add org to team
    await client.post(f"/api/teams/{team_id}/members/organizations", ...)

    # 5. Verify structure
    members = await client.get(f"/api/teams/{team_id}/members", ...)
    assert len(members.json()) == 2  # user + org
```

**Executar:**
```bash
pytest tests/e2e -v
```

---

## Executando Testes

### Setup Inicial

```bash
# 1. Instalar dependências
pip install -r requirements.txt
pip install -r requirements-test.txt

# 2. Criar database de teste
createdb test_app_db

# 3. Rodar migrations
POSTGRES_INTERNAL_URL=postgresql+asyncpg://localhost/test_app_db alembic upgrade head
```

### Comandos Básicos

```bash
# Todos os testes
pytest -v

# Por tipo
pytest tests/unit -v
pytest tests/integration -v
pytest tests/e2e -v
pytest tests/smoke -v

# Arquivo específico
pytest tests/unit/test_security.py -v

# Teste específico
pytest tests/unit/test_security.py::TestJWT::test_create_access_token -v

# Com coverage
pytest --cov=app --cov-report=term-missing

# Paralelo (4 workers)
pytest -n 4

# Stop no primeiro erro
pytest -x

# Mostrar prints
pytest -s

# Top 10 testes mais lentos
pytest --durations=10
```

### Comandos Avançados

```bash
# Apenas testes que falharam na última execução
pytest --lf

# Apenas novos testes
pytest --nf

# Markers
pytest -m "unit"
pytest -m "integration"
pytest -m "e2e"
pytest -m "smoke"

# Keyword
pytest -k "login"
pytest -k "not slow"

# Verbose + traceback curto
pytest -v --tb=short

# Com debugger (breakpoint)
pytest --pdb
```

---

## Escrevendo Testes

### 1. Testes Unitários

**Template:**
```python
import pytest

class TestMyFunction:
    def test_happy_path(self):
        result = my_function(valid_input)
        assert result == expected_output

    def test_edge_case(self):
        with pytest.raises(ValueError):
            my_function(invalid_input)

    @pytest.mark.parametrize("input,expected", [
        ("a", 1),
        ("b", 2),
        ("c", 3),
    ])
    def test_multiple_cases(self, input, expected):
        assert my_function(input) == expected
```

### 2. Testes de Integração

**Template:**
```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
class TestMyEndpoint:
    async def test_success(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/endpoint",
            headers=auth_headers,
            json={"field": "value"}
        )

        assert response.status_code == 201
        assert response.json()["field"] == "value"

    async def test_unauthorized(self, client: AsyncClient):
        response = await client.post("/api/endpoint", json={})
        assert response.status_code == 401

    async def test_forbidden(self, client: AsyncClient, db_session):
        # Create user without permission
        user = await UserFactory.create_with_team_async(db_session)
        token = create_access_token({"sub": str(user.id)}, user.token_version)
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.post("/api/endpoint", headers=headers, json={})
        assert response.status_code == 403
```

### 3. Usando Factories

```python
from tests.factories.user import UserFactory
from tests.factories.organization import OrganizationFactory, ProviderFactory

async def test_with_factory(db_session):
    # User básico
    user = await UserFactory.create_with_team_async(db_session)

    # User customizado
    admin = await UserFactory.create_with_team_async(
        db_session,
        email="admin@test.com",
        name="Admin User"
    )

    # Organization Provider
    provider = await ProviderFactory.create_async(
        db_session,
        name="My Provider",
        services_offered=["Development"]
    )

    await db_session.commit()
```

### 4. Fixtures Disponíveis

**Globais (tests/conftest.py):**
- `event_loop` - Event loop async (session-scoped)
- `db_session` - Database session com rollback automático
- `redis_client` - FakeRedis em memória
- `client` - httpx.AsyncClient com overrides
- `user` - User com personal team
- `auth_headers` - Headers de autenticação
- `team` - Team do user
- `organization` - Organization básica

**Exemplo de uso:**
```python
async def test_with_fixtures(client, user, auth_headers, team):
    # user e team já existem no banco
    # auth_headers já tem token JWT válido

    response = await client.get("/api/auth/me", headers=auth_headers)
    assert response.json()["user"]["id"] == user.id
```

---

## Coverage

### Meta: ≥80%

### Gerar Relatório

```bash
# Terminal
pytest --cov=app --cov-report=term-missing

# HTML (navegável)
pytest --cov=app --cov-report=html
open htmlcov/index.html

# XML (para CI)
pytest --cov=app --cov-report=xml
```

### Verificar Threshold

```bash
# Fail se < 80%
coverage report --fail-under=80
```

### Análise de Coverage

```bash
# Ver arquivos sem cobertura
coverage report --show-missing

# Ver apenas arquivos com < 80%
coverage report | grep -v "100%"
```

### Configuração (.coveragerc)

```ini
[run]
source = app
omit = */tests/*, */migrations/*, */mycelery/*

[report]
precision = 2
fail_under = 80
exclude_lines =
    pragma: no cover
    if __name__ == .__main__.:
```

---

## CI/CD

### Workflows

1. **Tests** - Push e PRs
   - Smoke → Unit → Integration → E2E
   - Coverage upload para Codecov
   - Lint (Ruff, Black, isort, mypy)

2. **Quick Check** - PRs apenas
   - Smoke tests (<5 min)
   - Feedback rápido

3. **Nightly** - Diariamente 2 AM UTC
   - Matrix: Python 3.11/3.12 × PostgreSQL 14/15/16
   - Testes paralelos
   - Security scan

### Status Checks

**Obrigatórios para merge:**
- ✅ Smoke tests passed
- ✅ All tests passed
- ✅ Coverage ≥80%
- ⚠️ Lint warnings (não bloqueia)

### Codecov

**Dashboard:** https://codecov.io/gh/seu-usuario/seu-repo

**Métricas:**
- Project coverage: ≥80%
- Patch coverage: ≥80%
- Diff em PRs
- Sunburst chart

---

## Troubleshooting

### Testes falhando localmente

```bash
# 1. Verificar database
psql -l | grep test_app_db

# 2. Recriar database
dropdb test_app_db
createdb test_app_db
POSTGRES_INTERNAL_URL=postgresql+asyncpg://localhost/test_app_db alembic upgrade head

# 3. Limpar cache do pytest
pytest --cache-clear

# 4. Reinstalar dependências
pip install -r requirements-test.txt --force-reinstall
```

### Testes lentos

```bash
# Identificar testes lentos
pytest --durations=10

# Otimizar:
# - Usar scope="session" ou "module" em fixtures
# - Mockar I/O (HTTP, file system)
# - Reduzir volume de dados em factories
```

### Coverage inconsistente

```bash
# Rodar em modo verbose
pytest --cov=app --cov-report=term-missing -v

# Verificar arquivos ignorados
coverage report --show-missing
```

### Fixtures não encontradas

```bash
# Listar fixtures disponíveis
pytest --fixtures

# Verificar conftest.py hierarchy
tests/conftest.py          # Globais
tests/unit/conftest.py     # Unit específicas
tests/integration/conftest.py  # Integration específicas
```

---

## Melhores Práticas

### ✅ DO

- Escrever testes antes de abrir PR
- Usar factories para dados de teste
- Testar happy path + edge cases + error cases
- Nomear testes descritivamente: `test_user_cannot_delete_team_without_permission`
- Usar fixtures para setup compartilhado
- Isolar testes (sem dependências entre eles)
- Mockar I/O externo (email, Celery)

### ❌ DON'T

- Commitar testes comentados
- Usar sleep() - use freezegun
- Testar implementação ao invés de comportamento
- Criar testes interdependentes
- Usar dados hardcoded - use factories
- Ignorar warnings do pytest
- Baixar coverage apenas para passar CI

---

## Recursos

- [pytest docs](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [factory-boy](https://factoryboy.readthedocs.io/)
- [Codecov docs](https://docs.codecov.io/)
- [GitHub Actions docs](https://docs.github.com/en/actions)
