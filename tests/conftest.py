import pytest
import tempfile
import shutil
from pathlib import Path


@pytest.fixture
def tmp_project(tmp_path):
    """Create a temporary project directory with basic structure."""
    project = tmp_path / "test-project"
    project.mkdir()
    (project / "myapp").mkdir()
    (project / "myapp" / "__init__.py").write_text("")
    (project / "myapp" / "domain").mkdir()
    (project / "myapp" / "domain" / "__init__.py").write_text("")
    (project / "myapp" / "service").mkdir()
    (project / "myapp" / "service" / "__init__.py").write_text("")
    (project / "myapp" / "infra").mkdir()
    (project / "myapp" / "infra" / "__init__.py").write_text("")
    (project / "myapp" / "api").mkdir()
    (project / "myapp" / "api" / "__init__.py").write_text("")
    (project / "docs").mkdir()
    return project
