# 🚀 Quick Start - Testes

## TL;DR

```bash
# 1. Instalar dependências
pip install -r requirements-test.txt

# 2. Iniciar database de testes
./scripts/start-test-db.sh

# 3. Rodar testes
./scripts/run-tests.sh smoke
```

---

## Setup Completo (5 minutos)

### Passo 1: Instalar Dependências
```bash
pip install -r requirements-test.txt
```

### Passo 2: Iniciar Database de Testes
```bash
chmod +x scripts/*.sh
./scripts/start-test-db.sh
```

**O que acontece:**
- Inicia PostgreSQL na porta 5433
- Inicia Redis na porta 6380
- Aguarda serviços ficarem prontos
- Executa migrations automaticamente

**Saída esperada:**
```
🚀 Starting test database containers...
⏳ Waiting for PostgreSQL to be ready...
✅ PostgreSQL is ready!
✅ Redis is ready!
🔄 Running database migrations...
✅ Test database is ready!
```

### Passo 3: Rodar Smoke Tests
```bash
./scripts/run-tests.sh smoke
```

**Saída esperada:**
```
🔥 Running smoke tests...
======================== test session starts =========================
collected 11 items

tests/smoke/test_critical_endpoints.py::TestCriticalEndpoints::test_register_endpoint PASSED
tests/smoke/test_critical_endpoints.py::TestCriticalEndpoints::test_login_endpoint PASSED
...
======================== 11 passed in 2.35s ==========================
✅ Tests passed!
```

---

## Comandos Rápidos

```bash
# Smoke tests (mais rápido, <10s)
./scripts/run-tests.sh smoke

# Todos os testes
./scripts/run-tests.sh

# Unit tests apenas
./scripts/run-tests.sh unit

# Integration tests apenas
./scripts/run-tests.sh integration

# E2E tests apenas
./scripts/run-tests.sh e2e

# Com coverage report
./scripts/run-tests.sh coverage

# Parar database de testes
./scripts/stop-test-db.sh
```

---

## Estrutura de Arquivos Criados

```
docker-compose.test.yaml         # PostgreSQL + Redis para testes
scripts/
  ├── start-test-db.sh          # Iniciar database de testes
  ├── stop-test-db.sh           # Parar database de testes
  └── run-tests.sh              # Rodar testes (smoke/unit/integration/e2e/coverage)
.env.test                        # Variáveis de ambiente de teste
tests/
  ├── conftest.py               # Fixtures globais (ATUALIZADO para porta 5433)
  ├── unit/                     # 265+ testes
  ├── integration/              # 590+ testes
  ├── e2e/                      # 16 testes
  └── smoke/                    # 11 testes
```

---

## Workflow Diário

### Manhã (Iniciar)
```bash
./scripts/start-test-db.sh
```

### Durante Desenvolvimento
```bash
# Desenvolver código...

# Testar rapidamente
./scripts/run-tests.sh smoke

# Testar feature específica
pytest tests/unit/test_my_feature.py -v
```

### Antes de Commit
```bash
# Rodar todos os testes
./scripts/run-tests.sh

# Verificar coverage
./scripts/run-tests.sh coverage
```

### Noite (Finalizar)
```bash
./scripts/stop-test-db.sh
```

---

## Portas Usadas

| Ambiente | PostgreSQL | Redis |
|----------|-----------|--------|
| **Testes** | 5433 | 6380 |
| Dev | 3384 | 6398 |

**Não há conflito:** Testes e dev podem rodar simultaneamente!

---

## Troubleshooting Rápido

### ❌ Erro: "connection refused"
```bash
# Verificar se containers estão rodando
docker ps | grep test

# Se não, iniciar
./scripts/start-test-db.sh
```

### ❌ Erro: "relation does not exist"
```bash
# Executar migrations
export POSTGRES_INTERNAL_URL="postgresql+asyncpg://test_user:test_pass@localhost:5433/test_app_db"
alembic upgrade head
```

### ❌ Testes falhando aleatoriamente
```bash
# Resetar database
docker-compose -f docker-compose.test.yaml down -v
./scripts/start-test-db.sh
```

---

## Próximos Passos

1. ✅ Setup completo? → Veja [Documentação Completa](TESTING_SETUP.md)
2. 📚 Escrever novos testes? → Veja [Guia de Testes](docs/TESTING.md)
3. 🚀 CI/CD? → Veja [Workflows](.github/workflows/README.md)

---

## Resumo das Mudanças

### O que foi criado:
- ✅ `docker-compose.test.yaml` - PostgreSQL + Redis isolados
- ✅ Scripts helper para iniciar/parar/rodar testes
- ✅ `.env.test` com configurações de teste
- ✅ Documentação completa

### O que foi corrigido:
- ✅ `app/main.py` - Não executa `create_all` em modo teste
- ✅ `tests/conftest.py` - Portas corretas (5433/6380)
- ✅ Isolamento completo entre ambientes dev e test

### Benefícios:
- 🚀 Dev e test podem rodar simultaneamente
- 🔒 Dados de teste isolados
- ⚡ Scripts automatizados
- 📊 Coverage tracking
- 🎯 Smoke tests em <10 segundos
