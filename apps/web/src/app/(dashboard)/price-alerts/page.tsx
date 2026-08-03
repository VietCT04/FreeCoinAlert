import { PageHeader } from "../../../components/page-header";
import { PriceAlertPanel } from "../../../features/alerts/price-alert-panel";

export default function PriceAlertsPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        description="Create and manage one-time price-crossing alerts for supported Binance Spot markets."
        title="Price Alerts"
      />
      <PriceAlertPanel />
    </div>
  );
}
