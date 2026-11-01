# Media Analysis

Turn each file into what the later steps need: a thumbnail, a CLIP embedding, content hashes,
and a few cheap signals.

## Requirements

### Requirement: REQ-ANL-1 Thumbnails
The system SHALL produce a WebP thumbnail (longest side 160 px) for each file and serve it over HTTP.
Thumbnails for videos SHALL be taken from a frame at about 30% of the video's duration.
EXIF orientation SHALL be applied.

#### Scenario: Portrait iPhone photo
- WHEN a HEIC photo carries orientation 6
- THEN its thumbnail is upright

### Requirement: REQ-ANL-2 Image embeddings
The system SHALL compute an L2-normalized CLIP ViT-B/32 image embedding (512-d) for each image
using a local ONNX model. The model SHALL be bundled in the Docker image, so it needs no download at runtime.

#### Scenario: Offline embedding
- WHEN the container has no network access
- THEN images are still embedded

### Requirement: REQ-ANL-3 Video embeddings
For each video the system SHALL extract up to 3 keyframes (at 20%, 50% and 80% of its duration)
with ffmpeg, embed each one, and use their normalized mean as the video's embedding.

#### Scenario: Short clip
- WHEN a video is 2 seconds long
- THEN it still gets an embedding from frames inside that range

### Requirement: REQ-ANL-4 Hashes
The system SHALL compute a SHA-256 of the file's bytes for each file and a 64-bit perceptual hash
(pHash) of each image and of each video's middle frame.

#### Scenario: Re-encoded copy
- WHEN `a.jpg` and `a_small.jpg` are the same photo at different sizes
- THEN their pHash Hamming distance is small (≤ 6)

### Requirement: REQ-ANL-5 Screenshot signal
The system SHALL flag an image as a likely screenshot when at least one holds:
its filename matches `screenshot|screen shot|scr_|captura|bildschirmfoto` (ignoring case), OR
it is a PNG without camera EXIF data whose aspect ratio is portrait and ≥ 1.7.

#### Scenario: Phone screenshot
- WHEN `Screenshot_2026-05-01.png` is analyzed
- THEN it is flagged as a screenshot

### Requirement: REQ-ANL-6 Cache
The system SHALL cache analysis results in SQLite under `/data`, keyed by `(absolute path, size, mtime)`.
A file whose key is unchanged SHALL NOT be analyzed again.

#### Scenario: Second run
- WHEN the same folder is analyzed twice with no changes
- THEN the second analysis performs zero embedding computations

### Requirement: REQ-ANL-7 Fault tolerance
A file that cannot be decoded SHALL be reported as `error` with a reason. It SHALL be left out of
categorization and SHALL NOT abort the run.

#### Scenario: Corrupt JPEG
- WHEN `broken.jpg` holds random bytes
- THEN the run completes and `broken.jpg` appears in `errors`

### Requirement: REQ-ANL-8 Parallelism
Decoding and thumbnailing SHALL run on a thread pool (default: number of CPUs). Embeddings SHALL be
computed in batches (default 32).
