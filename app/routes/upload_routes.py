# upload_routes.py
# Routes for file upload functionality

from flask import Blueprint, request, jsonify
from app.services.s3_service import S3Service
from app.utils.file_validator import validate_file
import os
import uuid

upload_bp = Blueprint('upload', __name__)

s3_service = S3Service()

@upload_bp.route('/upload', methods=['POST'])
def upload_file():

    if 'file' not in request.files:
        return jsonify({
            'message': 'No file provided',
            'error': 'file field is required'
        }), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({
            'message': 'No file selected',
            'error': 'filename is empty'
        }), 400
    
    validation_result = validate_file(file)
    if not validation_result['valid']:
        return jsonify({
            'message': 'File validation failed',
            'error': validation_result['error']
        }), 400
    
    try:
        file_extension = os.path.splitext(file.filename)[1].lower()
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        
        s3_url = s3_service.upload_file(file, unique_filename)
        
        return jsonify({
            'message': 'File uploaded successfully',
            'url': s3_url
        }), 200
        
    except Exception as e:
        return jsonify({
            'message': 'Upload failed',
            'error': str(e)
        }), 500
