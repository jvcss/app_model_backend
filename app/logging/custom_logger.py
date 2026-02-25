"""
Custom Logger com suporte a envio de notificações via WhatsApp
Níveis: warning, info, request, error, slow, great
"""
import logging
import traceback
from datetime import datetime, timezone
from typing import Dict, Any

from app.logging.log_levels import LogLevel
from app.logging.whatsapp_handler import WhatsAppHandler
from app.logging.formatters import get_formatter_for_level
from app.logging.filters import RateLimitFilter, EnvironmentFilter
from app.core.config import settings
from app.helpers.getters import isDebugMode



class CustomLogger:
    """
    Logger customizado com integração WhatsApp
    
    Uso:
        logger = CustomLogger("my_module")
        logger.info("Operação realizada", user_id=123)
        logger.error("Erro crítico", exc_info=True)
        logger.slow("Query lenta detectada", duration=5.2, query="SELECT...")
    """
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG if isDebugMode() else logging.DEBUG)#logging.INFO
        
        # Remove handlers existentes para evitar duplicação
        self.logger.handlers.clear()
        
        # Handler para console (sempre ativo)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # Handler WhatsApp (apenas em produção se configurado)
        if self._should_enable_whatsapp():
            whatsapp_handler = WhatsAppHandler(
                api_url=settings.EVOLUTION_API_URL,
                phone_number=settings.WHATSAPP_LOG_NUMBER,
                instance=settings.EVOLUTION_API_KEY,
                token=settings.EVOLUTION_API_TOKEN
            )
            
            # Adiciona filtros
            whatsapp_handler.addFilter(RateLimitFilter(max_per_hour=1000))
            whatsapp_handler.addFilter(EnvironmentFilter())
            
            self.logger.addHandler(whatsapp_handler)
    
    def _should_enable_whatsapp(self) -> bool:
        """Verifica se deve habilitar envio para WhatsApp"""
        required_settings = [
            'WHATSAPP_LOG_NUMBER',
            'EVOLUTIONS_API_KEY',
            'EVOLUTIONS_API_TOKEN',
        ]
        
        # Verifica se todas as configurações existem
        if all(hasattr(settings, key) and getattr(settings, key) for key in required_settings):
            return True
        return False
    
    def _log(
        self,
        level: LogLevel,
        message: str,
        exc_info: bool = False,
        **context: Any
    ) -> None:
        """Método interno de logging"""
        
        # Prepara contexto adicional
        log_data = {
            "level": level.value,
            "module": self.name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **context
        }
        
        # Adiciona backtrace se houver exceção
        if exc_info:
            log_data["traceback"] = self._get_clean_traceback()
        

        # formatted_message = get_formatter_for_level(level).format(
        #     message=message,
        #     **log_data
        # )
        # Cria um LogRecord temporário para formatar a mensagem
        import logging as logging_module
        record = logging_module.LogRecord(
            name=self.name,
            level=logging.INFO,  # Será sobrescrito depois
            pathname="",
            lineno=0,
            msg=message,
            args=(),
            exc_info=None
         )
        record.__dict__.update(log_data)
        formatted_message = get_formatter_for_level(level).format(record)

        # Mapeia para níveis padrão do logging
        log_level_map = {
            LogLevel.WARNING: logging.WARNING,
            LogLevel.INFO: logging.INFO,
            LogLevel.REQUEST: logging.INFO,
            LogLevel.ERROR: logging.ERROR,
            LogLevel.SLOW: logging.WARNING,
            LogLevel.GREAT: logging.INFO,
        }
        
        # Loga com contexto adicional
        self.logger.log(
            log_level_map[level],
            formatted_message,
            extra={"custom_data": log_data},
            exc_info=exc_info
        )
    
    def _get_clean_traceback(self) -> str:
        """
        Extrai traceback limpo, removendo duplicações e frames internos
        """
        tb_lines = traceback.format_exc().split('\n')
        
        # Remove linhas vazias e duplicadas
        seen = set()
        clean_lines = []
        
        for line in tb_lines:
            if line.strip() and line not in seen:
                # Filtra frames de bibliotecas internas se desejar
                if not any(skip in line for skip in ['/usr/local/lib/python', 'site-packages']):
                    seen.add(line)
                    clean_lines.append(line)
        
        return '\n'.join(clean_lines)
    
    # Métodos públicos para cada nível
    
    def warning(self, message: str, **context: Any) -> None:
        """
        Log de aviso - situações que merecem atenção mas não são erros
        
        Exemplo:
            logger.warning("Taxa de uso alta", usage_percent=85)
        """
        self._log(LogLevel.WARNING, message, **context)
    
    def info(self, message: str, **context: Any) -> None:
        """
        Log informativo - eventos importantes do sistema
        
        Exemplo:
            logger.info("Usuário criado com sucesso", user_id=123)
        """
        self._log(LogLevel.INFO, message, **context)
    
    def request(
        self,
        message: str,
        method: str,
        path: str,
        status_code: int,
        duration: float,
        **context: Any
    ) -> None:
        """
        Log de requisição HTTP
        
        Exemplo:
            logger.request(
                "API request",
                method="POST",
                path="/api/auth/login",
                status_code=200,
                duration=0.152
            )
        """
        self._log(
            LogLevel.REQUEST,
            message,
            method=method,
            path=path,
            status_code=status_code,
            duration=duration,
            **context
        )
    
    def error(
        self,
        message: str,
        exc_info: bool = True,
        **context: Any
    ) -> None:
        """
        Log de erro - falhas que requerem atenção imediata
        
        Exemplo:
            try:
                # código
            except Exception as e:
                logger.error("Falha ao processar pagamento", exc_info=True, payment_id=456)
        """
        self._log(LogLevel.ERROR, message, exc_info=exc_info, **context)
    
    def slow(
        self,
        message: str,
        duration: float,
        threshold: float = 1.0,
        **context: Any
    ) -> None:
        """
        Log de operação lenta - identifica gargalos de performance
        
        Exemplo:
            logger.slow(
                "Query demorou muito",
                duration=5.2,
                threshold=1.0,
                query="SELECT * FROM large_table"
            )
        """
        self._log(
            LogLevel.SLOW,
            message,
            duration=duration,
            threshold=threshold,
            **context
        )
    
    def great(self, message: str, **context: Any) -> None:
        """
        Log de sucesso - celebra eventos positivos importantes
        
        Exemplo:
            logger.great("Migração de dados completa!", records_migrated=10000)
        """
        self._log(LogLevel.GREAT, message, **context)


# Singleton global para facilitar uso
_loggers: Dict[str, CustomLogger] = {}


def get_logger(name: str) -> CustomLogger:
    """
    Obtém uma instância do logger customizado
    
    Uso:
        from app.logging import get_logger
        logger = get_logger(__name__)
    """
    if name not in _loggers:
        _loggers[name] = CustomLogger(name)
    return _loggers[name]
