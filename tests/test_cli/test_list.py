"""Tests for faststack list command."""

import hashlib

import yaml
from click.testing import CliRunner

from cli import cli_group


def _file_hash(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TestListCommand:
    """Tests for the 'list' command."""

    def test_no_config_file(self, tmp_path, monkeypatch) -> None:
        """Should fail when .project-config.yaml is missing."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(cli_group, ["list"])
        assert result.exit_code != 0
        assert "No .project-config.yaml found" in result.output

    def test_no_entities(self, tmp_path, monkeypatch) -> None:
        """Should inform user when no entities are registered."""
        monkeypatch.chdir(tmp_path)
        config_path = tmp_path / ".project-config.yaml"
        config_path.write_text(yaml.dump({"entities": {}}))

        runner = CliRunner()
        result = runner.invoke(cli_group, ["list"])
        assert result.exit_code == 0
        assert "No entities registered" in result.output

    def test_entity_up_to_date(self, tmp_path, monkeypatch) -> None:
        """Entity whose model hash matches stored hash shows 'up to date'."""
        monkeypatch.chdir(tmp_path)

        # Create model file
        model_dir = tmp_path / "app" / "models"
        model_dir.mkdir(parents=True)
        model_file = model_dir / "product.py"
        model_file.write_text("class Product: pass\n")

        current_hash = _file_hash(model_file)

        config = {
            "entities": {
                "Product": {
                    "model_path": "app/models/product.py",
                    "hash": current_hash,
                }
            }
        }
        (tmp_path / ".project-config.yaml").write_text(yaml.dump(config))

        runner = CliRunner()
        result = runner.invoke(cli_group, ["list"])
        assert result.exit_code == 0
        assert "up to date" in result.output

    def test_entity_schemas_outdated(self, tmp_path, monkeypatch) -> None:
        """Entity whose model changed since last generation shows 'schemas outdated'."""
        monkeypatch.chdir(tmp_path)

        model_dir = tmp_path / "app" / "models"
        model_dir.mkdir(parents=True)
        model_file = model_dir / "product.py"
        model_file.write_text("class Product: pass\n")

        # Store a stale hash
        config = {
            "entities": {
                "Product": {
                    "model_path": "app/models/product.py",
                    "hash": "stale_hash_value",
                }
            }
        }
        (tmp_path / ".project-config.yaml").write_text(yaml.dump(config))

        runner = CliRunner()
        result = runner.invoke(cli_group, ["list"])
        assert result.exit_code == 0
        assert "schemas outdated" in result.output

    def test_entity_missing_model(self, tmp_path, monkeypatch) -> None:
        """Entity whose model file does not exist shows 'MISSING'."""
        monkeypatch.chdir(tmp_path)

        config = {
            "entities": {
                "Product": {
                    "model_path": "app/models/product.py",
                    "hash": "some_hash",
                }
            }
        }
        (tmp_path / ".project-config.yaml").write_text(yaml.dump(config))

        runner = CliRunner()
        result = runner.invoke(cli_group, ["list"])
        assert result.exit_code == 0
        assert "MISSING" in result.output
