from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = BACKEND_ROOT.parent
REQUIRED_BACKEND_VARIABLES = {
    "DATABASE_URL",
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY",
    "SUPABASE_SECRET_KEY",
    "SUPABASE_STORAGE_BUCKET",
    "GEMINI_API_KEY",
    "EMBEDDING_MODEL",
    "EMBEDDING_DIMENSION",
    "CORS_ORIGINS",
}


def test_container_start_command_uses_platform_port_without_hardcoded_fallback():
    dockerfile = (BACKEND_ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "uvicorn app.main:app --host 0.0.0.0" in dockerfile
    assert '--port \\"$PORT\\"' in dockerfile
    assert "--reload" not in dockerfile
    assert "--port 8000" not in dockerfile
    assert "EXPOSE 8000" not in dockerfile


def test_backend_deployment_guide_contains_required_platform_configuration():
    guide = (REPOSITORY_ROOT / "docs" / "deployment.md").read_text(encoding="utf-8")

    assert "## Render backend" in guide
    assert "## Railway backend alternative" in guide
    assert "Root Directory" in guide
    assert "`backend`" in guide
    assert "pip install ." in guide
    assert "uvicorn app.main:app --host 0.0.0.0 --port $PORT" in guide
    assert "`/health`" in guide
    for variable in REQUIRED_BACKEND_VARIABLES:
        assert f"`{variable}`" in guide
