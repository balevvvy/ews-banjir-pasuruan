import asyncio
import os
import sys
import time
from contextlib import asynccontextmanager

import cv2
import numpy as np

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from fastapi import Cookie, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.config import load_config
from src.detection.detector import WaterLevelDetector
from src.web import auth, database

config = load_config()
detector = WaterLevelDetector(config)
PTZ_ENABLED = bool(config["ptz"]["enabled"])

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")
STREAM_INTERVAL_SEC = 0.066


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_db()
    detector.on_reading = database.insert_reading
    detector.on_alert = database.insert_alert
    detector.start()
    yield
    detector.stop()


app = FastAPI(title="EWS Banjir Dashboard", version="2.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATE_DIR)


def get_operator(session_token: str | None) -> dict | None:
    if not session_token:
        return None
    return auth.validate_session(session_token)


def unauthorized():
    return JSONResponse({"error": "Unauthorized"}, status_code=401)


# ---------------------------------------------------------------- halaman

@app.get("/", response_class=HTMLResponse)
async def halaman_publik(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.get("/login", response_class=HTMLResponse)
async def halaman_login(request: Request, error: str = ""):
    return templates.TemplateResponse(request, "login.html", {"error": error})


@app.post("/login")
async def proses_login(username: str = Form(...), password: str = Form(...)):
    token = auth.authenticate(username, password)
    if not token:
        return RedirectResponse(url="/login?error=Username atau password salah", status_code=303)

    response = RedirectResponse(url="/operator", status_code=303)
    response.set_cookie(key="session_token", value=token, httponly=True, max_age=auth.SESSION_DURATION)
    return response


@app.get("/logout")
async def proses_logout(session_token: str = Cookie(default=None)):
    if session_token:
        auth.logout(session_token)
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("session_token")
    return response


@app.get("/operator", response_class=HTMLResponse)
async def halaman_operator(request: Request, session_token: str = Cookie(default=None)):
    operator = get_operator(session_token)
    if not operator:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(request, "operator.html", {"operator": operator})


# ---------------------------------------------------------------- video

def _placeholder_jpeg(message: str) -> bytes:
    img = np.zeros((720, 1280, 3), dtype=np.uint8)
    for i, line in enumerate(["Kamera Tidak Terhubung", message]):
        scale, thick = (1.5, 3) if i == 0 else (0.7, 2)
        (tw, _), _ = cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, scale, thick)
        cv2.putText(img, line, ((1280 - tw) // 2, 340 + i * 60), cv2.FONT_HERSHEY_SIMPLEX, scale, (110, 110, 110), thick)
    return cv2.imencode(".jpg", img)[1].tobytes()


@app.get("/video_feed")
async def video_feed(view: str = "annotated"):
    view = view if view in ("annotated", "mask") else "annotated"

    async def generate():
        placeholder_msg, placeholder = None, None
        while True:
            frame = detector.get_jpeg(view)
            if frame is None:
                if detector.message != placeholder_msg:
                    placeholder_msg = detector.message
                    placeholder = _placeholder_jpeg(placeholder_msg)
                frame = placeholder
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
            await asyncio.sleep(STREAM_INTERVAL_SEC)

    return StreamingResponse(generate(), media_type="multipart/x-mixed-replace; boundary=frame")


# ---------------------------------------------------------------- API publik

@app.get("/api/status")
async def api_status():
    return JSONResponse(detector.get_status_dict())


@app.get("/api/history")
async def api_history(minutes: float = 10):
    return JSONResponse(database.get_history(minutes=minutes))


@app.get("/api/alerts")
async def api_alerts(hours: float = 24):
    return JSONResponse(database.get_alerts(hours=hours))


@app.get("/api/settings")
async def api_get_settings():
    return JSONResponse({
        "sensitivity": detector.sensitivity,
        "blur_size": detector.blur_size,
        "ptz_enabled": PTZ_ENABLED,
    })


# ---------------------------------------------------------------- API operator

@app.post("/api/settings")
async def api_post_settings(request: Request, session_token: str = Cookie(default=None)):
    if not get_operator(session_token):
        return unauthorized()

    body = await request.json()
    if "sensitivity" in body:
        detector.sensitivity = max(1, min(255, int(body["sensitivity"])))
    if "blur_size" in body:
        detector.blur_size = max(3, min(99, int(body["blur_size"])))
    return JSONResponse({"ok": True, "sensitivity": detector.sensitivity, "blur_size": detector.blur_size})


@app.post("/api/reference")
async def api_reference(session_token: str = Cookie(default=None)):
    if not get_operator(session_token):
        return unauthorized()

    ok, message = await asyncio.to_thread(detector.request_reference_capture)
    return JSONResponse({"ok": ok, "message": message}, status_code=200 if ok else 409)


@app.post("/api/recording")
async def api_recording(request: Request, session_token: str = Cookie(default=None)):
    if not get_operator(session_token):
        return unauthorized()

    body = await request.json()
    if body.get("action") == "start":
        try:
            files = detector.start_recording()
        except RuntimeError as e:
            return JSONResponse({"ok": False, "message": str(e)}, status_code=409)
        return JSONResponse({"ok": True, "recording": True, "files": files})

    info = detector.stop_recording()
    if not info["files"]:
        return JSONResponse({"ok": True, "recording": False, "message": "Tidak sedang merekam."})
    return JSONResponse({
        "ok": True,
        "recording": False,
        "message": f"Tersimpan di data/recordings ({info['duration_sec']} detik): " + ", ".join(info["files"]),
        **info,
    })


@app.post("/api/ptz/reset")
async def api_ptz_reset(session_token: str = Cookie(default=None)):
    if not get_operator(session_token):
        return unauthorized()

    if not PTZ_ENABLED:
        return JSONResponse({
            "ok": False,
            "ptz_disabled": True,
            "message": "Kontrol PTZ hanya tersedia untuk kamera Dahua PTZ. Kamera yang terpasang saat ini adalah kamera tetap.",
        })

    def reset():
        from src.camera import ptz_control

        koordinat = ptz_control.baca_koordinat_tersimpan()
        pan, tilt, zoom = koordinat["pan"], koordinat["tilt"], koordinat["zoom"]
        ptz_control.goto_position_abs(pan, tilt, zoom)
        time.sleep(3)
        ptz_control.axis_nudge_closed_loop("tilt", lambda s: s["tilt"], tilt, "Up", "Down", tolerance=0.5)
        ptz_control.axis_nudge_closed_loop("zoom", lambda s: s["zoom"], zoom, "ZoomTele", "ZoomWide", tolerance=0.5)

    try:
        await asyncio.to_thread(reset)
        return JSONResponse({"ok": True, "message": "Kamera dikembalikan ke posisi papan duga."})
    except FileNotFoundError:
        return JSONResponse({"ok": False, "message": "File koordinat belum ada."}, status_code=404)
    except Exception as e:
        return JSONResponse({"ok": False, "message": str(e)}, status_code=500)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.web.app:app", host="127.0.0.1", port=8000)
