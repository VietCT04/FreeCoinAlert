import { PageHeader } from "../../../components/page-header";
import { HistoricalAnalysisPanel } from "../../../features/historical-analysis/historical-analysis-panel";

export default function HistoricalAnalysisPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        description="Configure a bounded historical simulation, follow its server-owned lifecycle, and review the immutable hypothetical report."
        title="Historical Analysis"
      />
      <HistoricalAnalysisPanel />
    </div>
  );
}
