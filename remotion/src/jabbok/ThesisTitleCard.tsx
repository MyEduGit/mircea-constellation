import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

export type ThesisTitleCardProps = {
  thesisRo: string;
  thesisEn: string;
  subCaption: string;
};

export const thesisTitleCardDefaultProps: ThesisTitleCardProps = {
  thesisRo: "Religia LUI Isus vs. Religia DESPRE Isus",
  thesisEn: "The Religion OF Jesus vs. The Religion ABOUT Jesus",
  subCaption: "cu Dr. Emanoil Geaboc · JabbokRiver Productions",
};

export const ThesisTitleCard: React.FC<ThesisTitleCardProps> = ({
  thesisRo,
  thesisEn,
  subCaption,
}) => {
  const frame = useCurrentFrame();
  const roOpacity = interpolate(frame, [0, 30], [0, 1], {
    extrapolateRight: "clamp",
  });
  const enOpacity = interpolate(frame, [30, 70], [0, 1], {
    extrapolateRight: "clamp",
  });
  const capOpacity = interpolate(frame, [70, 110], [0, 1], {
    extrapolateRight: "clamp",
  });
  const lift = interpolate(frame, [0, 60], [30, 0], {
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        background:
          "radial-gradient(circle at 30% 30%, #2a1a3a 0%, #0a0a1a 70%, #000000 100%)",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "Segoe UI, system-ui, -apple-system, sans-serif",
        textAlign: "center",
        padding: "0 120px",
      }}
    >
      <div style={{ transform: `translateY(${lift}px)` }}>
        <div
          style={{
            color: "#FFD700",
            fontSize: 88,
            lineHeight: 1.15,
            opacity: roOpacity,
            fontWeight: 700,
          }}
        >
          {thesisRo}
        </div>
        <div
          style={{
            color: "#DDA0DD",
            fontSize: 42,
            marginTop: 36,
            opacity: enOpacity,
            fontWeight: 300,
            fontStyle: "italic",
          }}
        >
          {thesisEn}
        </div>
        <div
          style={{
            color: "#6495ED",
            fontSize: 26,
            marginTop: 60,
            opacity: capOpacity,
            letterSpacing: 4,
          }}
        >
          {subCaption}
        </div>
      </div>
    </AbsoluteFill>
  );
};
