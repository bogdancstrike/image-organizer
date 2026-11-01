# Library Scanning

Find the media files in the chosen source folder and collect their basic metadata.

## Requirements

### Requirement: REQ-SCAN-1 Media discovery
The system SHALL walk the source folder recursively and collect files whose extension is a supported
image type (`jpg jpeg png webp gif bmp tiff heic heif avif`) or video type (`mp4 mov m4v webm mkv avi 3gp`).
Matching SHALL ignore case.

#### Scenario: Mixed folder
- WHEN the source folder contains `a.JPG`, `b.mov`, `notes.txt`, and `sub/c.heic`
- THEN the scan returns `a.JPG` and `sub/c.heic` as images and `b.mov` as a video
- AND `notes.txt` is ignored

### Requirement: REQ-SCAN-2 Skip managed and hidden folders
The system SHALL skip hidden files and folders (names starting with `.`) and the output root folder
(default `Organized`), so a second run never re-sorts files that are already organized.

#### Scenario: Re-run after apply
- WHEN `Organized/Photos/Nature/x.jpg` exists in the source folder
- THEN `x.jpg` is not part of the next scan

### Requirement: REQ-SCAN-3 Path containment
The system SHALL resolve every requested source folder inside the library root and SHALL reject
paths that escape it (for example `../`, absolute paths outside it, or symlinks pointing outside).

#### Scenario: Traversal attempt
- WHEN a client asks to scan `../../etc`
- THEN the API answers `400` and nothing is scanned

### Requirement: REQ-SCAN-4 Metadata
For each file the system SHALL record its relative path, size, modification time, kind (`image`/`video`),
and its capture time from EXIF `DateTimeOriginal` for images, or `creation_time` from ffprobe for videos.
When neither is available, the capture time SHALL fall back to the modification time.

#### Scenario: Photo without EXIF
- WHEN `x.png` has no EXIF data
- THEN its capture time equals its modification time

### Requirement: REQ-SCAN-5 Folder browsing
The system SHALL expose the library's subfolders (one level per request) with their media counts,
so the user can choose a source folder in the UI.

#### Scenario: Pick a folder
- WHEN the UI requests the folders under `/`
- THEN it receives the immediate subfolders, without hidden ones and without the output root
