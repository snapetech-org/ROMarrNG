"""Loopback health probe; native TLS authenticates the configured leaf certificate."""
import hashlib
import hmac
import http.client
import os
from pathlib import Path
import ssl


def check(env=None):
    env = os.environ if env is None else env
    port = int(env.get("ROMARR_PORT", "6868"))
    cert = env.get("ROMARR_SSL_CERT", "")
    key = env.get("ROMARR_SSL_KEY", "")
    if bool(cert) != bool(key):
        raise ValueError("both TLS certificate and key are required")
    if cert:
        # Pin the leaf configured on THIS local listener. This also supports
        # self-signed deployments without disabling validation for remote HTTP.
        pem = Path(cert).read_text()
        leaf = pem[:pem.index("-----END CERTIFICATE-----") + len("-----END CERTIFICATE-----")]
        expected = hashlib.sha256(ssl.PEM_cert_to_DER_cert(leaf)).digest()
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE  # leaf pin checked before the request
        # nosemgrep: python.lang.security.audit.httpsconnection-detected.httpsconnection-detected -- Loopback only; authenticate the configured leaf pin immediately after handshake, before sending HTTP.
        conn = http.client.HTTPSConnection("127.0.0.1", port, timeout=4, context=context)
        conn.connect()
        actual = hashlib.sha256(conn.sock.getpeercert(binary_form=True)).digest()
        if not hmac.compare_digest(actual, expected):
            conn.close()
            raise ssl.SSLError("local certificate differs from configured certificate")
    else:
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=4)
    try:
        conn.request("GET", "/api/health")
        if conn.getresponse().status != 200:
            raise OSError("unhealthy service")
    finally:
        conn.close()


if __name__ == "__main__":
    check()
