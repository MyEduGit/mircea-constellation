import { AbsoluteFill, Sequence, useVideoConfig } from "remotion";
import { ImageShortClip } from "./ImageShortClip";
import { ShortClip } from "./ShortClip";
import type { ClipManifest, ClipSequenceProps } from "./types";

const renderClip = (clip: ClipManifest) => {
  if (clip.format === "face") {
    return (
      <ShortClip
        sourceVideo={clip.sourceVideo}
        sourceStartSec={clip.sourceStartSec}
        durationInSeconds={clip.durationInSeconds}
        title={clip.title}
        subtitle={clip.subtitle}
        words={clip.words}
        channelName={clip.channelName}
        channelHandle={clip.channelHandle}
        cta={clip.cta}
        accentColor={clip.accentColor}
      />
    );
  }
  return (
    <ImageShortClip
      locale={clip.locale}
      durationInSeconds={clip.durationInSeconds}
      title={clip.title}
      subtitle={clip.subtitle}
      words={clip.words}
      channelName={clip.channelName}
      channelHandle={clip.channelHandle}
      cta={clip.cta}
      accentColor={clip.accentColor}
      narrationAudio={clip.narrationAudio}
      images={clip.images}
    />
  );
};

export const ClipSequence: React.FC<ClipSequenceProps> = ({ clips }) => {
  const { fps } = useVideoConfig();

  let cursor = 0;
  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      {clips.map((clip, i) => {
        const durationFrames = Math.max(
          1,
          Math.round(clip.durationInSeconds * fps),
        );
        const node = (
          <Sequence
            key={`${clip.format}-${i}-${cursor}`}
            from={cursor}
            durationInFrames={durationFrames}
            layout="none"
          >
            {renderClip(clip)}
          </Sequence>
        );
        cursor += durationFrames;
        return node;
      })}
    </AbsoluteFill>
  );
};
