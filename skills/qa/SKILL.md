---
name: qa
description: Use when auditing landing page code against page specifications, design contracts, accessibility standards, and responsive requirements.
---

# QA Skill

Conduct a thorough, impartial verification of generated code against `page_spec.json`, `design_spec.json`, and `docs/QA_CHECKLIST.md`.

## Core Principle

**Strict, evidence-based gating over lenient assumptions.** Code either passes the contract or fails with specific, actionable defect details. Never grant a soft pass to broken syntax, missing sections, low contrast, or fabricated personal facts.

---

## Output Contract: `qa_report.json`

The QA agent must return a strict JSON object conforming to this schema:

```json
{
  "summary": "High-level audit summary detailing overall compliance and verification outcome.",
  "checks": [
    {
      "id": "content",
      "name": "Content & Sections",
      "status": "pass",
      "details": "All 8 sections from page_spec are present in order. Placeholders are preserved without fabricated metrics or fake employers."
    },
    {
      "id": "accessibility",
      "name": "Accessibility",
      "status": "pass",
      "details": "Semantic landmarks (<header>, <nav>, <main>, <section>, <footer>) used. Form inputs have explicit labels and interactive elements have visible focus rings."
    },
    {
      "id": "responsive",
      "name": "Responsive Design",
      "status": "pass",
      "details": "Grid breaks from 3 columns to 1 column on mobile. Mobile hamburger navigation implemented. No fixed overflow widths."
    },
    {
      "id": "engineering",
      "name": "Code Integrity & Syntax",
      "status": "pass",
      "details": "Valid syntax (HTML5 or React/TypeScript). Valid Lucide icon imports, complete component lifecycle, and no broken brackets."
    }
  ]
}
```

---

## 4 Mandatory Check Categories

Every `qa_report.json` must contain exactly these 4 check IDs:

1. **`content` (Content & Truthfulness):**
   - Verify every section in `page_spec.json` exists in the code.
   - Verify all facts are truthful; **fail immediately** if unverified claims, fabricated companies, or invented credentials appear.
   - Verify placeholders (e.g. `[Your Name]`, `[your.email@example.com]`) are properly preserved.

2. **`accessibility` (A11y & Contrast):**
   - Verify semantic tags (`<header>`, `<main>`, `<nav>`, `<section>`, `<footer>`).
   - Verify `aria-label` on icon-only buttons (mobile menu, social icons, scroll-to-top).
   - Verify focus states (`focus-visible:ring-2`) and color contrast.

3. **`responsive` (Cross-Device Behavior):**
   - Verify mobile hamburger menu exists for small viewports.
   - Verify grid/flex column drops (e.g. `grid-cols-1 md:grid-cols-2 lg:grid-cols-3`).
   - Verify no fixed widths that trigger horizontal scrolling on mobile.

4. **`engineering` (Code Quality & Build Integrity):**
   - For `html_css`: verify complete `<!doctype html>`, embedded `<style>`, matching tags.
   - For `react_ts`: verify valid JSX/TSX syntax, valid imports from `lucide-react`, clean TypeScript type annotations, and form state handling.

---

## Status Evaluation Rules

- `status` must be one of: `"pass"`, `"fail"`, or `"not_run"`.
- If **ANY** check has `status: "fail"`, the overall build is gated and must NOT be promoted to active preview.
- When failing a check, `details` must state the exact missing element or defect so the repair/revision agent can fix it.

---

## Rationalization Table

| Rationalization | Reality | Correct Action |
| :--- | :--- | :--- |
| "The author added cool statistics, so I'll let the content check pass." | Fabricated statistics violate trust and project rules. | Mark `content` as `fail` with details to use placeholders. |
| "A missing mobile menu is fine because most developers view on desktop." | Mobile responsiveness is a mandatory requirement in the design contract. | Mark `responsive` as `fail`. |
| "Missing label on contact input is a minor issue." | Screen readers cannot navigate unlabeled inputs. | Mark `accessibility` as `fail`. |
| "I'll edit the code myself during QA." | QA inspects and reports; only designated repair stages modify code. | Output strict defect report in `qa_report.json`. |
