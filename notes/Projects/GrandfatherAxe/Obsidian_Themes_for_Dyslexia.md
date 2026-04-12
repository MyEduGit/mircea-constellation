# Obsidian Themes for Dyslexia (April 2026)

**Goal:** Make every GA note and Mermaid timeline easy to read – bigger letters, more space, less visual noise, high contrast.

## Top Themes Ranked

| Rank | Theme | Why it's great | Difficulty |
|------|-------|----------------|------------|
| 1 | **JB Dyslexia** | Built by a dyslexic person, OpenDyslexic font | Very Easy |
| 2 | **Arcadia** | WCAG AA high contrast + OpenDyslexic toggle | Easy |
| 3 | **Minimal** + Style Settings | Most popular, very customisable | Easy |
| 4 | **Velocity** | Modern, clean, low visual clutter | Easy |

**Recommendation:** Start with **JB Dyslexia**.

## How to install
1. Obsidian → Settings → Appearance → Themes → Community themes
2. Search: `JB Dyslexia` → Install → Enable

## Quick CSS Snippet
1. Settings → Appearance → CSS snippets → Open folder
2. Create `dyslexia-friendly.css`
3. Paste:
```css
body {
    font-family: "OpenDyslexic", "Arial", sans-serif !important;
    line-height: 1.8 !important;
    letter-spacing: 0.5px !important;
}
.markdown-preview-view p {
    font-size: 18px !important;
}
```
4. Enable the snippet in Settings.
