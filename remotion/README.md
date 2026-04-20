# Remotion

Programmatic video generation for Mircea's Constellation. Uses [Remotion](https://www.remotion.dev/) (React-based video) and sits alongside the Python `scribeclaw` ffmpeg pipeline.

## Prerequisites

- Node.js >= 18
- ffmpeg (already required elsewhere in this repo for `scribeclaw/`)

## Install

```
cd remotion
npm install
```

## Develop

Open Remotion Studio (live preview at http://localhost:3000):

```
npm start
```

## Render

Render the default `HelloWorld` composition to MP4:

```
npm run build
```

Output lands in `remotion/out/HelloWorld.mp4`.

## Layout

```
remotion/
  package.json
  tsconfig.json
  remotion.config.ts
  src/
    index.ts        # registerRoot(RemotionRoot)
    Root.tsx        # <Composition id="HelloWorld" .../>
    HelloWorld.tsx  # the scene
```

Add new compositions by creating a component in `src/` and registering it inside `src/Root.tsx`.
