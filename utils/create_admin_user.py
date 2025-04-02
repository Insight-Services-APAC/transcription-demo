#!/usr/bin/env python3
import os
import sys
import getpass

# Add the project root directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

# Now we can import app modules
from app import create_app, db
from app.models.user import User
from app.admin.utils import generate_temp_password

def create_admin_user():
    """Create an admin user with prompted credentials"""
    print("\n===== Create Admin User =====\n")
    
    # Get username
    username = input("Enter admin username: ")
    while not username:
        print("Username cannot be empty.")
        username = input("Enter admin username: ")
    
    # Get email
    email = input("Enter admin email: ")
    while not email or '@' not in email:
        print("Please enter a valid email address.")
        email = input("Enter admin email: ")
    
    # Get password or generate one
    use_generated = input("Generate secure password? (y/n): ").lower() == 'y'
    
    if use_generated:
        password = generate_temp_password()
        print(f"\nGenerated password: {password}")
    else:
        password = getpass.getpass("Enter password (min 8 characters): ")
        while len(password) < 8:
            print("Password must be at least 8 characters long.")
            password = getpass.getpass("Enter password (min 8 characters): ")
        password_confirm = getpass.getpass("Confirm password: ")
        while password != password_confirm:
            print("Passwords do not match.")
            password = getpass.getpass("Enter password (min 8 characters): ")
            password_confirm = getpass.getpass("Confirm password: ")
    
    # Create app context
    app = create_app()
    with app.app_context():
        # Check if user already exists
        existing_user = User.query.filter((User.username == username) | 
                                        (User.email == email)).first()
        if existing_user:
            if existing_user.username == username:
                print(f"\nError: Username '{username}' already exists.")
            else:
                print(f"\nError: Email '{email}' already exists.")
            return False
        
        # Create the user (admins are always approved)
        admin = User(
            username=username,
            email=email,
            password=password,
            is_admin=True,
            is_temporary_password=use_generated,
            is_approved=True  # Admins are always approved
        )
        
        db.session.add(admin)
        db.session.commit()
        
        print(f"\nAdmin user '{username}' created successfully!")
        if use_generated:
            print(f"Remember the generated password: {password}")
        
        print("\nYou can now log in with these credentials.")
        return True

if __name__ == "__main__":
    create_admin_user()