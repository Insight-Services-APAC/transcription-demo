import random
import string
import logging

logger = logging.getLogger(__name__)


def generate_temp_password(length=12):
    """
    Generate a secure temporary password.

    Args:
        length (int): Length of the password (default: 12)

    Returns:
        str: A randomly generated password
    """
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    special = "!@#$%^&*()-_=+"
    password = [
        random.choice(lowercase),
        random.choice(uppercase),
        random.choice(digits),
        random.choice(special),
    ]
    all_chars = lowercase + uppercase + digits + special
    password.extend((random.choice(all_chars) for _ in range(length - 4)))
    random.shuffle(password)
    return "".join(password)


def send_welcome_email(email, username, password):
    """
    Send a welcome email to a new user with their temporary password.

    In a production environment, this would use a proper email sending service.
    For this demo, we'll just log the information.

    Args:
        email (str): User's email address
        username (str): User's username
        password (str): Temporary password

    Returns:
        bool: True if successful, False otherwise
    """
    logger.info(f"DEMO: Welcome email would be sent to {email}")
    logger.info(
        f"DEMO: Email would contain username: {username} and temporary password: {password}"
    )
    return True
