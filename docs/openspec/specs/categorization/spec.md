# Categorization

Map every analyzed file to exactly one category. There are four strategies, and AI assist is optional.

## Data model
```jsonc
// Category
{ "id": "food", "name": "Food & cafés", "emoji": "🍜",
  "prompts": ["a photo of food on a plate", "a cozy café interior with coffee"] }
// CategorySet
{ "id": "lifestyle", "name": "Lifestyle", "categories": [Category, ...] }
```
A category without prompts uses `"a photo of {name}"`.

## Requirements

### Requirement: REQ-CAT-1 Built-in presets
The system SHALL ship these presets:
- **Lifestyle** (default): Selfies & portraits, Outfits & fashion, Food & cafés, Travel & vibe, Nature,
  Aesthetic spaces, Sport & wellness, Music & hobby, Work from home, Pets, Text & captions, Screenshots.
- **Travel**: Beaches & sea, Mountains & hiking, Cities & streets, Landmarks & monuments, Hotels & stays,
  Food & markets, Transport & airports, Night life, People & friends, Screenshots & tickets.
- **Creator**: Talking to camera, Outfits & try-ons, Product shots, B-roll scenery, Behind the scenes,
  Text & captions, Memes, Screenshots.
- **Documents**: Receipts & invoices, IDs & cards, Notes & whiteboards, Slides & charts, Screenshots, Photos (other).

#### Scenario: List presets
- WHEN the client calls `GET /api/presets`
- THEN all four presets come back with their categories

### Requirement: REQ-CAT-2 Custom categories
The user SHALL be able to define their own category set in the UI (name, optional emoji, optional prompts)
and save it under a name. Saved sets SHALL persist in `/data/category_sets.json` and be offered next to the presets.
A set SHALL have between 1 and 40 categories with unique, non-empty names.

#### Scenario: User-defined set
- WHEN the user creates "Wedding" with categories "Ceremony", "Dress", "Cake", "Dance floor"
- THEN a run with that set produces exactly those folders (plus `Unsorted` and `Duplicates` when they are needed)

#### Scenario: Invalid set
- WHEN a set has two categories called "Cake"
- THEN saving fails with `422` and a message saying which name is duplicated

### Requirement: REQ-CAT-3 Zero-shot classification (preset & custom)
For `preset` and `custom` strategies the system SHALL:
1. embed every prompt with the CLIP text encoder and average the prompts of each category into one vector;
2. compute `softmax(100 · cos(image, category))` across the categories;
3. assign the category with the highest probability when it is ≥ `min_confidence` (default `0.30`), and `Unsorted` otherwise.

The probability SHALL be kept on each assignment as its `confidence`.

#### Scenario: Low confidence
- WHEN a file's best probability is 0.22 and `min_confidence` is 0.30
- THEN it is assigned to `Unsorted` (unless AI assist reassigns it, see REQ-CAT-7)

### Requirement: REQ-CAT-4 Screenshot override
When the active set has a category whose id or name contains "screenshot", files flagged as screenshots
(REQ-ANL-5) SHALL go to it no matter what the classifier says.

### Requirement: REQ-CAT-5 Auto-discovery
For the `auto` strategy the system SHALL cluster the embeddings and name the clusters:
1. Choose k with KMeans over `k ∈ [2, min(16, n/3)]`, keeping the best silhouette score. Fewer than 6 files → one cluster.
2. **Naming with AI**: when an OpenAI key is configured, build one 3×2 contact sheet (≤ 6 thumbnails nearest
   the centroid, 384 px wide) per cluster and send **all sheets in one request** to the configured Luna model
   (`reasoning.effort=low`, `detail=low`, JSON output). The model returns a short folder name (≤ 3 words, Title case) and an emoji per cluster.
3. **Naming without AI**: score each centroid against a built-in vocabulary of more than 100 labels using the CLIP
   text encoder, and take the best label not already used.
4. Clusters that come out with the same name SHALL be merged.

#### Scenario: No API key
- WHEN `OPENAI_API_KEY` is not set
- THEN auto mode still completes, using vocabulary names

#### Scenario: One LLM call
- WHEN auto mode finds 9 clusters
- THEN exactly one naming request is made to OpenAI

### Requirement: REQ-CAT-6 By date
For the `date` strategy, the category SHALL be `YYYY/MM - MonthName` taken from the capture time
(REQ-SCAN-4). Granularity SHALL be configurable: `year`, `month` (default), or `day`.

#### Scenario: Month granularity
- WHEN a photo was captured on 2025-07-14
- THEN it is assigned to `2025/07 - July`

### Requirement: REQ-CAT-8 Photos and videos split
When `split_media` is on (default), the destination SHALL be `Organized/Photos/<Category>` for images
and `Organized/Videos/<Category>` for videos. When it is off, the destination SHALL be `Organized/<Category>`.

### Requirement: REQ-CAT-7 AI assist for uncertain files (optional)
When `ai_assist` is on and a key is configured, files under `min_confidence` (at most `ai_max_files`, default 200)
SHALL be sent to Luna in batches of up to 12 low-detail thumbnails per request. Each request carries the list of
category names, and the model answers in JSON with one category name or `"Unsorted"` per thumbnail.
Answers that do not match a category name SHALL be treated as `Unsorted`.

#### Scenario: Assist rescues a file
- WHEN a file has confidence 0.2 and Luna answers "Food & cafés"
- THEN the file is assigned to "Food & cafés" with `source: "ai"`

### Requirement: REQ-CAT-9 LLM efficiency and resilience
Every OpenAI request SHALL use the Responses API with the configured model (default `gpt-5.6-luna`),
`reasoning.effort=low`, `detail=low` images, a JSON output format, and a ≤ 60 s timeout.
On any OpenAI error the system SHALL fall back to the local behavior and record a warning on the job. It SHALL NOT fail the run.
Token usage SHALL be summed and reported on the job.
