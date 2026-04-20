import {
  AbsoluteFill,
  OffthreadVideo,
  Sequence,
  useVideoConfig,
} from "remotion";
import { Captions } from "./Captions";
import { ChannelLockup } from "./ChannelLockup";
import { CTA } from "./CTA";
import { ProgressBar } from "./ProgressBar";
import { TitleCard } from "./TitleCard";
import type { ShortClipProps } from "./types";
import { DEFAULT_ACCENT } from "./types";

export const ShortClip: React.FC<ShortClipProps> = ({
  sourceVideo,
  sourceStartSec,
  title,
  subtitle,
  words,
  channelName,
  channelHandle,
  cta,
  accentColor,
}) => {
  const { fps, durationInFrames } = useVideoConfig();
  const ctaFrames = Math.min(Math.round(fps * 2), Math.round(durationInFrames / 3));
  const ctaFrom = Math.max(0, durationInFrames - ctaFrames);
  const accent = accentColor ?? DEFAULT_ACCENT;

  return (
    <AbsoluteFill style={{ backgroundColor: "#0a0a0a" }}>
      {sourceVideo ? (
        <AbsoluteFill>
          <OffthreadVideo
            src={sourceVideo}
            startFrom={Math.round(sourceStartSec * fps)}
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        </AbsoluteFill>
      ) : (
        <AbsoluteFill
          style={{
            background:
              "radial-gradient(ellipse at 50% 30%, #1a2a55 0%, #070b1c 70%, #020311 100%)",
          }}
        />
      )}

      <AbsoluteFill
        style={{
          background:
            "linear-gradient(to bottom, rgba(0,0,0,0.55) 0%, rgba(0,0,0,0) 28%, rgba(0,0,0,0) 62%, rgba(0,0,0,0.7) 100%)",
        }}
      />

      <TitleCard title={title} subtitle={subtitle} accentColor={accent} />
      <ChannelLockup name={channelName} handle={channelHandle} />
      <Captions words={words} accentColor={accent} />

      {cta ? (
        <Sequence from={ctaFrom} durationInFrames={ctaFrames}>
          <CTA text={cta} accentColor={accent} />
        </Sequence>
      ) : null}

      <ProgressBar accentColor={accent} />
    </AbsoluteFill>
  );
};
