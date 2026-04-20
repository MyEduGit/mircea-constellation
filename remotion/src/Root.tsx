import { Composition } from "remotion";
import { HelloWorld } from "./HelloWorld";
import { JabbokIntro } from "./jabbok/JabbokIntro";
import { JabbokOutro } from "./jabbok/JabbokOutro";
import {
  HostLowerThird,
  hostLowerThirdDefaultProps,
} from "./jabbok/HostLowerThird";
import {
  ThesisTitleCard,
  thesisTitleCardDefaultProps,
} from "./jabbok/ThesisTitleCard";

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
        id="JabbokIntro"
        component={JabbokIntro}
        durationInFrames={150}
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="JabbokOutro"
        component={JabbokOutro}
        durationInFrames={150}
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="HostLowerThird"
        component={HostLowerThird}
        durationInFrames={120}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={hostLowerThirdDefaultProps}
      />
      <Composition
        id="ThesisTitleCard"
        component={ThesisTitleCard}
        durationInFrames={180}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={thesisTitleCardDefaultProps}
      />
    </>
  );
};
