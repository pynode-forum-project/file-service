from flask import Blueprint

file_bp = Blueprint('files', __name__)

from app.routes.file_routes import *
