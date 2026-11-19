"""Request-local logical workspace; defaults to NORMAL for existing clients."""
from contextvars import ContextVar
current_namespace = ContextVar('investigation_namespace', default='NORMAL')
