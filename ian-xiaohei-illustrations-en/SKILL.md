---
name: ian-xiaohei-illustrations-en
description: 'Generates Ian-style "Xiaohei" surreal article illustrations for English writing. Use when the user asks to design or generate article illustrations, blog visuals, Notion diagrams, workflow sketches, metaphor illustrations, "shot list" planning, or to edit/regenerate an existing illustration. Triggers on requests like "article illustrations", "blog diagrams", "hand-drawn", "Xiaohei", "surreal", "shot list", "remove title", "regenerate with stronger Xiaohei", or any request to turn a judgment, process, state, or metaphor into one memorable 16:9 hand-drawn diagram. Default style: pure white background, black hand-drawn line art, sparse red/orange/blue handwritten English annotations, deadpan Xiaohei character performing the core action, clean but bizarre product-sketch feeling. Not for commercial illustration, flat brand key visuals, or cute mascot posters.'
metadata:
  author: agentskills (adapted from helloianneo/ian-xiaohei-illustrations)
  compatibility: 'Requires an image generation model that follows 16:9 aspect ratio and supports text/label rendering. Designed for single-image generation per illustration, not multi-panel composites.'
---

## Goal

Design and generate 16:9 horizontal article illustrations for English writing. The goal is not commercial illustration, slide infographics, or cute cartoons. It is to turn a key judgment, process, structure, state, or metaphor from the article into one memorable hand-drawn explanation diagram that is clean, slightly absurd, and creative — readable but not instructional.

The default visual IP is "Xiaohei" (小黑, literally "little black"): a small solid-black creature with white dot eyes, thin legs, and a blank expression, earnestly doing something absurd but coherent. Xiaohei must perform the core action of the scene, not stand in the corner as decoration.

## Read these references as needed

Load only what the task requires. Do not dump everything into context at once.

- `references/style-dna.md` — visual DNA, color rules, taboos.
- `references/xiaohei-ip.md` — Xiaohei character, personality, action library, taboos.
- `references/composition-patterns.md` — structure types, original-metaphor method, no-recycling rules.
- `references/prompt-template.md` — single-image generation prompt template.
- `references/qa-checklist.md` — post-generation checklist and iteration rules.

## Workflow

### 1. Digest the source

Read the article, post, link, Notion page, Markdown file, screenshot, or topic the user provides. Extract:

- The core claim or argument.
- Which paragraphs carry the cognitive turn.
- Which content is best explained visually.
- Which content is best left as plain prose.

Do not distribute illustrations evenly. Prioritize "cognitive anchors": core judgments, two-breakpoint comparisons, input/output loops, splits, before/after states, one-to-many reuse, handoff paths, common pitfalls, and character-state changes.

### 2. Produce a shot list first

If the user only asks to "analyze where to add illustrations" or "plan illustrations", output a shot list first. For each illustration include:

- Which paragraph it should follow.
- Topic of the illustration.
- Core meaning.
- Structure type.
- What Xiaohei is doing in the frame.
- Suggested elements.
- Suggested short English annotation words.

Default to 4-8 illustrations. Short articles: 1-3. Long articles: do not exceed 9 even for very long pieces. Enough is enough; do not turn the article into a picture book.

### 3. Generate one image at a time

When the user explicitly asks to "generate / output / make the image", do not stop to confirm. Use the available `image_gen` tool, one call per illustration. Never stitch multiple illustrations into a single image.

Each image must show only one core structure. The prompt must include:

- 16:9 horizontal English article illustration.
- Pure white background.
- Black hand-drawn line art.
- Sparse red/orange/blue handwritten English annotations.
- Generous negative space.
- Xiaohei as the actor performing the core action.
- Forbidden: slide deck, commercial illustration, childish mascot, complex architecture diagram, top-left type title.

Do not recycle past cases. The reference examples exist only to calibrate line density, whitespace, color restraint, and Xiaohei's involvement. Do not directly reuse "conveyor belt break / Xiaohei pulling wires / material fish / stamped script toolbox / common-pit path" and other existing compositions unless the user explicitly asks to reproduce a specific prior image. Always invent a new strange-but-coherent metaphor for the current article.

### 4. Check and iterate

After generation, run through `references/qa-checklist.md`. If any of these appear, prefer to regenerate or surgically edit:

- Xiaohei is decorative only.
- Frame is too full.
- Looks like a slide or formal flowchart.
- Too much text or severe spelling/garbled text in the image.
- A title like "Workflow / Process / System Diagram / Common Pitfalls" appears in the top-left.
- Style drifts cute, childish, or stiff.
- Background is not clean white.

### 5. Save the deliverables

When working inside a workspace, copy the final images to:

```text
assets/<article-slug>-illustrations/
```

Name them in order:

```text
01-topic-name.png
02-topic-name.png
```

Keep the original generated files; do not overwrite existing assets unless the user explicitly asks to replace them.

## Output shape

Pre-generation strategy output should be short and precise. Post-generation delivery should include:

- How many images were generated.
- The purpose of each image.
- The save path.
- Which images are the most stable, which are optional.

Do not write a long essay about style theory. Let the images speak.
