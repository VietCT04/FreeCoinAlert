import { PageHeader } from "../../../components/page-header";
import { TelegramConnectionPanel } from "../../../features/telegram/connection-panel";

export default function TelegramPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        description="Connect your private Telegram destination, review notification usage, and manage test delivery readiness."
        title="Telegram"
      />
      <TelegramConnectionPanel />
    </div>
  );
}
