"""Install, uninstall, create, and update plugins."""

import datetime
import operator
import re
import shutil
import tempfile
import urllib.request
from contextlib import contextmanager
from pathlib import Path

import collections

import boto3
import click
import semver
import toml
from tabulate import tabulate

from encapsia_cli import lib

main = lib.make_main(__doc__, for_plugins=True)


def _format_datetime(dt):
    return datetime.datetime.fromisoformat(dt).strftime("%a %d %b %Y %H:%M:%S")


def _add_to_local_store(plugins_local_dir, uri, force=False):
    full_name = uri.rsplit("/", 1)[-1]
    m = re.match(r"plugin-([^-]*)-([^-]*).tar.gz", full_name)
    if m:
        output_filename = plugins_local_dir / full_name
        if not force and output_filename.exists():
            lib.log(f"Found: {output_filename} (Skipping)")
        else:
            filename, headers = urllib.request.urlretrieve(uri, tempfile.mkstemp()[1])
            shutil.move(filename, output_filename)
            lib.log(f"Created: {output_filename}")
    else:
        lib.log_error("That doesn't look like a plugin. Aborting!", abort=True)


def _install_plugin(api, filename, print_output=False):
    """Use the API to install plugin directly from a file."""
    if not filename.is_file():
        lib.log_error(f"Cannot find plugin: {filename}", abort=True)
    blob_id = api.upload_file_as_blob(filename.as_posix())
    lib.log(f"Uploaded {filename} to blob: {blob_id}")
    lib.run_plugins_task(
        api,
        "install_plugin",
        dict(blob_id=blob_id),
        "Installing",
        print_output=print_output,
    )


def _read_versions_toml(filename):
    return lib.read_toml(Path(filename)).items()


def _download_plugin_from_s3(plugins_s3_bucket, name, filename):
    s3 = boto3.client("s3")
    with open(filename, "wb") as f:
        s3.download_fileobj(plugins_s3_bucket, name, f)


class PluginInfo:

    PLUGIN_REGEX = re.compile(r"^.*plugin-([^-]*)-(.*)\.tar.gz$")
    FOUR_DIGIT_VERSION_REGEX = re.compile(r"([0-9]+)\.([0-9]+)\.([0-9]+)\.([0-9]+)")
    DEV_VERSION_REGEX = re.compile(r"([0-9]+)\.([0-9]+)\.([0-9]+)dev([0-9]+)")

    def __init__(self, raw):
        """Takes either (name, version) or some kind of plugin filename."""
        if isinstance(raw, tuple):
            self.name, self.version = raw
        elif isinstance(raw, (str, Path)):
            m = self.PLUGIN_REGEX.match(str(raw))
            if m:
                self.name = m.group(1)
                self.version = m.group(2)
            else:
                raise ValueError(f"Unable to parse: {raw}")
        self.semver = self.parse_version(self.version)
        self.key = self.name, self.semver

    def parse_version(self, version):
        # Consider a 4th digit to be a SemVer pre-release.
        m = self.FOUR_DIGIT_VERSION_REGEX.match(version)
        if m:
            major, minor, patch, prerelease = m.groups()
            return semver.VersionInfo(
                major=major, minor=minor, patch=patch, prerelease=prerelease
            )
        # E.g. 0.0.209dev12 is build 12.
        m = self.DEV_VERSION_REGEX.match(version)
        if m:
            major, minor, patch, build = m.groups()
            return semver.VersionInfo(
                major=major, minor=minor, patch=patch, build=build
            )
        # Otherwise hope that the semver package can deal with it.
        try:
            return semver.VersionInfo.parse(version)
        except ValueError as e:
            lib.log_error(str(e))
            # At least return something comparable.
            return semver.VersionInfo(major=0)

    def formatted_version(self):
        version, semver = self.version, str(self.semver)
        if semver == version:
            return semver
        else:
            return f"{version} ({semver})"

    def get_as_filename(self):
        return f"plugin-{self.name}-{self.version}.tar.gz"

    def get_as_s3_name(self):
        return f"{self.name}/{self.get_as_filename()}"

    def matches(self, name, version_prefix=""):
        return self.name == name and self.version.startswith(version_prefix)

    def __str__(self):
        return self.get_as_filename()


class PluginInfos:
    def __init__(self, plugin_infos):
        self.pis = plugin_infos

    @staticmethod
    def make_from_local_store(plugins_local_dir):
        result = Path(plugins_local_dir).glob("plugin-*-*.tar.gz")
        return PluginInfos([PluginInfo(raw) for raw in result])

    @staticmethod
    def make_from_s3(plugins_s3_bucket):
        s3 = boto3.client("s3")
        paginator = s3.get_paginator("list_objects_v2")
        response = paginator.paginate(Bucket=plugins_s3_bucket)
        return PluginInfos(
            [
                PluginInfo(x["Key"])
                for r in response
                for x in r.get("Contents", [])
                if x["Key"].endswith(".tar.gz")
            ]
        )

    def latest(self):
        try:
            return max(self.pis, key=operator.attrgetter("key"),)
        except ValueError:
            return None

    @staticmethod
    def _split_spec(spec):
        if "-" in spec:
            return spec.split("-")
        else:
            return spec, ""

    def filter_to_spec(self, spec):
        name, version_prefix = self._split_spec(spec)
        return PluginInfos([pi for pi in self.pis if pi.matches(name, version_prefix)])

    def filter_to_specs(self, specs):
        return PluginInfos(
            [pi for spec in specs for pi in self.filter_to_spec(spec).pis]
        )

    def filter_to_latest(self):
        temp = collections.defaultdict(list)
        for pi in self.pis:
            temp[pi.name].append(pi)
        for name in temp:
            temp[name] = PluginInfos(temp[name]).latest()
        return PluginInfos(temp.values())

    def latest_version_matching_spec(self, spec):
        return self.filter_to_spec(spec).latest()

    def as_sorted_list(self):
        return sorted(self.pis, key=operator.attrgetter("key"))


@main.command()
@click.pass_obj
def dev_list_namespaces(obj):
    """Print information about the namespace usage of installed plugins."""
    api = lib.get_api(**obj)
    lib.run_plugins_task(api, "list_namespaces", dict(), "Fetching list of namespaces")


@main.command()
@click.pass_obj
def freeze(obj):
    """Print currently installed plugins as versions TOML."""
    api = lib.get_api(**obj)
    raw_info = api.run_view("pluginsmanager", "installed_plugins_with_tags")
    info = {i["name"]: i["version"] for i in raw_info}
    lib.log_output(toml.dumps(info))


@main.command()
@click.argument("plugins", nargs=-1)
@click.pass_obj
def logs(obj, plugins):
    """Print the latest install logs for given plugins."""
    api = lib.get_api(**obj)
    # Despite the name, this only fetches the latest log for each plugin, not all!
    raw_info = api.run_view("pluginsmanager", "all_plugin_logs")
    if plugins:
        # Filter to specified plugins.
        raw_info = [i for i in raw_info if i["name"] in plugins]
    for i in raw_info:
        for f in (
            "name",
            "version",
            "description",
            "action",
            "server",
            "success",
            "when",
        ):
            lib.log(f"{f.capitalize()}: {i[f]}")
        lib.log("Logs:")
        if i["success"]:
            lib.log_output(i["output"].strip())
        else:
            lib.log_error(i["output"].strip())
        lib.log("")


@main.command()
@click.argument("plugins", nargs=-1)
@click.pass_obj
def status(obj, plugins):
    """Print information about (successfully) installed plugins."""
    local_versions = PluginInfos.make_from_local_store(
        obj["plugins_local_dir"]
    ).filter_to_latest()
    api = lib.get_api(**obj)
    raw_info = api.run_view("pluginsmanager", "installed_plugins_with_tags")
    if plugins:
        # Filter to specified plugins.
        raw_info = [i for i in raw_info if i["name"] in plugins]
    # Tidy formatting
    for i in raw_info:
        i["version"] = PluginInfo((i["name"], i["version"])).formatted_version()
        plugin_tags = i.pop("plugin_tags")
        if isinstance(plugin_tags, list):
            i["plugin-tags"] = ", ".join(sorted(plugin_tags))
        else:
            i["plugin-tags"] = ""
        i["installed"] = _format_datetime(i.pop("when"))
        available = local_versions.latest_version_matching_spec(i["name"])
        if available:
            i["available"] = available.formatted_version()
            if i["available"] == i["version"]:
                i["available"] = "<same>"
        else:
            i["available"] = ""
    headers = [
        "name",
        "version",
        "available",
        "description",
        "installed",
        "plugin-tags",
    ]
    info = ([p[h] for h in headers] for p in raw_info)
    lib.log(tabulate(info, headers=headers))
    lib.log("\n(Equivalent semver versions in brackets, if any and if required)")


@main.command()
@click.option(
    "--versions", default=None, help="TOML file containing plugin names and versions."
)
@click.option(
    "--show-logs/--no-show-logs", default=False, help="Print installation logs."
)
@click.argument("plugins", nargs=-1)
@click.pass_obj
def install(obj, versions, show_logs, plugins):
    """Install plugins by name, from files, or from a versions.toml file.

    Plugins provided as files are put in the local before being installed.

    When described by name alone, the latest plugin of that name in the local will be used.

    And plugins specified in the versions.toml file will be taken from the local.

    """
    plugins_local_dir = obj["plugins_local_dir"]

    # First, create a list of plugin files to install.
    filenames = []
    for plugin in plugins:
        plugin_filename = Path(plugin).resolve()
        if plugin_filename.is_file():
            # If it looks like a file then just add it.
            _add_to_local_store(plugins_local_dir, plugin_filename.as_uri(), force=True)
            filenames.append(plugins_local_dir / plugin_filename.name)
        else:
            # Else assume it is a spec for a plugin already in the local store.
            pi = PluginInfos.make_from_local_store(
                plugins_local_dir
            ).latest_version_matching_spec(plugin)
            if pi:
                plugin_filename = pi.get_as_filename()
                filenames.append(plugins_local_dir / plugin_filename)
            else:
                lib.log_error(f"Cannot find plugin with name: {plugin}", abort=True)
    if versions:
        for name, version in _read_versions_toml(versions):
            filenames.append(
                plugins_local_dir / PluginInfo((name, version)).get_as_filename()
            )

    # Second, install them.
    api = lib.get_api(**obj)
    for filename in filenames:
        _install_plugin(api, filename, print_output=show_logs)


@main.command()
@click.option(
    "--show-logs/--no-show-logs", default=False, help="Print installation logs."
)
@click.argument("namespace")
@click.pass_obj
def uninstall(obj, show_logs, namespace):
    """Uninstall named plugin."""
    if not obj["force"]:
        click.confirm(
            "Are you sure you want to uninstall the plugin "
            + f"(delete all!) from namespace {namespace}",
            abort=True,
        )
    api = lib.get_api(**obj)
    lib.run_plugins_task(
        api,
        "uninstall_plugin",
        dict(namespace=namespace),
        f"Uninstalling {namespace}",
        print_output=show_logs,
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


class PluginsTaskError(Exception):

    pass


@contextmanager
def get_modified_plugin_directories(directory, reset=False):
    tracker = LastUploadedVsModifiedTracker(directory, reset=reset)
    try:
        yield list(tracker.get_modified_directories())
    except PluginsTaskError:
        pass
    except Exception:
        raise
    else:
        tracker.save()


@main.command("dev-update")
@click.argument("directory", default=".")
@click.pass_obj
def dev_update(obj, directory):
    """Update plugin parts which have changed since previous update.

    Optionally pass in the DIRECTORY of the plugin (defaults to cwd).

    """
    directory = Path(directory)
    plugin_toml_path = directory / "plugin.toml"
    if not plugin_toml_path.exists():
        lib.log_error("Not in a plugin directory.", abort=True)

    with get_modified_plugin_directories(
        directory, reset=obj["force"]
    ) as modified_plugin_directories:
        if modified_plugin_directories:
            with lib.temp_directory() as temp_directory:
                shutil.copy(plugin_toml_path, temp_directory)
                for modified_directory in modified_plugin_directories:
                    lib.log(f"Including: {modified_directory}")
                    shutil.copytree(
                        directory / modified_directory,
                        temp_directory / modified_directory,
                    )
                api = lib.get_api(**obj)
                lib.run_plugins_task(
                    api,
                    "dev_update_plugin",
                    dict(),
                    "Uploading to server",
                    data=lib.create_targz_as_bytes(temp_directory),
                )
        else:
            lib.log("Nothing to do.")


@main.command("dev-create-namespace")
@click.argument("namespace")
@click.argument("n_task_workers", default=1)
@click.pass_obj
def dev_create_namespace(obj, namespace, n_task_workers):
    """Create namespace of given name. Only useful during developmment."""
    api = lib.get_api(**obj)
    lib.run_plugins_task(
        api,
        "dev_create_namespace",
        dict(namespace=namespace, n_task_workers=n_task_workers),
        "Creating namespace",
    )


@main.command("dev-destroy-namespace")
@click.argument("namespace")
@click.pass_obj
def dev_destroy_namespace(obj, namespace):
    """Destroy namespace of given name. Only useful during development"""
    api = lib.get_api(**obj)
    lib.run_plugins_task(
        api, "dev_destroy_namespace", dict(namespace=namespace), "Destroying namespace"
    )


@main.command()
@click.argument("sources", nargs=-1)
@click.pass_obj
def dev_build(obj, sources):
    """Build plugins from given source directories."""
    plugins_local_dir = obj["plugins_local_dir"]
    force = obj["force"]
    for source_directory in sources:
        source_directory = Path(source_directory)
        manifest = lib.read_toml(source_directory / "plugin.toml")
        name = manifest["name"]
        version = manifest["version"]
        output_filename = plugins_local_dir / f"plugin-{name}-{version}.tar.gz"
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
@click.argument("plugins", nargs=-1)
@click.option(
    "--all-versions/--latest-versions",
    default=False,
    help="List all versions, not just the latest.",
)
@click.pass_obj
def upstream(obj, plugins, all_versions):
    """Print information about plugins on S3. By default, only includes latest versions."""
    plugins_s3_bucket = obj["plugins_s3_bucket"]
    plugin_infos = PluginInfos.make_from_s3(plugins_s3_bucket)
    if not all_versions:
        plugin_infos = plugin_infos.filter_to_latest()
    if plugins:
        plugin_infos = plugin_infos.filter_to_specs(plugins)
    info = ([r.name, r.formatted_version()] for r in plugin_infos.as_sorted_list())
    lib.log(tabulate(info, headers=["name", "version"]))
    lib.log("\n(Equivalent semver versions in brackets, if any and if required)")


@main.command()
@click.option(
    "--versions", default=None, help="TOML file containing plugin names and versions."
)
@click.argument("plugins", nargs=-1)
@click.pass_obj
def add(obj, versions, plugins):
    """Add plugin(s) to local store from file, URL, or S3."""
    plugins_local_dir = obj["plugins_local_dir"]
    plugins_s3_bucket = obj["plugins_s3_bucket"]
    force = obj["force"]
    to_download_from_s3 = []
    s3_versions = None  # For performance, only fetch if/when first needed.
    for plugin in plugins:
        if Path(plugin).is_file():
            _add_to_local_store(
                plugins_local_dir, Path(plugin).resolve().as_uri(), force
            )
        elif urllib.parse.urlparse(plugin).scheme != "":
            _add_to_local_store(plugins_local_dir, plugin, force)
        else:
            if s3_versions is None:
                s3_versions = PluginInfos.make_from_s3(plugins_s3_bucket)
            pi = s3_versions.latest_version_matching_spec(plugin)
            if pi is None:
                lib.log_error(f"Unable to find plugin from: {plugin}", abort=True)
            else:
                to_download_from_s3.append(pi)
    if versions:
        for name, version in _read_versions_toml(versions):
            to_download_from_s3.append(PluginInfo((name, version)))
    for pi in to_download_from_s3:
        filename = Path(plugins_local_dir, pi.get_as_filename())
        if not force and filename.exists():
            lib.log(f"Found: {filename} (Skipping)")
        else:
            _download_plugin_from_s3(plugins_s3_bucket, pi.get_as_s3_name(), filename)
            lib.log(f"Created: {filename}")


@main.command()
@click.option(
    "--all-versions/--latest-versions",
    default=False,
    help="List all versions, not just the latest.",
)
@click.argument("plugins", nargs=-1)
@click.pass_obj
def ls(obj, all_versions, plugins):
    """Print information about plugins in local store. By default, only includes latest versions."""
    plugins_local_dir = obj["plugins_local_dir"]
    plugin_infos = PluginInfos.make_from_local_store(plugins_local_dir)
    if not all_versions:
        plugin_infos = plugin_infos.filter_to_latest()
    if plugins:
        plugin_infos = plugin_infos.filter_to_specs(plugins)
    info = ([pi.name, pi.formatted_version()] for pi in plugin_infos.as_sorted_list())
    lib.log(tabulate(info, headers=["name", "version"]))
    lib.log("\n(Equivalent semver versions in brackets, if any and if required)")


@main.command()
@click.option(
    "--refresh-from-s3/--no-refresh-from-s3",
    default=False,
    help="First fetch latest versions from S3 before checking.",
)
@click.option(
    "--dry-run/--no-dry-run",
    default=False,
    help="Report what will be done but don't change anything.",
)
@click.option(
    "--show-logs/--no-show-logs", default=False, help="Print installation logs."
)
@click.argument("plugins", nargs=-1)
@click.pass_obj
@click.pass_context
def upgrade(ctx, obj, refresh_from_s3, dry_run, show_logs, plugins):
    """Install latest plugin versions from local, optionally limited to particular plugins."""
    plugins_local_dir = obj["plugins_local_dir"]
    force = obj["force"]
    if refresh_from_s3:
        ctx.invoke(add)
    local_plugin_infos = PluginInfos.make_from_local_store(
        plugins_local_dir
    ).filter_to_latest()
    api = lib.get_api(**obj)
    raw_info = api.run_view("pluginsmanager", "installed_plugins_with_tags")
    installed_versions = [PluginInfo((i["name"], i["version"])) for i in raw_info]
    for pi in installed_versions:
        if len(plugins) > 0 and pi.name not in plugins:
            continue
        local_pi = local_plugin_infos.latest_version_matching_spec(pi.name)
        if local_pi is None:
            lib.log(f"Skipping because plugin not in local: {pi.name}")
            continue
        if force or pi.semver < local_pi.semver:
            lib.log(
                f"Upgrading plugin: {pi.name} from {pi.formatted_version()} to {local_pi.formatted_version()}"
            )
            if not dry_run:
                _install_plugin(
                    api,
                    plugins_local_dir / local_pi.get_as_filename(),
                    print_output=show_logs,
                )
        else:
            lib.log(
                f"Skipping because already current: {pi.name} {pi.formatted_version()}"
            )
    for p in plugins:
        if p not in set(pi.name for pi in installed_versions):
            lib.log_error(f"Skipping because requested plugin is not installed: {p}")
