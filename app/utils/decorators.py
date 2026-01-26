from functools import wraps
from flask import request, jsonify
import logging

logger = logging.getLogger(__name__)


def handle_exceptions(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            logger.warning(f'Validation error in {f.__name__}: {str(e)}')
            return jsonify({'error': 'Validation error', 'message': str(e)}), 400
        except Exception as e:
            logger.error(f'Error in {f.__name__}: {str(e)}', exc_info=True)
            return jsonify({'error': 'Internal server error', 'message': str(e)}), 500
    return decorated_function


def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = request.headers.get('X-User-Id')
        
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        return f(*args, **kwargs)
    return decorated_function
