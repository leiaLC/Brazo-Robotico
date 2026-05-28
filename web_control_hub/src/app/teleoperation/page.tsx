"use client";

import { useCallback, useState } from "react";
import { TeleopControlPanel } from "@/components/teleop-control-panel";
import { TeleopViewport } from "@/components/robot-visuals";
import { jointControls } from "@/lib/mock-data";

const initialPreviewJointPositions = jointControls.map((joint) => joint.value);

export default function TeleoperationPage() {
  const [teleopEnabled, setTeleopEnabled] = useState(false);
  const [backendUrl, setBackendUrl] = useState("");
  const [previewJointPositions, setPreviewJointPositions] = useState(initialPreviewJointPositions);
  const handlePreviewPositionsChange = useCallback((positions: number[]) => {
    setPreviewJointPositions([...positions]);
  }, []);

  return (
    <div className="-mx-5 -mb-8 -mt-8 grid min-h-[calc(100vh-5rem)] md:-mx-9 xl:grid-cols-[720px_1fr]">
      <TeleopControlPanel
        joints={jointControls}
        onBackendUrlChange={setBackendUrl}
        onPreviewPositionsChange={handlePreviewPositionsChange}
        onTeleopEnabledChange={setTeleopEnabled}
      />
      <section className="relative">
        <TeleopViewport
          backendUrl={backendUrl}
          previewJointPositions={previewJointPositions}
          teleopEnabled={teleopEnabled}
        />
      </section>
    </div>
  );
}
