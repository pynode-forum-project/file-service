from flask import Flask
from flask_cors import CORS


def create_app():
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object('app.config.Config')
    
    # Enable CORS
    CORS(app, resources={r"/*": {"origins": "*"}})
    
    # Import and register blueprints
    from app.routes import file_bp
    app.register_blueprint(file_bp, url_prefix='/files')
    
    # Register error handlers
    from app.utils.error_handlers import register_error_handlers
    register_error_handlers(app)
    
    # Health check endpoint
    @app.route('/health')
    def health():
        return {'status': 'healthy', 'service': 'file-service'}
    
    return app
