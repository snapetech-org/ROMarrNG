"""Process-lifetime network deny policy, including leaked/background work.

Installed before test collection, never undone by fixture teardown. Mocks may
replace transports deliberately; restoration always restores this guard.
"""
import ipaddress
import socket
import urllib.request
from urllib.parse import urlsplit
import requests


def check_host(host):
    if host in {None, "", "localhost", b"localhost"}:
        return
    try:
        if ipaddress.ip_address(host.decode() if isinstance(host, bytes) else host).is_loopback:
            return
    except (ValueError, TypeError):
        pass
    raise AssertionError("External network disabled in unit tests; use a mock transport")


def check_url(url):
    parts = urlsplit(str(url))
    if parts.scheme in {"http", "https", "ws", "wss"}:
        check_host(parts.hostname)


_resolve = socket.getaddrinfo
_connect = socket.socket.connect
_connect_ex = socket.socket.connect_ex
_request = requests.Session.request
_open = urllib.request.OpenerDirector.open


def resolve(host, *args, **kwargs):
    check_host(host)
    return _resolve(host, *args, **kwargs)


def connect(sock, address):
    if sock.family in {socket.AF_INET, socket.AF_INET6}:
        check_host(address[0])
    return _connect(sock, address)


def connect_ex(sock, address):
    if sock.family in {socket.AF_INET, socket.AF_INET6}:
        check_host(address[0])
    return _connect_ex(sock, address)


def request(self, method, url, *args, **kwargs):
    check_url(url)
    return _request(self, method, url, *args, **kwargs)


def open_url(self, fullurl, *args, **kwargs):
    check_url(getattr(fullurl, "full_url", fullurl))
    return _open(self, fullurl, *args, **kwargs)


socket.getaddrinfo = resolve
socket.socket.connect = connect
socket.socket.connect_ex = connect_ex
requests.Session.request = request
urllib.request.OpenerDirector.open = open_url
try:
    import httpx
except ImportError:
    pass
else:
    _httpx_request = httpx.Client.request
    def httpx_request(self, method, url, *args, **kwargs):
        check_url(url)
        return _httpx_request(self, method, url, *args, **kwargs)
    httpx.Client.request = httpx_request
