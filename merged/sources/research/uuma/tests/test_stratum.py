import json, socket, threading
import pytest
from uuma.manager.stratum import StratumClient, StratumError, decode, encode

def test_codec_roundtrip_and_framing():
    m = {"id": 1, "method": "mining.subscribe", "params": ["x"]}
    raw = encode(m)
    assert raw.endswith(b"\n") and raw.count(b"\n") == 1 and decode(raw) == m

def test_decode_rejects_bad_input():
    for bad in (b"not json\n", b"[1,2]\n", b"\xff\xfe\n", b"1\n", b"x" * 70000):
        with pytest.raises(StratumError):
            decode(bad)

def _server(script):
    """Local one-connection test server. script(conn_file, send) drives replies."""
    srv = socket.socket(); srv.bind(("127.0.0.1", 0)); srv.listen(1)
    def run():
        c, _ = srv.accept(); f = c.makefile("rb")
        try: script(f, lambda o: c.sendall(o if isinstance(o, bytes) else encode(o)))
        finally: f.close(); c.close(); srv.close()
    threading.Thread(target=run, daemon=True).start()
    return srv.getsockname()[1]

def _req(f): return json.loads(f.readline())

def test_full_flow_with_notifications_before_reply():
    def script(f, send):
        r = _req(f); assert r["method"] == "mining.subscribe"
        send({"id": None, "method": "mining.set_difficulty", "params": [8]})
        send({"id": r["id"], "result": [[], "ab12", 4], "error": None})
        r = _req(f); send({"id": r["id"], "result": True, "error": None})
        send({"id": None, "method": "mining.notify", "params": ["job1", "aa"]})
        r = _req(f); assert r["method"] == "mining.submit" and r["params"][1] == "job1"
        send({"id": r["id"], "result": False, "error": None})
    c = StratumClient("127.0.0.1", _server(script))
    c.subscribe(); assert (c.extranonce1, c.extranonce2_size, c.difficulty) == ("ab12", 4, 8.0)
    assert c.authorize("w") is True
    assert c.submit("w", "job1", "00", "00", "00") is False   # read notify first, then reply
    assert c.current_job == ["job1", "aa"]; c.close()

def test_server_error_and_bad_replies_raise():
    def script(f, send):
        r = _req(f); send({"id": r["id"], "result": None, "error": [21, "Job not found", None]})
        r = _req(f); send({"id": 999, "result": True})
        r = _req(f); send(b"garbage\n")
    c = StratumClient("127.0.0.1", _server(script))
    for call in (lambda: c.submit("w", "j", "0", "0", "0"), lambda: c.authorize("w"), lambda: c.authorize("w")):
        with pytest.raises(StratumError):
            call()
    c.close()

def test_closed_connection_raises():
    c = StratumClient("127.0.0.1", _server(lambda f, send: _req(f)))
    with pytest.raises(StratumError):
        c.authorize("w")
    c.close()


def _make_cert(tmp_path, host):
    import datetime, ipaddress
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, host)])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now - datetime.timedelta(days=1))
            .not_valid_after(now + datetime.timedelta(days=1))
            .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address(host))]), critical=False)
            .sign(key, hashes.SHA256()))
    cp, kp = str(tmp_path / f"{host}.crt"), str(tmp_path / f"{host}.key")
    open(cp, "wb").write(cert.public_bytes(serialization.Encoding.PEM))
    open(kp, "wb").write(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    return cp, kp

def _tls_server(cp, kp):
    import ssl
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); ctx.load_cert_chain(cp, kp)
    srv = socket.socket(); srv.bind(("127.0.0.1", 0)); srv.listen(1)
    def run():
        try:
            c, _ = srv.accept(); c = ctx.wrap_socket(c, server_side=True); f = c.makefile("rb")
            r = json.loads(f.readline()); c.sendall(encode({"id": r["id"], "result": True, "error": None}))
        except Exception:
            pass
        finally:
            srv.close()
    threading.Thread(target=run, daemon=True).start()
    return srv.getsockname()[1]

def test_tls_verified_connection_works(tmp_path):
    cp, kp = _make_cert(tmp_path, "127.0.0.1")
    c = StratumClient("127.0.0.1", _tls_server(cp, kp), tls=True, cafile=cp)
    assert c.authorize("w") is True; c.close()

def test_tls_untrusted_certificate_rejected(tmp_path):
    cp, kp = _make_cert(tmp_path, "127.0.0.1")
    with pytest.raises(StratumError):   # no cafile: self-signed cert is not in system trust store
        StratumClient("127.0.0.1", _tls_server(cp, kp), tls=True)
