import pytest
from pydantic import ValidationError

from app.core.config import BACKEND_ROOT, MAX_UPLOAD_SIZE_BYTES, Settings


def test_supabase_backend_storage_settings_are_loaded_from_env(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "backend-secret")
    monkeypatch.setenv("SUPABASE_STORAGE_BUCKET", "knowledge-documents")
    monkeypatch.setenv("MAX_DOCUMENT_SIZE_BYTES", "1048576")

    settings = Settings()

    assert settings.supabase_url == "https://example.supabase.co"
    assert settings.supabase_anon_key == "anon-key"
    assert settings.supabase_secret_key is not None
    assert settings.supabase_secret_key.get_secret_value() == "backend-secret"
    assert settings.supabase_storage_bucket == "knowledge-documents"
    assert settings.max_document_size_bytes == 1048576


def test_supabase_secret_key_is_hidden_from_serialized_output(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "backend-secret")
    monkeypatch.setenv("SUPABASE_STORAGE_BUCKET", "knowledge-documents")
    monkeypatch.setenv("MAX_DOCUMENT_SIZE_BYTES", "5242880")

    settings = Settings()
    payload = settings.model_dump()

    assert "supabase_secret_key" not in payload
    assert "backend-secret" not in str(payload)
    assert str(settings.supabase_secret_key) == "**********"


def test_production_security_defaults_and_environment_location():
    settings = Settings(_env_file=None)

    assert settings.allowed_cors_origins == ["http://localhost:3000"]
    assert settings.max_document_size_bytes == MAX_UPLOAD_SIZE_BYTES == 5_242_880
    assert Settings.model_config["env_file"] == BACKEND_ROOT / ".env"


def test_cors_origins_load_from_environment_and_are_normalized(monkeypatch):
    monkeypatch.setenv(
        "CORS_ORIGINS",
        "https://support.example.com/, http://localhost:3000",
    )

    settings = Settings(_env_file=None)

    assert settings.allowed_cors_origins == [
        "https://support.example.com",
        "http://localhost:3000",
    ]


@pytest.mark.parametrize("value", ["", "*", "https://support.example.com/path"])
def test_cors_origins_reject_unsafe_values(value):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, CORS_ORIGINS=value)


def test_upload_limit_cannot_be_configured_above_five_mib():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, MAX_DOCUMENT_SIZE_BYTES=MAX_UPLOAD_SIZE_BYTES + 1)
