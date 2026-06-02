import {
  Activity,
  Boxes,
  Camera,
  Cpu,
  Gauge,
  Layers3,
  Mic,
  RefreshCw,
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
  mode: "Auto Mode Running",
  fence: "Safety Fence Active",
  uptime: "142h 31m",
  ip: "192.168.1.100",
  firmware: "V1.4.2-RC3",
  maintenance: "2023-10-24",
};

export const overviewMetrics: Metric[] = [
  {
    label: "Total Cycles",
    value: "142,850",
    detail: "+2.4%",
    tone: "green",
    icon: RefreshCw,
  },
  {
    label: "System Uptime",
    value: "99.8%",
    detail: "Last 30d",
    tone: "gray",
    icon: Activity,
  },
  {
    label: "Energy Consumption",
    value: "4.2 kWh",
    detail: "Nominal",
    tone: "blue",
    icon: Zap,
  },
  {
    label: "Cycle Time Avg",
    value: "2.41 s",
    detail: "Target 2.50s",
    tone: "gray",
    icon: Gauge,
  },
  {
    label: "Error Rate",
    value: "0.05%",
    detail: "Healthy",
    tone: "green",
    icon: ShieldCheck,
  },
];

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

export const energyTrend = [
  { time: "00:00", energy: 2.6 },
  { time: "02:00", energy: 2.8 },
  { time: "04:00", energy: 3.4 },
  { time: "06:00", energy: 4.2 },
  { time: "08:00", energy: 4.0 },
  { time: "10:00", energy: 4.6 },
  { time: "12:00", energy: 4.4 },
  { time: "14:00", energy: 3.8 },
  { time: "16:00", energy: 3.2 },
  { time: "18:00", energy: 3.6 },
  { time: "20:00", energy: 4.8 },
  { time: "Now", energy: 3.0 },
];

export const cycleDistribution = [
  { label: "Optimal (<2.4s)", value: 65, tone: "bg-[#8EF08C]" },
  { label: "Nominal (2.4-2.6s)", value: 25, tone: "bg-[#C9DCF6]" },
  { label: "Slow (>2.6s)", value: 8, tone: "bg-[#747B86]" },
  { label: "Fault/Timeout", value: 2, tone: "bg-[#C7181D]" },
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
    id: "perception",
    title: "Perception Pose",
    description: "Moves the arm to the configured camera/perception pose.",
    estimate: "00:20",
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
