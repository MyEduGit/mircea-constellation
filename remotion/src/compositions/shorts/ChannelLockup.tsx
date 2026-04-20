import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";

type ChannelLockupProps = {
  name: string;
  handle: string | null;
};

export const ChannelLockup: React.FC<ChannelLockupProps> = ({
  name,
  handle,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const opacity = interpolate(frame, [fps * 2, fps * 2 + 15], [0, 0.85], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        position: "absolute",
        top: 60,
        right: 60,
        opacity,
        display: "flex",
        flexDirection: "column",
        alignItems: "flex-end",
        fontFamily: '"Inter", sans-serif',
        color: "white",
        textShadow: "0 2px 8px rgba(0,0,0,0.8)",
      }}
    >
      <div style={{ fontSize: 28, fontWeight: 800, letterSpacing: -0.5 }}>
        {name}
      </div>
      {handle ? (
        <div style={{ fontSize: 22, fontWeight: 500, opacity: 0.85 }}>
          {handle}
        </div>
      ) : null}
    </div>
  );
};
