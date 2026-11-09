"""Browser request and trusted-proxy boundaries."""
import ipaddress
import ssl
from urllib.parse import urlsplit
from .sso import trusted_peer


def is_trusted(handler, service):
    ranges = [p.strip() for p in service._env.get("ROMARR_TRUSTED_PROXIES", "").split(",") if p.strip()]
    return trusted_peer(handler.client_address[0], ranges)


def is_secure(handler, service):
    return (isinstance(handler.connection, ssl.SSLSocket)
            or (is_trusted(handler, service)
                and handler.headers.get("X-Forwarded-Proto", "").lower() == "https"))


def rate_identity(handler, service):
    peer = handler.client_address[0]
    if not is_trusted(handler, service):
        return peer
    chain = handler.headers.get("X-Forwarded-For", "")
    if len(chain) > 2048:
        return peer
    try:
        hops = [str(ipaddress.ip_address(v.strip())) for v in chain.split(",") if v.strip()]
    except ValueError:
        return peer
    ranges = service._env.get("ROMARR_TRUSTED_PROXIES", "").split(",")
    for hop in reversed(hops):
        if not trusted_peer(hop, ranges):
            return hop
    return peer


def browser_mutation_allowed(handler, service):
    if handler.command in {"GET", "HEAD", "OPTIONS"}:
        return True
    # Explicit credentials do not depend on ambient browser/proxy sessions.
    presented = handler.headers.get("X-Api-Key", "")
    bearer = handler.headers.get("Authorization", "").split(None, 1)
    if len(bearer) == 2 and bearer[0].lower() == "bearer":
        presented = presented or bearer[1]
    if service.auth.check_key(presented) or service.auth.check_integration_key(handler.headers):
        return True
    origin = handler.headers.get("Origin", "")
    if origin:
        try:
            scheme = "https" if is_secure(handler, service) else "http"
            expected = urlsplit(f"{scheme}://{handler.headers.get('Host', '')}")
            actual = urlsplit(origin)
            return (actual.scheme in {"http", "https"} and not actual.username
                    and not actual.password and actual.path in {"", "/"}
                    and not actual.query and not actual.fragment
                    and (actual.scheme, actual.hostname, actual.port or (443 if actual.scheme == "https" else 80))
                    == (expected.scheme, expected.hostname, expected.port or (443 if expected.scheme == "https" else 80)))
        except ValueError:
            return False
    if handler.headers.get("Sec-Fetch-Site", "") in {"cross-site", "same-site"}:
        return False
    if handler.headers.get("Cookie") or (service.sso is not None and is_trusted(handler, service)):
        return handler.headers.get("X-ROMarr-CSRF", "") == "1"
    return True
