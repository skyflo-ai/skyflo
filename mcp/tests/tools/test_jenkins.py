"""Tests for tools.jenkins module."""

import pytest
from tools.jenkins import (
    _parse_credentials_ref,
    build_job_path
)


class TestParseCredentialsRef:
    """Test cases for _parse_credentials_ref function."""

    def test_parse_credentials_ref_valid(self):
        """Test parsing valid credentials reference."""
        namespace, name = _parse_credentials_ref("default/my-secret")
        assert namespace == "default"
        assert name == "my-secret"

    def test_parse_credentials_ref_valid_with_hyphens(self):
        """Test parsing credentials reference with hyphens."""
        namespace, name = _parse_credentials_ref("production/my-app-secret")
        assert namespace == "production"
        assert name == "my-app-secret"

    def test_parse_credentials_ref_invalid_format(self):
        """Test parsing invalid credentials reference format."""
        with pytest.raises(ValueError, match="credentials_ref must be in the form 'namespace/name'"):
            _parse_credentials_ref("invalid-format")

    def test_parse_credentials_ref_empty_namespace(self):
        """Test parsing credentials reference with empty namespace."""
        with pytest.raises(ValueError, match="credentials_ref components cannot be empty"):
            _parse_credentials_ref("/my-secret")

    def test_parse_credentials_ref_empty_name(self):
        """Test parsing credentials reference with empty name."""
        with pytest.raises(ValueError, match="credentials_ref components cannot be empty"):
            _parse_credentials_ref("default/")

    def test_parse_credentials_ref_invalid_characters(self):
        """Test parsing credentials reference with invalid characters."""
        with pytest.raises(ValueError, match="credentials_ref contains invalid characters"):
            _parse_credentials_ref("default/my_secret!")

    def test_parse_credentials_ref_colon_in_name(self):
        """Test parsing credentials reference with colon in name."""
        with pytest.raises(ValueError, match="credentials_ref must be in the form 'namespace/name'"):
            _parse_credentials_ref("default/my:secret")


class TestBuildJobPath:
    """Test cases for build_job_path function."""

    def test_build_job_path_simple(self):
        """Test simple job path building."""
        path = build_job_path("my-job")
        assert path == "/job/my-job"

    def test_build_job_path_nested(self):
        """Test nested job path building."""
        path = build_job_path("folder/my-job")
        assert path == "/job/folder/job/my-job"

    def test_build_job_path_deeply_nested(self):
        """Test deeply nested job path building."""
        path = build_job_path("a/b/c/my-job")
        assert path == "/job/a/job/b/job/c/job/my-job"
