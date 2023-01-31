import datetime
import shutil
import tempfile
import urllib.request
from contextlib import contextmanager
from io import TextIOWrapper
from pathlib import Path

import click
import toml
from tabulate import tabulate

from encapsia_cli import lib, s3
from encapsia_cli.plugininfo import (
    InvalidSpecError,
    PluginInfo,
    PluginInfos,
    PluginSpec,
    PluginSpecs,
    TooManyVariantTagsError,
    get_variant_from_tags,
)


class _PluginsTaskError(Exception):

    pass


@contextmanager
def _get_modified_plugin_directories(directory, reset=False):
    tracker = LastUploadedVsModifiedTracker(directory, reset=reset)
    try:
        yield list(tracker.get_modified_directories())
    except _PluginsTaskError:
        pass
    else:
        tracker.save()


def _get_available_from_local_store(local_versions: PluginInfos, pi: PluginInfo) -> str:
    available_pi = local_versions.latest_version_matching_spec(
        # filter for name-and-variant
        PluginSpec(pi.name, pi.variant)
    )
    if available_pi:
        available_version = available_pi.formatted_version()
        available = (
            "<same>"
            if available_version == pi.formatted_version()
            else available_version
        )
    else:
        available = ""
    return available


def _log_message_explaining_headers():
    lib.log(
        "\n(*) Plugin variant shown in square brackets when defined."
        "\n(**) Equivalent semver versions are shown in brackets when non-semver version is used."
    )


def _add_to_local_store_from_uri(
    plugins_local_dir: Path, uri: str, force: bool = False
):
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


def _add_to_local_store_from_s3(
    pi: PluginInfo, plugins_local_dir: Path, force: bool = False
):
    target = plugins_local_dir / pi.get_filename()
    if not force and target.exists():
        lib.log(f"Found: {target} (Skipping)")
    else:
        try:
            s3.download_file(pi.get_s3_bucket(), pi.get_s3_name(), target.as_posix())
        except s3.S3Error as e:
            lib.log_error(str(e))
        else:
            lib.log(
                f"Downloaded {pi.get_s3_bucket()}/{pi.get_s3_name()} and saved to {target}"
            )


def _create_install_plan(
    candidates,
    installed,
    local_store,
    plugins_s3_buckets,
    allow_reinstall,
    allow_downgrade,
):
    plan = []
    to_download_from_s3 = []
    s3_versions = None  # For performance, only fetch if/when first needed.
    for spec in candidates:
        candidate = local_store.latest_version_matching_spec(spec)
        will_get_from_s3 = False
        if not candidate:
            if s3_versions is None:
                s3_versions = PluginInfos.make_from_s3_buckets(plugins_s3_buckets)
            if (
                candidate := s3_versions.latest_version_matching_spec(spec)
            ) is not None:
                to_download_from_s3.append(candidate)
                will_get_from_s3 = True
            else:
                lib.log_error(
                    f"Could not find plugin matching {spec} in local store nor S3",
                    abort=True,
                )
        current = installed.latest_version_matching_spec(
            PluginSpec(spec.name, spec.variant)
        )
        if current:
            current_version = current.formatted_version()
            if current.semver < candidate.semver:
                action = "upgrade"
            elif current.semver > candidate.semver:
                action = "downgrade" if allow_downgrade else "skip"
            else:
                action = "reinstall" if allow_reinstall else "skip"
        else:
            current_version = ""
            action = "install"
        if will_get_from_s3 and action != "skip":
            action = "download from s3 and " + action
        plan.append(
            [
                candidate,  # keep first for sorting
                candidate.name_and_variant(),
                current_version,
                candidate.formatted_version(),
                action,
            ]
        )
    return sorted(plan), to_download_from_s3


def _install_plugin(api, filename: Path, print_output: bool = False):
    """Use the API to install plugin directly from a file."""
    if not filename.is_file():
        lib.log_error(f"Cannot find plugin: {filename}", abort=True)
    blob_id = api.upload_file_as_blob(
        filename.as_posix(),
    )
    lib.log(f"Uploaded {filename} to blob: {blob_id}")
    return lib.run_plugins_task(
        api,
        "install_plugin",
        dict(blob_id=blob_id),
        "Installing",
        print_output=print_output,
        is_idempotent=True,  # re-installing a plugin should be safe
    )


def _download_plugins_from_s3(
    plugins_to_download, plugins_local_dir, plugins_force, added_from_file_or_uri=False
):
    if plugins_to_download:
        for plugin in plugins_to_download:
            _add_to_local_store_from_s3(plugin, plugins_local_dir, force=plugins_force)
    else:
        if not added_from_file_or_uri:
            lib.log("Nothing to do!")


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
    help="Name of AWS S3 bucket (or path) containing plugins (may be provided multiple times).",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="[deprecated] Always fetch/build/etc again.",
)
@click.pass_context
def main(ctx, force, s3_buckets, local_dir):
    """Install, uninstall, create, and update plugins."""
    if force:
        lib.log_error(
            "Warning: --force option is deprecated, please use the other available options (use --help to find them)."
        )
    ctx.obj["plugins_local_dir"] = Path(local_dir).expanduser()
    ctx.obj["plugins_local_dir"].mkdir(parents=True, exist_ok=True)
    ctx.obj["plugins_s3_buckets"] = s3_buckets
    ctx.obj["plugins_force"] = force


@main.command()
@click.pass_obj
def freeze(obj):
    """Print currently installed plugins as versions TOML."""
    versions = PluginSpecs.make_from_plugininfos(
        PluginInfos.make_from_encapsia(obj["host"])
    ).as_version_dict()
    lib.log_output(toml.dumps(versions))


@main.command()
@click.argument("plugins", nargs=-1)
@click.pass_obj
def logs(obj, plugins):
    """Print the latest install logs for given plugins."""
    api = lib.get_api(**obj)
    # Despite the name, this only fetches the latest log for each plugin, not all!
    raw_info = api.run_view(
        "pluginsmanager",
        "all_plugin_logs",
    )
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
@click.option(
    "-l",
    "--long",
    "long_format",
    is_flag=True,
    default=False,
    help="Long format with description.",
)
@click.argument("plugins", nargs=-1)
@click.pass_obj
def status(obj, long_format, plugins):
    """Print information about (successfully) installed plugins."""
    host = obj["host"]
    plugins_local_dir = obj["plugins_local_dir"]
    local_versions = PluginInfos.make_from_local_store(
        plugins_local_dir
    ).filter_to_latest()
    plugin_infos = PluginInfos.make_from_encapsia(host)
    if plugins:
        specs = PluginSpecs.make_from_spec_strings(plugins)
        plugin_infos = specs.filter(plugin_infos)

    headers = ["name*", "version**", "available**", "installed"]
    if long_format:
        headers.extend(["description", "plugin-tags"])

    info = []
    for pi in plugin_infos:
        pi_info = [
            pi.name_and_variant(),
            pi.formatted_version(),
            _get_available_from_local_store(local_versions, pi),
            pi.extras["installed"],
        ]
        if long_format:
            pi_info.extend([pi.extras["description"], pi.extras["plugin-tags"]])
        info.append(pi_info)
    lib.log(tabulate(info, headers=headers))
    _log_message_explaining_headers()


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
@click.option(
    "--all-available",
    is_flag=True,
    default=False,
    help="Download all available plugins from s3.",
)
@click.option(
    "--yes",
    is_flag=True,
    default=False,
    help="Do not prompt for confirmation after presenting the install plan.",
)
@click.option(
    "--reinstall",
    is_flag=True,
    default=False,
    help="Allow re-installing plugins even if the same version is already installed.",
)
@click.option(
    "--downgrade",
    is_flag=True,
    default=False,
    help="Allow installing plugins even if a newer version is already installed.",
)
@click.option(
    "--overwrite",
    is_flag=True,
    default=False,
    help="Overwrite existing plugins having the same name and version in the local store.",
)
@click.argument("plugins", nargs=-1)
@click.pass_obj
def install(
    obj,
    versions,
    show_logs,
    latest_existing,
    all_available,
    yes,
    reinstall,
    downgrade,
    overwrite,
    plugins,
):
    """Install/upgrade plugins by name, from files, or from a versions.toml file.

    Plugins provided as files are put in the local store before being installed.

    When described by name alone, the latest plugin of that name in the local store will be used.

    Plugins specified in the versions.toml file will be taken from the local store.

    """
    plugins_local_dir = obj["plugins_local_dir"]
    plugins_force = obj["plugins_force"]
    plugins_s3_buckets = obj["plugins_s3_buckets"]
    host = obj["host"]

    # Create a list of installation candidates.
    to_install_candidates = []
    for plugin in plugins:
        if PluginInfo.looks_like_path_to_plugin(plugin):
            plugin_filename = Path(plugin).resolve()
            if plugin_filename.is_file():
                # If it looks like a file then just add it.
                _add_to_local_store_from_uri(
                    plugins_local_dir, plugin_filename.as_uri(), force=True
                )
                plugin_info = PluginInfo.make_from_filename(plugin_filename)
                plugin_spec = PluginSpec.make_from_plugininfo(plugin_info)
                to_install_candidates.append(plugin_spec)
            else:
                lib.log_error(
                    f"The requested plugin '{plugin}', which looks like a path to a file, was not found."
                )
        else:
            # Else assume it is a spec for a plugin already in the local store.
            to_install_candidates.append(PluginSpec.make_from_string(plugin))
    if versions:
        # Assume plugins already present in local store.
        to_install_candidates.extend(
            PluginSpecs.make_from_version_dict(
                lib.read_toml(Path(versions).expanduser())
            )
        )
    if latest_existing:
        to_install_candidates.extend(
            PluginSpec(pi.name, pi.variant)
            for pi in PluginInfos.make_from_encapsia(host)
        )

    # Get the plugins from S3
    if all_available and plugins_s3_buckets:
        s3_plugins = PluginInfos.make_from_s3_buckets(plugins_s3_buckets)
        for s3_plugin in s3_plugins:
            _add_to_local_store_from_s3(
                s3_plugin, plugins_local_dir, force=(plugins_force or overwrite)
            )
            to_install_candidates.append(PluginSpec.make_from_plugininfo(s3_plugin))

    # Work out and list installation plan.
    # to_install_candidates = sorted(PluginInfos(to_install_candidates))
    installed = PluginInfos.make_from_encapsia(host)
    local_store = PluginInfos.make_from_local_store(plugins_local_dir)
    plan, to_download_from_s3 = _create_install_plan(
        to_install_candidates,
        installed,
        local_store,
        plugins_s3_buckets,
        allow_reinstall=plugins_force or reinstall,
        allow_downgrade=plugins_force or downgrade,
    )
    to_install = [i[0] for i in plan if i[4] != "skip"]
    headers = ["name*", "existing version**", "new version**", "action"]
    lib.log(tabulate([i[1:] for i in plan], headers=headers))
    _log_message_explaining_headers()

    # Seek confirmation unless force.
    if to_install and not (plugins_force or yes):
        click.confirm(
            "Do you wish to proceed?",
            abort=True,
        )

    # Install them.
    lib.log("")
    if to_install:
        for pi in to_download_from_s3:
            _add_to_local_store_from_s3(
                pi, plugins_local_dir, force=(plugins_force or overwrite)
            )
        api = lib.get_api(**obj)
        for pi in to_install:
            success = _install_plugin(
                api, plugins_local_dir / pi.get_filename(), print_output=show_logs
            )
        if not success:
            lib.log_error("Some plugins failed to install.", abort=True)
    else:
        lib.log("Nothing to do!")


def variant_is_installed(api, plugin_spec):
    desired_tag = f'"variant={plugin_spec.variant}"'
    response = api.run_view(
        "pluginsmanager", "plugins", view_options={"having_tags": desired_tag}
    )
    matching_plugins = [item for item in response if item["name"] == plugin_spec.name]
    if len(matching_plugins) > 1:
        lib.log_error(
            f"More than one plugin with the name {plugin_spec.name} and variant {plugin_spec.variant} are installed."
        )
    return len(matching_plugins) > 0


@main.command()
@click.option(
    "--show-logs", is_flag=True, default=False, help="Print installation logs."
)
@click.option(
    "--yes", is_flag=True, default=False, help="Do not prompt for confirmation."
)
@click.argument("namespaces", nargs=-1)
@click.pass_obj
def uninstall(obj, show_logs, yes, namespaces):
    """Uninstall named plugin(s)."""
    if namespaces and not (obj["plugins_force"] or yes):
        lib.log("Preparing to uninstall: " + ", ".join(namespaces))
        click.confirm(
            "Are you sure?",
            abort=True,
        )
    api = lib.get_api(**obj)
    for namespace in namespaces:
        try:
            plugin_spec = PluginSpec.make_from_string(namespace)
            name = plugin_spec.name
            if plugin_spec.variant:
                if not variant_is_installed(api, plugin_spec):
                    lib.log_output(
                        f"Variant {plugin_spec.variant} specified for plugin {name} is not installed; skipping."
                    )
                    continue
            lib.run_plugins_task(
                api,
                "uninstall_plugin",
                dict(namespace=name),
                f"Uninstalling {name}",
                print_output=show_logs,
            )
        except InvalidSpecError as e:
            lib.log_error(e)


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


@main.command("dev-update")
@click.option(
    "--all",
    is_flag=True,
    default=False,
    help="Upload all folders, not just the new or modified ones.",
)
@click.argument("directory", default=".")
@click.pass_obj
def dev_update(obj, all, directory):
    """Update plugin parts which have changed since previous update.

    Optionally pass in the DIRECTORY of the plugin (defaults to cwd).

    """
    directory = Path(directory)
    plugin_toml_path = directory / "plugin.toml"
    if not plugin_toml_path.exists():
        lib.log_error("Not in a plugin directory.", abort=True)

    with _get_modified_plugin_directories(
        directory, reset=obj["plugins_force"] or all
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
                result = lib.run_plugins_task(
                    api,
                    "dev_update_plugin",
                    {},
                    "Uploading to server",
                    data=lib.create_targz_as_bytes(temp_directory),
                )
                if not result:
                    raise _PluginsTaskError
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
@click.option(
    "--yes", is_flag=True, default=False, help="Do not prompt for confirmation."
)
@click.argument("namespaces", nargs=-1)
@click.pass_obj
def dev_destroy(obj, all, yes, namespaces):
    """Destroy namespace(s) of given name. Only useful during development"""
    api = lib.get_api(**obj)
    if all:
        plugins_force = obj["plugins_force"]
        if not (plugins_force or yes):
            click.confirm(
                "Are you sure you want to destroy all namespaces?",
                abort=True,
            )
        lib.run_plugins_task(
            api,
            "dev_wipe",
            {},
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
@click.option(
    "--overwrite",
    is_flag=True,
    default=False,
    help="Overwrite any existing plugin with the same name and version in the local store.",
)
@click.argument("sources", nargs=-1)
@click.pass_obj
def dev_build(obj, overwrite, sources):
    """Build plugins from given source directories."""
    plugins_local_dir = obj["plugins_local_dir"]
    plugins_force = obj["plugins_force"]
    for source_directory in sources:
        source_directory = Path(source_directory)
        manifest = lib.read_toml(source_directory / "plugin.toml")
        name = manifest["name"]
        version = manifest["version"]
        tags = manifest.get("tags", [])
        try:
            variant = get_variant_from_tags(tags)
        except TooManyVariantTagsError as e:
            lib.log_error(str(e), abort=True)
        if variant:
            output_filename = (
                plugins_local_dir / f"plugin-{name}-variant-{variant}-{version}.tar.gz"
            )
        else:
            output_filename = plugins_local_dir / f"plugin-{name}-{version}.tar.gz"
        if not (plugins_force or overwrite) and output_filename.exists():
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
    """Print information about plugins on S3.

    By default, only includes latest versions.
    """
    plugins_s3_buckets = obj["plugins_s3_buckets"]
    lib.log(f"Searching for plugins in S3 bucket(s): {', '.join(plugins_s3_buckets)}")
    plugin_infos = PluginInfos.make_from_s3_buckets(plugins_s3_buckets)
    if plugins:
        plugin_infos = PluginSpecs.make_from_spec_strings(plugins).filter(plugin_infos)
    if not all_versions:
        plugin_infos = plugin_infos.filter_to_latest()
    info = (
        [
            r.name_and_variant(),
            r.formatted_version(),
            r.get_s3_bucket(),
            r.get_s3_path(),
        ]
        for r in sorted(plugin_infos)
    )
    lib.log(tabulate(info, headers=["name*", "version**", "bucket", "path"]))
    _log_message_explaining_headers()


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
@click.option(
    "--all-available",
    is_flag=True,
    default=False,
    help="Add to local store all available plugins from s3.",
)
@click.option(
    "--overwrite",
    is_flag=True,
    default=False,
    help="Overwrite if the same plugin version already exists in the local store.",
)
@click.argument("plugins", nargs=-1)
@click.pass_obj
def add(obj, versions, latest_existing, all_available, overwrite, plugins):
    """Add plugin(s) to local store from file, URL, or S3."""
    plugins_local_dir = obj["plugins_local_dir"]
    plugins_s3_buckets = obj["plugins_s3_buckets"]
    overwrite = overwrite or obj["plugins_force"]
    host = obj["host"]

    specs_to_search_in_s3 = []
    to_download_from_s3 = []
    s3_versions = None  # For performance, only fetch if/when first needed.
    added_from_file_or_uri = False

    # Get all available plugins from S3
    if all_available and plugins_s3_buckets:
        _download_plugins_from_s3(
            PluginInfos.make_from_s3_buckets(plugins_s3_buckets),
            plugins_local_dir,
            overwrite,
        )
        return

    for plugin in plugins:
        if Path(plugin).is_file():
            _add_to_local_store_from_uri(
                plugins_local_dir,
                Path(plugin).resolve().as_uri(),
                overwrite,
            )
            added_from_file_or_uri = True
        elif urllib.parse.urlparse(plugin).scheme != "":
            _add_to_local_store_from_uri(plugins_local_dir, plugin, overwrite)
            added_from_file_or_uri = True
        else:
            specs_to_search_in_s3.append(PluginSpec.make_from_string(plugin))
    if versions:
        specs_to_search_in_s3.extend(
            PluginSpecs.make_from_version_dict(
                lib.read_toml(Path(versions).expanduser())
            )
        )
    if latest_existing:
        specs_to_search_in_s3.extend(
            PluginSpecs.make_from_plugininfos(PluginInfos.make_from_encapsia(host))
        )
    if specs_to_search_in_s3:
        s3_versions = PluginInfos.make_from_s3_buckets(plugins_s3_buckets)
        not_found = []
        for spec in specs_to_search_in_s3:
            if (pi := s3_versions.latest_version_matching_spec(spec)) is not None:
                to_download_from_s3.append(pi)
            else:
                not_found.append(spec)
        if not_found:
            lib.log_error(
                "Some plugins could not be found in S3: {}".format(
                    ", ".join(str(s) for s in not_found)
                ),
                abort=True,
            )
    _download_plugins_from_s3(
        to_download_from_s3, plugins_local_dir, overwrite, added_from_file_or_uri
    )


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
    """Print information about plugins in local store.

    By default, only includes latest versions.
    """
    plugins_local_dir = obj["plugins_local_dir"]
    plugin_infos = PluginInfos.make_from_local_store(plugins_local_dir)
    if not all_versions:
        plugin_infos = plugin_infos.filter_to_latest()
    if plugins:
        plugin_infos = PluginSpecs.make_from_spec_strings(plugins).filter(plugin_infos)

    def _read_description(pi):
        filename = plugins_local_dir / pi.get_filename()
        try:
            with lib.open_targz_member(filename, "plugin.toml") as f:
                return lib.read_toml(TextIOWrapper(f))["description"]
        except SyntaxError:
            lib.log_error(f"Malformed? Unable to read: {filename}")
            return "N/A"

    if long_format:
        info = (
            [pi.name_and_variant(), pi.formatted_version(), _read_description(pi)]
            for pi in sorted(plugin_infos)
        )
        lib.log(tabulate(info, headers=["name*", "version**", "description"]))
    else:
        info = (
            [pi.name_and_variant(), pi.formatted_version()]
            for pi in sorted(plugin_infos)
        )
        lib.log(tabulate(info, headers=["name*", "version**"]))
    _log_message_explaining_headers()
