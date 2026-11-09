"""Atomic, durable publication of small state files."""
import json
import os
import tempfile
from pathlib import Path


class DurabilityError(OSError):
    """Publication happened, but the parent directory could not be synced."""
    committed = True


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".romarr-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            json.dump(value, out, indent=1, allow_nan=False)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temporary, path)
        if os.name == "posix":
            try:
                directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(directory)
                finally:
                    os.close(directory)
            except OSError as exc:
                raise DurabilityError("state published but directory sync failed") from exc
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
