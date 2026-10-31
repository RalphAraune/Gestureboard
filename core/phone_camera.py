"""Use a phone as the camera, with nothing installed on the phone.

The app serves a small web page over HTTPS. The phone opens it (by
scanning a QR code), allows the camera, and streams JPEG frames back
over a WebSocket. Everything stays on the local network, so it works
offline over USB tethering, a phone hotspot or the same Wi-Fi.

    PhoneCamera     drop-in stand-in for cv2.VideoCapture
                    (read / isOpened / release), so the gesture code
                    does not need to know where the frames come from.
    open_camera()   PhoneCamera for PHONE_CAMERA, cv2.VideoCapture
                    for a normal webcam index.
    stop_server()   called when the user switches back to a webcam
                    and when the app closes.

The browser only allows the camera on a secure (HTTPS) page, so a
self-signed certificate is made on first run and kept in
%APPDATA%/GestureBoard. The phone shows a security warning the first
time; tapping Advanced -> Proceed accepts it.
"""

import asyncio
import atexit
import datetime
import ipaddress
import os
import socket
import ssl
import threading
import time
from pathlib import Path

import cv2
import numpy as np

try:
    import psutil
except ImportError:
    psutil = None


# Camera "index" saved and passed around for the phone, next to the
# webcam indexes 0, 1, 2 ...
PHONE_CAMERA = "phone"
PHONE_CAMERA_NAME = "Phone Camera"

PORT = 8443

# Every network the laptop is on, so the phone can reach it over
# Wi-Fi, a hotspot or USB tethering.
BIND_HOST = "0.0.0.0"

# A connected phone that has sent nothing for this long is treated as
# paused (page hidden, screen locked).
STALE_SECONDS = 2.0

# Adapter names that belong to virtual machines / WSL: a phone can
# never reach these, so they go to the end of the list.
_VIRTUAL_HINTS = ("vethernet", "virtualbox", "vmware", "hyper-v", "wsl", "loopback", "tailscale", "zerotier")


# ============================================================
# FOLDERS AND ADDRESSES
# ============================================================

def data_dir():
    """Writable folder for the certificate: %APPDATA%/GestureBoard.

    Never inside the .exe's temporary folder, which is deleted when
    the app closes.
    """

    base = os.environ.get("APPDATA") or str(Path.home())
    folder = Path(base) / "GestureBoard"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def local_ipv4s():
    """[(adapter name, ip), ...] for every usable local IPv4 address.

    Wi-Fi, Ethernet, a phone hotspot and USB tethering (often
    192.168.42.x) all show up. Loopback and link-local (169.254.x)
    addresses are left out, and virtual adapters go last.
    """

    found = []

    if psutil is not None:
        try:
            stats = psutil.net_if_stats()

            for name, addresses in psutil.net_if_addrs().items():

                if name in stats and not stats[name].isup:
                    continue

                for address in addresses:
                    if address.family == socket.AF_INET:
                        found.append((name, address.address))
        except Exception:
            found = []

    if not found:
        try:
            for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
                found.append(("Network", info[4][0]))
        except Exception:
            pass

    usable = []
    seen = set()

    for name, ip in found:

        if ip in seen or ip.startswith("127.") or ip.startswith("169.254."):
            continue

        seen.add(ip)
        usable.append((name, ip))

    def rank(item):
        name = item[0].lower()
        if any(hint in name for hint in _VIRTUAL_HINTS):
            return 2
        if "wi-fi" in name or "wlan" in name or "wireless" in name:
            return 0
        return 1

    return sorted(usable, key=rank)


def phone_url(ip):
    return f"https://{ip}:{PORT}/"


# ============================================================
# SELF-SIGNED CERTIFICATE
# ============================================================

def _cert_paths():
    folder = data_dir()
    return folder / "phone_camera_cert.pem", folder / "phone_camera_key.pem"


def _cert_ips(cert_path):
    """IP addresses the saved certificate covers (empty if none)."""

    try:
        from cryptography import x509

        cert = x509.load_pem_x509_certificate(cert_path.read_bytes())

        if cert.not_valid_after_utc < datetime.datetime.now(datetime.timezone.utc):
            return set()

        san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
        return {str(ip) for ip in san.value.get_values_for_type(x509.IPAddress)}

    except Exception:
        return set()


def ensure_certificate(ips):
    """(cert path, key path) for a certificate covering every IP in `ips`.

    Made on first run, and again when the laptop has an address the
    saved one does not cover (USB tethering hands out a new address
    each time). A new certificate means the phone shows the security
    warning once more.
    """

    cert_path, key_path = _cert_paths()

    wanted = set(ips) | {"127.0.0.1"}

    if cert_path.exists() and key_path.exists() and wanted <= _cert_ips(cert_path):
        return cert_path, key_path

    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    # Keep the addresses the old certificate had, so switching between
    # Wi-Fi and the hotspot does not keep asking the phone again.
    wanted |= _cert_ips(cert_path)

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "GestureBoard Phone Camera")])
    now = datetime.datetime.now(datetime.timezone.utc)

    alt_names = [x509.DNSName("localhost")] + [
        x509.IPAddress(ipaddress.ip_address(ip)) for ip in sorted(wanted)
    ]

    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=825))
        .add_extension(x509.SubjectAlternativeName(alt_names), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )

    key_path.write_bytes(key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ))
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))

    return cert_path, key_path


# ============================================================
# SERVER
#
# aiohttp on its own asyncio loop in a background thread, bound to
# 0.0.0.0 so the phone can reach it on any of the laptop's networks.
# Only the newest frame is kept: a slow consumer just skips frames
# instead of falling behind (no growing delay).
# ============================================================

class PhoneCameraServer:

    _instance = None
    _instance_lock = threading.Lock()

    @classmethod
    def get(cls):
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    @classmethod
    def existing(cls):
        return cls._instance

    def __init__(self):

        self._thread = None
        self._loop = None
        self._runner = None
        self._clients = set()

        self.running = False
        self.error = None
        self.ips = []

        self._ever_connected = False
        self._frame = None
        self._frame_seq = 0
        self._frame_time = 0.0
        self._new_frame = threading.Condition()

    # --------------------------------------------------------
    # START / STOP
    # --------------------------------------------------------

    def start(self):
        """Start serving (no-op if already running). False on failure;
        the reason is in self.error."""

        if self.running:
            return True

        self.error = None
        self._ever_connected = False
        self.ips = [ip for _name, ip in local_ipv4s()]

        try:
            cert_path, key_path = ensure_certificate(self.ips)
        except Exception as error:
            self.error = f"Could not make the security certificate: {error}"
            return False

        started = threading.Event()

        self._thread = threading.Thread(
            target=self._serve, args=(cert_path, key_path, started), daemon=True
        )
        self._thread.start()

        started.wait(10)

        if not self.running and self.error is None:
            self.error = "The phone camera server did not start."

        return self.running

    def stop(self):
        """Close the phone's connection and stop the server."""

        loop = self._loop

        if loop is not None and loop.is_running():
            future = asyncio.run_coroutine_threadsafe(self._shutdown(), loop)
            try:
                future.result(timeout=5)
            except Exception:
                pass
            loop.call_soon_threadsafe(loop.stop)

        if self._thread is not None:
            self._thread.join(timeout=5)

        self._thread = None
        self._loop = None
        self.running = False

        with self._new_frame:
            self._frame = None
            self._new_frame.notify_all()

    def covers(self, ip):
        """True when the running server's certificate includes `ip`."""
        return ip in self.ips

    def restart(self):
        self.stop()
        return self.start()

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    @property
    def status(self):
        """"stopped", "waiting", "connected", "paused" or "disconnected"."""

        if not self.running:
            return "stopped"

        if self._clients:
            if time.monotonic() - self._frame_time > STALE_SECONDS:
                return "paused"
            return "connected"

        return "disconnected" if self._ever_connected else "waiting"

    # --------------------------------------------------------
    # FRAMES
    # --------------------------------------------------------

    def wait_frame(self, after_seq, timeout):
        """(seq, frame) of a frame newer than `after_seq`, waiting up to
        `timeout` seconds; (after_seq, None) if none came."""

        deadline = time.monotonic() + timeout

        with self._new_frame:
            while self._frame_seq <= after_seq or self._frame is None:
                remaining = deadline - time.monotonic()
                if remaining <= 0 or not self.running:
                    return after_seq, None
                self._new_frame.wait(remaining)

            return self._frame_seq, self._frame

    def latest_size(self):
        frame = self._frame
        if frame is None:
            return 0, 0
        return frame.shape[1], frame.shape[0]

    # --------------------------------------------------------
    # aiohttp
    # --------------------------------------------------------

    def _serve(self, cert_path, key_path, started):

        from aiohttp import web

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop

        try:
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            context.load_cert_chain(str(cert_path), str(key_path))

            app = web.Application()
            app.router.add_get("/", self._page)
            app.router.add_get("/ws", self._socket)

            self._runner = web.AppRunner(app, access_log=None, handle_signals=False)
            loop.run_until_complete(self._runner.setup())

            site = web.TCPSite(self._runner, BIND_HOST, PORT, ssl_context=context)
            loop.run_until_complete(site.start())

        except OSError as error:
            self.error = (
                f"Port {PORT} is already in use or blocked ({error.strerror or error})."
            )
            started.set()
            loop.close()
            return

        except Exception as error:
            self.error = f"The phone camera server could not start: {error}"
            started.set()
            loop.close()
            return

        self.running = True
        started.set()

        try:
            loop.run_forever()
        finally:
            self.running = False
            loop.close()

    async def _shutdown(self):

        for ws in list(self._clients):
            try:
                await ws.close()
            except Exception:
                pass

        self._clients.clear()

        if self._runner is not None:
            await self._runner.cleanup()
            self._runner = None

    async def _page(self, request):

        from aiohttp import web
        from core.phone_page import PAGE_HTML

        return web.Response(
            text=PAGE_HTML,
            content_type="text/html",
            headers={"Cache-Control": "no-store"},
        )

    async def _socket(self, request):

        from aiohttp import WSMsgType, web

        ws = web.WebSocketResponse(heartbeat=5, max_msg_size=8 * 1024 * 1024)
        await ws.prepare(request)

        # One phone at a time: a new connection (the page reloaded or
        # reconnected) replaces the old one.
        for old in list(self._clients):
            await old.close()
        self._clients.clear()

        self._clients.add(ws)
        self._ever_connected = True
        self._frame_time = time.monotonic()

        try:
            async for message in ws:

                if message.type == WSMsgType.BINARY:
                    self._store(message.data)

                elif message.type == WSMsgType.ERROR:
                    break
        finally:
            self._clients.discard(ws)

        return ws

    def _store(self, data):

        frame = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)

        if frame is None:
            return

        with self._new_frame:
            self._frame = frame
            self._frame_seq += 1
            self._frame_time = time.monotonic()
            self._new_frame.notify_all()


# ============================================================
# PHONE CAMERA  (cv2.VideoCapture stand-in)
# ============================================================

class PhoneCamera:
    """Frames from the phone, read like a webcam.

    read() waits up to READ_TIMEOUT seconds for a new frame, so a
    reading loop never spins while the phone is not sending.
    """

    READ_TIMEOUT = 1.0

    def __init__(self, *_args, **_kwargs):

        self.server = PhoneCameraServer.get()
        self._open = self.server.start()
        self._seq = 0

    def isOpened(self):
        return self._open and self.server.running

    def read(self):

        if not self.isOpened():
            return False, None

        seq, frame = self.server.wait_frame(self._seq, self.READ_TIMEOUT)

        if frame is None:
            return False, None

        self._seq = seq

        # A copy: callers draw on the frame they get.
        return True, frame.copy()

    def release(self):
        # The server keeps running for the other pages; stop_server()
        # ends it when the user switches back to a webcam.
        self._open = False

    def set(self, *_args):
        # Resolution, FPS and so on are chosen on the phone.
        return False

    def get(self, prop):

        width, height = self.server.latest_size()

        if prop == cv2.CAP_PROP_FRAME_WIDTH:
            return float(width)
        if prop == cv2.CAP_PROP_FRAME_HEIGHT:
            return float(height)
        return 0.0


def open_camera(index, backend=None):
    """PhoneCamera for PHONE_CAMERA, else cv2.VideoCapture as before."""

    if index == PHONE_CAMERA:
        return PhoneCamera()

    if backend is None:
        return cv2.VideoCapture(index)

    return cv2.VideoCapture(index, backend)


def stop_server():
    """Stop the phone camera server if it is running."""

    server = PhoneCameraServer.existing()

    if server is not None and server.running:
        server.stop()


atexit.register(stop_server)


# ============================================================
# QUICK TEST:  python -m core.phone_camera
# Starts the server, prints the addresses, and shows the phone's
# frames in a window. Press q to quit.
# ============================================================

if __name__ == "__main__":

    camera = PhoneCamera()

    if not camera.isOpened():
        print(camera.server.error)
        raise SystemExit(1)

    print("Open one of these on your phone:")
    for name, ip in local_ipv4s():
        print(f"  {phone_url(ip)}   ({name})")

    try:
        while True:
            ok, frame = camera.read()
            if ok:
                cv2.imshow("Phone camera (q to quit)", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
            print(f"\rstatus: {camera.server.status:12}", end="")
    finally:
        cv2.destroyAllWindows()
        stop_server()
