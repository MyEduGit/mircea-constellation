import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

export const JabbokOutro: React.FC = () => {
  const frame = useCurrentFrame();
  const ctaOpacity = interpolate(frame, [10, 40], [0, 1], {
    extrapolateRight: "clamp",
  });
  const footerOpacity = interpolate(frame, [60, 100], [0, 1], {
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        background:
          "linear-gradient(180deg, #0a0a1a 0%, #1a1a3e 100%)",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "Segoe UI, system-ui, -apple-system, sans-serif",
        textAlign: "center",
      }}
    >
      <div style={{ opacity: ctaOpacity }}>
        <div style={{ color: "#FFD700", fontSize: 72, letterSpacing: 4 }}>
          ABONEAZĂ-TE
        </div>
        <div style={{ color: "#DDA0DD", fontSize: 28, marginTop: 8, letterSpacing: 8 }}>
          SUBSCRIBE
        </div>
      </div>
      <div
        style={{
          position: "absolute",
          bottom: 80,
          color: "#6495ED",
          fontSize: 24,
          opacity: footerOpacity,
          textAlign: "center",
          maxWidth: 1400,
          lineHeight: 1.5,
        }}
      >
        Part of <strong style={{ color: "#FFD700" }}>Mircea's Constellation</strong>
        <br />
        Inspired by <em>The Urantia Book</em> · Paper 196 — The Faith of Jesus
      </div>
    </AbsoluteFill>
  );
};
