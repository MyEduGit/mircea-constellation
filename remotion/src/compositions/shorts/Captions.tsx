import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import type { Word } from "./types";

type CaptionsProps = {
  words: Word[];
  accentColor: string;
};

const WINDOW_SIZE = 3;

export const Captions: React.FC<CaptionsProps> = ({ words, accentColor }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const time = frame / fps;

  if (words.length === 0) return null;

  const activeIdx = findActiveWord(words, time);
  if (activeIdx < 0) return null;

  const windowStart = Math.max(
    0,
    Math.min(words.length - WINDOW_SIZE, activeIdx - 1),
  );
  const windowWords = words.slice(windowStart, windowStart + WINDOW_SIZE);

  const pop = spring({
    frame: frame - Math.round(words[activeIdx].start * fps),
    fps,
    config: { damping: 12, stiffness: 220, mass: 0.5 },
  });

  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        bottom: "22%",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        gap: 18,
        padding: "0 80px",
        flexWrap: "wrap",
      }}
    >
      {windowWords.map((w, i) => {
        const globalIdx = windowStart + i;
        const isActive = globalIdx === activeIdx;
        const scale = isActive ? interpolate(pop, [0, 1], [0.9, 1.12]) : 0.95;
        return (
          <span
            key={`${w.start}-${w.text}-${i}`}
            style={{
              display: "inline-block",
              fontSize: 86,
              fontWeight: 900,
              letterSpacing: -1,
              color: isActive ? accentColor : "white",
              textShadow:
                "0 4px 18px rgba(0,0,0,0.9), 0 2px 4px rgba(0,0,0,0.8)",
              fontFamily:
                '"Inter", "Helvetica Neue", Arial, sans-serif',
              transform: `scale(${scale})`,
              transformOrigin: "center",
              textTransform: "uppercase",
            }}
          >
            {w.text}
          </span>
        );
      })}
    </div>
  );
};

const findActiveWord = (words: Word[], time: number): number => {
  for (let i = 0; i < words.length; i++) {
    if (time >= words[i].start && time < words[i].end) return i;
  }
  for (let i = 0; i < words.length; i++) {
    if (time < words[i].start) return Math.max(0, i - 1);
  }
  return words.length - 1;
};
