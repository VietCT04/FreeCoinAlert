import { PageHeader } from "../../../components/page-header";
import { HistoricalAnalysisPanel } from "../../../features/historical-analysis/historical-analysis-panel";

export default function HistoricalAnalysisPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        description="Request bounded hypothetical simulations from server-provided fixed presets and stored data."
        title="Historical Analysis"
      />
      <HistoricalAnalysisPanel />
    </div>
  );
}
