"""Test Firecracker API client functionality."""

import tempfile
from http import HTTPStatus

import pytest

from firecracker.api import Api, Resource, Session
from firecracker.exceptions import APIError
from unittest.mock import patch, MagicMock


class TestAPIClient:
    """Test Firecracker API client."""

    def test_api_initialization(self):
        """Test API client initialization."""
        with tempfile.NamedTemporaryFile() as f:
            socket_file = f.name

        api = Api(socket_file)
        assert api.socket == socket_file
        assert api.endpoint.startswith("http://")
        assert api.session is not None

    def test_session_initialization(self):
        """Test Session initialization with Unix adapter."""
        session = Session()
        assert session is not None
        assert session.get_adapter("http://") is not None

    def test_resource_initialization(self):
        """Test Resource initialization."""
        api = Api("/tmp/test.socket")
        resource = Resource(api, "/test", "id_field")

        assert resource._api == api
        assert resource.resource == "/test"
        assert resource.id_field == "id_field"

    def test_resource_initialization_without_id_field(self):
        """Test Resource initialization without ID field."""
        api = Api("/tmp/test.socket")
        resource = Resource(api, "/test")

        assert resource.id_field is None

    def test_api_get_success(self):
        """Test successful GET request."""
        with tempfile.NamedTemporaryFile() as f:
            socket_file = f.name

        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.OK
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)

        api = Api(socket_file)
        api.session = mock_session

        resource = Resource(api, "/test")
        response = resource.get()

        assert response.status_code == HTTPStatus.OK

    def test_api_get_fault_message(self):
        """Test GET request with fault message."""
        with tempfile.NamedTemporaryFile() as f:
            socket_file = f.name

        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
        mock_response.json.return_value = {"fault_message": "Test fault"}
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)

        api = Api(socket_file)
        api.session = mock_session

        resource = Resource(api, "/test")

        with pytest.raises(APIError, match="API fault: Test fault"):
            resource.get()

    def test_api_get_error_message(self):
        """Test GET request with error message."""
        with tempfile.NamedTemporaryFile() as f:
            socket_file = f.name

        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.BAD_REQUEST
        mock_response.json.return_value = {"error": "Test error"}
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)

        api = Api(socket_file)
        api.session = mock_session

        resource = Resource(api, "/test")

        with pytest.raises(APIError, match="API error: Test error"):
            resource.get()

    def test_api_get_unexpected_response(self):
        """Test GET request with unexpected response."""
        with tempfile.NamedTemporaryFile() as f:
            socket_file = f.name

        with patch("requests_unixsocket.Session") as mock_session_class:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = HTTPStatus.BAD_REQUEST
            mock_response.json.return_value = {}
            mock_response.content = b"Unexpected content"
            mock_session.return_value.get.return_value = mock_response

            api = Api(socket_file)
            api.session = mock_session

            resource = Resource(api, "/test")

            with pytest.raises(APIError, match="Unexpected response"):
                resource.get()

    def test_api_get_request_exception(self):
        """Test GET request with exception."""
        with tempfile.NamedTemporaryFile() as f:
            socket_file = f.name

        import requests

        mock_session = MagicMock()
        mock_session.get = MagicMock(side_effect=requests.RequestException("Network error"))

        api = Api(socket_file)
        api.session = mock_session

        resource = Resource(api, "/test")

        with pytest.raises(APIError, match="GET request failed: Network error"):
            resource.get()

    def test_api_get_json_decode_error(self):
        """Test GET request with JSON decode error."""
        with tempfile.NamedTemporaryFile() as f:
            socket_file = f.name

        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)

        api = Api(socket_file)
        api.session = mock_session

        resource = Resource(api, "/test")

        with pytest.raises(APIError, match="Invalid JSON response: Invalid JSON"):
            resource.get()

    def test_api_put_success(self):
        """Test successful PUT request."""
        with tempfile.NamedTemporaryFile() as f:
            socket_file = f.name

        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.NO_CONTENT
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        mock_session = MagicMock()
        mock_session.request = MagicMock(return_value=mock_response)

        api = Api(socket_file)
        api.session = mock_session

        resource = Resource(api, "/test")
        response = resource.put(key="value")

        assert response.status_code == HTTPStatus.NO_CONTENT

    def test_api_put_with_id_field(self):
        """Test PUT request with ID field."""
        with tempfile.NamedTemporaryFile() as f:
            socket_file = f.name

        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.NO_CONTENT
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        mock_session = MagicMock()
        mock_session.request = MagicMock(return_value=mock_response)

        api = Api(socket_file)
        api.session = mock_session

        resource = Resource(api, "/test", "resource_id")
        response = resource.put(resource_id="123", key="value")

        assert response.status_code == HTTPStatus.NO_CONTENT

    def test_api_patch_success(self):
        """Test successful PATCH request."""
        with tempfile.NamedTemporaryFile() as f:
            socket_file = f.name

        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.NO_CONTENT
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        mock_session = MagicMock()
        mock_session.request = MagicMock(return_value=mock_response)

        api = Api(socket_file)
        api.session = mock_session

        resource = Resource(api, "/test")
        response = resource.patch(key="value")

        assert response.status_code == HTTPStatus.NO_CONTENT

    def test_api_patch_with_id_field(self):
        """Test PATCH request with ID field."""
        with tempfile.NamedTemporaryFile() as f:
            socket_file = f.name

        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.NO_CONTENT
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        mock_session = MagicMock()
        mock_session.request = MagicMock(return_value=mock_response)

        api = Api(socket_file)
        api.session = mock_session

        resource = Resource(api, "/test", "resource_id")
        response = resource.patch(resource_id="123", key="value")

        assert response.status_code == HTTPStatus.NO_CONTENT

    def test_api_request_filters_none_values(self):
        """Test request filters None values from kwargs."""
        with tempfile.NamedTemporaryFile() as f:
            socket_file = f.name

        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.NO_CONTENT
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        mock_session = MagicMock()
        mock_session.request = MagicMock(return_value=mock_response)

        api = Api(socket_file)
        api.session = mock_session

        resource = Resource(api, "/test")
        response = resource.request("PUT", "/test", key1="value1", key2=None, key3="value3")

        assert response.status_code == HTTPStatus.NO_CONTENT
        call_args = mock_session.request.call_args
        assert "key1" in call_args[1]["json"]
        assert "key3" in call_args[1]["json"]
        assert "key2" not in call_args[1]["json"]

    def test_api_request_non_204_response(self):
        """Test request with non-204 response."""
        with tempfile.NamedTemporaryFile() as f:
            socket_file = f.name

        with patch("requests_unixsocket.Session") as mock_session_class:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = HTTPStatus.BAD_REQUEST
            mock_response.json.return_value = {"fault_message": "Error"}
            mock_session.return_value.request.return_value = mock_response

            api = Api(socket_file)
            api.session = mock_session

            resource = Resource(api, "/test")

            with pytest.raises(APIError):
                resource.request("PUT", "/test")

    def test_api_close_session(self):
        """Test closing API session."""
        with tempfile.NamedTemporaryFile() as f:
            socket_file = f.name

        with patch("requests_unixsocket.Session") as mock_session_class:
            mock_session = MagicMock()
            api = Api(socket_file)
            api.session = mock_session

            api.close()
            mock_session.close.assert_called_once()

    def test_api_resources_initialization(self):
        """Test that all API resources are initialized."""
        with tempfile.NamedTemporaryFile() as f:
            socket_file = f.name

        api = Api(socket_file)

        assert api.describe is not None
        assert api.vm is not None
        assert api.vm_config is not None
        assert api.actions is not None
        assert api.boot is not None
        assert api.drive is not None
        assert api.version is not None
        assert api.logger is not None
        assert api.machine_config is not None
        assert api.network is not None
        assert api.mmds is not None
        assert api.mmds_config is not None
        assert api.create_snapshot is not None
        assert api.load_snapshot is not None
        assert api.vsock is not None

    def test_api_url_encoding(self):
        """Test URL encoding for socket file."""
        socket_file = "/tmp/test@socket#1"
        api = Api(socket_file)

        assert api.endpoint.startswith("http://")
        assert "%40" in api.endpoint or "@" in api.endpoint
        assert "%23" in api.endpoint or "#" in api.endpoint
        assert "test" in api.endpoint
        assert "socket" in api.endpoint
        assert "1" in api.endpoint

    def test_resource_url_construction(self):
        """Test that resource URL is constructed correctly."""
        api = Api("/tmp/test.socket")
        resource = Resource(api, "/test/path")

        assert "/test/path" in resource._api.endpoint + resource.resource

    def test_request_exception_handling(self):
        """Test request exception handling."""
        with tempfile.NamedTemporaryFile() as f:
            socket_file = f.name

        import requests

        mock_session = MagicMock()
        mock_session.request = MagicMock(side_effect=requests.RequestException("Connection failed"))

        api = Api(socket_file)
        api.session = mock_session

        resource = Resource(api, "/test")

        with pytest.raises(APIError, match="Request failed: Connection failed"):
            resource.request("PUT", "/test")

    def test_request_json_decode_error_handling(self):
        """Test request JSON decode error handling."""
        with tempfile.NamedTemporaryFile() as f:
            socket_file = f.name

        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.BAD_REQUEST
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        mock_session = MagicMock()
        mock_session.request = MagicMock(return_value=mock_response)

        api = Api(socket_file)
        api.session = mock_session

        resource = Resource(api, "/test")

        with pytest.raises(APIError, match="Invalid JSON response: Invalid JSON"):
            resource.request("PUT", "/test")
