# Duplicate Detection

## Requirements

### Requirement: REQ-DUP-1 Exact duplicates
Files with identical SHA-256 SHALL be grouped as duplicates.

#### Scenario: Same file downloaded twice
- WHEN `IMG_1.jpg` and `IMG_1 (1).jpg` are byte-identical
- THEN they form one duplicate group

### Requirement: REQ-DUP-2 Near duplicates
Images whose pHash Hamming distance is ≤ `near_dup_distance` (default 4) SHALL be grouped as duplicates,
as SHALL videos with that pHash distance whose durations differ by ≤ 0.5 s.
Grouping SHALL be transitive (union-find). Near-duplicate detection SHALL be optional (`detect_near_duplicates`, default on).

#### Scenario: Resized copy
- WHEN `beach.jpg` (4000×3000) and `beach_whatsapp.jpg` (1600×1200) show the same photo
- THEN they form one group

### Requirement: REQ-DUP-3 Keeper selection
In each group the system SHALL keep one file, chosen by most pixels, then largest size,
then earliest capture time, then shortest path. The keeper is categorized as usual. The other files
SHALL be assigned to the special category `Duplicates`, with destination `Organized/_Duplicates/`.

#### Scenario: Keep the best copy
- WHEN a group has a 12 MP original and a 2 MP copy
- THEN the 12 MP original is kept and the copy goes to `_Duplicates`

### Requirement: REQ-DUP-4 Never delete
Duplicates SHALL only ever be moved (or left alone in copy mode). The system SHALL NOT delete files.
