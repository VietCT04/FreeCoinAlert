export type SignalApiErrorPayload = {
  code?: string;
};

export class SignalApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code?: string,
    public readonly retryAfter?: string | null,
  ) {
    super("Signal request failed.");
  }
}

export function isSignalAuthenticationError(error: unknown): boolean {
  return (
    error instanceof SignalApiError &&
    (error.status === 401 || error.code === "AUTHENTICATION_REQUIRED")
  );
}

export function signalErrorMessage(error: unknown): string {
  if (error instanceof SignalApiError) {
    const retryAfter = error.retryAfter
      ? ` Try again in ${error.retryAfter} seconds.`
      : "";

    switch (error.code) {
      case "SIGNAL_PRESET_NOT_FOUND":
        return "This signal preset is no longer available.";
      case "SIGNAL_PRESET_UNAVAILABLE":
        return "This preset is not available for new subscriptions.";
      case "SIGNAL_MARKET_UNAVAILABLE":
        return "This market is not available for preset signals.";
      case "SIGNAL_SUBSCRIPTION_LIMIT_REACHED":
        return "You already have the maximum of 20 active signal subscriptions.";
      case "SIGNAL_SUBSCRIPTION_NOT_FOUND":
        return "This signal subscription is no longer available. Refresh and try again.";
      case "SIGNAL_SUBSCRIPTION_RATE_LIMITED":
        return `Too many subscription requests.${retryAfter}`;
      case "SIGNAL_SUBSCRIPTION_UNAVAILABLE":
        return "Signal subscriptions are temporarily unavailable. Please try again.";
      case "SIGNAL_FEED_CURSOR_INVALID":
        return "Signal history could not be loaded from that position. Refresh and try again.";
      case "SIGNAL_FEED_STREAM_CURSOR_INVALID":
      case "SIGNAL_FEED_REQUEST_INVALID":
        return "Signal history could not be loaded. Refresh and try again.";
      case "SIGNAL_FEED_RATE_LIMITED":
        return `Too many signal-history requests.${retryAfter}`;
      case "SIGNAL_FEED_CONNECTION_LIMIT_REACHED":
        return "Too many live-signal connections are open. Close another tab and try again.";
      case "SIGNAL_FEED_UNAVAILABLE":
        return "Signal history is temporarily unavailable. Please try again.";
      case "AUTHENTICATION_REQUIRED":
        return "Your session has ended. Please sign in again.";
      case "AUTH_CSRF_INVALID":
        return "Your session could not be confirmed. Please refresh and try again.";
      default:
        break;
    }
  }

  return "We couldn't complete that signal request. Please try again.";
}
