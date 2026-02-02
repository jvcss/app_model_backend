# GitHub Actions Workflows

Este diretório contém os workflows de CI/CD para o projeto.

## Workflows Disponíveis

### 1. Tests (`tests.yml`)
**Trigger:** Push e Pull Requests para `master`, `main`, `develop`

**Duração:** ~10-15 minutos

**Jobs:**
- **test**: Executa todos os testes com coverage
  - Smoke tests (verificação rápida)
  - Unit tests
  - Integration tests
  - E2E tests
  - Upload para Codecov
  - Fail se coverage < 80%

- **lint**: Verificações de qualidade de código
  - Ruff (linter)
  - Black (formatação)
  - isort (ordenação de imports)
  - mypy (type checking)

**Services:**
- PostgreSQL 15 (porta 5432)
- Redis 7 (porta 6379)

**Artifacts:**
- Coverage report (XML + HTML)
- Retenção: 30 dias

---

### 2. Quick Check (`quick-check.yml`)
**Trigger:** Pull Requests apenas

**Duração:** <5 minutos

**Objetivo:** Feedback rápido em PRs

**Executa:**
- Smoke tests apenas (11 testes críticos)
- Syntax check básico

**Uso:** Validação rápida antes do merge

---

### 3. Nightly Tests (`nightly.yml`)
**Trigger:**
- Agendado: 2 AM UTC diariamente
- Manual: workflow_dispatch

**Duração:** ~30-45 minutos

**Strategy Matrix:**
- Python: 3.11, 3.12
- PostgreSQL: 14, 15, 16
- Total: 6 combinações

**Jobs:**
- **comprehensive-test**: Testes completos com paralelização
  - Executa com `pytest -n 4` (4 workers)
  - Coverage por versão
  - Upload para Codecov com flags

- **security-scan**: Scan de segurança
  - Safety (vulnerabilidades em dependências)
  - Bandit (vulnerabilidades no código)

**Artifacts:**
- HTML coverage report por combinação
- Security reports (JSON)
- Retenção: 7 dias (coverage), 30 dias (security)

---

## Configuração Necessária

### 1. Secrets do GitHub

Adicione em **Settings → Secrets and variables → Actions**:

```
CODECOV_TOKEN=<seu_token_do_codecov>
```

Para obter o token:
1. Acesse [codecov.io](https://codecov.io)
2. Conecte seu repositório GitHub
3. Copie o token do repositório

### 2. Variáveis de Ambiente (já configuradas nos workflows)

```yaml
MODE=test
POSTGRES_INTERNAL_URL=postgresql+asyncpg://test_user:test_pass@localhost:5432/test_app_db
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=test-secret-key-for-ci-only
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

---

## Status Badges

Adicione no README.md principal:

```markdown
![Tests](https://github.com/seu-usuario/seu-repo/workflows/Tests/badge.svg)
[![codecov](https://codecov.io/gh/seu-usuario/seu-repo/branch/master/graph/badge.svg)](https://codecov.io/gh/seu-usuario/seu-repo)
```

---

## Execução Local

### Simular CI localmente

```bash
# Smoke tests (como Quick Check)
pytest tests/smoke -v --tb=short --maxfail=1

# Todos os testes (como Tests workflow)
pytest tests/ -v --cov=app --cov-report=term-missing

# Testes paralelos (como Nightly)
pytest tests/ -v -n 4 --cov=app --cov-report=html

# Verificar coverage threshold
coverage report --fail-under=80
```

### Linters localmente

```bash
# Instalar ferramentas
pip install ruff black isort mypy

# Executar
ruff check app/ tests/
black --check app/ tests/
isort --check-only app/ tests/
mypy app/
```

---

## Otimizações Implementadas

### 1. Cache de Dependências
```yaml
- uses: actions/setup-python@v5
  with:
    cache: 'pip'
```
**Benefício:** Reduz tempo de instalação em ~2-3 minutos

### 2. Health Checks em Services
```yaml
options: >-
  --health-cmd pg_isready
  --health-interval 10s
```
**Benefício:** Garante que PostgreSQL/Redis estejam prontos antes dos testes

### 3. Smoke Tests Primeiro
```yaml
- name: Run smoke tests
  run: pytest tests/smoke -v --tb=short --maxfail=3
```
**Benefício:** Fail fast - detecta problemas críticos em <1 minuto

### 4. Paralelização (Nightly)
```yaml
pytest tests/ -v -n 4
```
**Benefício:** Reduz tempo de execução em ~50-70%

### 5. Continue on Error (Lint)
```yaml
continue-on-error: true
```
**Benefício:** Linters não bloqueiam testes, apenas alertam

---

## Troubleshooting

### Testes falhando no CI mas passando localmente

**Problema comum:** Diferenças de ambiente

**Soluções:**
1. Verificar versões Python/PostgreSQL
2. Verificar variáveis de ambiente
3. Rodar migrations: `alembic upgrade head`

### Coverage abaixo de 80%

**Análise:**
```bash
# Localmente, gerar HTML report
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

**Identificar arquivos sem cobertura:**
```bash
coverage report --show-missing
```

### Timeout no CI

**Configuração atual:**
- Tests: 30 minutos
- Quick Check: 5 minutos
- Nightly: 45 minutos

**Se estourar:**
1. Revisar testes lentos: `pytest --durations=10`
2. Otimizar fixtures com `scope="session"`
3. Aumentar timeout no workflow

---

## Workflow de Desenvolvimento

### 1. Durante desenvolvimento
```bash
# Rodar smoke tests localmente (rápido)
pytest tests/smoke -v
```

### 2. Antes de commit
```bash
# Rodar testes relacionados
pytest tests/unit/test_my_module.py -v
pytest tests/integration/test_my_feature.py -v

# Verificar coverage
pytest --cov=app/my_module --cov-report=term-missing
```

### 3. Antes de abrir PR
```bash
# Rodar todos os testes
pytest tests/ -v --cov=app

# Verificar threshold
coverage report --fail-under=80

# Rodar linters
black app/ tests/
isort app/ tests/
ruff check app/ tests/
```

### 4. Abrir PR
- **Quick Check** roda automaticamente (<5 min)
- Revisar resultados antes de solicitar review

### 5. Após aprovação e merge
- **Tests** roda no master
- **Nightly** roda diariamente às 2 AM UTC

---

## Métricas e Relatórios

### Codecov Dashboard
- Coverage por arquivo
- Trend de coverage ao longo do tempo
- Diff coverage em PRs
- Sunburst chart de coverage

### GitHub Actions
- Tempo de execução por workflow
- Taxa de sucesso/falha
- Logs detalhados de cada step

---

## Próximos Passos

### Melhorias futuras:
1. **Dependabot** - Atualização automática de dependências
2. **CodeQL** - Análise de segurança avançada
3. **Deploy automatizado** - CD para staging/production
4. **Performance benchmarks** - Detectar regressões de performance
5. **Visual regression tests** - Para interfaces web (se aplicável)

---

## Suporte

Para problemas com workflows:
1. Verificar logs no GitHub Actions
2. Rodar localmente primeiro
3. Consultar documentação do GitHub Actions
4. Abrir issue no repositório
