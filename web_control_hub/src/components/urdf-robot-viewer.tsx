"use client";

import { type MutableRefObject, useEffect, useRef } from "react";
import * as THREE from "three";
import URDFLoader, { type URDFRobot } from "urdf-loader";
import { STLLoader } from "three/examples/jsm/loaders/STLLoader.js";

const URDF_URL = "/robot-assets/abb_irb14050_description/urdf/abb_irb14050.urdf";
const PACKAGE_ROOT = "/robot-assets/abb_irb14050_description";

function degToRad(value: number) {
  return (value * Math.PI) / 180;
}

function webCoarseMeshUrl(path: string) {
  const url = new URL(path, window.location.origin);
  if (url.pathname.includes("/meshes/gripper/")) {
    return url.pathname.replace("/meshes/gripper/", "/meshes/gripper/coarse/");
  }
  return url.pathname.replace("/meshes/", "/meshes/coarse/");
}

function materialForMesh(path: string) {
  if (path.includes("gripper")) {
    return new THREE.MeshStandardMaterial({ color: 0x202a31, metalness: 0.2, roughness: 0.42 });
  }
  if (path.includes("single_arm_base")) {
    return new THREE.MeshStandardMaterial({ color: 0x59666e, metalness: 0.18, roughness: 0.46 });
  }
  return new THREE.MeshStandardMaterial({ color: 0xe9f1f4, metalness: 0.08, roughness: 0.36 });
}

export function UrdfRobotViewer({
  jointPositions,
  controlsRef,
}: {
  jointPositions: number[] | null;
  controlsRef: MutableRefObject<{
    reset: () => void;
    zoomIn: () => void;
    zoomOut: () => void;
  } | null>;
}) {
  const mountRef = useRef<HTMLDivElement | null>(null);
  const robotRef = useRef<URDFRobot | null>(null);
  const latestJointsRef = useRef<number[]>([0, 0, 0, 0, 0, 0, 0]);

  useEffect(() => {
    latestJointsRef.current = jointPositions ?? [0, 0, 0, 0, 0, 0, 0];
    const robot = robotRef.current;
    if (!robot) {
      return;
    }

    latestJointsRef.current.forEach((value, index) => {
      robot.setJointValue(`joint_${index + 1}`, degToRad(value));
    });
  }, [jointPositions]);

  useEffect(() => {
    if (!mountRef.current) {
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

    const camera = new THREE.PerspectiveCamera(42, 1, 0.01, 10);
    const target = new THREE.Vector3(0, 0.34, 0.02);
    const orbit = { azimuth: -0.78, elevation: 0.42, radius: 1.45 };
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
      orbit.radius = Math.max(0.55, Math.min(2.8, orbit.radius + delta));
      updateCamera();
    }

    controlsRef.current = {
      reset: () => {
        orbit.azimuth = -0.78;
        orbit.elevation = 0.42;
        orbit.radius = 1.45;
        updateCamera();
      },
      zoomIn: () => applyZoom(-0.12),
      zoomOut: () => applyZoom(0.12),
    };
    updateCamera();

    scene.add(new THREE.HemisphereLight(0xf7fbff, 0x3f484f, 2.2));

    const key = new THREE.DirectionalLight(0xffffff, 2.8);
    key.position.set(-1.5, 2.7, 2.0);
    key.castShadow = true;
    key.shadow.mapSize.set(1024, 1024);
    scene.add(key);

    const fill = new THREE.DirectionalLight(0xaee4ff, 1.3);
    fill.position.set(1.8, 1.2, -2.4);
    scene.add(fill);

    const floor = new THREE.Mesh(
      new THREE.PlaneGeometry(2.5, 2.1),
      new THREE.MeshStandardMaterial({ color: 0xdfe5e8, roughness: 0.82 }),
    );
    floor.rotation.x = -Math.PI / 2;
    floor.receiveShadow = true;
    scene.add(floor);

    const grid = new THREE.GridHelper(2.5, 20, 0x6b7f8f, 0x9facb6);
    grid.position.y = 0.002;
    scene.add(grid);

    const manager = new THREE.LoadingManager();
    const loader = new URDFLoader(manager);
    loader.packages = {
      abb_irb14050_description: PACKAGE_ROOT,
    };
    loader.parseCollision = false;
    loader.loadMeshCb = (path, loadManager, done) => {
      const webPath = webCoarseMeshUrl(path);
      const stlLoader = new STLLoader(loadManager);
      stlLoader.load(
        webPath,
        (geometry) => {
          const mesh = new THREE.Mesh(geometry, materialForMesh(webPath));
          mesh.castShadow = true;
          mesh.receiveShadow = true;
          done(mesh);
        },
        undefined,
        (error) => done(new THREE.Object3D(), error instanceof Error ? error : undefined),
      );
    };

    loader.load(URDF_URL, (robot) => {
      robot.rotation.x = -Math.PI / 2;
      robot.traverse((object) => {
        object.castShadow = true;
        object.receiveShadow = true;
      });
      latestJointsRef.current.forEach((value, index) => {
        robot.setJointValue(`joint_${index + 1}`, degToRad(value));
      });
      robotRef.current = robot;
      scene.add(robot);
    });

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
      orbit.elevation = Math.max(-0.08, Math.min(1.08, orbit.elevation + dy * 0.004));
      updateCamera();
    }

    function onPointerUp(event: PointerEvent) {
      pointer.active = false;
      if (renderer.domElement.hasPointerCapture(event.pointerId)) {
        renderer.domElement.releasePointerCapture(event.pointerId);
      }
    }

    function onWheel(event: WheelEvent) {
      event.preventDefault();
      applyZoom(event.deltaY * 0.001);
    }

    renderer.domElement.addEventListener("pointerdown", onPointerDown);
    renderer.domElement.addEventListener("pointermove", onPointerMove);
    renderer.domElement.addEventListener("pointerup", onPointerUp);
    renderer.domElement.addEventListener("wheel", onWheel, { passive: false });

    let animationFrame = 0;
    function animate() {
      renderer.render(scene, camera);
      animationFrame = window.requestAnimationFrame(animate);
    }
    animate();

    return () => {
      window.cancelAnimationFrame(animationFrame);
      controlsRef.current = null;
      robotRef.current = null;
      resizeObserver.disconnect();
      renderer.domElement.removeEventListener("pointerdown", onPointerDown);
      renderer.domElement.removeEventListener("pointermove", onPointerMove);
      renderer.domElement.removeEventListener("pointerup", onPointerUp);
      renderer.domElement.removeEventListener("wheel", onWheel);
      scene.traverse((object) => {
        if (object instanceof THREE.Mesh) {
          object.geometry.dispose();
          if (Array.isArray(object.material)) {
            object.material.forEach((material) => material.dispose());
          } else {
            object.material.dispose();
          }
        }
      });
      renderer.dispose();
      if (renderer.domElement.parentNode === mount) {
        mount.removeChild(renderer.domElement);
      }
    };
  }, [controlsRef]);

  return <div ref={mountRef} className="absolute inset-0" />;
}
