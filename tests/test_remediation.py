"""Security regressions from the 2026-11-09 audit.
All network fixtures are loopback-only and all files are temporary.
"""
import contextlib
import json
import os
import socket
import ssl
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import zipfile
import zlib
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from unittest.mock import patch

import pytest

from romarr.app import ROMarr, make_handler, BoundedThreadingHTTPServer
from romarr.auth import Auth
from romarr.ops import make_backup
from romarr.store import Store, StateUnreadable
from romarr.totp import Totp, code_at
from romarr.scheduler import Scheduler
from romarr.library import import_rom, _PathSource, _ZipSource, verify_set
from romarr.dat import parse_dat, VERIFIED, BAD_DUMP, UNKNOWN
from romarr.platforms import resolve
from romarr.downloaders import DebridClient, DebridConfig, _stream_to, SiteDownloader, SiteConfig
from romarr import patches


def service_at(path, **extra):
    env = {"ROMARR_DATA": str(path), **extra}
    with patch.object(ROMarr, "_refresh_counts", return_value=None), patch.object(Scheduler, "start", return_value=None):
        return ROMarr(env)


@contextlib.contextmanager
def server(service):
    httpd = BoundedThreadingHTTPServer(("127.0.0.1", 0), make_handler(service))
    t = threading.Thread(target=httpd.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)
    t.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}"
    finally:
        httpd.shutdown()
        httpd.server_close()
        t.join(2)


def request(base, path, body=None, key=None, headers=None, method=None):
    heads = {"Content-Type":"application/json", **(headers or {})}
    if key:
        heads["X-Api-Key"] = key
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base+path, data=data, headers=heads, method=method)
    try:
        response = urllib.request.urlopen(req, timeout=4)
    except urllib.error.HTTPError as e:
        response = e
    with response:
        raw = response.read()
        return response.status, json.loads(raw), response.headers


def set_password(service):
    service.auth.password_hash = service.auth.hash_password("correct-password")
    service.store.settings["_password_hash"] = service.auth.password_hash
    service.claimed = True
    service.store.save()


def test_wrong_api_key_does_not_bypass_totp(tmp_path):
    s = service_at(tmp_path/"s.json", ROMARR_API_KEY="valid-admin-key")
    set_password(s)
    s.auth.totp = Totp("JBSWY3DPEHPK3PXP")
    with server(s) as base:
        assert request(base, "/api/v1/login", {"password":"correct-password"})[0] == 401
        code, _, headers = request(base, "/api/v1/login", {"password":"correct-password", "apikey":"wrong"})
        assert code == 401 and not headers.get("Set-Cookie")


def test_recovery_code_is_consumed_across_restart(tmp_path):
    path = tmp_path/"s.json"
    s = service_at(path, ROMARR_API_KEY="valid-admin-key")
    set_password(s)
    with server(s) as base:
        _, enrolled, _ = request(base, "/api/v1/totp/enroll", {}, key="valid-admin-key")
        assert not s.auth.totp.enabled
        assert request(base, "/api/v1/totp/confirm", {"totp":code_at(enrolled["secret"], int(time.time()))}, key="valid-admin-key")[0] == 200
        payload = {"password":"correct-password", "totp":enrolled["backup_codes"][0]}
        assert request(base, "/api/v1/login", payload)[0] == 200
        assert request(base, "/api/v1/login", payload)[0] == 401
    restarted = service_at(path, ROMARR_API_KEY="valid-admin-key")
    with server(restarted) as base:
        assert request(base, "/api/v1/login", payload)[0] == 401


def test_forward_auth_cannot_be_claimed(tmp_path):
    s = service_at(tmp_path/"s.json", ROMARR_AUTH="forward", ROMARR_TRUSTED_PROXIES="10.0.0.1/32")
    assert s.sso is not None and s.claimed
    with server(s) as base:
        assert request(base, "/api/v1/setup", {"password":"attacker-password"})[0] == 409


def test_first_run_claim_is_atomic(tmp_path):
    s = service_at(tmp_path/"s.json")
    barrier = threading.Barrier(2)
    with server(s) as base:
        def claim(password):
            barrier.wait(timeout=3)
            return request(base, "/api/v1/setup", {"password":password})
        with ThreadPoolExecutor(2) as pool:
            replies = list(pool.map(claim, ["password-one", "password-two"]))
        assert sorted(r[0] for r in replies) == [200,409]
        assert sum(bool(r[2].get("Set-Cookie")) for r in replies) == 1


def test_corrupt_state_is_preserved_and_cannot_open_setup(tmp_path):
    path = tmp_path/"s.json"
    damaged = '{"settings":{"_password_hash":"protected"},'
    path.write_text(damaged)
    with pytest.raises(StateUnreadable): service_at(path)
    assert path.read_text() == damaged


def test_config_redacts_all_credentials(tmp_path):
    s = service_at(tmp_path/"s.json", ROMARR_API_KEY="valid-admin-key")
    s.store.settings.update({"_totp_secret":"totp-marker", "_totp_backup":["recovery-marker"],
        "connections":[{"token":"notification-marker"}],
        "metadata_providers":[{"token":"metadata-marker"}],
        "import_lists":[{"npsso":"psn-marker"}]})
    with server(s) as base:
        status, body, headers = request(base, "/api/v1/config", key="valid-admin-key")
        assert status == 200
        encoded = json.dumps(body)
        assert all(x not in encoded for x in ["totp-marker","recovery-marker","notification-marker","metadata-marker","psn-marker"])
        assert headers.get("Cache-Control") == "no-store"


def test_portable_backup_is_secret_free():
    values = {k:"secret-"+k for k in ["api_token","app_token","client_secret","npsso","openxbl_key","itchio_key","ea_token","epic_code","humble_cookie","_organizer_journal_key"]}
    values["connections"] = [{"url":"https://example.invalid/private-webhook-secret"}]
    result = make_backup(values)
    assert not result["contains_secrets"]
    assert "secret-" not in json.dumps(result)
    assert "private-webhook-secret" not in json.dumps(result)


def test_restore_preserves_local_identity(tmp_path):
    path = tmp_path/"s.json"
    s = service_at(path)
    set_password(s)
    backup = make_backup(s.store.settings)
    with server(s) as base:
        assert request(base, "/api/v1/restore", backup, key=s.auth.api_key)[0] == 200
        assert s.claimed and s.auth.password_hash
    restarted = service_at(path)
    assert restarted.claimed and restarted.auth.check_password("correct-password")


def test_save_failure_propagates_and_rolls_back_memory(tmp_path):
    path = tmp_path/"s.json"
    s = Store(path)
    s.save()
    original = path.read_bytes()
    s.settings["public_url"] = "https://changed.invalid"
    with patch("romarr.store.os.replace", side_effect=OSError("simulated disk error")):
        with pytest.raises(OSError): s.save()
    assert s.settings["public_url"] == ""
    assert path.read_bytes() == original


def test_forward_auth_rejects_cross_origin_mutation(tmp_path):
    s = service_at(tmp_path/"s.json", ROMARR_AUTH="forward", ROMARR_TRUSTED_PROXIES="127.0.0.1/32", ROMARR_API_KEY="key")
    with server(s) as base:
        status, _, _ = request(base, "/api/v1/game/meta", {"platform":"snes", "game":"test", "notes":"changed via cross-site request"}, headers={
            "X-authentik-username":"operator", "Origin":"https://untrusted.invalid", "Content-Type":"text/plain"})
        assert status == 403
        assert s.store.game_meta("snes","test").get("notes") != "changed via cross-site request"


def test_symlink_platform_folder_is_rejected(tmp_path):
    library = tmp_path/"library"; library.mkdir()
    outside = tmp_path/"outside"; outside.mkdir()
    (library/"snes").symlink_to(outside, target_is_directory=True)
    source = tmp_path/"game.sfc"; source.write_bytes(b"safe probe")
    result = import_rom(source, resolve("snes"), library)
    assert not result[0].ok and not (outside/"game.sfc").exists()


def test_interrupted_import_leaves_no_final_and_retry_succeeds(tmp_path):
    source = tmp_path/"game.sfc"; source.write_bytes(b"complete")
    library = tmp_path/"library"
    def partial_copy(self, name, destination):
        destination.write(b"partial")
        raise OSError("simulated copy failure")
    with patch.object(_PathSource, "copy", partial_copy):
        assert not import_rom(source, resolve("snes"), library)[0].ok
    assert not (library/"snes"/"game.sfc").exists()
    result = import_rom(source, resolve("snes"), library)
    assert result[0].ok
    assert (library/"snes"/"game.sfc").read_bytes() == b"complete"


class FakeResponse:
    status_code = 200
    headers = {"Content-Disposition":'attachment; filename="same.sfc"'}
    def __enter__(self): return self
    def __exit__(self,*args): pass
    def close(self): pass
    def raise_for_status(self): pass
    def iter_content(self, **kw): yield b"replacement"


def test_direct_download_preserves_existing_file(tmp_path):
    path = tmp_path/"same.sfc"; path.write_bytes(b"old data")
    with pytest.raises(FileExistsError): _stream_to(FakeResponse(), tmp_path, "https://example.invalid/a")
    assert path.read_bytes() == b"old data"


def test_partial_symlink_cannot_redirect_writes(tmp_path):
    target = tmp_path/"downloads"; target.mkdir()
    victim = tmp_path/"victim"; victim.write_bytes(b"old data")
    (target/"same.sfc.partial").symlink_to(victim)
    _stream_to(FakeResponse(), target, "https://example.invalid/a")
    assert victim.read_bytes() == b"old data"


def test_debrid_rejects_traversal(tmp_path):
    root = tmp_path/"downloads"; root.mkdir()
    client = DebridClient(DebridConfig(api_token="dummy", save_path=str(root)))
    class FakeSession:
        def get(self,*args,**kwargs): return FakeResponse()
    client._session = FakeSession()
    assert not client._fetch_links([("../escaped.sfc", "https://example.invalid/a")], root)
    assert not (tmp_path/"escaped.sfc").exists()


def vlq(n):
    out = bytearray()
    while True:
        b = n & 0x7f; n >>= 7
        if not n:
            out.append(b|0x80); return bytes(out)
        out.append(b); n -= 1


def test_ups_reverse_output_is_bounded():
    small = b"ABCD"; large = small + b"\0"*28
    raw = b"UPS1" + vlq(len(large)) + vlq(len(small))
    raw += zlib.crc32(large).to_bytes(4,"little") + zlib.crc32(small).to_bytes(4,"little")
    raw += zlib.crc32(raw).to_bytes(4,"little")
    with patch.object(patches, "MAX_ROM_BYTES", 16):
        with pytest.raises(patches.PatchError): patches.apply_patch(small, raw)


def test_zip_metadata_reads_are_bounded(tmp_path):
    path = tmp_path/"rom.zip"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("game.cue", b"A"*(4*1024*1024))
    assert path.stat().st_size < 10000
    with pytest.raises(OSError): _ZipSource(path).read("game.cue")


def test_scheduled_and_manual_jobs_are_serialized():
    s = Scheduler(); entered = threading.Event(); release = threading.Event()
    state = {"active":0,"peak":0}; lock = threading.Lock()
    def work():
        with lock:
            state["active"] += 1; state["peak"] = max(state["peak"],state["active"])
            entered.set()
        release.wait(2)
        with lock: state["active"] -= 1
    job = s.add("probe","probe",lambda:1,work)
    t = threading.Thread(target=s._run,args=(job,)); t.start(); assert entered.wait(1)
    t2 = threading.Thread(target=s.run_now,args=("probe",)); t2.start()
    deadline = time.monotonic()+1
    while state["peak"] < 2 and time.monotonic() < deadline:
        threading.Event().wait(.01)
    release.set(); t.join(); t2.join()
    assert state["peak"] == 1


def tls_fixture(tmp_path):
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from datetime import datetime, timedelta, timezone
    key = rsa.generate_private_key(public_exponent=65537,key_size=2048)
    name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,"localhost")])
    cert=(x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key()).serial_number(1)
          .not_valid_before(datetime.now(timezone.utc)-timedelta(days=1)).not_valid_after(datetime.now(timezone.utc)+timedelta(days=1)).sign(key,hashes.SHA256()))
    cp=tmp_path/"cert.pem"; kp=tmp_path/"key.pem"
    cp.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    kp.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
    return cp, kp


def test_stalled_tls_handshake_cannot_block_other_clients(tmp_path):
    cp, kp = tls_fixture(tmp_path)
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200); self.end_headers(); self.wfile.write(b"ok")
        def log_message(self,*args): pass
    httpd=BoundedThreadingHTTPServer(("127.0.0.1",0),Handler)
    ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); ctx.load_cert_chain(cp,kp)
    httpd.tls_context=ctx
    httpd.socket_timeout=.1
    t=threading.Thread(target=httpd.serve_forever,kwargs={"poll_interval":.02},daemon=True); t.start()
    stalled=socket.create_connection(httpd.server_address,timeout=1)
    threading.Event().wait(.15)
    clientctx=ssl._create_unverified_context()
    try:
        with clientctx.wrap_socket(socket.create_connection(httpd.server_address,timeout=2),server_hostname="localhost") as healthy:
            healthy.sendall(b"GET / HTTP/1.0\r\n\r\n")
            assert b"200" in healthy.recv(4096)
    finally:
        stalled.close()
    with urllib.request.urlopen(f"https://127.0.0.1:{httpd.server_port}",context=clientctx,timeout=2) as r:
        assert r.status==200
    httpd.shutdown(); httpd.server_close(); t.join(2)


def test_plugin_cannot_signal_parent_or_sibling(tmp_path):
    code = """
import os, signal
from romarr.plugin_runtime.syscall_guard import install
install()
try:
    os.kill(os.getppid(), 0)
except PermissionError:
    print("denied")
else:
    raise AssertionError("plugin can signal the parent UID")
"""
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "denied"


def test_old_landlock_abis_fail_closed():
    from romarr.plugin_runtime.landlock import _rights_for_abi, LandlockUnavailable
    for abi in (0, 1, 2):
        with pytest.raises(LandlockUnavailable): _rights_for_abi(abi)


def sample_dat():
    return parse_dat('''<datafile><header><name>Audit fixture</name></header>
    <game name="Game A"><rom name="a.bin" size="8" crc="11111111" md5="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" sha1="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"/></game>
    <game name="Game B"><rom name="b.bin" size="16" crc="22222222" md5="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb" sha1="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"/></game>
    </datafile>''')


def test_stronger_hash_conflict_blocks_crc_fallback():
    result = sample_dat().lookup(size=8, crc="11111111", md5="c"*32, sha1="c"*40)
    assert result.status == BAD_DUMP


def test_size_alone_cannot_prove_corruption():
    result = sample_dat().lookup(size=8, crc="33333333", md5="c"*32, sha1="c"*40)
    assert result.status == UNKNOWN


def test_mixed_game_set_is_not_verified():
    class Source:
        def hashes(self, member):
            return {"sha1": ("a" if member == "a.bin" else "b") * 40}
    result = verify_set(Source(), ["a.bin", "b.bin"], sample_dat())
    assert result.status == UNKNOWN


def test_invalid_config_is_rejected_without_persistence(tmp_path):
    path = tmp_path/"s.json"
    s = service_at(path, ROMARR_API_KEY="valid-admin-key")
    with server(s) as base:
        status, _, _ = request(base, "/api/v1/config", {"library_path":{"invalid":"type"}},
                               key="valid-admin-key", method="PUT")
        assert status == 400
    assert isinstance(json.loads(path.read_text())["settings"]["library_path"], str)
    assert service_at(path, ROMARR_API_KEY="valid-admin-key").claimed


def test_public_download_transport_rejects_private_addresses():
    import requests
    from romarr.public_http import PublicSession
    with pytest.raises(requests.RequestException):
        PublicSession().get("http://127.0.0.1:9/internal", timeout=1)


def test_public_transport_pins_validated_dns_address(monkeypatch):
    from romarr import public_http
    seen=[]
    monkeypatch.setattr(public_http.socket,"getaddrinfo",lambda *a,**k:[(2,1,6,"",("8.8.8.8",443))])
    marker=object()
    monkeypatch.setattr(public_http,"create_connection",lambda address,*a,**k: seen.append(address) or marker)
    connection=public_http.PublicHTTPSConnection("download.example",443)
    assert connection._new_conn() is marker
    assert seen == [("8.8.8.8",443)]


def test_session_revocation_and_password_policy_invalidate_old_tokens():
    auth=Auth("fixture",session_key="independent",session_epoch="first")
    first=auth.issue_session();assert auth.check_session(first)
    auth.session_epoch="second";assert not auth.check_session(first)
    second=auth.issue_session();auth.password_hash="changed";assert not auth.check_session(second)
    third=auth.issue_session();auth.policy="changed issuer or allowlist";assert not auth.check_session(third)


def test_unconfirmed_totp_does_not_lock_out_operator(tmp_path):
    s=service_at(tmp_path/"s.json",ROMARR_API_KEY="fixture")
    set_password(s)
    with server(s) as base:
        assert request(base,"/api/v1/totp/enroll",{},key="fixture")[0]==200
        assert not s.auth.totp.enabled
        assert request(base,"/api/v1/totp/confirm",{"totp":"wrong"},key="fixture")[0]==401
        assert not s.auth.totp.enabled
        assert request(base,"/api/v1/login",{"password":"correct-password"})[0]==200


def test_stolen_session_cannot_reveal_master_key_or_disable_totp(tmp_path):
    s=service_at(tmp_path/"s.json",ROMARR_API_KEY="fixture")
    set_password(s);s.auth.totp=Totp("JBSWY3DPEHPK3PXP")
    headers={"Cookie":"romarr_session="+s.auth.issue_session(),"X-ROMarr-CSRF":"1"}
    with server(s) as base:
        assert request(base,"/api/v1/system/apikey",headers=headers)[0]==401
        assert request(base,"/api/v1/backup?secrets=1",headers=headers)[0]==401
        assert request(base,"/api/v1/backup/encrypted",headers={**headers,"X-ROMarr-Backup-Passphrase":"synthetic-long-passphrase"})[0]==401
        assert request(base,"/api/v1/backup",headers=headers)[0]==200
        assert request(base,"/api/v1/totp/disable",{},headers=headers)[0]==401
        assert s.auth.totp.enabled


def test_download_byte_budget_is_enforced_before_publication(tmp_path,monkeypatch):
    monkeypatch.setenv("ROMARR_MAX_DOWNLOAD_BYTES","4")
    with pytest.raises(OSError): _stream_to(FakeResponse(),tmp_path,"https://example.invalid/a")
    assert not (tmp_path/"same.sfc").exists()
    assert not list(tmp_path.glob(".romarr-*"))


def test_multifile_failure_keeps_previous_complete_set(tmp_path):
    from romarr.safe_files import atomic_directory
    target=tmp_path/"game";target.mkdir();(target/"old").write_bytes(b"complete")
    def failed(stage):
        (stage/"new").write_bytes(b"partial")
        raise OSError("full disk")
    with pytest.raises(OSError):atomic_directory(tmp_path,target,failed,overwrite=True)
    assert (target/"old").read_bytes()==b"complete" and not (target/"new").exists()


def test_rate_limit_uses_only_trusted_forwarded_identity(tmp_path):
    from romarr.http_security import rate_identity
    from types import SimpleNamespace
    service=service_at(tmp_path/"s.json",ROMARR_AUTH="forward",ROMARR_TRUSTED_PROXIES="127.0.0.1/32")
    handler=SimpleNamespace(client_address=("127.0.0.1",1),headers={"X-Forwarded-For":"198.51.100.1"})
    assert rate_identity(handler,service)=="198.51.100.1"
    handler.client_address=("198.51.100.2",1)
    assert rate_identity(handler,service)=="198.51.100.2"


def test_stale_config_cannot_restore_spent_recovery_codes(tmp_path):
    import copy
    s=service_at(tmp_path/'state.json',ROMARR_API_KEY='fixture')
    s.auth.totp=Totp('JBSWY3DPEHPK3PXP', ['fixture-recovery-code'])
    s.store.replace_settings({**s.store.settings,'_totp_secret':s.auth.totp.secret,'_totp_backup':s.auth.totp.backup})
    stale=copy.deepcopy(s.store.settings)
    assert s.verify_second_factor('fixture-recovery-code')
    s.apply_settings(stale)
    assert not s.store.settings['_totp_backup']
    assert not service_at(s.store.path).verify_second_factor('fixture-recovery-code')


def test_runtime_validation_precedes_state_commit(tmp_path,monkeypatch):
    s=service_at(tmp_path/'state.json',ROMARR_API_KEY='fixture')
    before=s.store.path.read_bytes()
    def reject(cfg): raise ValueError('unsupported client configuration')
    monkeypatch.setattr('romarr.app.build_client',reject)
    with pytest.raises(ValueError): s.apply_settings({**s.store.settings,'download_clients':[{'type':'invalid'}]})
    assert s.store.path.read_bytes()==before


def test_post_publish_sync_error_does_not_reenable_recovery_code(tmp_path,monkeypatch):
    import stat
    s=service_at(tmp_path/'state.json',ROMARR_API_KEY='fixture')
    s.auth.totp=Totp('JBSWY3DPEHPK3PXP',['fixture-recovery-code'])
    original=os.fsync
    def sync(fd):
        if stat.S_ISDIR(os.fstat(fd).st_mode):raise OSError('simulated directory sync failure')
        original(fd)
    monkeypatch.setattr('romarr.durable.os.fsync',sync)
    with pytest.raises(OSError):s.verify_second_factor('fixture-recovery-code')
    assert not s.verify_second_factor('fixture-recovery-code')
    assert not s.store.settings['_totp_backup']


def test_invalid_tls_configuration_never_opens_plaintext(monkeypatch,tmp_path):
    from romarr import app
    monkeypatch.setenv('ROMARR_SSL_CERT',str(tmp_path/'missing.pem'))
    monkeypatch.delenv('ROMARR_SSL_KEY',raising=False)
    touched=[]
    monkeypatch.setattr(app,'ROMarr',lambda *a,**k:touched.append('started'))
    with pytest.raises(ValueError):app.serve(port=0)
    assert touched==[]


def test_site_ledger_corruption_is_preserved(tmp_path):
    client=SiteDownloader(SiteConfig(save_path=str(tmp_path)))
    path=tmp_path/client.LEDGER
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(b'{invalid')
    with pytest.raises((ValueError,json.JSONDecodeError)):client._read()
    assert path.read_bytes()==b'{invalid'


def test_archive_members_and_cumulative_expansion_are_bounded(tmp_path,monkeypatch):
    monkeypatch.setenv('ROMARR_MAX_MEMBER_BYTES','16')
    archive=tmp_path/'bomb.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:z.writestr('game.sfc',b'A'*10000)
    result=import_rom(archive,resolve('snes'),tmp_path/'library')
    assert not result[0].ok
    assert not list((tmp_path/'library').rglob('*.sfc'))


def test_internal_redirect_never_reaches_unapproved_origin(tmp_path,monkeypatch):
    from romarr.public_http import PublicSession
    import requests
    seen=[]
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            seen.append(self.path)
            self.send_response(302)
            self.send_header('Location','http://127.0.0.1:9/private')
            self.end_headers()
        def log_message(self,*args):pass
    httpd=BoundedThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=httpd.serve_forever,daemon=True);thread.start()
    base=f'http://127.0.0.1:{httpd.server_port}'
    monkeypatch.setenv('ROMARR_ACQUISITION_PRIVATE_ORIGINS',base)
    try:
        with pytest.raises(requests.RequestException):PublicSession().get(base+'/redirect',timeout=2)
        assert seen==['/redirect']
    finally:httpd.shutdown();httpd.server_close();thread.join(2)


def test_ipv6_translation_cannot_hide_loopback(monkeypatch):
    from romarr.public_http import public_addresses
    for address in ('2002:7f00:1::','64:ff9b::7f00:1','::ffff:127.0.0.1'):
        monkeypatch.setattr(socket,'getaddrinfo',lambda *a,**k:[(10,1,6,'',(address,443,0,0))])
        with pytest.raises(OSError):public_addresses('fixture.example',443)


def test_native_tls_secure_cookie_and_health_certificate_pin(tmp_path):
    from romarr.healthcheck import check
    cert, key = tls_fixture(tmp_path)
    s = service_at(tmp_path/"state.json", ROMARR_API_KEY="valid-admin-key")
    set_password(s)
    httpd = BoundedThreadingHTTPServer(("127.0.0.1", 0), make_handler(s))
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(cert, key)
    httpd.tls_context = ctx
    thread = threading.Thread(target=httpd.serve_forever, kwargs={"poll_interval": .02}, daemon=True)
    thread.start()
    env = {"ROMARR_PORT": str(httpd.server_port), "ROMARR_SSL_CERT": str(cert), "ROMARR_SSL_KEY": str(key)}
    try:
        check(env)
        client = ssl.create_default_context(cafile=str(cert))
        req = urllib.request.Request(f"https://localhost:{httpd.server_port}/api/v1/login",
            data=json.dumps({"password":"correct-password"}).encode(), headers={"Content-Type":"application/json"})
        with urllib.request.urlopen(req, context=client, timeout=3) as response:
            assert response.status == 200
            assert "; Secure" in response.headers["Set-Cookie"]
        other = tmp_path/"other"; other.mkdir()
        wrong_cert, _ = tls_fixture(other)
        with pytest.raises(ssl.SSLError, match="differs"):
            check({**env, "ROMARR_SSL_CERT": str(wrong_cert)})
    finally:
        httpd.shutdown(); httpd.server_close(); thread.join(2)


@pytest.mark.parametrize("kind", ["directory", "zip", "archive-stream"])
def test_verification_enforces_an_aggregate_budget_across_members(tmp_path, monkeypatch, kind):
    from romarr.library import _BsdtarSource
    monkeypatch.setenv("ROMARR_MAX_EXPANDED_BYTES", "6")
    monkeypatch.setenv("ROMARR_MAX_MEMBER_BYTES", "64")
    for name in ("a.bin", "b.bin"):
        (tmp_path/name).write_bytes(b"abcd")
    if kind == "zip":
        path = tmp_path/"fixture.zip"
        with zipfile.ZipFile(path, "w") as archive:
            for name in ("a.bin", "b.bin"):
                archive.writestr(name, b"abcd")
        source = _ZipSource(path)
    elif kind == "archive-stream":
        tool = tmp_path/"archive-tool"
        tool.write_text("#!" + sys.executable + "\nimport sys\nsys.stdout.buffer.write(b'abcd')\n")
        tool.chmod(0o755)
        source = _BsdtarSource(tmp_path/"synthetic.7z", str(tool))
    else:
        source = _PathSource(tmp_path)
    assert source.hashes("a.bin")["size"] == 4
    with pytest.raises(OSError, match="byte budget"):
        source.hashes("b.bin")



def test_bulk_downloads_share_actual_byte_budget(monkeypatch):
    from io import BytesIO
    from types import SimpleNamespace
    from romarr.downloaders import _copy_response
    from romarr.limits import Budget
    response = SimpleNamespace(headers={}, iter_content=lambda **_: iter([b"abcd"]))
    budget = Budget(6)
    _copy_response(response, BytesIO(), budget=budget)
    with pytest.raises(OSError, match="byte budget"):
        _copy_response(response, BytesIO(), budget=budget)


def test_debrid_ledger_concurrent_adds_and_corruption(tmp_path):
    client = DebridClient(DebridConfig(api_token="synthetic", save_path=str(tmp_path)))
    with ThreadPoolExecutor(8) as workers:
        list(workers.map(client._remember, range(40)))
    assert len(client._ours()) == 40
    client._ledger_path().write_text("[broken")
    with pytest.raises(ValueError):
        client._remember("more")
    assert client._ledger_path().read_text() == "[broken"
