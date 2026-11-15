---
name: Attestatsiya UI
colors:
  surface: '#faf8ff'
  surface-dim: '#d2d9f4'
  surface-bright: '#faf8ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f3ff'
  surface-container: '#eaedff'
  surface-container-high: '#e2e7ff'
  surface-container-highest: '#dae2fd'
  on-surface: '#131b2e'
  on-surface-variant: '#434655'
  inverse-surface: '#283044'
  inverse-on-surface: '#eef0ff'
  outline: '#737686'
  outline-variant: '#c3c6d7'
  surface-tint: '#0053db'
  primary: '#004ac6'
  on-primary: '#ffffff'
  primary-container: '#2563eb'
  on-primary-container: '#eeefff'
  inverse-primary: '#b4c5ff'
  secondary: '#505f76'
  on-secondary: '#ffffff'
  secondary-container: '#d0e1fb'
  on-secondary-container: '#54647a'
  tertiary: '#943700'
  on-tertiary: '#ffffff'
  tertiary-container: '#bc4800'
  on-tertiary-container: '#ffede6'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dbe1ff'
  primary-fixed-dim: '#b4c5ff'
  on-primary-fixed: '#00174b'
  on-primary-fixed-variant: '#003ea8'
  secondary-fixed: '#d3e4fe'
  secondary-fixed-dim: '#b7c8e1'
  on-secondary-fixed: '#0b1c30'
  on-secondary-fixed-variant: '#38485d'
  tertiary-fixed: '#ffdbcd'
  tertiary-fixed-dim: '#ffb596'
  on-tertiary-fixed: '#360f00'
  on-tertiary-fixed-variant: '#7d2d00'
  background: '#faf8ff'
  on-background: '#131b2e'
  surface-variant: '#dae2fd'
typography:
  headline-lg:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.005em
  headline-sm:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 26px
  body-md:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 21px
  label-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '500'
    lineHeight: 24px
  label-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.02em
  code-inline:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1rem
  margin: 1rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.75rem
  space-lg: 1rem
  space-xl: 1.5rem
---

## Brand & Style

This design system supports a focused, low-cognitive-load mobile learning platform built for Uzbek computer science educators preparing for official national certification. The target audience spans ages 25 to 60, operating mid-range Android devices often under suboptimal lighting conditions or limited study windows between classes.

The design philosophy is strictly utilitarian, calm, and distraction-free:
- **Quiet Clarity:** Every screen removes visual noise. There are zero decorative illustrations, mascots, or arbitrary animations. Content and pedagogical progression remain the sole focus.
- **Academic Serenity:** Interactions mimic well-structured editorial examination papers rather than gamified consumer apps. Trust is established through predictable layouts, generous negative space, and disciplined typography.
- **Strictly Functional Iconography:** Icons serve purely navigational or state-clarifying purposes (e.g., checkmarks, warning flags, simple directional arrows). No emojis are permitted anywhere in the UI.
- **Cultural & Linguistic Tone:** The interface is localized in Latin-script Uzbek (`O‘zbek tili`), requiring deliberate spatial allowances for diacritics (such as inverted apostrophes `g‘`, `o‘`) and compound technical terms.

## Colors

The palette operates under rigorous functional constraints to prevent eye fatigue during prolonged test simulations and reading sessions.

### Surface and Canvas
- **Background Canvas:** `#F8FAFC` (Slate 50). Provides a soft, glare-reducing foundation that separates the display content from the physical bezel of mid-range displays.
- **Surface & Cards:** `#FFFFFF` (Pure White). Reserved for interactive zones, modular question blocks, and selectable list items.
- **Borders & Dividers:** `#E2E8F0` (Slate 200). A subtle, 1px structural boundary. Eliminates reliance on drop shadows to maintain rendering performance on hardware-constrained devices.

### Brand & Interactive Colors
- **Primary Accent:** `#2563EB` (Blue 600). Strictly assigned to focal calls-to-action, confirmed selections, and active pagination steps.
- **Primary Text:** `#0F172A` (Slate 900). High-contrast, WCAG AAA compliant text color for headlines, question prompts, and primary labels.
- **Secondary / Muted Text:** `#64748B` (Slate 500). Used for meta-information, question category badges, timer counters, and placeholder states.

### Feedback & Validation
Feedback states never rely on color alone; they must always pair with accompanying iconography (check or cross):
- **Success / Correct:** `#16A34A` (Green 600) for confirmed correct answers, completion indicators, and score tallies. Paired with background tint `#F0FDF4` and border `#BBF7D0`.
- **Danger / Incorrect:** `#DC2626` (Red 600) for erroneous choices, review warnings, and alert banners. Paired with background tint `#FEF2F2` and border `#FECACA`.

## Typography

Typography is standardized entirely on **Inter** across all UI tiers. Inter provides balanced horizontal proportions and open apertures, optimizing legibility for computer science code snippets, complex pedagogical prompts, and varied screen densities.

### Rules for Application
- **Generous Line Heights:** Reading comfort for teachers aged 25–60 demands relaxed line spacing. Body copy (`body-lg`) maintains a 1.625 ratio (`16px / 26px`), preventing line-skipping during lengthy problem statements.
- **Weight Restraint:** Limit weights to Regular (`400`), Medium (`500`), and Semi-bold (`600`). Bold (`700`) is avoided to keep visual hierarchy lightweight and academic.
- **Latin Script Diacritics:** In Uzbek Latin script, characters like `o‘`, `g‘`, `sh`, and `ch` occur frequently. Adequate line-height tokens guarantee that ascenders, descenders, and accompanying apostrophes do not overlap adjacent lines.
- **Code & Syntax Representation:** Inline technical terminology or code references within exam questions render in `code-inline` (14px/20px, Medium 500) against an isolated `#F1F5F9` background token to clearly distinguish logic from prose.

## Layout & Spacing

The mobile layout relies on a single-column, fluid structure constrained to standard handheld viewports (360dp to 428dp typical width). 

### Layout Model
- **Grid & Safe Regions:** A flexible 4-column system is used internally for metric overviews, while all interactive lists and question elements use full-width blocks within the gutter-bounded area.
- **Outer Canvas Margins:** Strict `16px` (`margin`) outer edge gutters protect content against accidental palm touches on modern edge-to-edge Android displays.
- **Vertical Rhythm:**
  - `space-xs` (4px): Micro-gaps between related sub-labels and icons.
  - `space-sm` (8px): Internal tag padding, gap between stacked meta-text rows.
  - `space-md` (12px): Standard spacing between form labels and inputs; padding within compact answer options.
  - `space-lg` (16px): Standard internal padding for cards and question blocks; gaps between stacked test questions.
  - `space-xl` (24px): Structural section division (e.g., separating question body from answer options, or separating header from progress tracking).

### Responsive Adaptation
- On devices narrower than 360dp, horizontal margins reduce to `12px` to maximize question readability without causing awkward word breaks in Uzbek technical compounds.
- Actions stick predictably to the screen base above the Android system navigation bar, pinned inside a persistent container padded with `space-lg`.

## Elevation & Depth

This system avoids layered dropshadows, blurs, and skeuomorphic bevels. Elevation is expressed entirely through **low-contrast outlines and tonal containment**:

- **Flat Layering:** Elevation 0 (Base Canvas) uses `#F8FAFC`. Elevation 1 (Card / Interactive Surface) uses `#FFFFFF` paired with a uniform `1px solid #E2E8F0` border.
- **Focused / Selected Surface:** Selected choices do not rise physically via shadow; instead, they transition their border to `1.5px solid #2563EB` with an optional subtle background shift to `#EFF6FF`.
- **Zero Skew & Zero Blur:** No ambient shadows or blur filters are allowed. This eliminates GPU overhead on entry-level Android chipsets and provides maximum clarity in direct sunlight.
- **Modal Sheets:** When required (e.g., question jump-lists), overlays slide upward on a pure `#FFFFFF` background with an anchoring top border `#E2E8F0` and a dark, non-blurred backdrop overlay `#0F172A` set at 40% opacity.

## Shapes

The geometric signature is disciplined, calm, and uniform:
- **Base Geometry:** A standard corner radius of `12px` (`0.75rem`) applies across all primary interactive surfaces, cards, input textboxes, and buttons.
- **Consistency Rule:** All corners within a composite component must match. A full-width option card with an embedded checkbox retains 12px outer rounding, preventing visual discordance.
- **Tags & Badges:** Small functional tags (e.g., topic labels like "Algoritmlar", timer pills) use a reduced `6px` radius (`space-sm` - 2px) to prevent them from looking like circular action pills.

## Components

### Buttons
- **Touch Standard:** All buttons enforce a mandatory minimum height of `48px` to guarantee physical accessibility under one-handed thumb navigation.
- **Single Primary Action:** Every screen permits exactly **one** primary solid button (`#2563EB` background, `#FFFFFF` text, 12px radius, full width). Examples include "Keyingisi" (Next) or "Testni yakunlash" (Finish test).
- **Secondary Action:** Outlined with `1px solid #E2E8F0`, `#0F172A` text, and `#FFFFFF` surface. Depressed state shifts background to `#F1F5F9`.
- **Disabled State:** Background `#F1F5F9`, text `#94A3B8`, border `#E2E8F0`. No pointer events.

### Multiple-Choice Option Cards (Test Engine)
- **Container:** Minimum height `56px`, `1px solid #E2E8F0`, background `#FFFFFF`, border-radius `12px`, padding `12px 16px`.
- **Default State:** Left-aligned question text in `body-lg` (`#0F172A`). Left indicator is a 20px circular ring (`1.5px solid #CBD5E1`).
- **Selected State:** Border switches to `1.5px solid #2563EB`, background becomes `#EFF6FF`. The circular ring fills with `#2563EB` featuring an internal white dot.
- **Validated Correct:** Border becomes `1.5px solid #16A34A`, background `#F0FDF4`. Leading indicator displays a crisp checkmark icon.
- **Validated Incorrect:** Border becomes `1.5px solid #DC2626`, background `#FEF2F2`. Leading indicator displays a crisp cross (X) icon.

### Form Inputs
- **Height & Frame:** `48px` height, `1px solid #E2E8F0`, `#FFFFFF` surface, `12px` radius, horizontal padding `16px`.
- **Typographic Scale:** Entered value is `16px` (`body-lg`) to prevent automatic iOS/Android webview zooming. Label sits above input in `label-md` (`#0F172A`).
- **Active State:** Focus ring uses `1.5px solid #2563EB`. Error state uses `1.5px solid #DC2626`.

### Chips & Badges
- **Question Number Chips:** `36px` square or proportional rounded boxes (12px radius) used in the exam overview matrix. Unvisited: `#FFFFFF` with `#E2E8F0` border. Answered: `#EFF6FF` with `#2563EB` border and text. Flagged: `#FEF2F2` with `#DC2626` text.
- **Topic Badges:** Background `#F1F5F9`, text `#475569`, font size `12px` (`label-sm`), vertical padding `4px`, horizontal padding `8px`, radius `6px`.

### Progress Indicator
- **Linear Bar:** `4px` height, full width across the top navigation bar. Track uses `#E2E8F0`; fill progress indicator uses `#2563EB` with straight, non-rounded ends.
- **Status Text:** Accompanying counter (e.g., "24 / 40 savol") rendered in `label-md` (`#64748B`).