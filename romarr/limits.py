"""Budgets enforced against actual bytes, including misleading archive sizes."""
import os
import struct
import time


def limit(name, default):
    value = int(os.environ.get(name, default))
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


class Budget:
    def __init__(self, maximum=None):
        self.maximum = maximum or limit("ROMARR_MAX_EXPANDED_BYTES", 64 << 30)
        self.member = limit("ROMARR_MAX_MEMBER_BYTES", 16 << 30)
        self.remaining = self.maximum
        self.deadline = time.monotonic() + limit("ROMARR_TRANSFER_SECONDS", 600)

    def copy(self, source, target, *, maximum=None):
        total = 0
        cap = min(self.member, maximum if maximum is not None else self.member)
        while True:
            if time.monotonic() > self.deadline:
                raise OSError("transfer exceeded its time budget")
            chunk = source.read(min(1 << 20, cap - total + 1, self.remaining + 1))
            if not chunk:
                return total
            total += len(chunk)
            self.remaining -= len(chunk)
            if total > cap or self.remaining < 0:
                raise OSError("transfer exceeded its byte budget")
            try:
                space = os.fstatvfs(target.fileno())
            except (AttributeError, OSError, ValueError):
                space = None
            if space is not None and space.f_bavail * space.f_frsize < len(chunk) + limit("ROMARR_MIN_FREE_BYTES", 64 << 20):
                raise OSError("transfer would exhaust free disk space")
            target.write(chunk)


def preflight_zip(path):
    """Bound central-directory allocation before ZipFile parses it, including ZIP64."""
    with open(path, "rb") as source:
        source.seek(0, 2)
        size = source.tell()
        source.seek(max(0, size - 65557))
        tail = source.read(65557)
        index = tail.rfind(b"PK\x05\x06")
        if index < 0 or len(tail) - index < 22:
            raise ValueError("invalid ZIP directory")
        end = struct.unpack("<4s4H2LH", tail[index:index+22])
        if index + 22 + end[-1] != len(tail):
            raise ValueError("invalid ZIP directory trailer")
        count, central_bytes = end[4], end[5]
        if count == 0xffff or central_bytes == 0xffffffff:
            absolute = max(0, size - 65557) + index
            source.seek(absolute - 20)
            locator = struct.unpack("<4sLQL", source.read(20))
            if locator[0] != b"PK\x06\x07" or locator[2] > absolute - 56:
                raise ValueError("invalid ZIP64 locator")
            source.seek(locator[2])
            record = struct.unpack("<4sQ2H2L4Q", source.read(56))
            if record[0] != b"PK\x06\x06":
                raise ValueError("invalid ZIP64 directory")
            count, central_bytes = record[7], record[8]
        if count > limit("ROMARR_MAX_ARCHIVE_FILES", 10000) or central_bytes > (16 << 20):
            raise ValueError("archive directory exceeds its budget")
