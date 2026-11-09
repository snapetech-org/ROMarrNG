"""Descriptor-relative, transactional writes beneath an operator-chosen root."""
from contextlib import contextmanager
import os
from pathlib import Path, PurePosixPath
import secrets
import shutil
import stat


def relative_parts(name):
    text = str(name).replace("\\", "/")
    parts = text.split("/")
    if (not text or text.startswith("/") or ":" in text or "\0" in text
            or any(p in {"", ".", ".."} for p in parts)):
        raise ValueError("unsafe relative file name")
    return parts


@contextmanager
def directory_fd(path, *, create=False):
    """Walk every component with O_NOFOLLOW; keep the selected inode open."""
    if os.name != "posix" or not hasattr(os, "O_NOFOLLOW"):
        raise OSError("safe imports require descriptor-relative filesystem support")
    path = Path(os.path.abspath(path))
    fd = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[1:]:
            if create:
                try:
                    os.mkdir(part, dir_fd=fd)
                except FileExistsError:
                    pass
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        yield fd
    finally:
        os.close(fd)


@contextmanager
def parent_fd(root, destination):
    root = Path(os.path.abspath(root))
    destination = Path(os.path.abspath(destination))
    parts = relative_parts(destination.relative_to(root).as_posix())
    with directory_fd(root, create=True) as root_fd:
        fd = os.dup(root_fd)
        try:
            for part in parts[:-1]:
                try:
                    os.mkdir(part, dir_fd=fd)
                except FileExistsError:
                    pass
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = child
            yield fd, parts[-1]
        finally:
            os.close(fd)


@contextmanager
def staging(parent):
    temporary = ".romarr-stage-" + secrets.token_hex(16)
    os.mkdir(temporary, 0o700, dir_fd=parent)
    fd = os.open(temporary, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
    try:
        yield fd
    finally:
        os.close(fd)
        shutil.rmtree(fd_path(parent) / temporary)


def atomic_file(root, destination, write, *, overwrite=False):
    with parent_fd(root, destination) as (parent, name), staging(parent) as stage:
        fd = os.open("payload", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o666, dir_fd=stage)
        with os.fdopen(fd, "wb") as output:
            write(output)
            output.flush()
            os.fsync(output.fileno())
        if overwrite:
            os.replace("payload", name, src_dir_fd=stage, dst_dir_fd=parent)
        else:
            os.link("payload", name, src_dir_fd=stage, dst_dir_fd=parent,
                    follow_symlinks=False)
            os.unlink("payload", dir_fd=stage)
        os.fsync(parent)
    return Path(destination)


def fd_path(fd):
    for base in ("/proc/self/fd", "/dev/fd"):
        path = Path(base) / str(fd)
        if path.is_dir():
            return path
    raise OSError("descriptor path access unavailable")


def _rename_directory(source_fd, source, target_fd, target, flags):
    # Linux renameat2 supplies no-replace and exchange without a check/use gap.
    import ctypes
    libc = ctypes.CDLL(None, use_errno=True)
    rename = getattr(libc, "renameat2", None)
    if rename is None:
        raise OSError("atomic directory publication requires renameat2")
    if rename(source_fd, os.fsencode(source), target_fd, os.fsencode(target), flags):
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))


def atomic_directory(root, destination, write, *, overwrite=False):
    with parent_fd(root, destination) as (parent, name), staging(parent) as stage:
        os.mkdir("payload", dir_fd=stage)
        payload = os.open("payload", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=stage)
        try:
            write(fd_path(payload))
            # Flush every completed member before publishing the set.
            for current, dirs, files in os.walk(fd_path(payload), followlinks=False):
                for filename in files:
                    with open(Path(current) / filename, "rb") as member:
                        os.fsync(member.fileno())
            os.fsync(payload)
            if overwrite:
                try:
                    _rename_directory(stage, "payload", parent, name, 2)  # EXCHANGE
                except FileNotFoundError:
                    _rename_directory(stage, "payload", parent, name, 1)
            else:
                _rename_directory(stage, "payload", parent, name, 1)  # NOREPLACE
            os.fsync(parent)
        finally:
            os.close(payload)
    return Path(destination)


@contextmanager
def source_file(path):
    path = Path(path)
    with directory_fd(path.parent) as parent:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent)
        with os.fdopen(fd, "rb") as source:
            if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                raise OSError("source is not a regular file")
            yield source
