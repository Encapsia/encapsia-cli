"""Create and install plugins."""
import datetime
import glob
import os
import shutil
import sys
import tempfile

import click
import toml
from encapsia_api import EncapsiaApi

from encapsia_cli import lib


@click.group()
@click.option("--host", help="Name to use to lookup credentials in .encapsia/credentials.toml")
@click.option("--host-env-var", default="ENCAPSIA_HOST", help="Environment variable containing DNS hostname (default ENCAPSIA_HOST)")
@click.option(
    "--token-env-var",
    default="ENCAPSIA_TOKEN",
    help="Environment variable containing server token (default ENCAPSIA_TOKEN)",
)
@click.pass_context
def main(ctx, host, host_env_var, token_env_var):
    """Create and install plugins."""
    host, token = lib.discover_credentials(host, host_env_var, token_env_var)
    ctx.obj = dict(host=host, token=token)


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


def make_plugin_toml_file(filename, name, description, version, created_by):
    obj = dict(
        name=name,
        description=description,
        version=version,
        created_by=created_by,
        n_task_workers=1,
        reset_on_install=True,
    )
    with open(filename, "w") as f:
        toml.dump(obj, f)


@main.command("create-from-webapp")
@click.argument("webapp")
@click.argument("version")
@click.option("--email", prompt="Your email")
def create_from_webapp(webapp, version, email):
    """Convert a webapp on S3 in to a plugin."""
    lib.log("Fetching webapp {} version {}...".format(webapp, version))
    with lib.temp_directory() as temp_directory:
        base_name = "plugin-{}-{}".format(webapp, version)
        base_dir = os.path.join(temp_directory, base_name)
        os.makedirs(base_dir)

        # Download everything from S3 into the webfiles folder.
        files_directory = os.path.join(base_dir, "webfiles")
        os.makedirs(files_directory)
        lib.run(
            "aws",
            "s3",
            "cp",
            "s3://ice-webapp-builds/{}/{}".format(webapp, version),
            files_directory,
            "--recursive",
        )

        # Move out the views if they exist.
        views_directory = os.path.join(files_directory, "views")
        if os.path.exists(views_directory):
            shutil.move(views_directory, base_dir)

        # Move out the tasks if they exist.
        tasks_directory = os.path.join(files_directory, "tasks")
        if os.path.exists(tasks_directory):
            shutil.move(tasks_directory, base_dir)

        # Create plugin.toml
        plugin_filename = os.path.join(base_dir, "plugin.toml")
        make_plugin_toml_file(
            plugin_filename, webapp, "Webapp {}".format(webapp), version, email
        )

        # Convert all into tar.gz
        filename = base_name + ".tar.gz"
        lib.create_targz(base_dir, filename)
        lib.log("Created plugin: {}".format(filename))
        return filename


@main.command()
@click.argument("filename")
@click.pass_context
def install(ctx, filename):
    """Install plugin from given tar.gz file or directory."""
    temp_filename = None
    if os.path.isdir(filename):
        fd, temp_filename = tempfile.mkstemp(suffix=".tar.gz")
        os.close(fd)
        lib.create_targz(filename, temp_filename)
        filename = temp_filename

    api = EncapsiaApi(ctx.obj["host"], ctx.obj["token"])
    blob_id = api.upload_file_as_blob(filename)
    # TODO create plugin entity
    # TODO also assign a blobtag?
    lib.log(f"Uploaded {filename} to blob: {blob_id}")
    lib.run_plugins_task(
        ctx.obj["host"],
        ctx.obj["token"],
        "install_plugin",
        dict(blob_id=blob_id),
        "Installing",
    )

    if temp_filename:
        os.remove(temp_filename)


@main.command()
@click.argument("namespace")
@click.pass_context
def uninstall(ctx, namespace):
    """Uninstall named plugin."""
    lib.run_plugins_task(
        ctx.obj["host"],
        ctx.obj["token"],
        "uninstall_plugin",
        dict(namespace=namespace),
        "Uninstalling {}".format(namespace),
    )


class LastUploadedVsModifiedTracker:

    DIRECTORIES = ["tasks", "views", "wheels", "webfiles", "schedules"]

    def __init__(self, directory, reset=False):
        self.directory = directory
        self.filename = os.path.join(self.directory, ".encapsia", "last_uploaded_plugin_parts.toml")
        if reset:
            self.make_empty()
        else:
            self.load()

    def make_empty(self):
        os.makedirs(os.path.join(self.directory, ".encapsia"), exist_ok=True)
        self.data = {}
        self.save()

    def load(self):
        if not os.path.exists(self.filename):
            self.make_empty()
        else:
            with open(self.filename) as f:
                self.data = toml.load(f)

    def save(self):
        with open(self.filename, "w") as f:
            toml.dump(self.data, f)

    def get_modified_directories(self):
        for name in self.DIRECTORIES:
            possible_files = glob.glob(os.path.join(self.directory, name, "**"))
            if possible_files:
                if name in self.data:
                    last_changed_file = max(possible_files, key=os.path.getctime)
                    last_modified = datetime.datetime.utcfromtimestamp(os.path.getctime(last_changed_file))
                    if last_modified > self.data[name]:
                        yield name
                        self.data[name] = datetime.datetime.utcnow()
                else:
                    yield name
                    self.data[name] = datetime.datetime.utcnow()
        self.save()


def get_modified_plugin_directories(directory, reset=False):
    return list(LastUploadedVsModifiedTracker(directory, reset=reset).get_modified_directories())


@main.command("dev-update")
@click.argument("directory", default=".")
@click.option("--force", is_flag=True, help="Force an update of all parts of the plugin")
@click.pass_context
def dev_update(ctx, directory, force):
    """Update plugin parts which have changed since previous update.

    Optionally pass in the DIRECTORY of the plugin (defaults to cwd).

    """
    if not os.path.exists(os.path.join(directory, "plugin.toml")):
        lib.error("Not in a plugin directory.")
        sys.exit(1)
    modified_plugin_directories = get_modified_plugin_directories(directory, reset=force)
    if modified_plugin_directories:
        with lib.temp_directory() as tmp_directory:
            shutil.copy(os.path.join(directory, "plugin.toml"), tmp_directory)
            for modified_directory in modified_plugin_directories:
                lib.log(f"Including: {modified_directory}")
                shutil.copytree(os.path.join(directory, modified_directory), os.path.join(tmp_directory, modified_directory))
            lib.run_plugins_task(
                ctx.obj["host"],
                ctx.obj["token"],
                "dev_update_plugin",
                dict(),
                "Uploading to server",
                data=lib.create_targz_as_bytes(tmp_directory),
            )
    else:
        lib.log("Nothing to do.")
