import type { CalculateMetadataFunction } from "remotion";
import { Composition } from "remotion";
import { ShortClip } from "./compositions/shorts/ShortClip";
import type { ShortClipProps } from "./compositions/shorts/types";
import { DEFAULT_ACCENT } from "./compositions/shorts/types";
import { HelloWorld } from "./HelloWorld";
import sampleClip from "../fixtures/sample-clip.json";

const SHORT_CLIP_FPS = 30;
const SHORT_CLIP_WIDTH = 1080;
const SHORT_CLIP_HEIGHT = 1920;

const calcShortClipMetadata: CalculateMetadataFunction<ShortClipProps> = ({
  props,
}) => {
  return {
    durationInFrames: Math.max(
      1,
      Math.round(props.durationInSeconds * SHORT_CLIP_FPS),
    ),
    fps: SHORT_CLIP_FPS,
    width: SHORT_CLIP_WIDTH,
    height: SHORT_CLIP_HEIGHT,
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
    </>
  );
};

export { DEFAULT_ACCENT };
