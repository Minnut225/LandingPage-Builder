---
name: revision
description: Use when converting human review feedback into a scoped, targeted revision plan (revision_request.json) while preserving existing approved sections.
---

# Revision Skill

Translate user feedback into a targeted, structured revision plan (`revision_request.json`) conforming to `docs/REVISION_PROTOCOL.md`.

## Core Principle

**Surgical scope over blanket redesign.** Address user feedback with the smallest necessary set of changes. Explicitly protect already approved sections in the `preserve` list to prevent unintended regressions.

---

## Output Contract: `revision_request.json`

The revision agent must return a strict JSON object conforming to this schema:

```json
{
  "source_version": 1,
  "target_section_ids": [
    "hero",
    "contact"
  ],
  "change_categories": [
    "color",
    "content"
  ],
  "requested_changes": [
    "Change the hero primary CTA background color from #2dd4bf to violet #8b5cf6 with hover state #7c3aed.",
    "Update the contact section description to specifically invite discussions on autonomous agent architectures."
  ],
  "preserve": [
    "header",
    "about",
    "skills",
    "projects",
    "experience",
    "footer"
  ],
  "constraints": [
    "Retain responsive mobile drawer navigation.",
    "Do not alter typography scales in preserved sections.",
    "Maintain high-contrast readability against dark background."
  ]
}
```

---

## Translation Rules: Subjective to Actionable

Convert subjective user requests into concrete design token and structural instructions:

| User Feedback | Misguided Interpretation | Actionable Revision Specification |
| :--- | :--- | :--- |
| *"Make the hero pop more"* | Adding flashing animations or 5 different bright colors | Increase hero headline font weight/size; add subtle radial gradient glow behind hero visual; intensify primary CTA contrast. |
| *"Too cramped on mobile"* | Removing entire content blocks | Increase section padding Y on mobile (`py-8` -> `py-12`); increase card gutters from `gap-3` to `gap-6`. |
| *"Make it look more corporate"* | Rewriting all text to sound dry | Shift accent from vibrant neon teal to professional sapphire blue (`#2563eb`); reduce border glow; square card corners (`rounded-lg` -> `rounded-md`). |
| *"Fix button contrast"* | Changing all button colors across the site | Update primary button background to `#2dd4bf` with text `#0f172a` (contrast > 10:1); add visible focus ring. |

---

## Versioning & Preservation Rules

1. **Explicit Preservation:**
   - Any section not explicitly requested to change in `target_section_ids` MUST be included in the `preserve` array.
2. **Append-Only History:**
   - Revisions always create a candidate version `v(N+1)`. Never overwrite or mutate the active version or previous versions.
3. **No Automatic Approval:**
   - The revision agent only plans changes; only the human user can approve a version.

---

## Rationalization Table

| Rationalization | Reality | Correct Action |
| :--- | :--- | :--- |
| "The user asked to change one button, but I will redesign the whole header too." | Unsolicited changes break user expectations and destroy approved work. | Confine changes strictly to the requested element. |
| "I don't need a preserve list since the developer knows what to keep." | Without an explicit preserve list, LLMs frequently alter or simplify untouched sections. | Enumerate every untouched section in `preserve`. |
| "User feedback is too brief, so I'll guess their secret intent." | Guessing creates misaligned designs. | Translate literal instructions into token adjustments; ask for clarification if fundamentally ambiguous. |
