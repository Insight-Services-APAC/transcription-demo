from flask import Blueprint
files_bp = Blueprint('files', __name__)
from app.files.routes import *
from app.files.uploads import *
from app.files.progress import *