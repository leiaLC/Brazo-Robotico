import {
  Boxes,
  Camera,
  Cpu,
  Layers3,
  Mic,
  Route,
  ScanLine,
  ShieldCheck,
  SquareStack,
  Zap,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

export type NavItem = {
  label: string;
  href: string;
};

export type Metric = {
  label: string;
  value: string;
  detail: string;
  tone: "blue" | "green" | "gray" | "red";
  icon: LucideIcon;
};

export type JointControl = {
  name: string;
  rosName: string;
  range: string;
  value: number;
  min: number;
  max: number;
  axis: string;
};

export type Sequence = {
  id: string;
  title: string;
  description: string;
  estimate: string;
  status: "running" | "idle";
  progress?: number;
  icon: LucideIcon;
};

export const navItems: NavItem[] = [
  { label: "Control", href: "/control" },
  { label: "Teleoperation", href: "/teleoperation" },
  { label: "Sequences", href: "/sequences" },
  { label: "Vision/Voice", href: "/vision-voice" },
  { label: "Dashboard", href: "/dashboard" },
];

export const systemStatus = {
  robot: "ABB IRB14050",
  connection: "ROS2 Active",
  ip: "192.168.1.100",
  firmware: "V1.4.2-RC3",
  maintenance: "2023-10-24",
};

export const controlCards: Metric[] = [
  {
    label: "Connection",
    value: "ROS2",
    detail: "Latency: 4ms",
    tone: "green",
    icon: Route,
  },
  {
    label: "Power Supply",
    value: "48.2 V",
    detail: "Stable Output",
    tone: "blue",
    icon: Zap,
  },
  {
    label: "Operational Mode",
    value: "Manual",
    detail: "Awaiting command sequence",
    tone: "gray",
    icon: Cpu,
  },
  {
    label: "System Health",
    value: "Nominal",
    detail: "All diagnostics passed",
    tone: "green",
    icon: ShieldCheck,
  },
];

export const jointControls: JointControl[] = [
  { name: "J1 - Base", rosName: "joint_1", axis: "axis 1", range: "-168.5 to +168.5", value: 0, min: -168.5, max: 168.5 },
  { name: "J2 - Shoulder", rosName: "joint_2", axis: "axis 2", range: "-143.5 to +43.5", value: 0, min: -143.5, max: 43.5 },
  { name: "J3 - Elbow", rosName: "joint_3", axis: "axis 3", range: "-168.5 to +168.5", value: 0, min: -168.5, max: 168.5 },
  { name: "J4 - Wrist Pitch", rosName: "joint_4", axis: "axis 4", range: "-123.5 to +80.0", value: 0, min: -123.5, max: 80 },
  { name: "J5 - Wrist Yaw", rosName: "joint_5", axis: "axis 5", range: "-290.0 to +290.0", value: 0, min: -290, max: 290 },
  { name: "J6 - Wrist Bend", rosName: "joint_6", axis: "axis 6", range: "-88.0 to +138.0", value: 0, min: -88, max: 138 },
  { name: "J7 - Wrist Twist", rosName: "joint_7", axis: "axis 7", range: "-229.0 to +229.0", value: 0, min: -229, max: 229 },
];

export const sequences: Sequence[] = [
  {
    id: "pick_place_completo",
    title: "Pick & Place Completo",
    description: "Rutina completa de toma y colocacion con poses enseñadas y control de gripper.",
    estimate: "02:45",
    status: "idle",
    icon: Route,
  },
  {
    id: "demo_pick_blue_cube",
    title: "Pick Blue Cube",
    description: "Runs the behavior-tree pick sequence for the blue cube demo.",
    estimate: "02:45",
    status: "idle",
    icon: Boxes,
  },
  {
    id: "home",
    title: "Home",
    description: "Moves the arm to the configured home joint pose.",
    estimate: "00:20",
    status: "idle",
    icon: SquareStack,
  },
  {
    id: "perception2",
    title: "Upward Perception Pose",
    description: "Moves the arm to the configured camera/perception pose.",
    estimate: "00:50",
    status: "idle",
    icon: ScanLine,
  },
  {
    id: "open_gripper",
    title: "Open Gripper",
    description: "Sends the gripper open command through the behavior tree.",
    estimate: "00:02",
    status: "idle",
    icon: Layers3,
  },
  {
    id: "close_gripper",
    title: "Close Gripper",
    description: "Sends the gripper close command through the behavior tree.",
    estimate: "00:02",
    status: "idle",
    icon: SquareStack,
  },
];

export const voiceCommands = [
  { command: "Move right 50mm", time: "14:35:10", confidence: "92%" },
  { command: "Open gripper", time: "14:36:22", confidence: "88%" },
  { command: "Identify Object 01", time: "14:38:05", confidence: "95%" },
];

export const suggestedVoiceCommands = ["Stop", "Home Position", "Close Gripper"];

export const visionDetections = [
  { label: "OBJ_01", confidence: "98%", x: "20%", y: "28%", w: "16%", h: "12%" },
  { label: "TGT_A", confidence: "95%", x: "61%", y: "54%", w: "19%", h: "20%" },
];

export const quickStart = [
  "Verify physical safety fence perimeter.",
  "Check connection status below.",
  "Proceed to Teleoperation tab.",
];

export const iconMap = {
  camera: Camera,
  mic: Mic,
};
