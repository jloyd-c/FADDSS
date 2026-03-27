from .models import AuditLog


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def log_action(action, actor=None, request=None, target_user=None, extra=None, purok=None):
    """
    Record an action in the audit trail.

    actor       — the User performing the action (None = system/CLI)
    request     — Django request object (used to extract IP + user-agent)
    target_user — the User the action was performed ON
    extra       — arbitrary dict for additional context
    purok       — Purok instance for profiling actions (enables STAFF audit filtering)
                  Pass None for system-level events (login, user management, etc.)
    """
    ip = None
    ua = ''
    if request:
        ip = get_client_ip(request)
        ua = request.META.get('HTTP_USER_AGENT', '')

    AuditLog.objects.create(
        actor=actor,
        action=action,
        target_user=target_user,
        purok=purok,
        ip_address=ip,
        user_agent=ua,
        extra=extra or {},
    )
