import {
  AbsoluteFill,
  Audio,
  Sequence,
  useVideoConfig,
} from "remotion";
import { Captions } from "./Captions";
import { ChannelLockup } from "./ChannelLockup";
import { CTA } from "./CTA";
import { KenBurnsImage } from "./KenBurnsImage";
import { ProgressBar } from "./ProgressBar";
import { TitleCard } from "./TitleCard";
import type { ImageShortClipProps } from "./types";
import { DEFAULT_ACCENT } from "./types";

export const ImageShortClip: React.FC<ImageShortClipProps> = ({
  durationInSeconds,
  images,
  narrationAudio,
  title,
  subtitle,
  words,
  channelName,
  channelHandle,
  cta,
  accentColor,
}) => {
  const { fps } = useVideoConfig();
  const ownDurationInFrames = Math.max(1, Math.round(durationInSeconds * fps));
  const ctaFrames = Math.min(
    Math.round(fps * 2),
    Math.round(ownDurationInFrames / 3),
  );
  const ctaFrom = Math.max(0, ownDurationInFrames - ctaFrames);
  const accent = accentColor ?? DEFAULT_ACCENT;

  return (
    <AbsoluteFill style={{ backgroundColor: "#0a0a0a" }}>
      {images.map((img, i) => {
        const startFrame = Math.round(img.start * fps);
        const beatDuration = Math.max(
          1,
          Math.round((img.end - img.start) * fps),
        );
        return (
          <Sequence
            key={`${img.src}-${i}`}
            from={startFrame}
            durationInFrames={beatDuration}
          >
            <KenBurnsImage
              src={img.src}
              panFrom={img.panFrom}
              panTo={img.panTo}
              beatDurationInFrames={beatDuration}
            />
          </Sequence>
        );
      })}

      <AbsoluteFill
        style={{
          background:
            "linear-gradient(to bottom, rgba(0,0,0,0.55) 0%, rgba(0,0,0,0) 28%, rgba(0,0,0,0) 62%, rgba(0,0,0,0.7) 100%)",
        }}
      />

      {narrationAudio ? <Audio src={narrationAudio} /> : null}

      <TitleCard title={title} subtitle={subtitle} accentColor={accent} />
      <ChannelLockup name={channelName} handle={channelHandle} />
      <Captions words={words} accentColor={accent} />

      {cta ? (
        <Sequence from={ctaFrom} durationInFrames={ctaFrames}>
          <CTA text={cta} accentColor={accent} />
        </Sequence>
      ) : null}

      <ProgressBar
        accentColor={accent}
        durationInFrames={ownDurationInFrames}
      />
    </AbsoluteFill>
  );
};
