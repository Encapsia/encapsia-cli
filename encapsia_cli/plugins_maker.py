"""Create plugins."""
import re
import shutil
import urllib.request
from pathlib import Path

import click
import toml

from encapsia_cli import lib


@click.group()
@click.option(
    "--plugins-cache-dir",
    default="~/.encapsia/plugins-cache",
    help="Name of directory in which to cache plugins.",
)
@click.option(
    "--force", is_flag=True, help="Always fetch/build even if already in cache."
)
@click.pass_context
def main(ctx, plugins_cache_dir, force):
    """Create plugins."""
    plugins_cache_dir = Path(plugins_cache_dir).expanduser()
    plugins_cache_dir.mkdir(parents=True, exist_ok=True)
    ctx.obj = dict(plugins_cache_dir=plugins_cache_dir, force=force)


def read_toml(filename):
    with filename.open() as f:
        return toml.load(f)


def make_plugin_toml_file(filename, name, description, version, created_by):
    obj = dict(
        name=name,
        description=description,
        version=version,
        created_by=created_by,
        n_task_workers=1,
        reset_on_install=True,
    )
    with filename.open("w") as f:
        toml.dump(obj, f)


@main.command()
@click.option("--versions", help="TOML file containing webapp names and versions.")
@click.option("--email", prompt="Your email", help="Email creator of the plugins.")
@click.option(
    "--s3-directory", default="ice-webapp-builds", help="Base directory on S3."
)
@click.pass_context
def build_from_legacy_s3(ctx, versions, email, s3_directory):
    """Build plugins from legacy webapps hosted on AWS S3."""
    plugins_cache_dir = ctx.obj["plugins_cache_dir"]
    force = ctx.obj["force"]
    versions = Path(versions)
    for name, version in read_toml(versions).items():
        output_filename = Path(plugins_cache_dir, f"plugin-{name}-{version}.tar.gz")
        if not force and output_filename.exists():
            lib.log(f"Found: {output_filename} (Skipping)")
        else:
            _download_and_build_plugin_from_s3(
                s3_directory, name, version, email, output_filename
            )
            lib.log(f"Created: {output_filename}")


def _download_and_build_plugin_from_s3(
    s3_directory, name, version, email, output_filename
):
    with lib.temp_directory() as temp_directory:
        base_dir = temp_directory / f"plugin-{name}-{version}"
        base_dir.mkdir()

        # Download everything from S3 into the webfiles folder.
        # (we will move out the views and tasks if present).
        files_directory = base_dir / "webfiles"
        files_directory.mkdir()
        lib.run(
            "aws",
            "s3",
            "cp",
            f"s3://{s3_directory}/{name}/{version}",
            files_directory.as_posix(),
            "--recursive",
        )

        # Move out the views if they exist.
        views_directory = files_directory / "views"
        if views_directory.exists():
            views_directory.rename(base_dir / "views")

        # Move out the tasks if they exist.
        tasks_directory = files_directory / "tasks"
        if tasks_directory.exists():
            tasks_directory.rename(base_dir / "tasks")

        # Create a plugin.toml manifest.
        make_plugin_toml_file(
            base_dir / "plugin.toml", name, f"Webapp {name}", version, email
        )

        # Convert all into tar.gz
        lib.create_targz(base_dir, output_filename)


@main.command()
@click.argument("sources", nargs=-1)
@click.pass_context
def build_from_src(ctx, sources):
    """Build plugins from given source directories."""
    plugins_cache_dir = ctx.obj["plugins_cache_dir"]
    force = ctx.obj["force"]
    for source_directory in sources:
        source_directory = Path(source_directory)
        manifest = read_toml(source_directory / "plugin.toml")
        name = manifest["name"]
        version = manifest["version"]
        output_filename = plugins_cache_dir / f"plugin-{name}-{version}.tar.gz"
        if not force and output_filename.exists():
            lib.log(f"Found: {output_filename} (Skipping)")
        else:
            with lib.temp_directory() as temp_directory:
                base_dir = temp_directory / f"plugin-{name}-{version}"
                base_dir.mkdir()
                for t in (
                    "webfiles",
                    "views",
                    "tasks",
                    "wheels",
                    "schedules",
                    "plugin.toml",
                ):
                    source_t = source_directory / t
                    if source_t.exists():
                        if source_t.is_file():
                            shutil.copy(source_t, base_dir / t)
                        else:
                            shutil.copytree(source_t, base_dir / t)
                lib.create_targz(base_dir, output_filename)
                lib.log(f"Created: {output_filename}")


@main.command()
@click.argument("url")
@click.pass_context
def fetch_from_url(ctx, url):
    """Copy a plugin from given URL into the plugin cache."""
    plugins_cache_dir = ctx.obj["plugins_cache_dir"]
    force = ctx.obj["force"]
    full_name = url.rsplit("/", 1)[-1]
    m = re.match(r"plugin-([^-]*)-([^-]*).tar.gz", full_name)
    if m:
        output_filename = plugins_cache_dir / full_name
        if not force and output_filename.exists():
            lib.log(f"Found: {output_filename} (Skipping)")
        else:
            filename, headers = urllib.request.urlretrieve(url)
            shutil.move(filename, output_filename)
            lib.log(f"Created: {output_filename}")
    else:
        print("That doesn't look like a plugin. Aborting!")
        raise click.Abort()
