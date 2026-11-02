---
name: frontend
description: Use when implementing accessible, responsive landing pages in HTML+CSS or React+TypeScript from page and design specifications.
---

# Frontend Skill

Implement production-ready, accessible, responsive landing page code strictly adhering to `page_spec.json` and `design_spec.json`.

## Core Principle

**Design contract fidelity and structural integrity.** Code what the specs specify. Do not add unrequested sections or invent personal data. Return ONLY the code artifact enclosed in appropriate markdown fences.

---

## Output Formats & Architecture

### Format 1: `html_css` (Standalone Single File)
- **File structure:** A single, complete `<!doctype html>` document.
- **Styling:** Embedded within `<style>` in `<head>`.
- **CSS Variables:** Define design tokens under `:root` matching `design_spec.json`.
- **Zero External JS:** No Node bundler, no heavy external JS libraries; lightweight native JS inside `<script>` for mobile menu toggling and scroll effects is allowed.

### Format 2: `react_ts` (Component for Vite + Tailwind)
- **File structure:** Self-contained `export default function App() { ... }` in `App.tsx`.
- **Imports:** Import standard React hooks (`useState`, `useEffect`, `FormEvent`) and icons from `lucide-react`.
- **Styling:** Use Tailwind CSS utility classes and inline styles with exact hex codes (e.g. `bg-[#101827]`, `text-[#2dd4bf]`).
- **Interactive States:**
  - Mobile hamburger drawer toggle (`mobileMenuOpen`).
  - Scroll-to-top button visibility and smooth scroll handler.
  - Active section observer for navigation highlights.
  - Contact form state machine: `'idle' | 'loading' | 'success' | 'error'`.
  - Notice on contact form: Transparent message stating backend submission is simulated/sample if API is unconfigured.

---

## Technical Standards & Accessibility (A11y)

1. **Semantic Landmarks:**
   - Use `<header>`, `<nav>`, `<main>`, `<section id="...">`, `<footer>`.
2. **Keyboard Navigation & Focus:**
   - All interactive elements (`<button>`, `<a>`, `<input>`, `<textarea>`) must have visible focus rings (`focus-visible:ring-2 focus-visible:ring-[#2dd4bf]`).
3. **Responsive Grid & Flexbox:**
   - Use CSS Grid and Flexbox with `max-w-7xl mx-auto px-4 sm:px-6 lg:px-8`.
   - Never use fixed pixel widths on parent containers that cause horizontal scrollbars on mobile (`320px` to `428px`).
4. **Anchor Integrity:**
   - Navigation links (e.g. `<a href="#projects">`) must match exact section IDs in the DOM (`<section id="projects">`).
5. **Form Labels:**
   - Every input must have an associated `<label htmlFor="...">` or `aria-label`.

---

## Scoped Revision Discipline

When revising existing code via `revision_request.json`:
- **Read `preserve` list first:** Sections listed in `preserve` must NOT be rewritten, refactored, or redesigned.
- **Targeted changes only:** Modify only the code necessary to address `target_section_ids` and `requested_changes`.
- **Never return diffs:** Always return the complete, runnable updated code artifact.

---

## Rationalization Table

| Rationalization | Reality | Correct Action |
| :--- | :--- | :--- |
| "I will replace the user's placeholders with fake credentials so it looks finished." | Fabricating personal history violates core rules and causes QA rejection. | Retain placeholders (`[Your Name]`, `[your.email@example.com]`). |
| "I'll simulate a 100% successful form submission without telling the user." | Deceptive UI implies a working email backend exists. | Include a clear disclaimer note: sample UI submission state. |
| "I'll rewrite the entire file during revision because it's easier." | Full rewrites introduce regressions to previously verified sections. | Keep existing sections intact; update only the targeted elements. |
| "I'll import an external UI component library (e.g. shadcn, mui)." | Output must run in standard Vite + Tailwind without extra unseen dependencies. | Build components natively with Tailwind and Lucide icons. |
