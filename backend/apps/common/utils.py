import secrets
import string
import uuid
from datetime import datetime


def generate_temp_password(length=12):
    """Generate a cryptographically secure temporary password."""
    special = '!@#$%'
    alphabet = string.ascii_letters + string.digits + special
    while True:
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(c.islower() for c in password)
            and any(c.isupper() for c in password)
            and any(c.isdigit() for c in password)
            and any(c in special for c in password)
        ):
            return password


def generate_username(first_name: str, last_name: str) -> str:
    """
    Generate a base username in the format `lastname_firstname`.
    e.g. 'Juan', 'Dela Cruz' → 'delacruz_juan'
    """
    import re

    def clean(name):
        return re.sub(r'[^a-z0-9]', '', name.lower().replace(' ', ''))

    base = f'{clean(last_name)}_{clean(first_name)}'
    return base or 'resident'


def get_unique_username(first_name: str, last_name: str) -> str:
    """Return a username derived from the name that doesn't already exist."""
    from apps.accounts.models import User

    base = generate_username(first_name, last_name)
    username = base
    counter = 1
    while User.objects.filter(username=username).exists():
        username = f'{base}{counter}'
        counter += 1
    return username


def generate_resident_id():
    year = datetime.now().year
    unique = str(uuid.uuid4().int)[:6]
    return f'RES-{year}-{unique}'


def generate_household_number():
    year = datetime.now().year
    unique = str(uuid.uuid4().int)[:4]
    return f'HH-{year}-{unique}'
