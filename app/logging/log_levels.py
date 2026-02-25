"""
Definição dos níveis customizados de log
"""
from enum import Enum


class LogLevel(str, Enum):
    """Níveis customizados de log"""
    WARNING = "warning"
    INFO = "info"
    REQUEST = "request"
    ERROR = "error"
    SLOW = "slow"
    GREAT = "great"
