import collections
import datetime
import operator
import re
import shutil
import tempfile
import urllib.request
from contextlib import contextmanager
from pathlib import Path

import arrow
import boto3
import botocore
import click
import semver
import toml
from tabulate import tabulate

from encapsia_cli import lib


@click.group("plugins")
@click.option(
    "--local-dir",
    type=click.Path(),
    default="~/.encapsia/plugins",
    help="Name of local directory used to store plugins.",
)
@click.option(
    "--s3-bucket",
    "s3_buckets",
    type=str,
    multiple=True,
    default="ice-plugins",
    help="Name of AWS S3 bucket containing plugins (may be provided multiple times).",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Always fetch/build/etc again.",
)
@click.pass_context
def main(ctx, force, s3_buckets, local_dir):
    """Install, uninstall, create, and update plugins."""
    ctx.obj["plugins_local_dir"] = Path(local_dir).expanduser()
    ctx.obj["plugins_local_dir"].mkdir(parents=True, exist_ok=True)
    ctx.obj["plugins_s3_buckets"] = s3_buckets
    ctx.obj["plugins_force"] = force


def _format_datetime(dt):
    return arrow.get(dt).strftime("%a %d %b %Y %H:%M:%S")
    # In Python 3.7 and beyond we could do the following. But we want to support Python 3.6.
    # return datetime.datetime.fromisoformat(dt).strftime("%a %d %b %Y %H:%M:%S")


def _log_message_explaining_semver():
    lib.log(
        "\n(Equivalent semver versions are shown in brackets when non-semver version is used)"
    )


def _add_to_local_store_from_uri(plugins_local_dir, uri, force=False):
    full_name = uri.rsplit("/", 1)[-1]
    try:
        PluginInfo.make_from_filename(full_name)  # Will raise if name is invalid.
    except ValueError:
        lib.log_error("That doesn't look like a plugin. Aborting!", abort=True)
    store_filename = plugins_local_dir / full_name
    if not force and store_filename.exists():
        lib.log(f"Found: {store_filename} (Skipping)")
    else:
        filename, headers = urllib.request.urlretrieve(uri, tempfile.mkstemp()[1])
        shutil.move(filename, store_filename)
        lib.log(f"Added to local store: {store_filename}")


def _add_to_local_store_from_s3(pi, plugins_local_dir, force=False):
    filename = plugins_local_dir / pi.get_filename()
    if not force and filename.exists():
        lib.log(f"Found: {filename} (Skipping)")
    else:
        s3 = boto3.client("s3")
        try:
            s3.download_file(pi.get_s3_bucket(), pi.get_s3_name(), str(filename))
        except botocore.exceptions.ClientError:
            lib.log_error(
                f"Unable to download: {pi.get_s3_bucket()}/{pi.get_s3_name()}"
            )
        else:
            lib.log(
                f"Downloaded {pi.get_s3_bucket()}/{pi.get_s3_name()} and saved to {filename}"
            )


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


class PluginInfo:

    PLUGIN_REGEX = re.compile(r"^.*plugin-([^-]*)-(.*)\.tar.gz$")
    FOUR_DIGIT_VERSION_REGEX = re.compile(r"([0-9]+)\.([0-9]+)\.([0-9]+)\.([0-9]+)")
    DEV_VERSION_REGEX = re.compile(r"([0-9]+)\.([0-9]+)\.([0-9]+)dev([0-9]+)")

    def __init__(self, s3_bucket, s3_path, name, version):
        """Private constructor. Use make_* factory methods instead."""
        self.s3_bucket = s3_bucket
        self.s3_path = s3_path
        self.name = name
        self.version = version
        self.semver = self.parse_version(self.version)
        self.key = self.name, self.semver

    @classmethod
    def get_name_and_version_from_filename(cls, filename):
        m = cls.PLUGIN_REGEX.match(str(filename))
        if m is None:
            raise ValueError(f"Unable to parse: {filename}")
        return m.group(1), m.group(2)  # (name, version)

    @staticmethod
    def make_from_name_version(name, version):
        return PluginInfo(None, None, name, version)

    @classmethod
    def make_from_filename(cls, filename):
        name, version = cls.get_name_and_version_from_filename(filename)
        return PluginInfo(None, None, name, version)

    @classmethod
    def make_from_s3(cls, s3_bucket, s3_path):
        name, version = cls.get_name_and_version_from_filename(s3_path)
        s3_path_without_filename = "/".join(s3_path.split("/")[:-1])
        return PluginInfo(s3_bucket, s3_path_without_filename, name, version)

    def parse_version(self, version):
        # Consider a 4th digit to be a SemVer pre-release.
        # E.g. 1.2.3.4 is 1.2.3-4
        m = self.FOUR_DIGIT_VERSION_REGEX.match(version)
        if m:
            major, minor, patch, prerelease = m.groups()
            return semver.VersionInfo(
                major=major, minor=minor, patch=patch, prerelease=prerelease
            )
        # Consider a "dev" build to be a SemVer pre-release.
        # E.g. 0.0.209dev12 is 0.0.209-12
        m = self.DEV_VERSION_REGEX.match(version)
        if m:
            major, minor, patch, prerelease = m.groups()
            return semver.VersionInfo(
                major=major, minor=minor, patch=patch, prerelease=prerelease
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

    def get_filename(self):
        return f"plugin-{self.name}-{self.version}.tar.gz"

    def get_s3_bucket(self):
        return self.s3_bucket

    def get_s3_path(self):
        return self.s3_path

    def get_s3_name(self):
        if self.s3_path:
            return f"{self.s3_path}/{self.get_filename()}"
        else:
            # In the unlikely scenario that plugin files are stored flat in a bucket.
            return self.get_filename()

    @staticmethod
    def _split_spec(spec):
        if "-" in spec:
            return spec.split("-", 1)
        else:
            return spec, ""

    def matches(self, spec):
        name, version_prefix = self._split_spec(spec)
        return self.name == name and self.version.startswith(version_prefix)

    def __str__(self):
        return self.get_filename()


class PluginInfos:
    def __init__(self, plugin_infos):
        self.pis = plugin_infos

    @staticmethod
    def make_from_local_store(plugins_local_dir):
        result = plugins_local_dir.glob("plugin-*-*.tar.gz")
        return PluginInfos([PluginInfo.make_from_filename(p) for p in result])

    @staticmethod
    def make_from_s3_buckets(plugins_s3_buckets):
        s3 = boto3.client("s3")
        plugin_infos = []
        for bucket_path in plugins_s3_buckets:
            if "/" in bucket_path:
                bucket, path = bucket_path.split("/", 1)
            else:
                bucket, path = bucket_path, ""
            try:
                paginator = s3.get_paginator("list_objects_v2")
                response = paginator.paginate(Bucket=bucket, Prefix=path)
                plugin_infos.extend(
                    PluginInfo.make_from_s3(bucket, x["Key"])
                    for r in response
                    for x in r.get("Contents", [])
                    if x["Key"].endswith(".tar.gz")
                )
            except botocore.exceptions.ClientError as e:
                lib.log_error(f"Unable to search bucket: {bucket}")
                lib.log_error(str(e), abort=True)
        return PluginInfos(plugin_infos)

    @staticmethod
    def make_from_encapsia(host):
        api = lib.get_api(host=host)
        raw_info = api.run_view("pluginsmanager", "installed_plugins_with_tags")
        return PluginInfos(
            [
                PluginInfo.make_from_name_version(i["name"], i["version"])
                for i in raw_info
            ]
        )

    def latest(self):
        try:
            return max(
                self.pis,
                key=operator.attrgetter("key"),
            )
        except ValueError:
            return None

    def filter_to_spec(self, spec):
        return PluginInfos([pi for pi in self.pis if pi.matches(spec)])

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
    if len(raw_info) == 0 and len(plugins) > 0:
        lib.log(
            "No logs found. Note that any plugins must be exact name matches without version info."
        )


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
    plugin_infos = []
    for i in raw_info:
        pi = PluginInfo.make_from_name_version(i["name"], i["version"])

        available_pi = local_versions.latest_version_matching_spec(i["name"])
        if available_pi:
            temp = available_pi.formatted_version()
            available = "<same>" if temp == pi.formatted_version() else temp
        else:
            available = ""

        pi.extras = {
            "description": i["description"],
            "plugin-tags": (
                ", ".join(sorted(i["plugin_tags"]))
                if isinstance(i["plugin_tags"], list)
                else ""
            ),
            "installed": _format_datetime(i["when"]),
            "available": available,
        }

        plugin_infos.append(pi)

    if plugins:
        plugin_infos = PluginInfos(plugin_infos).filter_to_specs(plugins).pis

    for i in raw_info:
        i["version"] = PluginInfo.make_from_name_version(
            i["name"], i["version"]
        ).formatted_version()
    headers = [
        "name",
        "version",
        "available",
        "description",
        "installed",
        "plugin-tags",
    ]
    info = (
        [
            pi.name,
            pi.formatted_version(),
            pi.extras["available"],
            pi.extras["description"],
            pi.extras["installed"],
            pi.extras["plugin-tags"],
        ]
        for pi in plugin_infos
    )
    lib.log(tabulate(info, headers=headers))
    _log_message_explaining_semver()


@main.command()
@click.option(
    "--versions", default=None, help="TOML file containing plugin names and versions."
)
@click.option(
    "--show-logs", is_flag=True, default=False, help="Print installation logs."
)
@click.option(
    "--latest-existing",
    is_flag=True,
    default=False,
    help="Upgrade existing plugins.",
)
@click.argument("plugins", nargs=-1)
@click.pass_obj
def install(obj, versions, show_logs, latest_existing, plugins):
    """Install/upgrade plugins by name, from files, or from a versions.toml file.

    Plugins provided as files are put in the local store before being installed.

    When described by name alone, the latest plugin of that name in the local store will be used.

    Plugins specified in the versions.toml file will be taken from the local store.

    """
    plugins_local_dir = obj["plugins_local_dir"]
    plugins_force = obj["plugins_force"]

    # Create a list of installation candidates.
    to_install_candidates = []
    for plugin in plugins:
        plugin_filename = Path(plugin).resolve()
        if plugin_filename.is_file():
            # If it looks like a file then just add it.
            _add_to_local_store_from_uri(
                plugins_local_dir, plugin_filename.as_uri(), force=True
            )
            to_install_candidates.append(PluginInfo.make_from_filename(plugin_filename))
        else:
            # Else assume it is a spec for a plugin already in the local store.
            pi = PluginInfos.make_from_local_store(
                plugins_local_dir
            ).latest_version_matching_spec(plugin)
            if pi:
                to_install_candidates.append(pi)
            else:
                lib.log_error(f"Cannot find plugin: {plugin}", abort=True)
    if versions:
        for name, version in _read_versions_toml(versions):
            to_install_candidates.append(
                PluginInfo.make_from_name_version(name, version)
            )
    if latest_existing:
        available = PluginInfos.make_from_local_store(
            plugins_local_dir
        ).filter_to_latest()
        for pi in PluginInfos.make_from_encapsia(obj["host"]).as_sorted_list():
            a = available.latest_version_matching_spec(pi.name)
            if a:
                to_install_candidates.append(a)

    # Work out and list installation plan.
    to_install_candidates = PluginInfos(to_install_candidates).as_sorted_list()
    to_install = []
    installed = PluginInfos.make_from_encapsia(obj["host"])
    headers = ["name", "existing version", "new version", "action"]
    info = []
    for pi in to_install_candidates:
        current = installed.latest_version_matching_spec(pi.name)
        if current:
            current_version = current.formatted_version()
            if current.semver < pi.semver:
                action = "upgrade"
            elif current.semver > pi.semver:
                action = "downgrade"
            else:
                action = "reinstall" if plugins_force else "skip"
        else:
            current_version = ""
            action = "install"
        info.append([pi.name, current_version, pi.formatted_version(), action])
        if action != "skip":
            to_install.append(pi)
    lib.log(tabulate(info, headers=headers))
    _log_message_explaining_semver()

    # Seek confirmation unless force.
    if to_install and not plugins_force:
        click.confirm(
            "Do you wish to proceed with the above plan?",
            abort=True,
        )

    # Install them.
    lib.log("")
    if to_install:
        api = lib.get_api(**obj)
        for pi in to_install:
            _install_plugin(
                api, plugins_local_dir / pi.get_filename(), print_output=show_logs
            )
    else:
        lib.log("Nothing to do!")


@main.command()
@click.option(
    "--show-logs", is_flag=True, default=False, help="Print installation logs."
)
@click.argument("namespaces", nargs=-1)
@click.pass_obj
def uninstall(obj, show_logs, namespaces):
    """Uninstall named plugin(s)."""
    if namespaces and not obj["plugins_force"]:
        lib.log("Preparing to uninstall: " + ", ".join(namespaces))
        click.confirm(
            "Are you sure?",
            abort=True,
        )
    api = lib.get_api(**obj)
    for namespace in namespaces:
        lib.run_plugins_task(
            api,
            "uninstall_plugin",
            dict(namespace=namespace),
            f"Uninstalling {namespace}",
            print_output=show_logs,
        )


@main.command()
@click.pass_obj
def dev_list(obj):
    """Print information about the namespace usage of installed plugins."""
    api = lib.get_api(**obj)
    lib.run_plugins_task(api, "list_namespaces", dict(), "Fetching list of namespaces")


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
        directory, reset=obj["plugins_force"]
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


@main.command("dev-create")
@click.argument("namespace")
@click.argument("n_task_workers", default=1)
@click.pass_obj
def dev_create(obj, namespace, n_task_workers):
    """Create namespace of given name. Only useful during developmment."""
    api = lib.get_api(**obj)
    lib.run_plugins_task(
        api,
        "dev_create_namespace",
        dict(namespace=namespace, n_task_workers=n_task_workers),
        "Creating namespace",
    )


@main.command("dev-destroy")
@click.option("--all", is_flag=True, default=False, help="Destroy all namespaces!")
@click.argument("namespaces", nargs=-1)
@click.pass_obj
def dev_destroy(obj, all, namespaces):
    """Destroy namespace(s) of given name. Only useful during development"""
    api = lib.get_api(**obj)
    if all:
        click.confirm(
            "Are you sure you want to destroy all namespaces?",
            abort=True,
        )
        lib.run_plugins_task(
            api,
            "dev_wipe",
            dict(),
            "Destroying all namespaces",
        )
    else:
        for namespace in namespaces:
            lib.run_plugins_task(
                api,
                "dev_destroy_namespace",
                dict(namespace=namespace),
                f"Destroying namespace: {namespace}",
            )


@main.command()
@click.argument("sources", nargs=-1)
@click.pass_obj
def dev_build(obj, sources):
    """Build plugins from given source directories."""
    plugins_local_dir = obj["plugins_local_dir"]
    plugins_force = obj["plugins_force"]
    for source_directory in sources:
        source_directory = Path(source_directory)
        manifest = lib.read_toml(source_directory / "plugin.toml")
        name = manifest["name"]
        version = manifest["version"]
        output_filename = plugins_local_dir / f"plugin-{name}-{version}.tar.gz"
        if not plugins_force and output_filename.exists():
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
                lib.log(f"Added to local store: {output_filename}")


@main.command()
@click.argument("plugins", nargs=-1)
@click.option(
    "--all-versions",
    is_flag=True,
    default=False,
    help="List all versions, not just the latest.",
)
@click.pass_obj
def upstream(obj, plugins, all_versions):
    """Print information about plugins on S3. By default, only includes latest versions."""
    plugins_s3_buckets = obj["plugins_s3_buckets"]
    lib.log(f"Searching for plugins in S3 bucket(s): {', '.join(plugins_s3_buckets)}")
    plugin_infos = PluginInfos.make_from_s3_buckets(plugins_s3_buckets)
    if plugins:
        plugin_infos = plugin_infos.filter_to_specs(plugins)
    if not all_versions:
        plugin_infos = plugin_infos.filter_to_latest()
    info = (
        [r.get_s3_bucket(), r.get_s3_path(), r.name, r.formatted_version()]
        for r in plugin_infos.as_sorted_list()
    )
    lib.log(tabulate(info, headers=["bucket", "path", "name", "version"]))
    _log_message_explaining_semver()


@main.command()
@click.option(
    "--versions", default=None, help="TOML file containing plugin names and versions."
)
@click.option(
    "--latest-existing",
    is_flag=True,
    default=False,
    help="Upgrade existing plugins.",
)
@click.argument("plugins", nargs=-1)
@click.pass_obj
def add(obj, versions, latest_existing, plugins):
    """Add plugin(s) to local store from file, URL, or S3."""
    plugins_local_dir = obj["plugins_local_dir"]
    plugins_s3_buckets = obj["plugins_s3_buckets"]
    plugins_force = obj["plugins_force"]
    to_download_from_s3 = []
    s3_versions = None  # For performance, only fetch if/when first needed.
    for plugin in plugins:
        if Path(plugin).is_file():
            _add_to_local_store_from_uri(
                plugins_local_dir,
                Path(plugin).resolve().as_uri(),
                plugins_force,
            )
        elif urllib.parse.urlparse(plugin).scheme != "":
            _add_to_local_store_from_uri(plugins_local_dir, plugin, plugins_force)
        else:
            if s3_versions is None:
                s3_versions = PluginInfos.make_from_s3_buckets(plugins_s3_buckets)
            pi = s3_versions.latest_version_matching_spec(plugin)
            if pi is None:
                lib.log_error(f"Cannot find plugin: {plugin}", abort=True)
            else:
                to_download_from_s3.append(pi)
    if versions:
        if s3_versions is None:
            s3_versions = PluginInfos.make_from_s3_buckets(plugins_s3_buckets)
        to_download_from_s3.extend(
            s3_versions.latest_version_matching_spec(f"{name}-{version}")
            for name, version in _read_versions_toml(versions)
        )
    if latest_existing:
        to_download_from_s3.extend(
            PluginInfos.make_from_encapsia(obj["host"]).as_sorted_list()
        )
    for pi in to_download_from_s3:
        _add_to_local_store_from_s3(pi, plugins_local_dir, force=plugins_force)


@main.command()
@click.option(
    "--all-versions",
    is_flag=True,
    default=False,
    help="List all versions, not just the latest.",
)
@click.option(
    "-l",
    "--long",
    "long_format",
    is_flag=True,
    default=False,
    help="Long format with extra info (takes a few seconds).",
)
@click.argument("plugins", nargs=-1)
@click.pass_obj
def ls(obj, all_versions, long_format, plugins):
    """Print information about plugins in local store. By default, only includes latest versions."""
    plugins_local_dir = obj["plugins_local_dir"]
    plugin_infos = PluginInfos.make_from_local_store(plugins_local_dir)
    if not all_versions:
        plugin_infos = plugin_infos.filter_to_latest()
    if plugins:
        plugin_infos = plugin_infos.filter_to_specs(plugins)

    def _read_description(pi):
        filename = plugins_local_dir / pi.get_filename()
        try:
            with lib.temp_directory() as tmp_dir:
                lib.extract_targz(filename, tmp_dir)
                manifests = list(tmp_dir.glob("**/plugin.toml"))
                return lib.read_toml(manifests[0])["description"]
        except Exception:
            lib.log_error(f"Malformed? Unable to read: {filename}")

    if long_format:
        info = (
            [pi.name, pi.formatted_version(), _read_description(pi)]
            for pi in plugin_infos.as_sorted_list()
        )
        lib.log(tabulate(info, headers=["name", "version", "description"]))
    else:
        info = (
            [pi.name, pi.formatted_version()] for pi in plugin_infos.as_sorted_list()
        )
        lib.log(tabulate(info, headers=["name", "version"]))
    _log_message_explaining_semver()
