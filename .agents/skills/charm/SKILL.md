---
name: charm
description: Warm, approachable design system with coral actions, cream surfaces, pill-shaped controls, and softly rounded panels — polished for SaaS, storefronts, dashboards, and onboarding flows.
license: MIT
metadata:
  author: reimplemented
---

# Charm Design System Skill (Universal)

## Mission
You are an expert design-system guideline author for Charm — a warm, production-ready design system.
Create practical, implementation-ready guidance that feels approachable and confident rather than cold or corporate.
Charm works equally well for expressive marketing pages and dense product interfaces.

## Brand
Warm surfaces, vivid coral actions, cream accent bands, pill-shaped controls, softly rounded panels.
The system must feel trustworthy and refined without becoming formal or sterile.

## Style Foundations

### Visual Style
- Warm, matte, approachable — not cold, not corporate, not sterile.
- Depth is created through tone changes, hairline borders, and spacing — NOT heavy shadows.
- Flat and untextured by default; one optional subtle line-pattern is permitted in the hero section only.

### Color Tokens

| Token         | Value     | Purpose                                      |
|---------------|-----------|----------------------------------------------|
| surface       | #F7F7F5   | Warm, matte content canvas (marketing pages) |
| panel         | #FBFAF9   | Cards, raised content surfaces               |
| accent-band   | #F1F2EA   | Hero and footer backgrounds                  |
| brand         | #E4544B   | Primary actions and brand emphasis           |
| brand-text    | #C9443A   | Accessible links and in-text accents         |
| heading       | #1C1917   | High-emphasis warm stone ink                 |
| body          | #57534E   | Primary reading text                         |
| muted         | #79716B   | Supporting copy, metadata, placeholders      |
| border        | #E7E6E5   | Subtle component boundaries                  |
| success       | #16A34A   | Real success states only — not decorative    |
| warning       | #D97706   | Real warning states only — not decorative    |
| danger        | #DC2626   | Real error/danger states only                |

**Rules:**
- Marketing content must use `surface` as the page background.
- Hero and footer sections must use `accent-band` and fade smoothly into the page.
- `brand` and `brand-text` are reserved for actions, links, focus rings, and intentional brand accents. Never use them decoratively.
- Status colors (`success`, `warning`, `danger`) are reserved for real functional states. Never use them for visual decoration.

### Typography

| Role      | Font          | Fallback         | Weights        | Notes                            |
|-----------|---------------|------------------|----------------|----------------------------------|
| Body/UI   | Inter         | system-ui, sans  | 400, 500, 600  | Controls, labels, body copy      |
| Display   | DM Sans       | sans-serif       | 700, 800       | Bold, tight letter-spacing       |
| Mono      | JetBrains Mono| monospace        | 400, 500       | Eyebrows, labels, code, tickers  |

**Type Scale (desktop-first):**
- `text-xs`:  12px / 1.5 — mono labels, eyebrows (uppercase + tracked)
- `text-sm`:  14px / 1.5 — supporting UI, captions
- `text-base`:16px / 1.6 — primary body copy
- `text-lg`:  20px / 1.5 — large body, intro paragraphs
- `text-xl`:  24px / 1.4 — section subheadings
- `text-2xl`: 32px / 1.3 — component headings
- `text-3xl`: 48px / 1.2 — page headings
- `text-4xl`: 60px / 1.1 — hero headings
- `text-5xl`: 72px / 1.05 — marketing display headings

**Rules:**
- Display headings must use DM Sans, bold (700+), tight letter-spacing (-0.02em to -0.03em).
- Eyebrows and uppercase labels must use JetBrains Mono, `text-xs`, `letter-spacing: 0.08em`, uppercase.
- Body and UI text must use Inter.
- Never mix display and body fonts in the same text block.

### Shape (Border Radius)

| Context                          | Radius  |
|----------------------------------|---------|
| Buttons, inputs, alerts, badges  | 9999px  (pill) |
| Cards, modals, drawers, tables   | 24px    |
| Menus, dropdowns, popovers       | 12px    |
| Textareas                        | 24px    (panel shape) |
| Checkboxes, radio indicators     | 4px     |

### Spacing Scale (4px base)
`4 / 8 / 12 / 16 / 24 / 32 / 48 / 64 / 96 / 128`

**Layout:**
- Max content container: `1280px`, centered with horizontal padding.
- Section vertical rhythm: generous (`64px–96px` between sections).
- Control group internal spacing: tight (`8px–12px`).

### Surface & Depth

| Layer                  | Treatment                                    |
|------------------------|----------------------------------------------|
| Default page           | `surface` background, no shadow              |
| Cards / Panels         | `panel` background + `border` hairline       |
| Buttons / Inputs       | Subtle control-lift shadow (1–2px, warm tint)|
| Menus / Popovers       | Medium floating shadow (8–16px, soft warm)   |
| Brand emphasis element | Optional coral glow (use sparingly)          |

- Must NOT use heavy drop shadows on cards or page sections.
- Depth hierarchy: tone change → border → spacing → shadow (in that order of preference).

## Accessibility
WCAG 2.2 AA minimum. All interactive elements must have visible focus states.
- Focus ring: 2px solid `brand` (#E4544B) with 2px offset — must be visible on all surfaces.
- Keyboard-first: all interactions must be fully operable via keyboard.
- Every contrast pairing must be testable: `body` on `surface` ≥ 4.5:1, `heading` on `surface` ≥ 7:1.
- `brand-text` (#C9443A) must always meet 4.5:1 against `surface`, `panel`, and `accent-band`.

## Writing Tone
Warm, confident, approachable. Clear over clever. Never formal or corporate. Concise labels.

## Rules: Do
- Use semantic color tokens — never raw hex values in component code.
- Use pill shape for all interactive controls (buttons, inputs, search, alerts).
- Separate surfaces with tone and border before reaching for shadows.
- Reserve `brand` coral exclusively for primary actions, links, and focus states.
- Use `accent-band` for hero and footer, fading into `surface` smoothly.
- Keep marketing sections flat and untextured (hero line-pattern is the one exception).

## Rules: Don't
- Don't use heavy box-shadows on cards or section containers.
- Don't apply `brand` or `brand-text` decoratively to non-interactive elements.
- Don't use status colors (success/warning/danger) for decoration.
- Don't use squared or sharp corners on buttons or inputs — pill is required.
- Don't mix DM Sans and Inter in the same heading.
- Don't place text directly on `accent-band` without verifying contrast.

## Component Language

### Primary Button
- Shape: pill (border-radius: 9999px)
- Background: coral gradient — `linear-gradient(135deg, #E87060 0%, #E4544B 60%, #D94A41 100%)`
- Label: white, Inter 600, 15–16px
- Shadow: `0 1px 3px rgba(228,84,75,0.25), 0 1px 2px rgba(0,0,0,0.06)` (control lift)
- Hover: lighten gradient slightly, lift shadow by 1px
- Focus-visible: 2px solid `brand` ring, 2px offset
- Active: darken gradient, flatten shadow
- Disabled: 40% opacity, no pointer events

### Secondary / Ghost Button
- Shape: pill, `border: 1.5px solid border-token`
- Background: transparent or `panel`
- Label: `heading` color, Inter 600
- Hover: `surface` background tint
- Focus-visible: same coral focus ring

### Cards / Panels
- Background: `panel` (#FBFAF9)
- Border: 1px solid `border` (#E7E6E5)
- Border-radius: 24px
- Shadow: none by default; control-lift only when interactive (e.g. clickable card)

### Inputs & Text Fields
- Shape: pill (border-radius: 9999px), except textarea (24px)
- Border: 1.5px solid `border`
- Background: white or `panel`
- Focus: border becomes `brand`, coral focus ring
- Placeholder: `muted` color
- Error state: border `danger`, error message in `danger` below field

### Navigation
- Background: `panel` or `surface`
- Links: `body` color, hover → `brand-text`
- Active link: `brand-text`, medium weight (600)
- Separator: `border` hairline

### Hero Section
- Background: `accent-band` (#F1F2EA), fading into `surface`
- Optional: one subtle SVG line-pattern behind content (low opacity, warm-tinted)
- Heading: DM Sans, 60–72px, `heading` color
- Subheading: Inter, 18–20px, `body` color

### Menus & Popovers
- Border-radius: 12px
- Background: white or `panel`
- Border: 1px solid `border`
- Shadow: `0 8px 24px rgba(28,25,23,0.10), 0 2px 6px rgba(28,25,23,0.06)`

## Expected Behavior
- Apply tokens and shape rules first; component-specific rules second.
- When uncertain between warmth and accessibility, always choose accessibility.
- Provide concrete token references for every color, spacing, and radius decision.
- Treat dense product UI (tables, dashboards, forms) with the same token discipline as marketing pages.

## Guideline Authoring Workflow
1. Restate the design intent in one sentence before proposing rules.
2. Define tokens and foundational constraints before component-level guidance.
3. Specify component anatomy, states, variants, and interaction behavior.
4. Include accessibility acceptance criteria and content-writing expectations.
5. Add anti-patterns and migration notes for existing inconsistent UI.
6. End with a QA checklist that can be executed in code review.

## Required Output Structure
When generating design-system guidance, use this structure:
- Context and goals
- Design tokens and foundations
- Component-level rules (anatomy, variants, states, responsive behavior)
- Accessibility requirements and testable acceptance criteria
- Content and tone standards with examples
- Anti-patterns and prohibited implementations
- QA checklist

## Component Rule Expectations
- Define required states: default, hover, focus-visible, active, disabled, loading, error (as relevant).
- Describe interaction behavior for keyboard, pointer, and touch.
- State spacing, typography, and color-token usage explicitly.
- Include responsive behavior and edge cases (long labels, empty states, overflow).

## Quality Gates
- No rule should depend on ambiguous adjectives alone; anchor each rule to a token, threshold, or measurable value.
- Every accessibility statement must be testable in implementation.
- Prefer system consistency over one-off local optimizations.
- Flag conflicts between aesthetics and accessibility, then prioritize accessibility.

## Example Constraint Language
- Use "must" for non-negotiable rules and "should" for recommendations.
- Pair every do-rule with at least one concrete don't-example.
- If introducing a new pattern, include migration guidance for existing components.

## Best Used For
Polished SaaS products, welcoming marketing sites, modern storefronts, customer dashboards, onboarding experiences, productivity tools, and service brands that should feel warm, trustworthy, and refined without becoming formal or sterile.
