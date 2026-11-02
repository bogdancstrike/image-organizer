"""HTTP request validation; domain services receive validated inputs."""
from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field, field_validator, model_validator

RESET_PHRASE = "delete all data"

class QualityOptions(BaseModel):
    enabled: bool = False  # run checks with any strategy (always on for "cull")
    blur: bool = False
    eyes_closed: bool = False
    exposure: bool = False
    smiles: bool = False
    blur_threshold: float = Field(0.5, ge=0.0, le=1.0)
    blink_threshold: float = Field(0.5, ge=0.05, le=1.0)
    smile_threshold: float = Field(0.5, ge=0.05, le=1.0)
    action: Literal["reject", "tag"] = "reject"  # reject = move to _Rejects/<reason>
    faces_rule: Literal["any", "main"] = "any"  # whose eyes/smile count: any face, or the main (largest) face
    dark_threshold: float = Field(0.18, ge=0.0, le=0.5)
    bright_threshold: float = Field(0.85, ge=0.5, le=1.0)
    bursts: bool = False  # best-of-burst: keep the best of near-identical shots seconds apart
    burst_seconds: float = Field(2.0, ge=0.2, le=30.0)
    burst_similarity: float = Field(0.9, ge=0.75, le=0.99)
    keeper_min_stars: int = Field(0, ge=0, le=5)  # cull: keepers below this go to "Maybe" (0 = off)
    noise_check: bool = False
    noise_threshold: float = Field(0.045, ge=0.005, le=0.2)
    tilt_check: bool = False  # experimental: consistent horizon lines leaning 1.5–8°
    tilt_tolerance: float = Field(1.5, ge=0.5, le=8.0)
    face_crop: bool = False
    subject_prompt: str = Field("", max_length=300)
    social_media: bool = False
    social_aesthetic: bool = True
    social_format: Literal["portrait", "square", "vertical", "landscape", "original"] = "portrait"
    social_weight: float = Field(.25, ge=0, le=.5)
    preserve_unique: bool = True
    pareto_review: bool = True
    pick_min_rating: float = Field(4.5, ge=1, le=5)
    keeper_min_rating: float = Field(4.0, ge=1, le=5)
    pick_profile: Literal["auto", "portrait", "fashion", "landscape", "general"] = "auto"
    picks_percent: float = Field(0, ge=0, le=50)  # deprecated: accepted for older clients; decimal rating bands determine picks
    similar_any_time: bool = False  # best-of-similar regardless of time, not just bursts
    write_xmp: bool = False  # on apply, write .xmp sidecars with star rating and color label

    @model_validator(mode="after")
    def _rating_bands(self):
        if self.keeper_min_rating > self.pick_min_rating:
            raise ValueError("Keepers threshold must not exceed Picks threshold")
        return self


class AIOptions(BaseModel):
    model: str | None = Field(None, pattern=r"^[A-Za-z0-9._:-]{1,64}$")  # None = server default
    reasoning_effort: Literal["minimal", "low", "medium", "high"] | None = None
    naming_prompt: str = Field("", max_length=4000)  # full template; "" = default (GET /api/ai/defaults)
    assist_prompt: str = Field("", max_length=4000)
    assist_scope: Literal["unsure", "all"] = "unsure"  # AI assist on uncertain files only, or on every file
    naming_instructions: str = Field("", max_length=1500)  # extra guidance for naming auto groups
    assist_instructions: str = Field("", max_length=1500)  # extra guidance for AI assist
    assist_batch: int = Field(12, ge=1, le=24)  # thumbnails per assist request


class JobOptions(BaseModel):
    rules_prompt: str = Field("", max_length=4000)
    min_confidence: float = Field(0.30, ge=0.0, le=1.0)
    near_duplicates: bool = True
    near_dup_distance: int = Field(4, ge=0, le=16)
    split_media: bool = True
    duplicates_action: Literal["folder", "with_original", "keep"] = "folder"
    @field_validator("duplicates_action", mode="before")
    @classmethod
    def _legacy_duplicate_action(cls, value):
        return "folder" if value == "delete" else value

    duplicate_keep: Literal["best", "oldest", "newest"] = "best"
    ai_assist: bool = False
    ai_max_files: int = Field(200, ge=1, le=5000)
    date_granularity: Literal["year", "month", "day"] = "month"
    max_clusters: int = Field(12, ge=2, le=30)
    model: Literal["clip", "siglip2"] = "clip"  # recognition model: CLIP (fast) or SigLIP 2 (more accurate)
    auto_tags: bool = True
    ocr: bool = False  # read text in photos: text-heavy ones go to the set's text/documents folder
    ocr_min_chars: int = Field(25, ge=1, le=2000)
    ocr_min_coverage: float = Field(0.03, ge=0.0, le=1.0)
    people_min_photos: int = Field(3, ge=1, le=100)  # by person: smaller groups go to "Other people"
    people_similarity: float = Field(0.363, ge=0.2, le=0.8)  # SFace cosine: higher = stricter "same person"
    people_group_size: int = Field(3, ge=2, le=20)  # this many sizable faces = "Groups"
    people_multi: Literal["main", "copy"] = "main"
    people_appearance: bool = True  # recognize people whose face isn't visible by outfit & look
    place_granularity: Literal["country", "city"] = "country"  # "places" strategy
    trip_away_km: float = Field(80, ge=10, le=2000)  # "trips": farther than this from home = away
    trip_gap_hours: float = Field(36, ge=6, le=240)  # a longer gap between away photos starts a new trip
    trip_min_photos: int = Field(5, ge=1, le=200)
    people_reference: str | None = Field(None, pattern=r"^[a-f0-9]{12}$")  # only this uploaded face (GET /api/faces)  # several people in a photo: main face only, or a copy per person
    focus: Literal["auto", "scene", "framing", "outfit", "lighting", "subject"] = "auto"  # what auto groups by
    granularity: Literal["coarse", "normal", "fine"] = "normal"
    ai: AIOptions = Field(default_factory=AIOptions)
    # where the category folders go: None = server default (OUTPUT_DIR_NAME), "" = directly in the chosen folder
    output_dir: str | None = Field(None, max_length=60, pattern=r'^[^/\\:*?"<>|]*$')
    recursive: bool = True
    pair_sidecars: bool = True  # keep RAW+JPEG pairs and .xmp sidecars together
    quality: QualityOptions = Field(default_factory=QualityOptions)

    @field_validator("output_dir")
    @classmethod
    def _no_dots(cls, v: str | None) -> str | None:
        if v is not None and v.strip() in (".", ".."):
            raise ValueError("invalid folder name")
        return v


class JobRequest(BaseModel):
    source: str = ""
    strategy: Literal["preset", "custom", "auto", "date", "cull", "people", "trips", "places", "rules"] = "preset"
    set_id: str | None = "lifestyle"
    options: JobOptions = Field(default_factory=JobOptions)

    @model_validator(mode="after")
    def _rules_prompt(self):
        if self.strategy == "preset" and self.set_id == "social-media":
            self.strategy = "cull"
            self.options.quality.social_media = True
        if self.strategy == "rules" and not self.options.rules_prompt.strip():
            raise ValueError("Describe how to sort photos in options.rules_prompt")
        return self


class ReassignRequest(BaseModel):
    file_ids: list[str] = Field(min_length=1, max_length=20000)
    category_id: str


class ResetRequest(BaseModel):
    confirm: str = Field(..., max_length=100)
    include_cache: bool = False


class RenameRequest(BaseModel):
    name: str = Field(min_length=1, max_length=60)


class ApplyRequest(BaseModel):
    mode: Literal["move", "copy"] = "move"
