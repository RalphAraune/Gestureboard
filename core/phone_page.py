"""The page the phone opens (served by core/phone_camera.py).

Kept in Python as a string, so the .exe needs no extra data files.

It shows the camera preview, the connection status and a button to
switch between the front and back camera, and sends JPEG frames
(about 640x480, quality 0.7) over a WebSocket. It reconnects by
itself if the connection drops, and keeps the screen awake where the
browser supports the Screen Wake Lock API.
"""

PAGE_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#0E2F76">
<title>GestureBoard camera</title>
<style>
  :root {
    --navy: #0E2F76;
    --ink: #0A1D47;
    --cyan: #22C3DE;
    --text: #F5FEFF;
    --muted: #AFC2E4;
    --ok: #3DDC97;
    --wait: #FFC857;
    --bad: #FF7A70;
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; height: 100%; }
  body {
    background: var(--ink);
    color: var(--text);
    font: 16px/1.45 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
    display: flex;
    flex-direction: column;
    padding: max(16px, env(safe-area-inset-top)) 16px max(16px, env(safe-area-inset-bottom));
    gap: 14px;
  }
  header { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
  h1 { font-size: 19px; margin: 0; font-weight: 800; }
  .status {
    display: inline-flex; align-items: center; gap: 8px;
    padding: 6px 12px; border-radius: 999px;
    background: rgba(255,255,255,0.08);
    font-size: 14px; font-weight: 700; white-space: nowrap;
  }
  .dot { width: 9px; height: 9px; border-radius: 50%; background: var(--wait); }
  .status[data-state="connected"] .dot { background: var(--ok); }
  .status[data-state="disconnected"] .dot,
  .status[data-state="error"] .dot { background: var(--bad); }
  .stage {
    position: relative; flex: 1; min-height: 0;
    border-radius: 18px; overflow: hidden;
    background: #061331;
    border: 1px solid rgba(255,255,255,0.12);
  }
  video { width: 100%; height: 100%; object-fit: contain; display: block; }
  video.mirror { transform: scaleX(-1); }
  .overlay {
    position: absolute; inset: 0; display: flex; flex-direction: column;
    align-items: center; justify-content: center; gap: 14px;
    padding: 24px; text-align: center; color: var(--muted);
  }
  .overlay[hidden] { display: none; }
  .fps {
    position: absolute; right: 10px; bottom: 10px;
    font-size: 12px; color: var(--muted);
    background: rgba(0,0,0,0.45); padding: 3px 8px; border-radius: 8px;
  }
  button {
    font: inherit; font-weight: 700; color: var(--ink);
    background: var(--cyan); border: none; border-radius: 12px;
    padding: 14px 18px; min-height: 52px; width: 100%;
  }
  button:active { transform: translateY(1px); }
  button:focus-visible { outline: 3px solid var(--text); outline-offset: 2px; }
  button.secondary { background: rgba(255,255,255,0.1); color: var(--text); }
  .note {
    margin: 0; font-size: 14px; color: var(--muted);
    border-left: 3px solid var(--cyan); padding: 4px 0 4px 10px;
  }
</style>
</head>
<body>
  <header>
    <h1>GestureBoard camera</h1>
    <span class="status" id="status" data-state="waiting">
      <span class="dot"></span><span id="statusText">Starting</span>
    </span>
  </header>

  <div class="stage">
    <video id="video" autoplay playsinline muted></video>
    <div class="overlay" id="overlay">
      <span id="overlayText">Allow the camera when your browser asks.</span>
      <button id="start" hidden>Start camera</button>
    </div>
    <span class="fps" id="fps" hidden></span>
  </div>

  <button class="secondary" id="flip">Switch to back camera</button>

  <p class="note">Keep this page open. Don't lock the screen or switch apps.</p>

<script>
(() => {
  const SEND_WIDTH = 640;
  const QUALITY = 0.7;
  const FPS = 20;

  const video = document.getElementById("video");
  const overlay = document.getElementById("overlay");
  const overlayText = document.getElementById("overlayText");
  const startButton = document.getElementById("start");
  const flipButton = document.getElementById("flip");
  const statusBox = document.getElementById("status");
  const statusText = document.getElementById("statusText");
  const fpsLabel = document.getElementById("fps");

  const canvas = document.createElement("canvas");
  const context = canvas.getContext("2d");

  let facing = "user";
  let stream = null;
  let socket = null;
  let retryDelay = 1000;
  let sending = false;
  let sentThisSecond = 0;
  let wakeLock = null;

  function setStatus(state, text) {
    statusBox.dataset.state = state;
    statusText.textContent = text;
  }

  function showOverlay(text, withButton) {
    overlayText.textContent = text;
    startButton.hidden = !withButton;
    overlay.hidden = false;
  }

  // ---------- camera ----------

  async function startCamera() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      showOverlay("This browser can't use the camera here. Open the link in Chrome or Safari.", false);
      setStatus("error", "No camera");
      return;
    }

    if (stream) stream.getTracks().forEach(track => track.stop());

    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: false,
        video: { facingMode: facing, width: { ideal: 640 }, height: { ideal: 480 } },
      });
    } catch (error) {
      stream = null;
      const denied = error && error.name === "NotAllowedError";
      showOverlay(
        denied
          ? "Camera access was blocked. Allow it in your browser's site settings, then tap Start camera."
          : "The camera couldn't start. Close other apps using it, then tap Start camera.",
        true
      );
      setStatus("error", "No camera");
      return;
    }

    video.srcObject = stream;
    video.classList.toggle("mirror", facing === "user");
    flipButton.textContent = facing === "user" ? "Switch to back camera" : "Switch to front camera";
    overlay.hidden = true;
    fpsLabel.hidden = false;
    requestWakeLock();
  }

  startButton.addEventListener("click", startCamera);

  flipButton.addEventListener("click", () => {
    facing = facing === "user" ? "environment" : "user";
    startCamera();
  });

  // ---------- connection ----------

  function connect() {
    const scheme = location.protocol === "https:" ? "wss" : "ws";
    socket = new WebSocket(`${scheme}://${location.host}/ws`);
    socket.binaryType = "arraybuffer";
    setStatus("waiting", "Connecting");

    socket.onopen = () => {
      retryDelay = 1000;
      setStatus("connected", "Connected");
    };

    socket.onclose = () => {
      setStatus("disconnected", "Reconnecting");
      setTimeout(connect, retryDelay);
      retryDelay = Math.min(retryDelay * 2, 5000);
    };

    socket.onerror = () => socket.close();
  }

  // ---------- sending ----------
  // One frame in flight at a time, and none while the connection is
  // still busy with the last one, so a slow network drops frames
  // instead of building up delay.

  function sendFrame() {
    const ready =
      socket && socket.readyState === WebSocket.OPEN &&
      socket.bufferedAmount < 256 * 1024 &&
      !sending && video.videoWidth > 0;

    if (!ready) return;

    const scale = Math.min(1, SEND_WIDTH / Math.max(video.videoWidth, video.videoHeight));
    canvas.width = Math.round(video.videoWidth * scale);
    canvas.height = Math.round(video.videoHeight * scale);
    context.drawImage(video, 0, 0, canvas.width, canvas.height);

    sending = true;
    canvas.toBlob(blob => {
      sending = false;
      if (blob && socket.readyState === WebSocket.OPEN) {
        socket.send(blob);
        sentThisSecond += 1;
      }
    }, "image/jpeg", QUALITY);
  }

  setInterval(sendFrame, 1000 / FPS);

  setInterval(() => {
    fpsLabel.textContent = `${sentThisSecond} fps`;
    sentThisSecond = 0;
  }, 1000);

  // ---------- keep the screen on ----------

  async function requestWakeLock() {
    if (!("wakeLock" in navigator) || wakeLock) return;
    try {
      wakeLock = await navigator.wakeLock.request("screen");
      wakeLock.addEventListener("release", () => { wakeLock = null; });
    } catch (error) {
      wakeLock = null;   // Not supported or not allowed: carry on.
    }
  }

  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") {
      requestWakeLock();
      if (stream && stream.getVideoTracks().every(track => track.readyState === "ended")) {
        startCamera();
      }
    }
  });

  connect();
  startCamera();
})();
</script>
</body>
</html>
"""
