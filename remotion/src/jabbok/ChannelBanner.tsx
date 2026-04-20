import { AbsoluteFill } from "remotion";

// YouTube channel banner. Upload size: 2560×1440. The safe-for-all-devices
// visible area is ~1546×423 centered horizontally. Keep text inside that
// inner zone so nothing critical is cropped on mobile.
export const ChannelBanner: React.FC = () => {
  return (
    <AbsoluteFill
      style={{
        background:
          "radial-gradient(ellipse at 50% 50%, #1a1a3e 0%, #0a0a1a 60%, #000000 100%)",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "Segoe UI, system-ui, -apple-system, sans-serif",
      }}
    >
      <div
        style={{
          width: 1546,
          height: 423,
          textAlign: "center",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
        }}
      >
        <div
          style={{
            color: "#FFD700",
            fontSize: 96,
            letterSpacing: 6,
            fontWeight: 700,
            lineHeight: 1,
          }}
        >
          JABBOK RIVER
        </div>
        <div
          style={{
            color: "#DDA0DD",
            fontSize: 28,
            letterSpacing: 16,
            marginTop: 6,
            fontWeight: 300,
          }}
        >
          PRODUCTIONS
        </div>
        <div
          style={{
            color: "#6495ED",
            fontSize: 34,
            marginTop: 40,
            fontStyle: "italic",
          }}
        >
          Religia LUI Isus, nu religia DESPRE Isus
        </div>
        <div
          style={{
            color: "#888",
            fontSize: 20,
            marginTop: 8,
            letterSpacing: 4,
          }}
        >
          THE RELIGION OF JESUS · cu Dr. Emanoil Geaboc
        </div>
      </div>
    </AbsoluteFill>
  );
};
