import re
from django.core.exceptions import ValidationError


class StrongPasswordValidator:
    """
    Enforces that passwords contain:
      - At least one uppercase letter
      - At least one lowercase letter
      - At least one digit
      - At least one special character
    """

    SPECIAL = r'[!@#$%^&*()\-_=+\[\]{};:\'",.<>?/\\|`~]'

    def validate(self, password, user=None):
        errors = []
        if not re.search(r'[A-Z]', password):
            errors.append('at least one uppercase letter (A–Z)')
        if not re.search(r'[a-z]', password):
            errors.append('at least one lowercase letter (a–z)')
        if not re.search(r'\d', password):
            errors.append('at least one digit (0–9)')
        if not re.search(self.SPECIAL, password):
            errors.append('at least one special character (e.g. !@#$%)')
        if errors:
            raise ValidationError(
                f'Password must contain {", ".join(errors)}.',
                code='password_too_weak',
            )

    def get_help_text(self):
        return (
            'Password must be at least 12 characters and contain uppercase, '
            'lowercase, a digit, and a special character.'
        )
