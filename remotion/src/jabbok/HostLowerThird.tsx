import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

export type HostLowerThirdProps = {
  name: string;
  credential: string;
};

export const hostLowerThirdDefaultProps: HostLowerThirdProps = {
  name: "Dr. Emanoil Geaboc",
  credential: "Theologian · JabbokRiver Productions",
};

export const HostLowerThird: React.FC<HostLowerThirdProps> = ({
  name,
  credential,
}) => {
  const frame = useCurrentFrame();
  const slideIn = interpolate(frame, [0, 20], [-600, 60], {
    extrapolateRight: "clamp",
  });
  const fadeOut = interpolate(frame, [100, 120], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        background: "transparent",
        fontFamily: "Segoe UI, system-ui, -apple-system, sans-serif",
      }}
    >
      <div
        style={{
          position: "absolute",
          left: slideIn,
          bottom: 120,
          padding: "18px 28px",
          background:
            "linear-gradient(90deg, rgba(26,26,62,0.95) 0%, rgba(58,58,92,0.85) 100%)",
          borderLeft: "6px solid #FFD700",
          boxShadow: "0 6px 24px rgba(0,0,0,0.4)",
          opacity: fadeOut,
          maxWidth: 900,
        }}
      >
        <div style={{ color: "#FFD700", fontSize: 44, fontWeight: 700, letterSpacing: 1 }}>
          {name}
        </div>
        <div
          style={{
            color: "#DDA0DD",
            fontSize: 24,
            marginTop: 4,
            letterSpacing: 2,
          }}
        >
          {credential}
        </div>
      </div>
    </AbsoluteFill>
  );
};
