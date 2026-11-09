"""Public-source HTTP: validate and pin the address at connection time.

Unlike a preflight DNS check followed by a second resolver call for the host,
this connects to the exact validated numeric address. TLS still authenticates
the original hostname. Redirects use the same adapter and policy.
"""
import ipaddress
import os
import socket
from urllib.parse import urlsplit
import requests
from requests.adapters import HTTPAdapter
from urllib3.connection import HTTPConnection, HTTPSConnection
from urllib3.connectionpool import HTTPConnectionPool, HTTPSConnectionPool
from urllib3.exceptions import NewConnectionError
from urllib3.util.connection import create_connection


def private_origin_allowed(scheme, host, port):
    for value in os.environ.get("ROMARR_ACQUISITION_PRIVATE_ORIGINS", "").split(","):
        try:
            origin = urlsplit(value.strip())
            if (origin.scheme, origin.hostname, origin.port or (443 if origin.scheme == "https" else 80)) == (scheme, host, port):
                return True
        except ValueError:
            continue
    return False


def public_addresses(host, port, scheme="https"):
    infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    addresses = list(dict.fromkeys(info[4][0] for info in infos))
    if not addresses:
        raise OSError("download host has no addresses")
    if not private_origin_allowed(scheme, host, port):
        for value in addresses:
            address = ipaddress.ip_address(value)
            translated = []
            if isinstance(address, ipaddress.IPv6Address):
                translated = [address.ipv4_mapped, address.sixtofour]
                if address.teredo:
                    translated.extend(address.teredo)
                if address in ipaddress.ip_network("64:ff9b::/96"):
                    translated.append(ipaddress.IPv4Address(int(address) & 0xffffffff))
            if (not address.is_global or address.is_multicast
                    or any(ip is not None and (not ip.is_global or ip.is_multicast) for ip in translated)):
                raise OSError("untrusted download cannot access a non-public address")
    return addresses


class _PinnedConnection:
    scheme = "http"

    def _new_conn(self):
        try:
            addresses = public_addresses(self.host, self.port, self.scheme)
            last = None
            for address in addresses:
                try:
                    return create_connection((address, self.port), self.timeout,
                        source_address=self.source_address, socket_options=self.socket_options)
                except OSError as exc:
                    last = exc
            raise last or OSError("connection failed")
        except (OSError, ValueError) as exc:
            raise NewConnectionError(self, "public-source connection refused") from exc


class PublicHTTPConnection(_PinnedConnection, HTTPConnection):
    pass


class PublicHTTPSConnection(_PinnedConnection, HTTPSConnection):
    scheme = "https"


class PublicHTTPPool(HTTPConnectionPool):
    ConnectionCls = PublicHTTPConnection


class PublicHTTPSPool(HTTPSConnectionPool):
    ConnectionCls = PublicHTTPSConnection


class PublicAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        super().init_poolmanager(*args, **kwargs)
        self.poolmanager.pool_classes_by_scheme = {"http": PublicHTTPPool, "https": PublicHTTPSPool}

    def send(self, request, **kwargs):
        parts = urlsplit(request.url)
        if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username is not None or parts.password is not None:
            raise requests.exceptions.InvalidURL("invalid public-source URL")
        if any((kwargs.get("proxies") or {}).values()):
            raise requests.exceptions.InvalidURL("public acquisition cannot bypass address policy through a proxy")
        return super().send(request, **kwargs)


class PublicSession(requests.Session):
    def __init__(self):
        super().__init__()
        self.trust_env = False
        self.headers["Accept-Encoding"] = "identity"
        self.mount("http://", PublicAdapter())
        self.mount("https://", PublicAdapter())
