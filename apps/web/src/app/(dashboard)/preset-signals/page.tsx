import { PageHeader } from "../../../components/page-header";
import { PresetSignalPanel } from "../../../features/signals/preset-signal-panel";

export default function PresetSignalsPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        description="Browse fixed informational signals, manage subscriptions, and review owner-visible history."
        title="Preset Signals"
      />
      <PresetSignalPanel />
    </div>
  );
}
