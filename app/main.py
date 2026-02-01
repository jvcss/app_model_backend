from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import auth, teams
from app.db.session import engine_internal_sync
from app.db.base import Base

app = FastAPI(
    title="API Applicativo",
    description="""
## 🔐 Autenticação

Esta API usa OAuth2 com Password Flow para autenticação.

### Como autenticar no Swagger UI:

1. **Faça registro** (se ainda não tem conta):
   - Use `POST /api/auth/register`
   - Copie o `access_token` retornado
   - Clique no botão **Authorize** (cadeado verde) e cole o token

2. **OU faça login direto pelo Swagger**:
   - Clique no botão **Authorize** (cadeado verde)
   - Digite seu **email** no campo `username`
   - Digite sua **senha** no campo `password`
   - Clique em **Authorize**

3. **OU faça login via endpoint**:
   - Use `POST /api/auth/login` com JSON `{"email": "...", "password": "..."}`
   - Copie o `access_token` retornado
   - Clique em **Authorize** e cole o token

### Importante:
- No campo `username` do OAuth2, use seu **email**
- Deixe os campos `client_id` e `client_secret` **vazios** (não são necessários)
- O token é válido por um longo período (não requer refresh)

### Endpoints protegidos:
Endpoints que requerem autenticação terão um ícone de cadeado 🔒
    """,
    version="1.0.0"
)

Base.metadata.create_all(bind=engine_internal_sync)

origins = [
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,         # Permite apenas as origens definidas na lista
    allow_credentials=True,        # Permite o envio de cookies e credenciais
    allow_methods=["*"],           # Permite todos os métodos (GET, POST, etc.)
    allow_headers=["*"],           # Permite todos os cabeçalhos
)


app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(teams.router, prefix="/api/teams", tags=["teams"])

@app.get("/")
def root():
    return {"message": "Bem-vindo à API do Applicativo. Aqui terá o OpenAPI da aplicação"}
