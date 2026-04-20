export type Word = {
  text: string;
  start: number;
  end: number;
};

export type Locale = "ro-RO" | "en-US" | "es-MX" | "pt-BR";

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

export type PanState = {
  x: number;
  y: number;
  scale: number;
};

export type ImageBeat = {
  src: string;
  start: number;
  end: number;
  panFrom: PanState | null;
  panTo: PanState | null;
};

export type ImageShortClipProps = {
  locale: Locale;
  durationInSeconds: number;
  title: string;
  subtitle: string | null;
  words: Word[];
  channelName: string;
  channelHandle: string | null;
  cta: string | null;
  accentColor: string;
  narrationAudio: string | null;
  images: ImageBeat[];
};

export type ClipManifest =
  | ({ format: "face" } & ShortClipProps)
  | ({ format: "image" } & ImageShortClipProps);

export type ClipSequenceProps = {
  clips: ClipManifest[];
  transitionFrames: number;
  width: number;
  height: number;
  fps: number;
};

export const DEFAULT_ACCENT = "#FFD34E";

export const DEFAULT_PAN_FROM: PanState = { x: 0, y: 0, scale: 1.05 };
export const DEFAULT_PAN_TO: PanState = { x: 0, y: 0, scale: 1.2 };
