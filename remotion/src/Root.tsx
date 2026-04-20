import type { CalculateMetadataFunction } from "remotion";
import { Composition } from "remotion";
import { ClipSequence } from "./compositions/shorts/ClipSequence";
import { ImageShortClip } from "./compositions/shorts/ImageShortClip";
import { ShortClip } from "./compositions/shorts/ShortClip";
import type {
  ClipSequenceProps,
  ImageShortClipProps,
  ShortClipProps,
} from "./compositions/shorts/types";
import { DEFAULT_ACCENT } from "./compositions/shorts/types";
import { HelloWorld } from "./HelloWorld";
import sampleClip from "../fixtures/sample-clip.json";
import sampleClipEn from "../fixtures/sample-clip-en.json";
import sampleSequence from "../fixtures/sample-sequence.json";

const SHORT_CLIP_FPS = 30;
const SHORT_CLIP_WIDTH = 1080;
const SHORT_CLIP_HEIGHT = 1920;

const calcShortClipMetadata: CalculateMetadataFunction<ShortClipProps> = ({
  props,
}) => ({
  durationInFrames: Math.max(
    1,
    Math.round(props.durationInSeconds * SHORT_CLIP_FPS),
  ),
  fps: SHORT_CLIP_FPS,
  width: SHORT_CLIP_WIDTH,
  height: SHORT_CLIP_HEIGHT,
});

const calcImageShortClipMetadata: CalculateMetadataFunction<
  ImageShortClipProps
> = ({ props }) => ({
  durationInFrames: Math.max(
    1,
    Math.round(props.durationInSeconds * SHORT_CLIP_FPS),
  ),
  fps: SHORT_CLIP_FPS,
  width: SHORT_CLIP_WIDTH,
  height: SHORT_CLIP_HEIGHT,
});

const calcClipSequenceMetadata: CalculateMetadataFunction<
  ClipSequenceProps
> = ({ props }) => {
  const fps = props.fps || SHORT_CLIP_FPS;
  const totalSeconds = props.clips.reduce(
    (acc, c) => acc + c.durationInSeconds,
    0,
  );
  return {
    durationInFrames: Math.max(1, Math.round(totalSeconds * fps)),
    fps,
    width: props.width || SHORT_CLIP_WIDTH,
    height: props.height || SHORT_CLIP_HEIGHT,
  };
};

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="HelloWorld"
        component={HelloWorld}
        durationInFrames={150}
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="ShortClip"
        component={ShortClip}
        calculateMetadata={calcShortClipMetadata}
        durationInFrames={SHORT_CLIP_FPS * 30}
        fps={SHORT_CLIP_FPS}
        width={SHORT_CLIP_WIDTH}
        height={SHORT_CLIP_HEIGHT}
        defaultProps={sampleClip as ShortClipProps}
      />
      <Composition
        id="ImageShortClip"
        component={ImageShortClip}
        calculateMetadata={calcImageShortClipMetadata}
        durationInFrames={SHORT_CLIP_FPS * 30}
        fps={SHORT_CLIP_FPS}
        width={SHORT_CLIP_WIDTH}
        height={SHORT_CLIP_HEIGHT}
        defaultProps={sampleClipEn as unknown as ImageShortClipProps}
      />
      <Composition
        id="ClipSequence"
        component={ClipSequence}
        calculateMetadata={calcClipSequenceMetadata}
        durationInFrames={SHORT_CLIP_FPS * 120}
        fps={SHORT_CLIP_FPS}
        width={SHORT_CLIP_WIDTH}
        height={SHORT_CLIP_HEIGHT}
        defaultProps={sampleSequence as unknown as ClipSequenceProps}
      />
    </>
  );
};

export { DEFAULT_ACCENT };
