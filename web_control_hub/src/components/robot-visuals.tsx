"use client";

import { Maximize, Minus, Plus, RotateCcw, Box, Radio } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { UrdfRobotViewer } from "@/components/urdf-robot-viewer";

const WEBRTC_TIMEOUT_MS = 8_000;

export function RobotHeroPanel() {
  return (
    <div className="relative min-h-[520px] overflow-hidden rounded-lg border border-[#B8C2CD] bg-[#D4DEE2]">
      <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(255,255,255,0.2)_1px,transparent_1px),linear-gradient(rgba(255,255,255,0.24)_1px,transparent_1px)] bg-[size:80px_80px]" />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_35%_30%,rgba(255,255,255,0.9),rgba(255,255,255,0)_32%),linear-gradient(135deg,rgba(0,60,105,0.2),rgba(17,24,32,0.15))]" />
      <div className="absolute left-[16%] top-[8%] h-[72%] w-[26%] rotate-[12deg] rounded-[44%] border-[34px] border-[#EEF4F6] shadow-[inset_0_0_0_8px_#AAB8C0,0_22px_46px_rgba(15,25,35,0.18)]" />
      <div className="absolute left-[38%] top-[11%] h-24 w-52 -rotate-[7deg] rounded-full border-[26px] border-[#EEF4F6] bg-[#AEBCC4] shadow-[inset_0_0_0_7px_#73818A]" />
      <div className="absolute left-[45%] top-[26%] h-[38%] w-[18%] rotate-[23deg] rounded-full border-[30px] border-[#E9F0F2] bg-[#B7C4CB] shadow-[inset_0_0_0_8px_#7F8D95]" />
      <div className="absolute bottom-[6%] left-[36%] h-28 w-64 rounded-t-[80px] border-[24px] border-[#E9F0F2] bg-[#AEBBC2] shadow-[inset_0_0_0_8px_#73818A]" />
      <div className="absolute left-[55%] top-[18%] h-20 w-20 rounded-lg bg-[#27323A] shadow-lg" />
      <div className="absolute left-[58%] top-[28%] h-36 w-6 rounded-full bg-[#27323A]" />
      <div className="absolute bottom-10 left-10 rounded-lg border border-[#CBD2DA] bg-white/92 p-5 shadow-lg">
        <div className="mb-3 flex items-center gap-3 text-sm font-black uppercase tracking-[0.1em]">
          <span className="h-3 w-3 rounded-full bg-[#79EE81]" />
          System Online
        </div>
        <p className="font-mono text-lg">Uptime: 142h 31m</p>
      </div>
    </div>
  );
}

type RobotStateMessage = {
  connected?: boolean;
  state_count?: number;
  positions_deg?: number[] | null;
};

type RenderConnectionState = "idle" | "connecting" | "connected" | "error";
type RenderMode = "urdf" | "simple";


function getRobotStateWebSocketUrl(backendUrl: string) {
  const url = new URL(backendUrl || getDefaultBackendUrl());
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = "/ws/robot-state";
  url.search = "";
  return url.toString();
}

function degToRad(value: number) {
  return (value * Math.PI) / 180;
}

function createLink(length: number, radius: number, material: THREE.Material) {
  const mesh = new THREE.Mesh(new THREE.CylinderGeometry(radius, radius, length, 28), material);
  mesh.rotation.z = Math.PI / 2;
  mesh.position.x = length / 2;
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  return mesh;
}

function createJoint(radius: number, material: THREE.Material) {
  const mesh = new THREE.Mesh(new THREE.SphereGeometry(radius, 28, 18), material);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  return mesh;
}

export function TeleopViewport({
  backendUrl,
  teleopEnabled,
}: {
  backendUrl: string;
  teleopEnabled: boolean;
}) {
  const mountRef = useRef<HTMLDivElement | null>(null);
  const jointsRef = useRef<number[]>([0, 0, 0, 0, 0, 0, 0]);
  const cameraControlsRef = useRef<{
    reset: () => void;
    zoomIn: () => void;
    zoomOut: () => void;
  } | null>(null);
  const [renderEnabled, setRenderEnabled] = useState(true);
  const [renderMode, setRenderMode] = useState<RenderMode>("urdf");
  const [connectionState, setConnectionState] = useState<RenderConnectionState>("idle");
  const [frameCount, setFrameCount] = useState(0);
  const [jointPositions, setJointPositions] = useState<number[] | null>(null);
  const renderActive = renderEnabled && teleopEnabled;
  const simpleRenderActive = renderActive && renderMode === "simple";

  useEffect(() => {
    if (!renderActive) {
      return;
    }

    const socket = new WebSocket(getRobotStateWebSocketUrl(backendUrl));

    socket.addEventListener("open", () => setConnectionState("connected"));
    socket.addEventListener("error", () => setConnectionState("error"));
    socket.addEventListener("close", () => setConnectionState("idle"));
    socket.addEventListener("message", (event) => {
      const robotState = JSON.parse(event.data) as RobotStateMessage;
      if (!robotState.positions_deg || robotState.positions_deg.length !== 7) {
        return;
      }
      jointsRef.current = robotState.positions_deg.map(degToRad);
      setJointPositions(robotState.positions_deg);
      setFrameCount(robotState.state_count ?? 0);
    });

    return () => {
      socket.close();
    };
  }, [backendUrl, renderActive]);

  useEffect(() => {
    if (!simpleRenderActive || !mountRef.current) {
      return;
    }

    const mount = mountRef.current;
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xb7c1c8);

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFShadowMap;
    renderer.domElement.className = "h-full w-full";
    mount.appendChild(renderer.domElement);

    const camera = new THREE.PerspectiveCamera(45, 1, 0.01, 10);
    const target = new THREE.Vector3(0.34, 0.38, 0);
    const orbit = { azimuth: -0.72, elevation: 0.46, radius: 1.85 };
    const pointer = { active: false, x: 0, y: 0 };

    function updateCamera() {
      const horizontal = Math.cos(orbit.elevation) * orbit.radius;
      camera.position.set(
        target.x + Math.sin(orbit.azimuth) * horizontal,
        target.y + Math.sin(orbit.elevation) * orbit.radius,
        target.z + Math.cos(orbit.azimuth) * horizontal,
      );
      camera.lookAt(target);
    }

    function applyZoom(delta: number) {
      orbit.radius = Math.max(0.82, Math.min(3.1, orbit.radius + delta));
      updateCamera();
    }

    cameraControlsRef.current = {
      reset: () => {
        orbit.azimuth = -0.72;
        orbit.elevation = 0.46;
        orbit.radius = 1.85;
        updateCamera();
      },
      zoomIn: () => applyZoom(-0.16),
      zoomOut: () => applyZoom(0.16),
    };

    function resetCamera() {
      orbit.azimuth = -0.72;
      orbit.elevation = 0.46;
      orbit.radius = 1.85;
      updateCamera();
    }
    resetCamera();
    updateCamera();

    const ambient = new THREE.HemisphereLight(0xf4fbff, 0x4a545a, 2.0);
    scene.add(ambient);

    const key = new THREE.DirectionalLight(0xffffff, 2.6);
    key.position.set(-1.8, 2.8, 2.0);
    key.castShadow = true;
    key.shadow.mapSize.set(1024, 1024);
    scene.add(key);

    const fill = new THREE.DirectionalLight(0xb9e8ff, 1.2);
    fill.position.set(2.0, 1.4, -2.2);
    scene.add(fill);

    const floor = new THREE.Mesh(
      new THREE.PlaneGeometry(3.4, 2.6),
      new THREE.MeshStandardMaterial({ color: 0xdfe5e8, roughness: 0.82 }),
    );
    floor.rotation.x = -Math.PI / 2;
    floor.receiveShadow = true;
    scene.add(floor);

    const grid = new THREE.GridHelper(3.4, 22, 0x6b7f8f, 0x9facb6);
    grid.position.y = 0.002;
    scene.add(grid);

    const baseMaterial = new THREE.MeshStandardMaterial({ color: 0x4f5d66, metalness: 0.15, roughness: 0.45 });
    const shellMaterial = new THREE.MeshStandardMaterial({ color: 0xe8f0f3, metalness: 0.08, roughness: 0.34 });
    const accentMaterial = new THREE.MeshStandardMaterial({ color: 0x00a0df, metalness: 0.05, roughness: 0.38 });
    const jointMaterial = new THREE.MeshStandardMaterial({ color: 0x25313a, metalness: 0.16, roughness: 0.32 });
    const toolMaterial = new THREE.MeshStandardMaterial({ color: 0x1c252b, metalness: 0.18, roughness: 0.42 });

    const base = new THREE.Mesh(new THREE.CylinderGeometry(0.15, 0.18, 0.10, 48), baseMaterial);
    base.position.y = 0.05;
    base.castShadow = true;
    base.receiveShadow = true;
    scene.add(base);

    const groups = Array.from({ length: 7 }, () => new THREE.Group());
    scene.add(groups[0]);
    groups[0].position.y = 0.11;
    groups[0].add(createJoint(0.08, jointMaterial));

    const pedestal = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.075, 0.27, 32), shellMaterial);
    pedestal.position.y = 0.13;
    pedestal.castShadow = true;
    groups[0].add(pedestal);

    groups[1].position.set(0, 0.27, 0);
    groups[0].add(groups[1]);
    groups[1].add(createJoint(0.075, accentMaterial));
    groups[1].add(createLink(0.34, 0.045, shellMaterial));

    groups[2].position.x = 0.34;
    groups[1].add(groups[2]);
    groups[2].add(createJoint(0.065, jointMaterial));
    groups[2].add(createLink(0.30, 0.04, shellMaterial));

    groups[3].position.x = 0.30;
    groups[2].add(groups[3]);
    groups[3].add(createJoint(0.055, accentMaterial));
    groups[3].add(createLink(0.22, 0.035, shellMaterial));

    groups[4].position.x = 0.22;
    groups[3].add(groups[4]);
    groups[4].add(createJoint(0.048, jointMaterial));
    groups[4].add(createLink(0.18, 0.03, shellMaterial));

    groups[5].position.x = 0.18;
    groups[4].add(groups[5]);
    groups[5].add(createJoint(0.042, accentMaterial));
    groups[5].add(createLink(0.14, 0.026, shellMaterial));

    groups[6].position.x = 0.14;
    groups[5].add(groups[6]);
    groups[6].add(createJoint(0.036, jointMaterial));

    const wrist = createLink(0.10, 0.022, toolMaterial);
    groups[6].add(wrist);
    const fingerA = new THREE.Mesh(new THREE.BoxGeometry(0.07, 0.012, 0.014), toolMaterial);
    fingerA.position.set(0.13, 0.028, 0.02);
    fingerA.castShadow = true;
    groups[6].add(fingerA);
    const fingerB = fingerA.clone();
    fingerB.position.z = -0.02;
    groups[6].add(fingerB);

    function resize() {
      const width = Math.max(1, mount.clientWidth);
      const height = Math.max(1, mount.clientHeight);
      renderer.setSize(width, height, false);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
    }

    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(mount);
    resize();

    function onPointerDown(event: PointerEvent) {
      pointer.active = true;
      pointer.x = event.clientX;
      pointer.y = event.clientY;
      renderer.domElement.setPointerCapture(event.pointerId);
    }

    function onPointerMove(event: PointerEvent) {
      if (!pointer.active) {
        return;
      }
      const dx = event.clientX - pointer.x;
      const dy = event.clientY - pointer.y;
      pointer.x = event.clientX;
      pointer.y = event.clientY;
      orbit.azimuth -= dx * 0.006;
      orbit.elevation = Math.max(-0.05, Math.min(1.12, orbit.elevation + dy * 0.004));
      updateCamera();
    }

    function onPointerUp(event: PointerEvent) {
      pointer.active = false;
      renderer.domElement.releasePointerCapture(event.pointerId);
    }

    function onWheel(event: WheelEvent) {
      event.preventDefault();
      orbit.radius = Math.max(0.82, Math.min(3.1, orbit.radius + event.deltaY * 0.001));
      updateCamera();
    }

    renderer.domElement.addEventListener("pointerdown", onPointerDown);
    renderer.domElement.addEventListener("pointermove", onPointerMove);
    renderer.domElement.addEventListener("pointerup", onPointerUp);
    renderer.domElement.addEventListener("wheel", onWheel, { passive: false });

    let animationFrame = 0;
    function animate() {
      const joints = jointsRef.current;
      groups[0].rotation.y = joints[0] ?? 0;
      groups[1].rotation.z = joints[1] ?? 0;
      groups[2].rotation.z = joints[2] ?? 0;
      groups[3].rotation.x = joints[3] ?? 0;
      groups[4].rotation.z = joints[4] ?? 0;
      groups[5].rotation.x = joints[5] ?? 0;
      groups[6].rotation.z = joints[6] ?? 0;
      renderer.render(scene, camera);
      animationFrame = window.requestAnimationFrame(animate);
    }
    animate();

    return () => {
      window.cancelAnimationFrame(animationFrame);
      cameraControlsRef.current = null;
      resizeObserver.disconnect();
      renderer.domElement.removeEventListener("pointerdown", onPointerDown);
      renderer.domElement.removeEventListener("pointermove", onPointerMove);
      renderer.domElement.removeEventListener("pointerup", onPointerUp);
      renderer.domElement.removeEventListener("wheel", onWheel);
      renderer.dispose();
      scene.traverse((object) => {
        if (object instanceof THREE.Mesh) {
          object.geometry.dispose();
        }
      });
      mount.removeChild(renderer.domElement);
    };
  }, [simpleRenderActive]);

  const statusText = renderActive
    ? connectionState === "connected"
      ? "Live joint stream"
      : connectionState === "connecting" || connectionState === "idle"
        ? "Connecting"
        : "Waiting for stream"
    : teleopEnabled
      ? "3D render disabled"
      : "Enable teleop to start 3D render";

  return (
    <div className="relative min-h-[calc(100vh-8rem)] overflow-hidden bg-[#AEB7B9]">
      <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(255,255,255,0.19)_1px,transparent_1px),linear-gradient(rgba(255,255,255,0.19)_1px,transparent_1px)] bg-[size:72px_72px]" />
      <div className="absolute inset-0 bg-[linear-gradient(to_bottom,rgba(255,255,255,0),rgba(246,247,248,0.62))]" />
      {renderActive ? (
        renderMode === "urdf" ? (
          <UrdfRobotViewer controlsRef={cameraControlsRef} jointPositions={jointPositions} />
        ) : (
          <div ref={mountRef} className="absolute inset-0" />
        )
      ) : (
        <div className="absolute inset-0 grid place-items-center px-8 text-center">
          <div className="max-w-sm rounded-lg border border-[#C1C9D3] bg-white/92 px-6 py-5 shadow-lg">
            <Box className="mx-auto mb-3 h-8 w-8 text-[#003C69]" />
            <p className="font-mono text-sm font-bold uppercase tracking-[0.12em] text-[#29303A]">
              {statusText}
            </p>
          </div>
        </div>
      )}

      <div className="absolute right-9 top-9 overflow-hidden rounded-lg border border-[#C1C9D3] bg-white shadow-lg">
        {[Plus, Minus, RotateCcw, Maximize].map((Icon, index) => (
          <button
            className="grid h-16 w-16 place-items-center border-b border-[#C1C9D3] last:border-b-0"
            key={index}
            onClick={() => {
              if (Icon === Plus) cameraControlsRef.current?.zoomIn();
              if (Icon === Minus) cameraControlsRef.current?.zoomOut();
              if (Icon === RotateCcw) cameraControlsRef.current?.reset();
              if (Icon === Maximize) cameraControlsRef.current?.reset();
            }}
            title="Viewport camera control"
            type="button"
          >
            <Icon className="h-6 w-6" />
          </button>
        ))}
      </div>

      <label className="absolute left-8 top-8 flex min-h-12 items-center gap-3 rounded-lg border border-[#C1C9D3] bg-white/94 px-4 py-3 shadow-lg">
        <input
          checked={renderEnabled}
          className="h-5 w-5 accent-[#003C69]"
          onChange={(event) => setRenderEnabled(event.target.checked)}
          type="checkbox"
        />
        <span className="font-mono text-xs font-black uppercase tracking-[0.12em] text-[#29303A]">
          3D Render
        </span>
      </label>

      <label className="absolute left-8 top-24 flex min-h-12 items-center gap-3 rounded-lg border border-[#C1C9D3] bg-white/94 px-4 py-3 shadow-lg">
        <span className="font-mono text-xs font-black uppercase tracking-[0.12em] text-[#29303A]">
          Model
        </span>
        <select
          className="rounded border border-[#BFC7D2] bg-white px-3 py-2 font-mono text-xs font-black uppercase tracking-[0.08em] text-[#003C69] outline-none focus:border-[#003C69] focus:ring-2 focus:ring-[#CFE1F6]"
          disabled={!renderEnabled}
          onChange={(event) => setRenderMode(event.target.value as RenderMode)}
          value={renderMode}
        >
          <option value="urdf">URDF</option>
          <option value="simple">Simple</option>
        </select>
      </label>

      <div className="absolute bottom-8 left-10 flex flex-wrap gap-5 pr-6">
        <Readout
          title="Render Status"
          value={statusText}
          success={renderActive && connectionState === "connected"}
        />
        <Readout title="Feedback Frames" value={`${frameCount}`} />
        <Readout
          title="Joint Snapshot"
          value={
            jointPositions
              ? jointPositions.map((value) => value.toFixed(0)).join("  ")
              : "No joint data"
          }
        />
      </div>

      <div className="absolute right-8 bottom-8 hidden h-12 w-12 place-items-center rounded-lg border border-[#C1C9D3] bg-white/90 text-[#003C69] xl:grid">
        <Radio className="h-5 w-5" />
      </div>
    </div>
  );
}

function Readout({ title, value, success = false }: { title: string; value: string; success?: boolean }) {
  return (
    <div className="rounded-lg border border-[#C2CAD6] bg-white/94 px-6 py-4 shadow-lg">
      <p className="text-sm font-semibold uppercase tracking-[0.12em] text-[#29303A]">{title}</p>
      <p className="mt-2 font-mono text-lg text-black">
        {success ? <span className="mr-2 text-[#00751A]">OK</span> : null}
        {value}
      </p>
    </div>
  );
}

export function VisionCameraPanel() {
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL ?? getDefaultBackendUrl();
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [status, setStatus] = useState("Connecting...");

  useEffect(() => {
    let pc: RTCPeerConnection | null = new RTCPeerConnection();
    let cancelled = false;
    const abortController = new AbortController();
    const timeoutId = window.setTimeout(() => abortController.abort(), WEBRTC_TIMEOUT_MS);
    const remoteStream = new MediaStream();

    pc.ontrack = (event) => {
      if (cancelled) {
        return;
      }

      const track = event.track;
      if (!track) {
        return;
      }

      remoteStream.addTrack(track);
      if (videoRef.current) {
        videoRef.current.srcObject = remoteStream;
      }
      setStatus("Stream received");
    };

    pc.oniceconnectionstatechange = () => {
      if (pc && ["failed", "disconnected", "closed"].includes(pc.iceConnectionState)) {
        setStatus("WebRTC disconnected");
        pc.close();
        pc = null;
      }
    };

    async function startWebRTC() {
      try {
        pc?.addTransceiver("video", { direction: "recvonly" });
        const offer = await pc?.createOffer();
        if (!offer) {
          return;
        }

        await pc?.setLocalDescription(offer);

        const response = await fetch(`${backendUrl}/webrtc/offer`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          signal: abortController.signal,
          body: JSON.stringify({ sdp: offer.sdp, type: offer.type }),
        });

        if (!response.ok) {
          throw new Error("Could not create WebRTC offer");
        }

        const answer = await response.json();
        await pc?.setRemoteDescription(answer);
        window.clearTimeout(timeoutId);
        setStatus("Video connected");
      } catch (error) {
        console.error("WebRTC init failed", error);
        setStatus("WebRTC error");
        if (pc) {
          pc.close();
          pc = null;
        }
      }
    }

    startWebRTC();

    return () => {
      cancelled = true;
      window.clearTimeout(timeoutId);
      abortController.abort();
      if (pc) {
        pc.close();
        pc = null;
      }
    };
  }, [backendUrl]);

  return (
    <div className="relative min-h-[620px] overflow-hidden rounded-lg border border-[#B8C2CD] bg-[#091D22] shadow-[0_2px_8px_rgba(20,30,45,0.08)]">
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        className="absolute inset-0 h-full w-full bg-black object-cover"
      />
      <div className="absolute left-4 top-4 rounded-full bg-black/60 px-3 py-1 text-xs text-white">
        {status}
      </div>
    </div>
  );
}

function getDefaultBackendUrl() {
  if (typeof window === "undefined") {
    return "http://localhost:8000";
  }

  return `${window.location.protocol}//${window.location.hostname}:8000`;
}
