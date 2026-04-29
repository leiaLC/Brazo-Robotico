from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.simulated_camera import generate_simulated_realsense_feed
from app.ros_bridge_sim import get_robot_telemetry, get_history, toggle_emergency_stop

app = FastAPI(title="ABB Robot Web Dashboard")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={}
    )

@app.get("/video")
def video_feed():
    return StreamingResponse(
        generate_simulated_realsense_feed(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.get("/telemetry")
def telemetry():
    return JSONResponse(content=get_robot_telemetry())

@app.get("/history")
def history():
    return JSONResponse(content=get_history())

@app.post("/emergency-stop")
def emergency_stop():
    state = toggle_emergency_stop()
    return {"emergency_stop": state}