import re
import socket

def is_valid_email_format(email: str) -> bool:
    """Базовая проверка формата email."""
    return bool(re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email))

def email_domain_exists(email: str) -> bool:
    """
    Проверяет существование домена через DNS MX-запись.
    Использует dnspython если установлен, иначе fallback через socket.
    """
    try:
        domain = email.split('@')[1].lower()
    except IndexError:
        return False

    # Попытка через dnspython (точнее — проверяет MX)
    try:
        import dns.resolver
        dns.resolver.resolve(domain, 'MX')
        return True
    except ImportError:
        pass
    except Exception:
        return False

    # Fallback: просто проверяем что домен резолвится (A-запись)
    try:
        socket.getaddrinfo(domain, None)
        return True
    except socket.gaierror:
        return False