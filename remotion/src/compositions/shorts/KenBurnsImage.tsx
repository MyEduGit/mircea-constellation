import { Img, interpolate, useCurrentFrame } from "remotion";
import type { PanState } from "./types";
import { DEFAULT_PAN_FROM, DEFAULT_PAN_TO } from "./types";

type KenBurnsImageProps = {
  src: string;
  panFrom: PanState | null;
  panTo: PanState | null;
  beatDurationInFrames: number;
};

export const KenBurnsImage: React.FC<KenBurnsImageProps> = ({
  src,
  panFrom,
  panTo,
  beatDurationInFrames,
}) => {
  const frame = useCurrentFrame();
  const progress = interpolate(
    frame,
    [0, Math.max(1, beatDurationInFrames - 1)],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  const from = panFrom ?? DEFAULT_PAN_FROM;
  const to = panTo ?? DEFAULT_PAN_TO;

  const scale = interpolate(progress, [0, 1], [from.scale, to.scale]);
  const tx = interpolate(progress, [0, 1], [from.x, to.x]);
  const ty = interpolate(progress, [0, 1], [from.y, to.y]);

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        overflow: "hidden",
        background: "#000",
      }}
    >
      <Img
        src={src}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          transform: `translate(${tx}%, ${ty}%) scale(${scale})`,
          transformOrigin: "center center",
          willChange: "transform",
        }}
      />
    </div>
  );
};
