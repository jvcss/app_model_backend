"""
    Authentication and Authorization Endpoints
    This module provides API endpoints for user authentication, registration, password reset, and two-factor authentication (2FA) management. It leverages FastAPI for routing, SQLAlchemy for database interactions, and JWT for secure token handling. The endpoints are designed with security best practices, including rate limiting, anti-enumeration measures, and support for out-of-band OTP delivery.
    Endpoints:
    - /login: Authenticates a user and issues a JWT access token.
    - /me: Returns the current authenticated user's information and a fresh access token.
    - /logout: Handles user logout (JWT-based, client-side or via blacklist).
    - /register: Registers a new user, creates a personal team, and issues an access token.
    - /forgot-password/start: Initiates the password reset process by sending an OTP to the user's email.
    - /forgot-password/verify: Verifies the OTP (and optionally TOTP) for password reset and issues a reset session token.
    - /forgot-password/confirm: Confirms the password reset using the reset session token and updates the user's password.
    - /2fa/setup: Generates and returns a TOTP secret and provisioning URI for 2FA setup.
    - /2fa/verify: Verifies the TOTP code and enables 2FA for the user.
    Security Features:
    - Rate limiting to prevent brute-force and enumeration attacks.
    - Uniform error responses to avoid leaking user existence.
    - OTP and TOTP verification for secure password reset and 2FA.
    - Token versioning to invalidate old tokens upon password change.
    Dependencies:
    - FastAPI, SQLAlchemy, pyotp, jose, custom security and helper modules.

"""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError, jwt
import pyotp
from redis import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.helpers.getters import isDebugMode
from app.helpers.qrcode_generator import generate_qr_code_base64
from app.schemas.user import UserCreate
from app.schemas.auth import (
    Token, 
    Login, 
    ForgotPasswordStartIn, 
    ForgotPasswordVerifyIn, 
    ForgotPasswordVerifyOut, 
    ForgotPasswordConfirmIn, 
    TwoFASetupOut
)

from app.models.team import Team as TeamModel
from app.api.dependencies import get_current_user, get_db, get_redis

from app.models.user import User
from app.models.password_reset import PasswordReset

from app.core.security import (
    generate_otp, hash_otp, verify_otp, create_reset_session_token, verify_password,
    verify_totp, generate_totp_secret, create_access_token, get_password_hash, SECRET_KEY, ALGORITHM
)
from app.helpers.rate_limit import allow
from app.mycelery.worker import send_password_otp, send_password_otp_local

router = APIRouter()

@router.post("/token", response_model=Token)
async def oauth2_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint OAuth2 padrão para autenticação.

    O Swagger UI usa este endpoint automaticamente quando você clica em "Authorize".

    Note: O campo 'username' do OAuth2 é usado para aceitar o email do usuário.
    """
    # OAuth2 usa 'username', mas aceitamos email
    result = await db.execute(select(User).filter(User.email == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha inválidos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": str(user.id)},
        token_version=user.token_version
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login", response_model=Token)
async def login(login_data: Login, db: AsyncSession = Depends(get_db)):
    """
    Endpoint alternativo de autenticação via JSON body.

    Use este endpoint se preferir enviar credenciais como JSON em vez de form-data.
    """
    result = await db.execute(select(User).filter(User.email == login_data.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(login_data.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")

    access_token = create_access_token(
        data={"sub": str(user.id)},
        token_version=user.token_version
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me")
async def read_me(current_user: User = Depends(get_current_user)):
    access_token = create_access_token(
        data={"sub": str(current_user.id)}, 
        token_version=current_user.token_version
    )
    return {
        "user": current_user,
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.post("/logout")
async def logout(
    authorization: str = Header(...),
    redis: Redis = Depends(get_redis)
):
    if isDebugMode():
        return {"message": "Logout successful"}
    
    token = authorization.replace("Bearer ", "")
    
    # Decodifica para pegar expiração
    from jose import jwt
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    exp = payload["exp"]
    ttl = exp - int(datetime.now(timezone.utc).timestamp())
    
    # Adiciona à blacklist
    await redis.setex(f"blacklist:{token}", ttl, "revoked")
    
    return {"message": "Logout successful"}

@router.post("/register", response_model=Token)
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).filter(User.email == user.email))
    db_user = result.scalar_one_or_none()
    
    if db_user:
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    hashed_password = get_password_hash(user.password)
    new_user = User(name=user.name, email=user.email, password=hashed_password)
    db.add(new_user)
    await db.flush()

    # Cria um time para o novo usuário
    new_team = TeamModel(name=f"Time de {new_user.name}", user_id=new_user.id, personal_team=True)
    db.add(new_team)
    await db.flush()  # Garante que new_team.id seja atribuído

    # Atualiza o usuário com o ID do time criado
    new_user.current_team_id = new_team.id

    # Efetua o commit de todas as operações
    await db.commit()
    await db.refresh(new_user)

    # Cria o token de acesso para o novo usuário
    access_token = create_access_token(data={"sub": str(new_user.id)}, token_version=new_user.token_version)
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/forgot-password/start", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password_start(payload: ForgotPasswordStartIn, request: Request, db: AsyncSession = Depends(get_db)):
    client_ip = request.headers.get("x-forwarded-for", request.client.host)
    if not allow("fp:start", payload.email, client_ip, max_attempts=5, window_sec=900):
        raise HTTPException(status_code=429, detail="Too many requests")

    result = await db.execute(select(User).filter(User.email == payload.email))
    user = result.scalar_one_or_none()

    if user:
        otp = generate_otp()
        pr = PasswordReset(
            user_id=user.id,
            email=payload.email,
            otp_hash=hash_otp(otp),
            otp_expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            require_totp=user.two_factor_enabled
        )
        db.add(pr)
        await db.commit()

        # Envia OTP de forma assíncrona via Celery
        send_password_otp_local.delay(payload.email, otp)

    return {"message": "If the email exists, a verification code has been sent."}

@router.post("/forgot-password/verify", response_model=ForgotPasswordVerifyOut)
async def forgot_password_verify(payload: ForgotPasswordVerifyIn, request: Request, db: AsyncSession = Depends(get_db)):
    client_ip = request.headers.get("x-forwarded-for", request.client.host)
    if not allow("fp:verify", payload.email, client_ip, max_attempts=10, window_sec=900):
        raise HTTPException(status_code=429, detail="Too many attempts")

    result = await db.execute(
        select(PasswordReset)
        .filter(PasswordReset.email == payload.email, PasswordReset.consumed_at.is_(None))
        .order_by(PasswordReset.id.desc())
    )
    pr = result.scalar_one_or_none()

    if not pr or not pr.otp_hash or not pr.otp_expires_at or pr.otp_expires_at < datetime.now(pr.otp_expires_at.tzinfo):
        raise HTTPException(status_code=400, detail="Invalid or expired code")

    if not payload.otp or not verify_otp(payload.otp, pr.otp_hash):
        pr.attempts += 1
        await db.commit()
        raise HTTPException(status_code=400, detail="Invalid or expired code")

    pr.otp_verified = True

    user = None
    if pr.user_id:
        result = await db.execute(select(User).filter(User.id == pr.user_id))
        user = result.scalar_one_or_none()
    
    if pr.require_totp:
        if not user or not user.two_factor_secret or not payload.totp or not verify_totp(user.two_factor_secret, payload.totp):
            pr.attempts += 1
            await db.commit()
            raise HTTPException(status_code=400, detail="Invalid or missing authenticator code")
        pr.totp_verified = True

    pr.reset_session_issued_at = datetime.now(timezone.utc)
    await db.commit()

    rst = create_reset_session_token(user_id=user.id, token_version=user.token_version)
    return ForgotPasswordVerifyOut(reset_session_token=rst)

@router.post("/forgot-password/confirm", status_code=status.HTTP_204_NO_CONTENT)
async def forgot_password_confirm(payload: ForgotPasswordConfirmIn, request: Request, db: AsyncSession = Depends(get_db)):
    auth_header = request.headers.get("authorization", "")
    if not auth_header.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing reset session")

    token = auth_header.split(" ", 1)[1]
    try:
        claims = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid reset session")

    if claims.get("scope") != "pwd_reset":
        raise HTTPException(status_code=401, detail="Invalid reset session")

    user_id = int(claims["sub"])
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid reset session")

    user.password = get_password_hash(payload.new_password)
    user.token_version = (user.token_version or 1) + 1
    await db.commit()

    # Marca o reset de senha como consumido
    result = await db.execute(
        select(PasswordReset)
        .filter(PasswordReset.user_id == user_id, PasswordReset.consumed_at.is_(None))
        .order_by(PasswordReset.id.desc())
    )
    pr = result.scalar_one_or_none()
    
    if pr:
        pr.consumed_at = datetime.now(timezone.utc)
        await db.commit()

    return

@router.post("/2fa/setup", response_model=TwoFASetupOut)
async def twofa_setup(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    Configura 2FA para o usuário autenticado.
    
    Retorna:
    - secret: Chave secreta (para backup manual)
    - otpauth_url: URL para configuração manual
    - qr_code: Imagem Base64 do QR Code para leitura direta
    """
    secret = generate_totp_secret()
    issuer = "Application"
    label = f"{issuer}:{current_user.email}"
    url = pyotp.totp.TOTP(secret).provisioning_uri(name=label, issuer_name=issuer)
    try:
        qr_code_base64 = generate_qr_code_base64(url)
    except ValueError as e:
        raise HTTPException(status_code=500, detail="Erro ao gerar QR Code")
    current_user.two_factor_secret = secret
    current_user.two_factor_enabled = False
    await db.commit()
    return TwoFASetupOut(secret=secret, otpauth_url=url, qr_code=qr_code_base64)

@router.post("/2fa/verify", status_code=204)
async def twofa_verify(code: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not current_user.two_factor_secret or not verify_totp(current_user.two_factor_secret, code):
        raise HTTPException(status_code=400, detail="Invalid code")
    current_user.two_factor_enabled = True
    await db.commit()
    return
