import { ImageResponse } from "next/og";

export const alt =
  "FreeCoinAlert crypto strategy backtesting and alert workflow";
export const size = {
  width: 1200,
  height: 630,
};
export const contentType = "image/png";

export default function OpenGraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          alignItems: "center",
          background: "#101828",
          color: "#f8fafc",
          display: "flex",
          flexDirection: "column",
          height: "100%",
          justifyContent: "center",
          padding: "72px",
          width: "100%",
        }}
      >
        <div
          style={{
            color: "#38bdf8",
            fontSize: 38,
            fontWeight: 700,
            letterSpacing: "0.04em",
          }}
        >
          FreeCoinAlert
        </div>
        <div
          style={{
            fontSize: 64,
            fontWeight: 700,
            lineHeight: 1.1,
            marginTop: 32,
            textAlign: "center",
          }}
        >
          Backtest it. Understand it. Get alerted when it happens.
        </div>
      </div>
    ),
    size,
  );
}
