import pytest
from click.testing import CliRunner

from encapsia_cli.encapsia import main

MANIFEST = """\
name = "example"
description = "Example plugin"
version = "0.0.1"
created_by = "timothy.corbettclark@gmail.com"
n_task_workers = 1
reset_on_install = true
"""


@pytest.fixture
def local_store(tmp_path):
    local_store = tmp_path / "local_store"
    local_store.mkdir()
    return local_store


@pytest.fixture
def example_plugin(tmp_path):
    manifest = MANIFEST + 'tags = ["example"]\n'
    plugin_dir = tmp_path / "example"
    plugin_dir.mkdir()
    manifest_file = plugin_dir / "plugin.toml"
    manifest_file.write_text(manifest)
    return plugin_dir


@pytest.fixture
def example_plugin_variant(tmp_path):
    manifest = MANIFEST + 'tags = ["example", "variant=example_variant"]\n'
    plugin_dir = tmp_path / "example"
    plugin_dir.mkdir()
    manifest_file = plugin_dir / "plugin.toml"
    manifest_file.write_text(manifest)
    return plugin_dir


@pytest.fixture
def example_plugin_extra_variant(tmp_path):
    manifest = (
        MANIFEST
        + 'tags = ["example", "variant=example_variant", "variant=extra_variant"]\n'
    )
    plugin_dir = tmp_path / "example"
    plugin_dir.mkdir()
    manifest_file = plugin_dir / "plugin.toml"
    manifest_file.write_text(manifest)
    return plugin_dir


def test_dev_build_without_variant(example_plugin, local_store):
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "plugins",
            "--force",
            "--local-dir",
            local_store.as_posix(),
            "dev-build",
            example_plugin.as_posix(),
        ],
    )
    assert result.exit_code == 0
    assert (local_store / "plugin-example-0.0.1.tar.gz").exists()


def test_dev_build_with_variant(example_plugin_variant, local_store):
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "plugins",
            "--force",
            "--local-dir",
            local_store.as_posix(),
            "dev-build",
            example_plugin_variant.as_posix(),
        ],
    )
    assert result.exit_code == 0
    assert (
        local_store / "plugin-example-variant-example_variant-0.0.1.tar.gz"
    ).exists()


def test_dev_build_with_extra_variant_fails(example_plugin_extra_variant, local_store):
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "plugins",
            "--force",
            "--local-dir",
            local_store.as_posix(),
            "dev-build",
            example_plugin_extra_variant.as_posix(),
        ],
    )
    assert result.exit_code != 0
    assert list(local_store.iterdir()) == []
