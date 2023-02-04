from __future__ import annotations

import collections
import re
import typing as T
from dataclasses import dataclass
from functools import total_ordering
from pathlib import Path
from warnings import warn

import arrow
import semver

from encapsia_cli import lib, s3


ALLOWED_PLUGIN_NAME = "[a-z][a-z0-9_]*"
ALLOWED_VERSION = "[0-9][a-zA-Z0-9.+-]*"
ALLOWED_VARIANT = "[a-zA-Z0-9_]+"

T_VersionDict = T.Union[T.Dict[str, str], T.Dict[str, T.Dict[str, T.Any]]]
T_AnyVariant = T.NewType("T_AnyVariant", object)
T_Variant = T.Union[str, T_AnyVariant]


class TooManyVariantTagsError(Exception):

    pass


class InvalidSpecError(Exception):

    pass


def _format_datetime(dt):
    return arrow.get(dt).strftime("%a %d %b %Y %H:%M:%S")
    # In Python 3.7 and beyond we could do the following. But we want to support Python 3.6.
    # return datetime.datetime.fromisoformat(dt).strftime("%a %d %b %Y %H:%M:%S")


def get_variant_from_tags(tags):
    variant_tags = [t for t in tags if t.startswith("variant=")]
    if len(variant_tags) == 0:
        variant = None
    elif len(variant_tags) == 1:
        variant = variant_tags[0].split("=", 1)[1]
    else:
        raise TooManyVariantTagsError("Found more than one variant tags.")
    return variant


@total_ordering
class PluginInfo:
    """Parse and use plugin information like name, variant and version."""

    PLUGIN_FILENAME_REGEX: T.ClassVar[re.Pattern] = re.compile(
        rf"^.*plugin-({ALLOWED_PLUGIN_NAME})(?:-variant-({ALLOWED_VARIANT}))?-({ALLOWED_VERSION})\.tar\.gz$"
    )
    FOUR_DIGIT_VERSION_REGEX: T.ClassVar[re.Pattern] = re.compile(
        r"([0-9]+)\.([0-9]+)\.([0-9]+)\.([0-9]+)"
    )
    DEV_VERSION_REGEX: T.ClassVar[re.Pattern] = re.compile(
        r"([0-9]+)\.([0-9]+)\.([0-9]+)dev([0-9]+)"
    )

    def __init__(
        self,
        s3_bucket: T.Optional[str],
        s3_path: T.Optional[str],
        name: str,
        version: str,
        variant: T.Optional[str],
    ):
        """Private constructor. Use make_* factory methods instead."""
        self.s3_bucket = s3_bucket
        self.s3_path = s3_path
        self.name = name
        self.version = version
        self.semver = self._parse_version(self.version)
        self.variant = "" if variant is None else variant
        self.extras: T.Dict[str, str] = {}

    def __eq__(self, other) -> bool:
        if isinstance(other, PluginInfo):
            return (
                self.name == other.name
                and self.semver == other.semver
                and self.variant == other.variant
            )
        return NotImplemented

    def __lt__(self, other) -> bool:
        if isinstance(other, PluginInfo):
            self_values = (self.name, self.variant, self.semver)
            other_values = (other.name, other.variant, other.semver)
            return self_values < other_values
        return NotImplemented

    def __str__(self):
        return self.get_filename()

    def __repr__(self):
        return (
            f"PluginInfo({self.s3_bucket!r}, {self.s3_path!r}, "
            f"{self.name!r}, {self.variant!r}, {self.version!r})"
        )

    @classmethod
    def get_name_variant_version_from_filename(cls, filename):
        m = cls.PLUGIN_FILENAME_REGEX.match(str(filename))
        if m is None:
            raise ValueError(f"Unable to parse: {filename}")
        return m.group(1), m.group(2), m.group(3)  # (name, variant, version)

    @classmethod
    def make_from_name_version(cls, name, version) -> PluginInfo:
        warn(
            "Use make_from_name_variant_version() instead.",
            category=DeprecationWarning,
        )
        return cls(None, None, name, version, variant=None)

    @classmethod
    def make_from_name_variant_version(cls, name, variant, version) -> PluginInfo:
        return cls(None, None, name, version, variant=variant)

    @classmethod
    def make_from_filename(cls, filename: T.Union[str, Path]) -> PluginInfo:
        name, variant, version = cls.get_name_variant_version_from_filename(filename)
        return cls(None, None, name, version, variant=variant)

    @classmethod
    def make_from_s3(cls, s3_bucket, s3_path):
        name, variant, version = cls.get_name_variant_version_from_filename(s3_path)
        s3_path_without_filename = "/".join(s3_path.split("/")[:-1])
        return cls(s3_bucket, s3_path_without_filename, name, version, variant=variant)

    @classmethod
    def make_from_spec(cls, spec: PluginSpec) -> PluginInfo:
        if spec.variant is PluginSpec.ANY_VARIANT:
            raise ValueError("Cannot make PluginInfo from PluginSpec with ANY variant")
        return cls(None, None, spec.name, spec.version_prefix, str(spec.variant))

    @classmethod
    def _parse_version(cls, version):
        # Consider a 4th digit to be a SemVer pre-release.
        # E.g. 1.2.3.4 is 1.2.3-4
        m = cls.FOUR_DIGIT_VERSION_REGEX.match(version)
        if m:
            major, minor, patch, prerelease = m.groups()
            return semver.VersionInfo(
                major=major, minor=minor, patch=patch, prerelease=prerelease
            )
        # Consider a "dev" build to be a SemVer pre-release.
        # E.g. 0.0.209dev12 is 0.0.209-12
        m = cls.DEV_VERSION_REGEX.match(version)
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

    def formatted_version(self) -> str:
        version, semver = self.version, str(self.semver)
        return semver if semver == version else f"{version} ({semver})"

    def name_and_variant(self) -> str:
        variant_str = f" [{self.variant}]" if self.variant else ""
        return f"{self.name}{variant_str}"

    def get_filename(self) -> str:
        variant = f"-variant-{self.variant}" if self.variant else ""
        return f"plugin-{self.name}{variant}-{self.version}.tar.gz"

    def get_s3_bucket(self) -> T.Optional[str]:
        return self.s3_bucket

    def get_s3_path(self) -> T.Optional[str]:
        return self.s3_path

    def get_s3_name(self) -> str:
        if self.s3_path:
            return f"{self.s3_path}/{self.get_filename()}"
        else:
            # In the unlikely scenario that plugin files are stored flat in a bucket.
            return self.get_filename()

    @classmethod
    def looks_like_path_to_plugin(cls, spec_string: str) -> bool:
        return cls.PLUGIN_FILENAME_REGEX.match(spec_string) is not None


class PluginInfos:
    """Container for one or more PluginInfo."""

    def __init__(self, plugin_infos: T.Iterable[PluginInfo]):
        self.pis = list(plugin_infos)

    def __iter__(self):
        return iter(self.pis)

    def __repr__(self):
        return f"PluginInfos({self.pis!r})"

    @staticmethod
    def make_from_local_store(plugins_local_dir):
        result = plugins_local_dir.glob("plugin-*-*.tar.gz")
        pis = []
        for p in result:
            try:
                pis.append(PluginInfo.make_from_filename(p))
            except ValueError as e:
                lib.log_error(str(e))
        return PluginInfos(pis)

    @staticmethod
    def make_from_s3_buckets(plugins_s3_buckets):
        try:
            return PluginInfos(
                [
                    PluginInfo.make_from_s3(bucket, x["Key"])
                    for bucket, x in s3.list_buckets(plugins_s3_buckets)
                    if x["Key"].endswith(".tar.gz")
                ]
            )
        except s3.S3Error as e:
            lib.log_error(str(e), abort=True)
            return None  # Never reached, but keep linters happy

    @staticmethod
    def make_from_encapsia(host: str, bad_plugins_bin=None) -> PluginInfos:
        api = lib.get_api(host=host)
        raw_info = api.run_view(
            "pluginsmanager",
            "plugins",
        )
        pis = []
        for i in raw_info:

            # keys should be present and non-null
            MANDATORY_ENTRIES = ("name", "version")
            missing_mandatory_entries = [
                key for key in MANDATORY_ENTRIES if i.get(key) is None
            ]
            if missing_mandatory_entries:
                lib.log_error(
                    f"Invalid plugin info!\nMissing mandatory entries {missing_mandatory_entries} in {i}"
                )
                if bad_plugins_bin is not None:
                    bad_plugins_bin.add(i.get("name"))
                continue

            # keys should be present and non-null
            IMPORTANT_ENTRIES = ("manifest", "when")
            missing_important_entries = [
                key for key in IMPORTANT_ENTRIES if i.get(key) is None
            ]
            if missing_important_entries:
                lib.log_error(
                    f"Missing important information {missing_important_entries} for plugin {i}"
                )
                if bad_plugins_bin is not None:
                    bad_plugins_bin.add(i.get("name"))

            manifest = i.get("manifest")
            tags = manifest.get("tags") if hasattr(manifest, "get") else None
            if not isinstance(tags, list):
                tags = []
            try:
                variant = get_variant_from_tags(tags)
            except TooManyVariantTagsError as e:
                lib.log_error(f"Error in {i['name']} tag list: {e}")
                if bad_plugins_bin is not None:
                    bad_plugins_bin.add(i.get("name"))
            pi = PluginInfo.make_from_name_variant_version(
                i["name"], variant, i["version"]
            )
            pi.extras.update(
                {
                    "description": i.get("description"),
                    "installed": (
                        _format_datetime(i.get("when")) if "when" in i else "Unknown"
                    ),
                    "plugin-tags": ", ".join(sorted(tags)),
                }
            )
            pis.append(pi)
        return PluginInfos(pis)

    def latest(self) -> T.Optional[PluginInfo]:
        """Returns greatest PluginInfo with in sort order (name, variant, version).

        Careful: this has little value when comparing plugins with different name and
        variant!
        """
        return max(self.pis, default=None)

    def filter_to_latest(self) -> PluginInfos:
        groupped_pis = collections.defaultdict(list)
        for pi in self.pis:
            groupped_pis[(pi.name, pi.variant)].append(pi)
        return PluginInfos(
            p
            for pis in groupped_pis.values()
            if (p := PluginInfos(pis).latest()) is not None
        )

    def latest_version_matching_spec(self, spec) -> T.Optional[PluginInfo]:
        return PluginSpec.make_from_spec_or_string(spec).filter(self).latest()


@dataclass
class PluginSpec:
    name: str
    variant: T_Variant
    version_prefix: str = ""
    exact_match: bool = False

    PLUGIN_SPEC_NVV_REGEX: T.ClassVar[re.Pattern] = re.compile(
        rf"^({ALLOWED_PLUGIN_NAME})(?:-variant-({ALLOWED_VARIANT}))?(?:-({ALLOWED_VERSION}))?$"
    )
    PLUGIN_SPEC_ANY_REGEX: T.ClassVar[re.Pattern] = re.compile(
        rf"^({ALLOWED_PLUGIN_NAME})(?i:-ANY)(?:-({ALLOWED_VERSION}))?$"
    )
    ANY_VARIANT: T.ClassVar[T_Variant] = T_AnyVariant(object())

    def __post_init__(self):
        if self.variant is None:
            self.variant = ""
        if self.version_prefix is None:
            self.version_prefix = ""

    def __str__(self):
        if self.variant is self.ANY_VARIANT:
            variant = "-ANY"
        elif self.variant:
            variant = f"-variant-{self.variant}"
        else:
            variant = ""

        if self.version_prefix:
            version = f"-{self.version_prefix}"
        else:
            version = ""

        if self.exact_match:
            exact = " [exact]"
        else:
            exact = ""

        return f"{self.name}{variant}{version}{exact}"

    @classmethod
    def _split_spec_string(cls, spec_string: str) -> T.Tuple[str, T_Variant, str]:
        """Split `spec_string` into components. A spec string can take three forms:
        * <plugin_name>
        * <plugin_name>-ANY  ("ANY" is case insensitive)
        * <plugin_name>-<version_prefix>
        * <plugin_name>-variant-<variant_name>-<version_prefix>
        """
        m = cls.PLUGIN_SPEC_NVV_REGEX.match(spec_string)
        if m:
            return m.group(1), m.group(2), m.group(3)  # name, variant, version_prefix
        m = cls.PLUGIN_SPEC_ANY_REGEX.match(spec_string)
        if m:
            return m.group(1), cls.ANY_VARIANT, m.group(2)  # name, ANY, version
        raise InvalidSpecError(f"Spec string {spec_string} is invalid.")

    @classmethod
    def make_from_string(
        cls, spec_string: str, exact_match: bool = False
    ) -> PluginSpec:
        return cls(*cls._split_spec_string(spec_string), exact_match=exact_match)

    @classmethod
    def make_from_spec_or_string(
        cls, spec_or_string: T.Union[str, PluginSpec]
    ) -> PluginSpec:
        if isinstance(spec_or_string, str):
            instance = cls.make_from_string(spec_or_string)
        elif isinstance(spec_or_string, PluginSpec):
            instance = cls(
                spec_or_string.name,
                spec_or_string.variant,
                spec_or_string.version_prefix,
                exact_match=spec_or_string.exact_match,
            )
        else:
            raise TypeError(f"Unknown spec type {type(spec_or_string)}")
        return instance

    @classmethod
    def make_from_plugininfo(
        cls,
        plugininfo: PluginInfo,
        exact_match: bool = True,
    ) -> PluginSpec:
        return cls(
            plugininfo.name,
            plugininfo.variant,
            plugininfo.version,
            exact_match=exact_match,
        )

    def _variant_match(self, pi: PluginInfo) -> bool:
        return self.variant is self.ANY_VARIANT or self.variant == pi.variant

    def _version_match(self, pi: PluginInfo) -> bool:
        return (
            self.version_prefix == pi.version
            if self.exact_match
            else pi.version.startswith(self.version_prefix)
        )

    def match(self, pi: PluginInfo) -> bool:
        return (
            self.name == pi.name and self._variant_match(pi) and self._version_match(pi)
        )

    def filter(self, plugin_infos: PluginInfos) -> PluginInfos:
        return PluginInfos(filter(self.match, plugin_infos))

    def as_version_dict(self) -> T_VersionDict:
        version_dict: T_VersionDict
        if self.variant:
            if self.exact_match:
                version_dict = {
                    self.name: {"version": self.version_prefix, "variant": self.variant}
                }
            else:
                version_dict = {
                    self.name: {
                        "version": self.version_prefix,
                        "variant": self.variant,
                        "exact": False,
                    }
                }
        elif self.exact_match:
            version_dict = {self.name: self.version_prefix}
        else:
            version_dict = {self.name: {"version": self.version_prefix, "exact": False}}
        return version_dict


class PluginSpecs:
    def __init__(self, specs: T.Iterable[PluginSpec]):
        self.specs = [PluginSpec.make_from_spec_or_string(s) for s in specs]

    def __iter__(self):
        return iter(self.specs)

    def __repr__(self):
        return f"PluginSpecs({self.specs!r})"

    @classmethod
    def make_from_version_dict(cls, versions: dict) -> PluginSpecs:
        specs = []
        for name, definition in versions.items():
            if isinstance(definition, str):
                version, variant, exact = definition, "", True
            elif isinstance(definition, dict):
                version = definition["version"]
                variant = definition.get("variant", "")
                exact = definition.get("exact", True)
            else:
                raise TypeError(f"Unknown definition type {type(definition)}")
            specs.append(PluginSpec(name, variant, version, exact_match=exact))
        return cls(specs)

    @classmethod
    def make_from_spec_strings(cls, spec_strings: T.Iterable[str]) -> PluginSpecs:
        return cls(
            PluginSpec.make_from_string(spec_string) for spec_string in spec_strings
        )

    @classmethod
    def make_from_plugininfos(cls, plugin_infos: PluginInfos) -> PluginSpecs:
        return cls([PluginSpec.make_from_plugininfo(pi) for pi in plugin_infos])

    def as_version_dict(self) -> T_VersionDict:
        return {k: v for s in self for k, v in s.as_version_dict().items()}

    def as_plugininfos(self) -> PluginInfos:
        return PluginInfos(
            [
                PluginInfo.make_from_name_variant_version(
                    s.name, s.variant, s.version_prefix
                )
                for s in self
            ]
        )

    def match_any(self, plugin_info: PluginInfo) -> bool:
        return any(s.match(plugin_info) for s in self)

    def filter(self, plugin_infos: PluginInfos) -> PluginInfos:
        return PluginInfos(filter(self.match_any, plugin_infos))
