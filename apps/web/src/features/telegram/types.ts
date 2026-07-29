export type TelegramConnectionStatus =
  | "not_connected"
  | "linking"
  | "connected"
  | "degraded"
  | "disconnected";

export type TelegramConnection = {
  status: TelegramConnectionStatus;
  username?: string | null;
  connectedAt?: string | null;
  lastVerifiedAt?: string | null;
  linkExpiresAt?: string | null;
  statusReason?: string | null;
};

export type TelegramConnectionEnvelope = {
  connection: TelegramConnection;
};

export type TelegramLinkResponse = TelegramConnectionEnvelope & {
  telegramUrl: string;
};

export type TelegramTestNotificationStatus =
  | "queued"
  | "sending"
  | "retrying"
  | "sent"
  | "failed";

export type TelegramTestNotification = {
  id: string;
  status: TelegramTestNotificationStatus;
  createdAt: string;
  sentAt?: string | null;
  failureCode?: string | null;
};

export type TelegramTestNotificationEnvelope = {
  notification: TelegramTestNotification;
};
