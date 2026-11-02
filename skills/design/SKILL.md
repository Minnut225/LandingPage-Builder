---
name: design
description: Use when translating a page specification (page_spec.json) into a cohesive visual design system and design tokens (design_spec.json).
---

# Design Skill

Establish an implementable, high-contrast, cohesive visual system and design tokens (`design_spec.json`) based on `page_spec.json`.

## Core Principle

**Design system clarity over decorative clutter.** Every token must be explicit, measurable, and directly usable by frontend engineers without guesswork. Prioritize readability, WCAG AA color contrast, responsive consistency, and clear visual hierarchy.

---

## Output Contract: `design_spec.json`

The design agent must return a strict JSON object conforming to this schema:

```json
{
  "visual_direction": {
    "theme": "Modern Editorial & Futuristic Tech",
    "aesthetic": "Clean, high-contrast dark theme with sharp borders, glowing accents, and subtle gradients.",
    "mood": "Sophisticated, professional, reliable, and forward-looking"
  },
  "color_tokens": {
    "background_primary": "#101827",
    "background_secondary": "#1e293b",
    "background_tertiary": "#0b0f19",
    "surface_card": "#1e293b",
    "surface_card_hover": "#27354f",
    "text_primary": "#f1f5f9",
    "text_secondary": "#94a3b8",
    "text_muted": "#64748b",
    "accent_primary": "#2dd4bf",
    "accent_hover": "#14b8a6",
    "accent_glow": "rgba(45, 212, 191, 0.15)",
    "border_color": "rgba(148, 163, 184, 0.15)",
    "border_focus": "#2dd4bf",
    "success": "#10b981",
    "error": "#ef4444"
  },
  "typography": {
    "font_family_sans": "Inter, system-ui, sans-serif",
    "font_family_mono": "JetBrains Mono, Fira Code, monospace",
    "scale": {
      "display_hero": { "size_desktop": "3.5rem", "size_mobile": "2.25rem", "line_height": "1.1", "weight": "700" },
      "h1": { "size_desktop": "2.5rem", "size_mobile": "1.875rem", "line_height": "1.2", "weight": "700" },
      "h2": { "size_desktop": "2rem", "size_mobile": "1.5rem", "line_height": "1.25", "weight": "600" },
      "h3": { "size_desktop": "1.25rem", "size_mobile": "1.125rem", "line_height": "1.4", "weight": "600" },
      "body": { "size_desktop": "1rem", "size_mobile": "0.9375rem", "line_height": "1.6", "weight": "400" },
      "caption": { "size_desktop": "0.875rem", "size_mobile": "0.8125rem", "line_height": "1.5", "weight": "500" }
    }
  },
  "layout_system": {
    "container_max_width": "1280px",
    "grid_columns": 12,
    "gutter": "1.5rem",
    "section_padding_y": { "desktop": "5rem", "mobile": "3rem" },
    "breakpoints": {
      "mobile": "0px",
      "tablet": "768px",
      "desktop": "1024px",
      "wide": "1280px"
    }
  },
  "component_styles": {
    "button_primary": "bg-[#2dd4bf] text-[#101827] font-semibold px-6 py-3 rounded-lg hover:bg-[#14b8a6] transition",
    "button_secondary": "border border-[#94a3b8]/30 text-[#f1f5f9] px-6 py-3 rounded-lg hover:bg-[#1e293b] transition",
    "card": "bg-[#1e293b]/80 border border-[#94a3b8]/15 rounded-xl p-6 transition-all hover:border-[#2dd4bf]/40"
  },
  "responsive_rules": [
    "Nav collapses to hamburger menu on screens < 768px",
    "Hero layout switches from 2 columns on desktop to 1 stacked column on mobile",
    "Project grid displays 3 columns on desktop, 2 on tablet, and 1 on mobile",
    "Core skills displayed in 4 columns on desktop, 2 on tablet, 1 on mobile"
  ]
}
```

---

## Design Principles Checklist

- [ ] **Contrast Ratio:** Text on backgrounds must meet minimum WCAG AA contrast (4.5:1 for body, 3:1 for large text).
- [ ] **Focus States:** Every interactive button and link must specify an explicit focus ring (`focus-visible:ring-2 focus-visible:ring-accent`).
- [ ] **Color Economy:** Maximum 2-3 accent colors to avoid visual chaos.
- [ ] **Reduced Motion:** Interactive transitions should be fast (150ms-250ms), never jarring or disorienting.
- [ ] **Semantic Consistency:** Section IDs must strictly mirror those defined in `page_spec.json`.

---

## Rationalization Table

| Rationalization | Reality | Correct Action |
| :--- | :--- | :--- |
| "Low contrast gray text looks more sleek and minimalistic." | Unreadable text fails accessibility audits and frustrates real users. | Use `#94a3b8` or lighter on dark backgrounds. |
| "I will use 10 different colors for each project card." | Inconsistent color schemes look amateurish and fragment branding. | Anchor cards to unified surface tokens with subtle accent badges. |
| "I'll omit mobile typography since modern phones have high DPI." | Desktop font sizes on mobile cause horizontal overflow and awkward wraps. | Always define explicit desktop and mobile scales in typography tokens. |
