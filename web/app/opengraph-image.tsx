import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "Cardyssey – Deine TCG-Plattform";
export const size = {
  width: 1200,
  height: 630,
};
export const contentType = "image/png";

export default function Image() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "linear-gradient(135deg, #0b1020 0%, #151c34 100%)",
          color: "white",
          fontFamily: "sans-serif",
          padding: "72px",
        }}
      >
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "28px",
            maxWidth: "980px",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "20px",
              fontSize: 42,
              fontWeight: 700,
            }}
          >
            <div
              style={{
                width: 68,
                height: 68,
                border: "5px solid white",
                borderRadius: "50%",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <div
                style={{
                  width: 18,
                  height: 18,
                  border: "4px solid white",
                  borderRadius: "50%",
                }}
              />
            </div>
            Cardyssey
          </div>

          <div
            style={{
              display: "flex",
              flexDirection: "column",
              fontSize: 76,
              lineHeight: 1.05,
              fontWeight: 800,
              letterSpacing: "-2px",
            }}
          >
            <span>Sammeln. Entdecken.</span>
            <span>Eine Plattform.</span>
          </div>

          <div
            style={{
              display: "flex",
              fontSize: 30,
              opacity: 0.82,
            }}
          >
            Sammlung · Scanner · Wishlist · Marketplace · Community
          </div>
        </div>
      </div>
    ),
    size
  );
}
