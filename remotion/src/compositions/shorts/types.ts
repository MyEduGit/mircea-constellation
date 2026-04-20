export type Word = {
  text: string;
  start: number;
  end: number;
};

export type ShortClipProps = {
  sourceVideo: string | null;
  sourceStartSec: number;
  durationInSeconds: number;
  title: string;
  subtitle: string | null;
  words: Word[];
  channelName: string;
  channelHandle: string | null;
  cta: string | null;
  accentColor: string;
};

export const DEFAULT_ACCENT = "#FFD34E";
