# __init__.py
# Flask application factory

from flask import Flask
from config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    from app.routes.upload_routes import upload_bp
    app.register_blueprint(upload_bp, url_prefix='/api/files')
    
    return app
