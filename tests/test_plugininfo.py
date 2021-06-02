import itertools
import operator
from io import StringIO

import pytest
import semver
import toml

from encapsia_cli.plugininfo import PluginInfo, PluginInfos, PluginSpec, PluginSpecs

# Note: these need to be both extended (in coverage) and reduced (in test data duplication).


@pytest.fixture(
    scope="module",
    params=[
        operator.eq,
        operator.ne,
        operator.lt,
        operator.le,
        operator.gt,
        operator.ge,
    ],
)
def comparison(request):
    return request.param


@pytest.fixture(
    scope="module",
    params=[
        ("alpha", "", "1.2.3"),
        ("alpha", "beta", "1.2.3"),
    ],
)
def name_variant_version(request):
    return request.param


@pytest.fixture(scope="module")
def example_filename(name_variant_version):
    name, variant, version = name_variant_version
    if variant:
        filename = f"plugin-{name}-variant-{variant}-{version}.tar.gz"
    else:
        filename = f"plugin-{name}-{version}.tar.gz"
    return filename, name, variant, version


@pytest.fixture(scope="module")
def pi_from_filename(example_filename):
    filename, name, variant, version = example_filename
    return PluginInfo.make_from_filename(filename), filename, name, variant, version


@pytest.fixture
def name_variant_version_list():
    # using name, variant, version for natural sorting
    # can't use None (easily) to be able to sort the tuples,
    # so using "" equivalently for no variant
    return [
        ("foo", "", "2.0.0"),
        ("bar", "", "1.0.0"),
        ("foo", "trial", "1.0.0"),
        ("foo", "", "1.0.0"),
        ("bar", "trial", "1.0.0"),
        ("foo", "", "1.1.0"),
        ("foo", "zzz", "1.0.0"),
    ]


@pytest.fixture
def versions_file():
    return StringIO(
        """\
first = "1.0.0"
second = {version="2.0.0-1", variant="not_quite"}
[third]
version = "2.0.0"
exact = false
"""
    )


@pytest.fixture
def plugininfo_list(name_variant_version_list):
    return [
        PluginInfo.make_from_name_variant_version(name, variant, version)
        for name, variant, version in name_variant_version_list
    ]


@pytest.fixture
def presorted_plugininfo_list(name_variant_version_list):
    return [
        PluginInfo.make_from_name_variant_version(name, variant, version)
        for name, variant, version in sorted(name_variant_version_list)
    ]


class TestPluginInfo:
    @pytest.mark.parametrize(
        "filename,expected",
        [
            # without variant
            ("plugin-foo-1.2.3.tar.gz", ("foo", None, "1.2.3")),
            ("plugin-foo-1.2.3-4.tar.gz", ("foo", None, "1.2.3-4")),
            ("plugin-foo-1.2.3.4.tar.gz", ("foo", None, "1.2.3.4")),
            ("plugin-foo-1.2.3dev4.tar.gz", ("foo", None, "1.2.3dev4")),
            ("plugin-foo_bar-1.2.3.tar.gz", ("foo_bar", None, "1.2.3")),
            ("plugin-foo_bar2-1.2.3.tar.gz", ("foo_bar2", None, "1.2.3")),
            # wrong versions, still parsed
            ("plugin-foo-1.tar.gz", ("foo", None, "1")),
            ("plugin-foo-1.2.tar.gz", ("foo", None, "1.2")),
            ("plugin-foo-1.2.3-+.tar.gz", ("foo", None, "1.2.3-+")),
            ("plugin-foo-1.2.3aaa.tar.gz", ("foo", None, "1.2.3aaa")),
            # with variant
            ("plugin-foo-variant-variant-1.2.3.tar.gz", ("foo", "variant", "1.2.3")),
            (
                "plugin-foo-variant-va_ri_ant-1.2.3.tar.gz",
                ("foo", "va_ri_ant", "1.2.3"),
            ),
            (
                "plugin-foo-variant-15612204_uat-1.2.3.tar.gz",
                ("foo", "15612204_uat", "1.2.3"),
            ),
            (
                "plugin-foo-variant-15612204_uat-1.2.3-4.tar.gz",
                ("foo", "15612204_uat", "1.2.3-4"),
            ),
            (
                "plugin-foo-variant-15_612_204_uat-1.2.3.4.tar.gz",
                ("foo", "15_612_204_uat", "1.2.3.4"),
            ),
            (
                "plugin-foo-variant-15612204_uat-1.2.3dev4.tar.gz",
                ("foo", "15612204_uat", "1.2.3dev4"),
            ),
        ],
    )
    def test_get_name_variant_version_from_filename(self, filename, expected):
        assert PluginInfo.get_name_variant_version_from_filename(filename) == expected

    @pytest.mark.parametrize(
        "filename",
        [
            "foo",
            "foo-1.2.3.tar.gz" "plugin-foo",
            "plugin-foo.tar.gz",
            "plugin-foo-1.2.3tar.gz",
            "plugin-fo,o-1.2.3.tar.gz",
            "plugin-foo-variant-1.2.3.tar.gz",
            "plugin-foo-va.ri.ant.1.2.3.tar.gz",
            "plugin-foo-variantmyvariant-1.2.3.tar.gz",
            "plugin-foo-variant-myvariant1.2.3.tar.gz",
            "plugin--foo-1.2.3.tar.gz",
            "plugin-foo--1.2.3.tar.gz",
            "plugin-foo--variant-myvariant-1.2.3.tar.gz",
            "plugin-foo-variant--myvariant-1.2.3.tar.gz",
            "plugin-foo-variant-myvariant--1.2.3.tar.gz",
        ],
    )
    def test_get_name_variant_version_from_filename_fails(self, filename):
        with pytest.raises(ValueError):
            PluginInfo.get_name_variant_version_from_filename(filename)

    @pytest.mark.parametrize(
        "version,expected",
        [
            ("1.2.3", semver.VersionInfo(major=1, minor=2, patch=3)),
            ("1.2.3-4", semver.VersionInfo(major=1, minor=2, patch=3, prerelease=4)),
            ("1.2.3", semver.VersionInfo(major=1, minor=2, patch=3)),
            ("1.2.3", semver.VersionInfo(major=1, minor=2, patch=3)),
            ("1.2.3", semver.VersionInfo(major=1, minor=2, patch=3)),
            # No parse
            ("1", semver.VersionInfo(major=0)),
            ("1.2", semver.VersionInfo(major=0)),
            ("1.2.3-+", semver.VersionInfo(major=0)),
            ("123aaa", semver.VersionInfo(major=0)),
        ],
    )
    def test_parse_version(self, version, expected):
        assert PluginInfo._parse_version(version) == expected

    @pytest.mark.parametrize(
        "nvv1,nvv2",
        # poor person's QuickCheck / hypotesis
        itertools.product(
            itertools.product(
                ("name_aaa", "name_bbb"),
                ("var_aaa", "var_bbb"),
                ("1.0.0", "2.0.0", "1.0.1-4"),
            ),
            repeat=2,
        ),
    )
    def test_comparison(self, comparison, nvv1, nvv2):
        pi1 = PluginInfo.make_from_name_variant_version(*nvv1)
        pi2 = PluginInfo.make_from_name_variant_version(*nvv2)
        t1 = (nvv1[0], nvv1[1], semver.VersionInfo.parse(nvv1[2]))
        t2 = (nvv2[0], nvv2[1], semver.VersionInfo.parse(nvv2[2]))
        assert comparison(pi1, pi2) is comparison(t1, t2)

    def test_make_from_filename(self, pi_from_filename):
        """Quickly assert it works. Heavy lifting done in get_name_variant_version_from_filename."""
        pi, filename, name, variant, version = pi_from_filename
        assert pi.name == name
        assert pi.variant == variant
        assert pi.semver == semver.VersionInfo.parse(version)
        assert pi == PluginInfo.make_from_name_variant_version(name, variant, version)
        assert pi.get_s3_bucket() is None
        assert pi.get_s3_path() is None
        assert pi.get_s3_name() == filename

    def test_make_from_s3(self, example_filename):
        filename, name, variant, version = example_filename
        pi = PluginInfo.make_from_s3("bucket", f"s3_path/{filename}")
        assert pi.name == name
        assert pi.variant == variant
        assert pi.semver == semver.VersionInfo.parse(version)
        assert pi.get_s3_bucket() == "bucket"
        assert pi.get_s3_path() == "s3_path"
        assert pi.get_s3_name() == f"s3_path/{filename}"

    def test_dunder_str(self, pi_from_filename):
        pi, filename, name, variant, version = pi_from_filename
        assert str(pi) == filename


class TestPluginInfos:
    def test_plugininfos_iterable(self, plugininfo_list):
        pis = PluginInfos(plugininfo_list)
        assert list(pis) == plugininfo_list

    def test_plugininfos_sorted(self, plugininfo_list, presorted_plugininfo_list):
        pis = PluginInfos(plugininfo_list)
        sorted_pis = sorted(pis)
        assert sorted_pis == presorted_plugininfo_list

    def test_latest(self, plugininfo_list):
        pis = PluginInfos(plugininfo_list)
        assert pis.latest() == PluginInfo.make_from_name_variant_version(
            "foo", "zzz", "1.0.0"
        )

    def test_filter_to_latest(self, plugininfo_list):
        pis = PluginInfos(plugininfo_list)
        expected = [
            PluginInfo.make_from_name_variant_version(*nvv)
            for nvv in [
                ("bar", "", "1.0.0"),
                ("bar", "trial", "1.0.0"),
                ("foo", "", "2.0.0"),
                ("foo", "trial", "1.0.0"),
                ("foo", "zzz", "1.0.0"),
            ]
        ]
        assert sorted(pis.filter_to_latest()) == expected

    @pytest.mark.parametrize(
        "spec,expected_nvv",
        [
            ("foo-1", ("foo", "", "1.1.0")),
            ("foo-variant-trial-1", ("foo", "trial", "1.0.0")),
            ("bar-1", ("bar", "", "1.0.0")),
        ],
    )
    def test_latest_version_matching_spec(self, plugininfo_list, spec, expected_nvv):
        pis = PluginInfos(plugininfo_list)
        expected = PluginInfo.make_from_name_variant_version(*expected_nvv)
        assert pis.latest_version_matching_spec(spec) == expected

    @pytest.mark.parametrize("spec", ["foo-3", "zuzu"])
    def test_latest_version_matching_spec_none(self, plugininfo_list, spec):
        pis = PluginInfos(plugininfo_list)
        assert pis.latest_version_matching_spec(spec) is None


class TestPluginSpec:
    @pytest.mark.parametrize(
        "spec,expected",
        [
            (
                "foo",
                [
                    ("foo", "", "1.0.0"),
                    ("foo", "", "1.1.0"),
                    ("foo", "", "2.0.0"),
                ],
            ),
            (
                "foo-variant-zzz",
                [
                    ("foo", "zzz", "1.0.0"),
                ],
            ),
            (
                "foo-1",
                [
                    ("foo", "", "1.0.0"),
                    ("foo", "", "1.1.0"),
                ],
            ),
            (
                "foo-1.1",
                [
                    ("foo", "", "1.1.0"),
                ],
            ),
            (
                "bar-ANY",
                [
                    ("bar", "", "1.0.0"),
                    ("bar", "trial", "1.0.0"),
                ],
            ),
        ],
    )
    def test_filter(self, plugininfo_list, spec, expected):
        pis = PluginInfos(plugininfo_list)
        expected = [PluginInfo.make_from_name_variant_version(*nvv) for nvv in expected]
        assert sorted(PluginSpec.make_from_string(spec).filter(pis)) == expected


class TestPluginSpecs:
    def test_make_from_version_dict(self, versions_file):
        versions = toml.load(versions_file)
        specs = PluginSpecs.make_from_version_dict(versions)
        specs_list = list(specs)
        assert len(specs_list) == 3

        assert specs_list[0].name == "first"
        assert specs_list[0].variant == ""
        assert specs_list[0].version_prefix == "1.0.0"
        assert specs_list[0].exact_match is True

        assert specs_list[1].name == "second"
        assert specs_list[1].variant == "not_quite"
        assert specs_list[1].version_prefix == "2.0.0-1"
        assert specs_list[1].exact_match is True

        assert specs_list[2].name == "third"
        assert specs_list[2].variant == ""
        assert specs_list[2].version_prefix == "2.0.0"
        assert specs_list[2].exact_match is False

    def test_as_version_dict(self, versions_file):
        versions = toml.load(versions_file)
        specs = PluginSpecs.make_from_version_dict(versions)
        assert specs.as_version_dict() == versions

    def test_filter(self, plugininfo_list):
        pis = PluginInfos(plugininfo_list)
        expected = [
            PluginInfo.make_from_name_variant_version(*nvv)
            for nvv in [
                ("bar", "", "1.0.0"),
                ("bar", "trial", "1.0.0"),
                ("foo", "", "2.0.0"),
            ]
        ]
        assert sorted(PluginSpecs(["foo-2", "bar-ANY"]).filter(pis)) == expected
