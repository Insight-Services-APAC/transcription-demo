from flask import Blueprint
transcripts_bp = Blueprint('transcripts', __name__)
from app.transcripts.routes import *