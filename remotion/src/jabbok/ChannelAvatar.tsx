import { AbsoluteFill } from "remotion";

// YouTube channel avatar. Square 1080×1080 render; YouTube auto-crops to a
// circle, so keep critical marks inside the inscribed circle (radius 540).
export const ChannelAvatar: React.FC = () => {
  return (
    <AbsoluteFill
      style={{
        background:
          "radial-gradient(circle at 50% 45%, #2a1a3a 0%, #0a0a1a 70%, #000000 100%)",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "Segoe UI, system-ui, -apple-system, sans-serif",
      }}
    >
      <div
        style={{
          textAlign: "center",
          color: "#FFD700",
        }}
      >
        <div
          style={{
            fontSize: 340,
            lineHeight: 1,
            filter: "drop-shadow(0 0 40px rgba(255,215,0,0.4))",
          }}
        >
          🏞️
        </div>
        <div
          style={{
            color: "#FFD700",
            fontSize: 120,
            letterSpacing: 10,
            marginTop: 20,
            fontWeight: 700,
          }}
        >
          JR
        </div>
        <div
          style={{
            color: "#DDA0DD",
            fontSize: 42,
            letterSpacing: 8,
            marginTop: 10,
            fontWeight: 300,
          }}
        >
          PRODUCTIONS
        </div>
      </div>
    </AbsoluteFill>
  );
};
