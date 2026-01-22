# file_validator.py
# Utility functions for validating uploaded files

from flask import current_app
from werkzeug.datastructures import FileStorage

def validate_file(file: FileStorage) -> dict:
    """
    Args:
        file: FileStorage object from Flask request
        
    Returns:
        dict: {'valid': bool, 'error': str or None}
    """
    if not file:
        return {'valid': False, 'error': 'No file provided'}
    
    if not file.filename:
        return {'valid': False, 'error': 'Filename is required'}
    
    allowed_extensions = current_app.config['ALLOWED_EXTENSIONS']
    file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
    
    if file_ext not in allowed_extensions:
        return {
            'valid': False,
            'error': f'File type not allowed. Allowed types: {", ".join(allowed_extensions)}'
        }
    
    file.seek(0, 2)
    file_size = file.tell()
    file.seek(0)
    
    max_size = current_app.config['MAX_FILE_SIZE']
    if file_size > max_size:
        max_size_mb = max_size / (1024 * 1024)
        return {
            'valid': False,
            'error': f'File size exceeds maximum allowed size of {max_size_mb}MB'
        }
    
    if file_size == 0:
        return {'valid': False, 'error': 'File is empty'}
    
    return {'valid': True, 'error': None}
