import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

type CTAProps = {
  text: string;
  accentColor: string;
};

export const CTA: React.FC<CTAProps> = ({ text, accentColor }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const enter = spring({
    frame,
    fps,
    config: { damping: 14, stiffness: 160 },
  });
  const translateY = interpolate(enter, [0, 1], [80, 0]);
  const opacity = interpolate(enter, [0, 1], [0, 1]);

  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        bottom: 80,
        display: "flex",
        justifyContent: "center",
        opacity,
        transform: `translateY(${translateY}px)`,
      }}
    >
      <div
        style={{
          background: accentColor,
          color: "#111",
          padding: "22px 44px",
          borderRadius: 14,
          fontFamily: '"Inter", sans-serif',
          fontWeight: 900,
          fontSize: 40,
          letterSpacing: -0.5,
          boxShadow: "0 10px 40px rgba(0,0,0,0.45)",
          textTransform: "uppercase",
        }}
      >
        {text}
      </div>
    </div>
  );
};
