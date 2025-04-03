import uuid
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    is_temporary_password = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    is_approved = db.Column(db.Boolean, default=False)
    files = db.relationship("File", backref="owner", lazy="dynamic")

    def __init__(
        self,
        username,
        email,
        password,
        is_admin=False,
        is_temporary_password=False,
        is_approved=False,
    ):
        self.username = username
        self.email = email
        self.set_password(password)
        self.is_admin = is_admin
        self.is_temporary_password = is_temporary_password
        self.is_approved = is_approved

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return (
            f"<User(id='{self.id}', username='{self.username}', email='{self.email}')>"
        )
