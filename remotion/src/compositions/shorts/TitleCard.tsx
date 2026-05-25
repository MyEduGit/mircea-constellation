import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

type TitleCardProps = {
  title: string;
  subtitle: string | null;
  accentColor: string;
};

export const TitleCard: React.FC<TitleCardProps> = ({
  title,
  subtitle,
  accentColor,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const enter = spring({
    frame,
    fps,
    config: { damping: 16, stiffness: 140, mass: 0.7 },
  });
  const opacity = interpolate(enter, [0, 1], [0, 1]);
  const translateY = interpolate(enter, [0, 1], [-30, 0]);

  return (
    <div
      style={{
        position: "absolute",
        top: 120,
        left: 60,
        right: 60,
        opacity,
        transform: `translateY(${translateY}px)`,
      }}
    >
      <div
        style={{
          display: "inline-block",
          padding: "8px 18px",
          background: accentColor,
          color: "#111",
          fontFamily: '"Inter", sans-serif',
          fontWeight: 800,
          fontSize: 26,
          letterSpacing: 2,
          textTransform: "uppercase",
          borderRadius: 6,
          marginBottom: 18,
        }}
      >
        {subtitle ?? "Evergreen"}
      </div>
      <div
        style={{
          fontFamily: '"Inter", "Helvetica Neue", Arial, sans-serif',
          fontWeight: 900,
          color: "white",
          fontSize: 72,
          lineHeight: 1.05,
          letterSpacing: -1.5,
          textShadow: "0 4px 20px rgba(0,0,0,0.85)",
        }}
      >
        {title}
      </div>
    </div>
  );
};
