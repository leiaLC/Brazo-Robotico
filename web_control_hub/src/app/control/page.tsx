import { RosNodeHealthPanel } from "@/components/ros-node-health-panel";
import { PageTitle } from "@/components/ui";

export default function ControlPage() {
  return (
    <div className="space-y-7">
      <PageTitle centered title="Control Panel" />

      <RosNodeHealthPanel />
    </div>
  );
}
