from flask import request, jsonify, current_app
from app.routes import file_bp
from app.services.s3_service import S3Service
from app.utils.decorators import handle_exceptions, require_auth
import uuid
import os

s3_service = S3Service()


def allowed_file(filename):
    """Check if file extension is allowed"""
    allowed_extensions = current_app.config.get('ALLOWED_EXTENSIONS', set())
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions


@file_bp.route('/upload', methods=['POST'])
@handle_exceptions
@require_auth
def upload_file():
    """Upload a file to S3"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400
    
    user_id = request.headers.get('X-User-Id')
    
    # Generate unique filename
    ext = file.filename.rsplit('.', 1)[1].lower()
    unique_filename = f"{user_id}/{uuid.uuid4()}.{ext}"
    
    # Determine file type for folder organization
    file_type = request.form.get('type', 'general')  # 'profile', 'post', 'attachment'
    key = f"{file_type}/{unique_filename}"
    
    # Upload to S3
    result = s3_service.upload_file(file, key)
    
    if not result:
        return jsonify({'error': 'Failed to upload file'}), 500
    
    return jsonify({
        'message': 'File uploaded successfully',
        'key': key,
        'url': result['url']
    }), 201


@file_bp.route('/<path:key>', methods=['GET'])
@handle_exceptions
@require_auth
def get_file(key):
    """Get a presigned URL for a file"""
    url = s3_service.get_presigned_url(key)
    
    if not url:
        return jsonify({'error': 'File not found'}), 404
    
    return jsonify({
        'key': key,
        'url': url
    }), 200


@file_bp.route('/<path:key>', methods=['DELETE'])
@handle_exceptions
@require_auth
def delete_file(key):
    """Delete a file from S3"""
    user_id = request.headers.get('X-User-Id')
    user_type = request.headers.get('X-User-Type')
    
    # Check if user owns the file or is admin
    file_user_id = key.split('/')[1] if '/' in key else None
    is_owner = file_user_id == user_id
    is_admin = user_type in ['admin', 'super_admin']
    
    if not is_owner and not is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    result = s3_service.delete_file(key)
    
    if not result:
        return jsonify({'error': 'Failed to delete file'}), 500
    
    return jsonify({'message': 'File deleted successfully'}), 200


@file_bp.route('/presigned-upload', methods=['POST'])
@handle_exceptions
@require_auth
def get_presigned_upload_url():
    """Get a presigned URL for direct upload to S3"""
    data = request.get_json()
    filename = data.get('filename')
    file_type = data.get('type', 'general')
    
    if not filename:
        return jsonify({'error': 'Filename is required'}), 400
    
    if not allowed_file(filename):
        return jsonify({'error': 'File type not allowed'}), 400
    
    user_id = request.headers.get('X-User-Id')
    
    # Generate unique filename
    ext = filename.rsplit('.', 1)[1].lower()
    unique_filename = f"{user_id}/{uuid.uuid4()}.{ext}"
    key = f"{file_type}/{unique_filename}"
    
    # Get presigned upload URL
    presigned_data = s3_service.get_presigned_upload_url(key)
    
    if not presigned_data:
        return jsonify({'error': 'Failed to generate upload URL'}), 500
    
    return jsonify({
        'key': key,
        'uploadUrl': presigned_data['url'],
        'fields': presigned_data.get('fields', {})
    }), 200
