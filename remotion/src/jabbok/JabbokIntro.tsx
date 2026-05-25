import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

export const JabbokIntro: React.FC = () => {
  const frame = useCurrentFrame();
  const titleOpacity = interpolate(frame, [10, 40], [0, 1], {
    extrapolateRight: "clamp",
  });
  const taglineOpacity = interpolate(frame, [50, 80], [0, 1], {
    extrapolateRight: "clamp",
  });
  const subOpacity = interpolate(frame, [70, 100], [0, 1], {
    extrapolateRight: "clamp",
  });
  const lift = interpolate(frame, [10, 60], [40, 0], {
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        background:
          "radial-gradient(ellipse at 50% 70%, #1a1a3e 0%, #0a0a1a 60%, #000000 100%)",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "Segoe UI, system-ui, -apple-system, sans-serif",
        textAlign: "center",
      }}
    >
      <div style={{ transform: `translateY(${lift}px)` }}>
        <h1
          style={{
            color: "#FFD700",
            fontSize: 110,
            letterSpacing: 6,
            opacity: titleOpacity,
            margin: 0,
          }}
        >
          JABBOK RIVER
        </h1>
        <h2
          style={{
            color: "#DDA0DD",
            fontSize: 36,
            letterSpacing: 14,
            opacity: titleOpacity,
            marginTop: 8,
            fontWeight: 300,
          }}
        >
          PRODUCTIONS
        </h2>
        <div
          style={{
            color: "#6495ED",
            fontSize: 42,
            opacity: taglineOpacity,
            marginTop: 60,
            fontStyle: "italic",
          }}
        >
          Religia LUI Isus, nu religia DESPRE Isus
        </div>
        <div
          style={{
            color: "#888",
            fontSize: 24,
            opacity: subOpacity,
            marginTop: 14,
          }}
        >
          The religion OF Jesus, not the religion ABOUT Jesus
        </div>
      </div>
    </AbsoluteFill>
  );
};
