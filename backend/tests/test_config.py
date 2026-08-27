from app.core.config import Settings


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
