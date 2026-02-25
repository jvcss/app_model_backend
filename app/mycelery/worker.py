import os
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.mycelery.app import celery_app
from app.core.config import settings
from app.logging import get_logger

@celery_app.task(name="create_task")
def create_task(task_type):
    time.sleep(int(task_type) * 10)
    return True

@celery_app.task(name="send_password_otp")
def send_password_otp(email: str, otp: str):
    """Envia OTP por email usando Gmail SMTP"""
    try:
        # Configurações SMTP
        get_logger("auth").info(f"Preparing to send OTP to {email}")
        smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_username = os.getenv("SMTP_USERNAME")
        smtp_password = os.getenv("SMTP_PASSWORD")
        from_email = os.getenv("SMTP_FROM_EMAIL", smtp_username)
        from_name = os.getenv("SMTP_FROM_NAME", "Sistema de Sindicância")

        if not smtp_username or not smtp_password:
            get_logger("auth").error("SMTP credentials not configured")
            raise ValueError("SMTP credentials not configured")
        get_logger("auth").info(f"SMTP configuration loaded for {smtp_username}")
        # Criar mensagem
        msg = MIMEMultipart()
        msg['From'] = f"{from_name} <{from_email}>"
        msg['To'] = email
        msg['Subject'] = "Código de Verificação - Sistema de Sindicância Applicativo"

        # Corpo do email
        body = f"""
        <html>
            <body>
                <h2>Código de Verificação</h2>
                <p>Você solicitou a recuperação de senha.</p>
                <p>Seu código de verificação é: <strong>{otp}</strong></p>
                <p>Este código expira em 10 minutos.</p>
                <p>Se você não solicitou esta recuperação, ignore este email.</p>
                <hr>
                <p><small>Sistema de Sindicância Applicativo - Não responda este email</small></p>
            </body>
        </html>
        """
        get_logger("auth").info(f"Sending OTP to {email}")

        msg.attach(MIMEText(body, 'html'))

        # Conectar e enviar
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # Habilita criptografia TLS
        server.login(smtp_username, smtp_password)
        text = msg.as_string()
        server.sendmail(from_email, email, text)
        server.quit()

        return {"sent": True, "email": email}

    except Exception as e:
        # Log do erro (em produção, use logging adequado)
        get_logger("auth").error(f"Erro ao enviar email para {email}: {str(e)}")
        return {"sent": False, "error": str(e)}

@celery_app.task(name="send_password_otp_local")
def send_password_otp_local(email: str, otp: str):
    """Simula envio de OTP localmente (para desenvolvimento)"""
    print(f"=== EMAIL SIMULADO ===")
    print(f"Para: {email}")
    print(f"Assunto: Código de Verificação - Sistema de Sindicância {settings.APP_NAME}")
    print(f"Código: {otp}")
    print(f"====================")
    get_logger("auth").info(f"Simulated sending OTP to {email}")
    return {"sent": True}

@celery_app.task(name="send_whatsapp_log", max_retries=3)
def send_whatsapp_log(api_url: str, token: str, instance: str, phone_number: str, message: str):
    """Tarefa Celery para enviar log via WhatsApp"""
    try:
        import asyncio
        from app.services.whatsapp import WhatsAppService

        # Inicializa o serviço WhatsApp
        whatsapp_service = WhatsAppService(
            api_url=api_url,
            token=token,
            instance=instance
        )

        # Envia a mensagem de forma assíncrona
        asyncio.run(whatsapp_service.send_message(phone_number, message))
        return True

    except Exception as e:
        get_logger("auth").error(f"Erro ao enviar log via WhatsApp: {e}")
        print(f"Erro ao enviar log via WhatsApp: {e}")
        # Em caso de falha, tenta novamente com backoff exponencial que significa que a cada falha o tempo de espera dobra
        raise send_whatsapp_log.retry(exc=e, countdown=2 ** send_whatsapp_log.request.retries)
