import { PageHeader } from "../../../components/page-header";
import { HistoricalAnalysisPanel } from "../../../features/historical-analysis/historical-analysis-panel";

export default function HistoricalAnalysisPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        description="Choose a market, signal, and date range to see a historical simulation."
        title="Historical Analysis"
      />
      <HistoricalAnalysisPanel />
    </div>
  );
}
