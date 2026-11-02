# Quality & Culling

Photographer-grade checks that score every photo and separate keepers from rejects.

## Requirements

### Requirement: REQ-QC-1 Signals
For each photo the system SHALL compute, from a 2048 px decode (embedded preview for RAW):
sharpness (Laplacian variance on faces' eye regions when faces exist, else on the sharpest of 4×4 tiles, normalized 0..1),
mean brightness and clipped-shadow / clipped-highlight shares, and per face (MediaPipe Face Landmarker, tiled 1×1 + 2×2 + 3×3
detection so full-body and group shots are covered) blink and smile scores, box and area. Signals SHALL be cached; thresholds are
applied at classification time.

#### Scenario: Full-body couple shot
- WHEN faces cover under 2% of the frame
- THEN tiled detection still finds them and reports blink and smile per face

### Requirement: REQ-QC-2 Verdicts
A photo SHALL be flagged `blurry` (sharpness < `blur_threshold`), `eyes-closed` (blink ≥ `blink_threshold` on any face, or only the
largest face when `faces_rule = main`), `too-dark` / `too-bright` (brightness beyond `dark_threshold` / `bright_threshold` with > 25%
clipped pixels). Each check SHALL be switchable. `smiling` means every considered face smiles ≥ `smile_threshold`.

### Requirement: REQ-QC-3 Score & stars
Each analyzed photo SHALL get a 0..1 keeper score and 1–5 stars = 1 + round(score × 4). Cull mode SHALL use the genre-aware recommendation score (REQ-QC-8); quality overlays in other strategies retain the technical score.

### Requirement: REQ-QC-4 Best of burst
Photos in the same folder taken ≤ `burst_seconds` apart (consecutive by capture time) with CLIP cosine ≥ `burst_similarity` SHALL form a
burst. The best frame (not rejected, highest score) is kept; the others are `burst` extras.

#### Scenario: Three frames, one sharp
- WHEN three frames are 0.5 s apart and frame 2 scores highest
- THEN frame 2 is a keeper and frames 1 and 3 go to "Burst extras"

### Requirement: REQ-QC-5 Cull strategy
The `cull` strategy SHALL produce: Keepers, Smiling (if enabled), Maybe (keepers under `keeper_min_stars`), Blurry, Eyes closed, Too dark,
Too bright, Burst extras, Videos (only non-empty folders are created).

### Requirement: REQ-QC-6 Rejects overlay
With any other strategy and `quality.enabled`, `action = reject` SHALL move rejected photos and burst extras to `_Rejects/<reason>`;
`action = tag` only annotates the plan.

### Requirement: REQ-QC-7 RAW workflow
RAW files SHALL be decoded via the embedded preview. A RAW and a same-named JPEG/HEIC in the same folder SHALL be planned as one item
(the JPEG is analyzed, the RAW travels with it), and sidecars (`.xmp .aae .thm .pp3 .dop`) SHALL move with their photo under the same
collision-free stem; all moves are journaled and undoable.


### Requirement: REQ-QC-8 Explainable genre-aware recommendations
Cull SHALL rank analyzed photos even when the Picks folder is disabled. Profiles SHALL include auto, portrait,
fashion, landscape and general. The score SHALL combine technical focus/clipping/noise, expression when relevant,
composition, light and semantic presentation, with absolute and relative shoot/scene quality. Group and main-subject
preferences SHALL apply to both expressions and per-face eye-region focus. Fashion SHALL not require eye contact
or a smile. Mean brightness alone SHALL not penalize low-key work.

Top picks SHALL exclude enabled technical rejects, candidates below minimum recommendation quality and near-duplicates.
The requested percentage SHALL be an upper bound. Scene coverage SHALL favor useful variety. Review SHALL support
recommendation sorting and Top picks filtering; the viewer SHALL expose profile, components and reasons.

#### Scenario: Group photo with an out-of-focus important face
- WHEN two sizable faces have different eye focus
- THEN group ranking accounts for the weak face
- AND main-subject mode can use the largest face independently

### Requirement: REQ-QC-9 Consistent stars and labels
Keeper thresholds, displayed stars and exported XMP SHALL use the same recommendation score in Cull mode.
Picks SHALL receive Green labels, rejects SHALL receive rating -1/Red, and manual reassignment SHALL update the
pick marker and exported label. Undo SHALL restore originals and remove generated sidecars.
