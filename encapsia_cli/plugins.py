"""Install / uninstall plugins."""
import datetime
import shutil
import sys
from pathlib import Path

import click
import toml
from encapsia_api import EncapsiaApi

from encapsia_cli import lib


main = lib.make_main(__doc__)


@main.command("dev-create-namespace")
@click.argument("namespace")
@click.argument("n_task_workers", default=1)
@click.pass_context
def dev_create_namespace(ctx, namespace, n_task_workers):
    """Create namespace of given name. Only useful during developmment."""
    lib.run_plugins_task(
        ctx.obj["host"],
        ctx.obj["token"],
        "dev_create_namespace",
        dict(namespace=namespace, n_task_workers=n_task_workers),
        "Creating namespace",
    )


@main.command("dev-destroy-namespace")
@click.argument("namespace")
@click.pass_context
def dev_destroy_namespace(ctx, namespace):
    """Destroy namespace of given name. Only useful during development"""
    lib.run_plugins_task(
        ctx.obj["host"],
        ctx.obj["token"],
        "dev_destroy_namespace",
        dict(namespace=namespace),
        "Destroying namespace",
    )


@main.command()
@click.pass_context
def info(ctx):
    """Provide some information about installed plugins."""
    lib.run_plugins_task(
        ctx.obj["host"],
        ctx.obj["token"],
        "list_namespaces",
        dict(),
        "Fetching list of namespaces",
    )


def read_toml(filename):
    with filename.open() as f:
        return toml.load(f)


@main.command()
@click.option("--versions", help="TOML file containing webapp names and versions.")
@click.option(
    "--plugins-cache-dir",
    default="~/.encapsia/plugins-cache",
    help="Name of directory in which to cache plugins.",
)
@click.option("--force", is_flag=True, help="Always install even if already installed.")
@click.pass_context
def install(ctx, versions, plugins_cache_dir, force):
    """Install plugins of particular versions."""
    plugins_cache_dir = Path(plugins_cache_dir).expanduser()
    versions = Path(versions)
    api = EncapsiaApi(ctx.obj["host"], ctx.obj["token"])
    for name, version in read_toml(versions).items():
        plugin_filename = plugins_cache_dir / f"plugin-{name}-{version}.tar.gz"
        if not plugin_filename.exists():
            print(
                f"Unable to find plugin {name} version {name} in cache ({plugins_cache_dir})"
            )
            raise click.abort()

        # TODO only upload if not already installed? (unless --force)
        blob_id = api.upload_file_as_blob(plugin_filename.as_posix())
        # TODO create plugin entity and pass that in (the pluginsmanager creates the pluginlogs entity)
        lib.log(f"Uploaded {plugin_filename} to blob: {blob_id}")
        lib.run_plugins_task(
            ctx.obj["host"],
            ctx.obj["token"],
            "install_plugin",
            dict(blob_id=blob_id),
            "Installing",
        )


@main.command()
@click.argument("namespace")
@click.pass_context
def uninstall(ctx, namespace):
    """Uninstall named plugin."""
    click.confirm(f'Are you sure you want to uninstall the plugin (delete all!) from namespace "{namespace}"?', abort=True)
    lib.run_plugins_task(
        ctx.obj["host"],
        ctx.obj["token"],
        "uninstall_plugin",
        dict(namespace=namespace),
        f"Uninstalling {namespace}",
    )


class LastUploadedVsModifiedTracker:

    DIRECTORIES = ["tasks", "views", "wheels", "webfiles", "schedules"]

    def __init__(self, directory, reset=False):
        self.directory = directory
        encapsia_directory = directory / ".encapsia"
        encapsia_directory.mkdir(parents=True, exist_ok=True)
        self.filename = encapsia_directory / "last_uploaded_plugin_parts.toml"
        if reset:
            self.make_empty()
        else:
            self.load()

    def make_empty(self):
        self.data = {}
        self.save()

    def load(self):
        if not self.filename.exists():
            self.make_empty()
        else:
            with self.filename.open() as f:
                self.data = toml.load(f)

    def save(self):
        with self.filename.open("w") as f:
            toml.dump(self.data, f)

    def get_modified_directories(self):
        for name in self.DIRECTORIES:
            last_modified = lib.most_recently_modified(self.directory / name)
            if last_modified is not None:
                if name in self.data:
                    if last_modified > self.data[name]:
                        yield Path(name)
                        self.data[name] = datetime.datetime.utcnow()
                else:
                    yield Path(name)
                    self.data[name] = datetime.datetime.utcnow()
        self.save()


def get_modified_plugin_directories(directory, reset=False):
    return list(
        LastUploadedVsModifiedTracker(directory, reset=reset).get_modified_directories()
    )


@main.command("dev-update")
@click.argument("directory", default=".")
@click.option("--reset", is_flag=True, help="Always update everything.")
@click.pass_context
def dev_update(ctx, directory, reset):
    """Update plugin parts which have changed since previous update.

    Optionally pass in the DIRECTORY of the plugin (defaults to cwd).

    """
    directory = Path(directory)
    plugin_toml_path = directory / "plugin.toml"
    if not plugin_toml_path.exists():
        lib.error("Not in a plugin directory.")
        sys.exit(1)
    modified_plugin_directories = get_modified_plugin_directories(
        directory, reset=reset
    )
    if modified_plugin_directories:
        with lib.temp_directory() as temp_directory:
            shutil.copy(plugin_toml_path, temp_directory)
            for modified_directory in modified_plugin_directories:
                lib.log(f"Including: {modified_directory}")
                shutil.copytree(
                    directory / modified_directory, temp_directory / modified_directory
                )
            lib.run_plugins_task(
                ctx.obj["host"],
                ctx.obj["token"],
                "dev_update_plugin",
                dict(),
                "Uploading to server",
                data=lib.create_targz_as_bytes(temp_directory),
            )
    else:
        lib.log("Nothing to do.")
