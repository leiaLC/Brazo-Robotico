import asyncio
import json
import math
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.config import get_settings
from app.models import (
    JointTargetRequest,
    RobotState,
    SequenceRequest,
    TeleopState,
    TeleopTwistRequest,
    VoiceTextRequest,
)
from app.ros_gateway import JointSnapshot, RosGateway


settings = get_settings()
gateway = RosGateway(settings)


def snapshot_to_state(snapshot: JointSnapshot | None) -> RobotState:
    if snapshot is None:
        return RobotState(
            connected=False,
            state_count=0,
            joint_names=settings.joint_names,
            positions_rad=None,
            positions_deg=None,
        )

    return RobotState(
        connected=True,
        state_count=snapshot.count,
        joint_names=snapshot.names,
        positions_rad=snapshot.positions_rad,
        positions_deg=[math.degrees(value) for value in snapshot.positions_rad],
    )


@asynccontextmanager
async def lifespan(_: FastAPI):
    gateway.start()
    try:
        yield
    finally:
        gateway.stop()


app = FastAPI(title="Yumi Web Control Backend", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {
        "ok": True,
        "command_topic": settings.command_topic,
        "state_topic": settings.state_topic,
        "sequence_topic": settings.sequence_topic,
        "teleop_twist_topic": settings.teleop_twist_topic,
        "voice_text_topic": settings.voice_text_topic,
        "image_topic": settings.image_topic,
        "teleop_enabled": gateway.is_teleop_enabled(),
        "task_status": gateway.get_latest_task_status(),
    }


@app.get("/robot/state", response_model=RobotState)
def robot_state():
    return snapshot_to_state(gateway.get_snapshot())


@app.get("/robot/task-status")
def robot_task_status():
    return gateway.get_latest_task_status() or {
        "mode": "UNKNOWN",
        "message": "No /robot_task/status received yet",
    }


@app.post("/teleop/enable", response_model=TeleopState)
def enable_teleop():
    gateway.enable_teleop()
    return TeleopState(enabled=True)


@app.post("/teleop/disable", response_model=TeleopState)
def disable_teleop():
    gateway.disable_teleop()
    return TeleopState(enabled=False)


@app.post("/teleop/joint-target")
def joint_target(request: JointTargetRequest):
    try:
        gateway.publish_joint_target_deg(request.positions_deg)
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {"ok": True}


@app.post("/teleop/twist")
def teleop_twist(request: TeleopTwistRequest):
    try:
        gateway.publish_teleop_twist(
            (request.linear_x, request.linear_y, request.linear_z),
            (request.angular_x, request.angular_y, request.angular_z),
        )
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {"ok": True}


@app.post("/sequence/run")
def run_sequence(request: SequenceRequest):
    try:
        gateway.publish_sequence(request.sequence_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {"ok": True, "sequence_id": request.sequence_id}


@app.post("/voice/text")
def voice_text(request: VoiceTextRequest):
    try:
        gateway.publish_voice_text(request.text)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {"ok": True}


@app.post("/task/cancel")
def cancel_task():
    try:
        gateway.publish_task_command("CANCEL")
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"ok": True}


@app.post("/task/estop")
def estop_task():
    try:
        gateway.publish_task_command("ESTOP")
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"ok": True}


@app.websocket("/ws/robot-state")
async def robot_state_ws(websocket: WebSocket):
    await websocket.accept()
    queue: asyncio.Queue[JointSnapshot] = asyncio.Queue(maxsize=1)
    loop = asyncio.get_running_loop()

    def enqueue(snapshot: JointSnapshot) -> None:
        def put_latest() -> None:
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            queue.put_nowait(snapshot)

        loop.call_soon_threadsafe(put_latest)

    gateway.add_state_callback(enqueue)

    try:
        initial = snapshot_to_state(gateway.get_snapshot()).model_dump()
        await websocket.send_text(json.dumps(initial))

        while True:
            snapshot = await queue.get()
            await websocket.send_text(json.dumps(snapshot_to_state(snapshot).model_dump()))
    except WebSocketDisconnect:
        pass
    finally:
        gateway.remove_state_callback(enqueue)


async def mjpeg_generator():
    boundary = b"--frame"
    while True:
        frame = gateway.get_latest_jpeg()
        if frame is None:
            await asyncio.sleep(0.1)
            continue

        yield (
            boundary
            + b"\r\nContent-Type: image/jpeg\r\nContent-Length: "
            + str(len(frame)).encode("ascii")
            + b"\r\n\r\n"
            + frame
            + b"\r\n"
        )
        await asyncio.sleep(0.03)


@app.get("/video/mjpeg")
def video_mjpeg():
    return StreamingResponse(
        mjpeg_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


if __name__ == "__main__":
    uvicorn.run("app.main:app", host=settings.backend_host, port=settings.backend_port, reload=False)
