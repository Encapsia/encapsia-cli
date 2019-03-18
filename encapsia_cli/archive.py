"""Create, restore from, and migrate Long Term Storage Archive representations."""
import click

from encapsia_cli import lib

main = lib.make_main(__doc__)


"""


get / to retrieve result.version


/assertions/0000....json
/blobs/<uuid>. raw and meta??
/encapsia.toml -> manifest
    version
    updated
    hwm ?
    n blobs?
    checksum?

encapsia archive --host foo upload <dir>
encapsia archive --host foo download <dir>

archive will only work if version in manifest matches that of the server.archive


encapsia migrate versions -> list available version-version migrations
encapsia migrate <src> <dest> --to-version <...>
encapsia

"""


@main.command()
@click.pass_obj
def show(obj):
    """Show entire configuration."""
    api = lib.get_api(**obj)
    lib.pretty_print(api.get_all_config(), "json")