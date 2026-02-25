import logging
from app.logging.log_levels import LogLevel

class BaseFormatter(logging.Formatter):
    """Formatter base com formato padrão"""
    def __init__(self, fmt=None):
        super().__init__(fmt or '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class ErrorFormatter(BaseFormatter):
    def __init__(self):
        super().__init__('❌ [ERROR] %(asctime)s - %(name)s - %(message)s')

class WarningFormatter(BaseFormatter):
    def __init__(self):
        super().__init__('⚠️  [WARNING] %(asctime)s - %(name)s - %(message)s')

class InfoFormatter(BaseFormatter):
    def __init__(self):
        super().__init__('ℹ️  [INFO] %(asctime)s - %(name)s - %(message)s')

class RequestFormatter(BaseFormatter):
    def __init__(self):
        super().__init__('🌐 [REQUEST] %(asctime)s - %(message)s')

class SlowFormatter(BaseFormatter):
    def __init__(self):
        super().__init__('🐌 [SLOW] %(asctime)s - %(name)s - %(message)s')

class GreatFormatter(BaseFormatter):
    def __init__(self):
        super().__init__('✅ [GREAT] %(asctime)s - %(name)s - %(message)s')

class DefaultFormatter(BaseFormatter):
    pass

def get_formatter_for_level(level: LogLevel) -> logging.Formatter:
    """Retorna o formatter apropriado para o nível de log"""
    if level == LogLevel.ERROR:
        return ErrorFormatter()
    elif level == LogLevel.WARNING:
        return WarningFormatter()
    elif level == LogLevel.INFO:
        return InfoFormatter()
    elif level == LogLevel.REQUEST:
        return RequestFormatter()
    elif level == LogLevel.SLOW:
        return SlowFormatter()
    elif level == LogLevel.GREAT:
        return GreatFormatter()
    else:
        return DefaultFormatter()