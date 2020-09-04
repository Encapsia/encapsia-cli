"""Selection of example functions showing which arguments work and which don't work."""
import json
import os
from contextlib import closing
from tempfile import mkstemp

from encapsia_api import EncapsiaApi


def _mkstemp_for_plugins(prefix="iceplugin"):
    """Return filename for a tempory file specific to ICE."""
    fd, path = mkstemp(dir="/tmp/ice", prefix=prefix)
    os.chmod(path, 0o770)
    return fd, path


def test_function(name=None, meta=None):
    """The most standard form of function."""
    return f"hello {name}"


def test_function_with_meta_as_fixed_arg(meta):
    """This form is ok."""
    import time

    time.sleep(30)
    return meta


def test_function_with_fixed_args(meta, name):
    """This form is ok, but will fail if `name` is not provided."""
    return f"hello {name}"


def test_function_with_any_args(**kwargs):
    """This form is ok and will accept any arguments."""
    return kwargs


def test_function_with_single_arg_and_no_meta(name):
    """This cannot be called because meta is always passed."""
    return f"hello {name}"


def test_function_with_single_kwarg(name=None):
    """This cannot be called because meta is always passed."""
    return f"hello {name}"


def test_function_with_no_args():
    """This cannot be called because meta is always passed."""
    return "look, no args!"


def test_function_for_posted_data(
    posted_data_filename=None, posted_data_type=None, meta=None
):
    """Show how to use an uploaded file."""
    if posted_data_type == "application/json":
        # Pass back the JSON as JSON.
        with open(posted_data_filename, "rt") as f:
            return json.load(f)
    elif posted_data_type == "text/plain":
        # Pass back the plain text as plain text.
        with open(posted_data_filename, "rt") as f:
            # Core will pass this back to the caller as a JSON string.
            # To actually pass back text, use the "asfile" mechanism.
            return f.read()
    else:
        # Pass back the binary data using a file (the only way).
        fd, filename = _mkstemp_for_plugins(prefix="example-task-file")
        with open(posted_data_filename, "rb") as f_read:
            with closing(os.fdopen(fd, "wb")) as f_write:
                f_write.write(f_read.read())
        return {
            "__encapsia_asfile__": True,
            "filename": filename,
            "mime_type": posted_data_type,
        }


def test_function_for_a_job(meta, name):
    """Show how a *job* task works (the result is PUT back as a joblog)."""
    # First, pretend to do some work to make a result.
    result = {
        "status": "success",  # Or "failure" or "error".
        "output": f"Hello {name}",  # Any object.
    }

    # Then put the result back on jobs, creating a joblogs entry.
    base_url = meta["url"].split("/v1/")[0]
    token = meta["token"]
    namespace = meta["namespace"]
    job_id = meta["job_id"]
    api = EncapsiaApi(base_url, token)
    api.put(["jobs", namespace, job_id], json=result)

    # NB we don't need to return anything
    return None


def test_function_returning_file_via_nginx(meta):
    """Show how to return data as file"""
    data = "the quick brown fox jumps over the lazy dog"
    fd, filename = _mkstemp_for_plugins(prefix="example-task-file")
    with closing(os.fdopen(fd, "wb")) as f:
        f.write(data.encode())
    return {
        "__encapsia_asfile__": True,
        "filename": filename,
        "mime_type": "text/plain",
        "download_as": "pangram.txt",
    }
