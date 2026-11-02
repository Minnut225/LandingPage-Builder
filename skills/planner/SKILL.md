---
name: planner
description: Use when converting a user brief into a truthful, structured page specification (page_spec.json) for a personal landing page.
---

# Planner Skill

Transform unstructured user requirements into a complete, truthful, and actionable page specification (`page_spec.json`) without fabricating any personal facts or metrics.

## Core Principle

**Truthful specification over creative fabrication.** Every factual statement (work history, employer names, degrees, statistics, metrics, testimonials) must come directly from the user's brief. Anything not explicitly provided must use obvious placeholders (e.g. `[Your Name]`, `[Company Name]`, `[Metric]`).

---

## Output Contract: `page_spec.json`

The planner agent must return a strict JSON object conforming to this schema:

```json
{
  "project_title": "Senior AI Engineer Portfolio",
  "audience": "Tech recruiters, engineering managers, and AI collaborators",
  "primary_goal": "Showcase expertise in LLM applications and scalable AI systems",
  "tone": "Modern, sophisticated, technologically advanced",
  "sections": [
    {
      "id": "header",
      "type": "navigation",
      "purpose": "Persistent navigation and quick action",
      "content_requirements": "Brand logo [Your Name], menu links to sections, CTA button 'Let's Connect'"
    },
    {
      "id": "hero",
      "type": "hero",
      "purpose": "High-impact introduction establishing core expertise",
      "content_requirements": "Headline, 2-sentence intro, CTA buttons ('Explore Work', 'Download CV'), expertise tags"
    },
    {
      "id": "about",
      "type": "about",
      "purpose": "Technical mindset and architectural philosophy",
      "content_requirements": "Background overview, technical pillars, 2-column layout"
    },
    {
      "id": "skills",
      "type": "skills",
      "purpose": "Categorized technical competencies",
      "content_requirements": "4 skill groups with icons and technology tags"
    },
    {
      "id": "projects",
      "type": "projects",
      "purpose": "Demonstrated technical achievements",
      "content_requirements": "Featured project cards with problem, solution, tech stack, and placeholder links"
    },
    {
      "id": "experience",
      "type": "experience",
      "purpose": "Career timeline and verified milestones",
      "content_requirements": "Chronological vertical timeline with role, company, dates, and achievements"
    },
    {
      "id": "contact",
      "type": "contact",
      "purpose": "Direct communication channel",
      "content_requirements": "Contact form (Name, Email, Message), social links, placeholder email"
    },
    {
      "id": "footer",
      "type": "footer",
      "purpose": "Copyright and secondary navigation",
      "content_requirements": "Copyright notice, back-to-top button, navigation links"
    }
  ]
}
```

---

## Standard Section IDs

Always use stable, lowercase section IDs so downstream design, frontend, and QA agents can reliably bind anchors and styles:
- `header` / `nav`
- `hero`
- `about`
- `skills`
- `projects`
- `experience`
- `contact`
- `footer`

---

## Anti-Hallucination Rules

| Category | Allowed | Strictly Prohibited |
| :--- | :--- | :--- |
| **Personal Identity** | `[Your Name]`, `[Your Title]` | Inventing names like "John Doe", "Alex Rivera" |
| **Work History** | Companies stated in brief or `[Company Name]` | Fabricating past employers (e.g. "Google", "Meta") |
| **Metrics & Claims** | Real numbers from brief or `[X% latency reduction]` | Inventing "99.9% accuracy", "10M+ users served" |
| **Social / Links** | User-provided URLs or `[GitHub Repository]` | Fabricating fake URLs (e.g. `github.com/alex-dev`) |
| **Email** | Real email or `[your.email@example.com]` | Inventing fake personal email addresses |

---

## Rationalization Table

| Rationalization | Reality | Correct Action |
| :--- | :--- | :--- |
| "A landing page looks better with real-sounding company names." | Fabricating employers damages user trust and breaks product guidelines. | Use explicit brackets: `[Previous Company]`. |
| "Users expect metrics like '10x performance boost'." | Unsubstantiated metrics are misleading and fail QA checks. | Use descriptive capabilities without invented numbers or use placeholders. |
| "The prompt didn't specify section order, so I'll invent unusual ones." | Standard portfolio flow builds logical credibility. | Follow: Nav -> Hero -> About -> Skills -> Projects -> Experience -> Contact -> Footer. |
