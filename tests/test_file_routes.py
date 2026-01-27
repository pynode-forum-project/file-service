"""
API Integration Tests for File Service Routes

Tests the HTTP endpoints using Flask test client:
- POST /files/upload
- GET /files/{key}
- DELETE /files/{key}
- POST /files/presigned-upload
- GET /health
"""

import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO
from app import create_app


@pytest.fixture
def app():
    """Create Flask app for testing"""
    app = create_app()
    app.config['TESTING'] = True
    app.config['JWT_SECRET'] = 'test-jwt-secret-key'
    app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'txt'}
    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def mock_s3_service():
    """Mock S3Service"""
    with patch('app.routes.file_routes.s3_service') as mock:
        yield mock


def create_auth_headers(user_id=1, user_type='user'):
    """Helper to create authentication headers"""
    return {
        'X-User-Id': str(user_id),
        'X-User-Type': user_type,
        'Authorization': 'Bearer test-token'
    }


def create_test_file(filename='test.png', content=b'test file content'):
    """Helper to create a test file"""
    file_obj = BytesIO(content)
    file_obj.filename = filename
    file_obj.content_type = 'image/png' if filename.endswith('.png') else 'application/octet-stream'
    return file_obj


class TestUploadFileEndpoint:
    """Test POST /files/upload endpoint"""
    
    def test_upload_file_success(self, client, mock_s3_service):
        """Test successful file upload returns 201"""
        mock_s3_service.upload_file.return_value = {
            'key': 'profile/1/uuid.png',
            'url': 'https://bucket.s3.amazonaws.com/profile/1/uuid.png'
        }
        
        file_obj = create_test_file('test.png')
        file_obj.seek(0)  # Reset file pointer
        
        data = {
            'file': (file_obj, file_obj.filename),
            'type': 'profile'
        }
        
        response = client.post(
            '/files/upload',
            data=data,
            headers=create_auth_headers()
        )
        
        assert response.status_code == 201
        response_data = response.get_json()
        assert response_data['message'] == 'File uploaded successfully'
        assert 'key' in response_data
        assert 'url' in response_data
        mock_s3_service.upload_file.assert_called_once()
    
    def test_upload_file_no_file(self, client):
        """Test upload without file returns 400"""
        response = client.post(
            '/files/upload',
            headers=create_auth_headers()
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'file' in data['error'].lower()
    
    def test_upload_file_invalid_extension(self, client):
        """Test upload with invalid file extension returns 400"""
        file_obj = create_test_file('test.exe')
        file_obj.seek(0)
        
        data = {
            'file': (file_obj, file_obj.filename)
        }
        
        response = client.post(
            '/files/upload',
            data=data,
            headers=create_auth_headers()
        )
        
        assert response.status_code == 400
        response_data = response.get_json()
        assert 'error' in response_data
        assert 'type' in response_data['error'].lower() or 'allowed' in response_data['error'].lower()
    
    def test_upload_file_requires_auth(self, client):
        """Test that upload requires authentication"""
        file_obj = create_test_file('test.png')
        file_obj.seek(0)
        
        data = {
            'file': (file_obj, file_obj.filename)
        }
        
        response = client.post(
            '/files/upload',
            data=data
        )
        
        assert response.status_code == 401
    
    def test_upload_file_s3_failure(self, client, mock_s3_service):
        """Test upload when S3 fails returns 500"""
        mock_s3_service.upload_file.return_value = None
        
        file_obj = create_test_file('test.png')
        file_obj.seek(0)
        
        data = {
            'file': (file_obj, file_obj.filename)
        }
        
        response = client.post(
            '/files/upload',
            data=data,
            headers=create_auth_headers()
        )
        
        assert response.status_code == 500
        response_data = response.get_json()
        assert 'error' in response_data


class TestGetFileEndpoint:
    """Test GET /files/{key} endpoint"""
    
    def test_get_file_success(self, client, mock_s3_service):
        """Test successful file retrieval returns 200"""
        mock_s3_service.get_presigned_url.return_value = 'https://presigned-url.com/file.png'
        
        response = client.get(
            '/files/profile/1/uuid.png',
            headers=create_auth_headers()
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'key' in data
        assert 'url' in data
        assert data['url'] == 'https://presigned-url.com/file.png'
    
    def test_get_file_not_found(self, client, mock_s3_service):
        """Test getting non-existent file returns 404"""
        mock_s3_service.get_presigned_url.return_value = None
        
        response = client.get(
            '/files/nonexistent/file.png',
            headers=create_auth_headers()
        )
        
        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data
    
    def test_get_file_requires_auth(self, client):
        """Test that getting file requires authentication"""
        response = client.get('/files/profile/1/uuid.png')
        
        assert response.status_code == 401


class TestDeleteFileEndpoint:
    """Test DELETE /files/{key} endpoint"""
    
    def test_delete_file_success_owner(self, client, mock_s3_service):
        """Test successful file deletion by owner returns 200"""
        mock_s3_service.delete_file.return_value = True
        
        response = client.delete(
            '/files/profile/1/uuid.png',
            headers=create_auth_headers(user_id=1)
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['message'] == 'File deleted successfully'
        mock_s3_service.delete_file.assert_called_once()
    
    def test_delete_file_success_admin(self, client, mock_s3_service):
        """Test successful file deletion by admin returns 200"""
        mock_s3_service.delete_file.return_value = True
        
        response = client.delete(
            '/files/profile/999/uuid.png',
            headers=create_auth_headers(user_id=1, user_type='admin')
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['message'] == 'File deleted successfully'
    
    def test_delete_file_access_denied(self, client, mock_s3_service):
        """Test deletion by non-owner non-admin returns 403"""
        response = client.delete(
            '/files/profile/999/uuid.png',
            headers=create_auth_headers(user_id=1, user_type='user')
        )
        
        assert response.status_code == 403
        data = response.get_json()
        assert 'error' in data
        assert 'denied' in data['error'].lower()
    
    def test_delete_file_s3_failure(self, client, mock_s3_service):
        """Test deletion when S3 fails returns 500"""
        mock_s3_service.delete_file.return_value = False
        
        response = client.delete(
            '/files/profile/1/uuid.png',
            headers=create_auth_headers(user_id=1)
        )
        
        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data
    
    def test_delete_file_requires_auth(self, client):
        """Test that deletion requires authentication"""
        response = client.delete('/files/profile/1/uuid.png')
        
        assert response.status_code == 401


class TestPresignedUploadEndpoint:
    """Test POST /files/presigned-upload endpoint"""
    
    def test_get_presigned_upload_success(self, client, mock_s3_service):
        """Test successful presigned upload URL generation returns 200"""
        mock_s3_service.get_presigned_upload_url.return_value = {
            'url': 'https://presigned-upload-url.com',
            'fields': {'key': 'value'}
        }
        
        response = client.post(
            '/files/presigned-upload',
            json={
                'filename': 'test.png',
                'type': 'profile'
            },
            headers=create_auth_headers()
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'key' in data
        assert 'uploadUrl' in data
        assert 'fields' in data
        mock_s3_service.get_presigned_upload_url.assert_called_once()
    
    def test_get_presigned_upload_missing_filename(self, client):
        """Test presigned upload without filename returns 400"""
        response = client.post(
            '/files/presigned-upload',
            json={'type': 'profile'},
            headers=create_auth_headers()
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'filename' in data['error'].lower()
    
    def test_get_presigned_upload_invalid_extension(self, client):
        """Test presigned upload with invalid extension returns 400"""
        response = client.post(
            '/files/presigned-upload',
            json={
                'filename': 'test.exe',
                'type': 'profile'
            },
            headers=create_auth_headers()
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
    
    def test_get_presigned_upload_s3_failure(self, client, mock_s3_service):
        """Test presigned upload when S3 fails returns 500"""
        mock_s3_service.get_presigned_upload_url.return_value = None
        
        response = client.post(
            '/files/presigned-upload',
            json={
                'filename': 'test.png',
                'type': 'profile'
            },
            headers=create_auth_headers()
        )
        
        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data
    
    def test_get_presigned_upload_requires_auth(self, client):
        """Test that presigned upload requires authentication"""
        response = client.post(
            '/files/presigned-upload',
            json={
                'filename': 'test.png',
                'type': 'profile'
            }
        )
        
        assert response.status_code == 401


class TestHealthEndpoint:
    """Test GET /health endpoint"""
    
    def test_health_check(self, client):
        """Test health endpoint returns 200"""
        response = client.get('/health')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'healthy'
        assert data['service'] == 'file-service'
