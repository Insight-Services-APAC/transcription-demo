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
    # Define character sets
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    special = '!@#$%^&*()-_=+'
    
    # Ensure at least one of each character type
    password = [
        random.choice(lowercase),
        random.choice(uppercase),
        random.choice(digits),
        random.choice(special)
    ]
    
    # Fill the rest with a mix of all characters
    all_chars = lowercase + uppercase + digits + special
    password.extend(random.choice(all_chars) for _ in range(length - 4))
    
    # Shuffle the password characters
    random.shuffle(password)
    
    return ''.join(password)

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
    # In a real system, you would integrate with an email service
    # For the demo, we'll just log the email that would be sent
    logger.info(f"DEMO: Welcome email would be sent to {email}")
    logger.info(f"DEMO: Email would contain username: {username} and temporary password: {password}")
    
    # In production, you might use something like:
    # from flask_mail import Message
    # from app.extensions import mail
    # 
    # msg = Message("Welcome to the Application",
    #               sender="noreply@example.com",
    #               recipients=[email])
    # msg.body = f"Hello {username},\n\nYour temporary password is: {password}\n\nPlease log in and change your password immediately."
    # mail.send(msg)
    
    return True