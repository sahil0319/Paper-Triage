<!--
Source: https://raw.githubusercontent.com/VoltAgent/awesome-design-md/main/design-md/ibm/DESIGN.md
Fetched: 2026-10-03. Repo licence: MIT (https://github.com/VoltAgent/awesome-design-md).
NOT VERBATIM. The research agent has no shell; its only fetch tool (WebFetch) returns a model-processed
extract and refused a verbatim dump. Below is the token extract returned for the YAML front matter
(colours, type, spacing, radius, components) and four quoted principles. Prose sections (do/don't,
responsive, agent prompt) were not captured. To get the true file run:
  curl -fsSL https://raw.githubusercontent.com/VoltAgent/awesome-design-md/main/design-md/ibm/DESIGN.md -o docs/research/ibm-DESIGN.md
-->

# IBM (Carbon) DESIGN.md: token extract

## Colors
```
primary: "#0f62fe"
on-primary: "#ffffff"
ink: "#161616"
ink-muted: "#525252"
ink-subtle: "#8c8c8c"
canvas: "#ffffff"
surface-1: "#f4f4f4"
surface-2: "#e0e0e0"
inverse-canvas: "#161616"
inverse-surface-1: "#262626"
inverse-ink: "#ffffff"
inverse-ink-muted: "#c6c6c6"
hairline: "#e0e0e0"
hairline-strong: "#161616"
blue-60: "#0043ce"
blue-80: "#002d9c"
blue-hover: "#0050e6"
semantic-success: "#24a148"
semantic-warning: "#f1c21b"
semantic-error: "#da1e28"
semantic-info: "#0f62fe"
```

## Typography (IBM Plex Sans)
| Style | Size | Weight | Line height | Letter spacing |
|---|---|---|---|---|
| display-xl | 76px | 300 | 1.17 | -0.5px |
| display-lg | 60px | 300 | 1.17 | -0.4px |
| display-md | 42px | 300 | 1.20 | 0 |
| headline | 32px | 400 | 1.25 | 0 |
| card-title | 24px | 400 | 1.33 | 0 |
| body | 16px | 400 | 1.50 | 0.16px |
| body-sm | 14px | 400 | 1.29 | 0.16px |
| body-emphasis | 14px | 600 | 1.29 | 0.16px |
| button | 14px | 400 | 1.29 | 0.16px |
| caption | 12px | 400 | 1.33 | 0.32px |

## Spacing
xxs 4px, xs 8px, sm 12px, md 16px, lg 24px, xl 32px, xxl 48px, section 96px

## Border radius
none 0px, xs 2px, sm 4px, md 6px, lg 8px, pill 9999px

## Components (core)
- button-primary: blue bg, white text, 12px/16px padding, 0px radius
- button-primary-pressed: #002d9c bg
- button-secondary: charcoal bg, white text, 0px radius
- button-tertiary: white bg, blue text, 1px blue border
- button-danger: red bg, white text
- text-input: light gray bg, 11px/16px padding, 0px radius
- text-input-focused: "2px primary outline + 1px hairline-strong underline"
- text-input-error: red underline variant
- feature-card: white bg, 24px padding, 1px hairline border, 0px radius
- feature-card-elevated: light gray bg, same structure
- product-card: white bg, 32px padding, 0px radius
- product-tab: white bg, muted text, bottom hairline
- product-tab-selected: blue 2px bottom underline, body-emphasis weight
- customer-logo-tile: white bg, caption type, 1px border
- footer: charcoal bg, inverse text, 64px/32px padding

## Quoted principles
- "flat-square aesthetic where corners stay at 0-4px"
- "IBM Plex Sans at light weight 300 for display sizes (a brand signature)"
- "letter-spacing: 0.16px (a Carbon precision detail)"
- "only color in the system is one assertive blue - #0f62fe"
- "Card hierarchy carried by 1px hairlines and surface change, never by drop shadow"
