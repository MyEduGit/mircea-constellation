import { useCurrentFrame, useVideoConfig } from "remotion";

type ProgressBarProps = {
  accentColor: string;
};

export const ProgressBar: React.FC<ProgressBarProps> = ({ accentColor }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const progress = Math.min(1, frame / Math.max(1, durationInFrames - 1));

  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        bottom: 0,
        height: 8,
        background: "rgba(255,255,255,0.15)",
      }}
    >
      <div
        style={{
          width: `${progress * 100}%`,
          height: "100%",
          background: accentColor,
        }}
      />
    </div>
  );
};
