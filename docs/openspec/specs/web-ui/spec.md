# Web UI

A single-page app that follows the look of the reference demo: soft pink and white, an editorial serif
headline, big counters, folder cards, and a pile of thumbnails that flies into the folders.

## Requirements

### Requirement: REQ-UI-1 Layout
The page SHALL show:
- a header with the logo, the headline *"Sorting my **<folder>** folder"* (the folder name in italic serif),
  a status line, and a primary **Sort** button with the flower mark;
- a stats row: Total files · Videos · Photos · Folders created · Duplicates found;
- a stage with **Photos** category cards on the left, the **pile** in the center, and **Videos** cards plus the
  **Duplicates → trash** card on the right;
- at the end, a pink flower drawing with the caption *"a total mess"*, which turns into *"…not anymore"* once applied.

At widths under 900 px the columns SHALL stack (pile on top, then Photos, then Videos).

### Requirement: REQ-UI-2 Pile and fly animation
The animation SHALL be drawn on one canvas overlaying the stage:
1. During discovery, each `file` event adds a thumbnail sprite to a circular pile: a random position inside a disk,
   a random rotation of ±25°, a white 2 px border, rounded corners and a soft shadow. Sprites fade and scale in.
2. Each `assign` event queues a flight. Flights leave the pile at an adaptive rate, so a whole run takes about 4–10 s
   whatever the file count. Each sprite eases (cubic in-out, ~700 ms) along a slight arc
   to the next free slot in its category card, straightening its rotation to 0°.
3. Landed sprites stay drawn in a tight grid inside the card, following the card's current position on resize.
   The card's counter goes up when a sprite lands.
4. The stats counters SHALL count up smoothly.
5. With `prefers-reduced-motion`, sprites SHALL jump straight to their slots.

The animation SHALL hold 60 fps with 1,500 sprites on a typical laptop (sprites are cached ImageBitmaps).

### Requirement: REQ-UI-3 Settings drawer
A settings drawer (antd) SHALL let the user choose:
- the source folder (browsing the library tree);
- the strategy (`Preset` / `My categories` / `Auto-discover` / `By date`) as a segmented control;
- the preset or saved custom set; the date granularity;
- min confidence (slider), near-duplicate detection (switch), split photos/videos (switch), AI assist (switch, disabled with a tooltip when no key is set);
- apply mode (`move` / `copy`).
Settings SHALL persist in `localStorage`.

### Requirement: REQ-UI-4 Category editor
The user SHALL be able to create, edit, duplicate (from a preset), and delete custom category sets in a modal,
with one row per category (emoji, name, prompts as tags), and validation that matches REQ-CAT-2.

### Requirement: REQ-UI-5 Review and apply
After a job is done the UI SHALL:
- show **Apply** (primary) and **Re-run** buttons, and a summary (counts, AI tokens used, warnings);
- open a drawer listing a category's files when its card is clicked;
- after Apply, show a success notice with **Undo**, and list past runs in a "History" drawer, each with an Undo button.

### Requirement: REQ-UI-6 Tech
React 19 + TypeScript + Vite; antd 6 for complex widgets (Drawer, Modal, Select, Segmented, Slider, Switch,
Tree, notifications); shadcn/ui-style primitives (Button, Card, Badge) built on Tailwind CSS 4,
`class-variance-authority` and `tailwind-merge`. The UI is served by the backend from the same origin.
