# Culling methods and verification

The supplied 50-idea article is an implementation checklist, not evidence that an app using these methods matches
professional selections. This implementation covers the following 31 core ideas, plus the scoped extensions below.
“Existing” identifies a method already present before this expansion; “added” and “strengthened” identify this work.

| Article idea | Implementation and scope | Status | Verification |
|---|---|---|---|
| 1 Laplacian variance | Global/tile detail and face-region focus in `quality.py` | Existing | `test_sharpness_detects_blur` |
| 2 Tenengrad | Sobel gradient energy supplements focus, with a small weight | Added | `test_advanced_gradients_and_thumbnail_detail_decrease_with_blur` |
| 3 Multi-scale sharpness | Edge persistence across resolutions discounts noise-like fine detail | Strengthened | `test_multiscale_detail_distinguishes_noise_from_real_edges` |
| 4 Subject-aware focus | Focus on detected faces; sharpest tile fallback without faces. No object segmentation model | Strengthened | `test_group_focus_uses_the_weakest_important_face_but_honors_main_subject` |
| 5 Eye-region focus | Upper face regions use the larger analysis image (up to 2048 px), independently per face. Not an eyelash detector | Strengthened | `test_detected_face_eye_focus_is_cached_with_the_new_analysis_version` |
| 6 Highlight clipping | Preview highlight fractions inform technical quality and optional rejects | Existing | `test_dark_intentional_photo_is_not_punished_for_mean_brightness` |
| 7 Shadow clipping | Shadow fractions; mean brightness alone does not penalize low-key photographs | Existing | `test_verdicts` and intentional-dark test |
| 8 Exposure suitability | Context/profile scoring and user-controlled exposure checks | Existing | `test_cull_strategy_and_reject_overlay` |
| 11 Face quality | YuNet confidence, size and landmark geometry qualify identity anchors; readable face regions exposed for review | Strengthened | `test_identity_anchors_require_readable_landmarks_and_confident_detection` |
| 12 Eye-open assessment | MediaPipe blendshapes and readable per-face counts | Strengthened | `test_expression_prefers_open_eyes_and_camera_gaze` |
| 13 Expression suitability | Mouth/gaze/smile/squint signals, genre-dependent | Existing | `test_fashion_profile_does_not_require_eye_contact_or_a_smile` |
| 14 Group expressions | Worst/average important-face fusion and main-subject preference | Existing | `test_main_face_preference_and_small_background_faces` |
| 15 Head pose/gaze | Landmark-based head turn and blendshape gaze; fashion permits looking away | Existing | `test_expression_extracts_gaze_mouth_and_head_turn_from_landmarks` |
| 16 Exact duplicates | SHA-256; explicit duplicate group and keeper policy | Existing | `test_core.py` duplicate tests |
| 17 Perceptual hash | pHash candidate detection with embedding confirmation | Existing | `test_core.py` near-duplicate tests |
| 18 Difference hash | Additional spatial-gradient guard for near-duplicate merging; cached values backfilled from thumbnails | Added | `test_difference_hash_does_not_merge_distinct_burst_frames` |
| 19 Embedding similarity | Local CLIP/SigLIP similarity for scenes, groups and diversity | Existing | `test_select_tells_the_story_and_skips_near_duplicates` |
| 20 Temporal bursts | Capture time, same-folder scope and embedding similarity | Existing | `test_find_bursts` |
| 21 Thirds/centering | Weak face-placement geometry; centered compositions are valid | Existing | `test_composition_thirds_and_cut_faces` |
| 22 Horizon geometry | Consistent line orientation; optional experimental reject check | Existing | `test_horizon_tilt_needs_consistent_lines` |
| 23 Crop integrity | Face/frame intersection plus social crop-retention assessment; no limb/pose detector | Strengthened | `test_crop_suitability_preserves_important_faces_and_originals` |
| 24 Visual balance | Gradient centroid/border energy combined with semantic composition | Strengthened | `test_multiscale_detail_distinguishes_noise_from_real_edges` |
| 30 Aesthetic embedding ranker | Bundled LAION V1 linear head on verified OpenAI CLIP B/32 vectors; optional Social Media component, CPU NumPy | Added | `test_aesthetics.py`: original-model parity, wrong-space rejection, caching and shortlist limits |
| 32 Scene classification | Local semantic tags and genre inference, rather than event-specific trained classification | Strengthened | `test_semantic_genre_auto_detection_and_fallbacks` and tagging tests |
| 33 Prompt relevance | Optional local photographer subject-priority prompt influences ranking | Added | `test_social_overlay_subject_relevance_pareto_and_novelty_are_explainable` |
| 35 Novelty | Nearest-view distance within scenes gives a small contribution; separate Unique views filter | Added | Social overlay/novelty test and comparison filter test |
| 37 Noise estimation | Immerkær estimate discounts noise; optional user threshold | Existing | `test_noise_estimate_separates_grainy_from_clean` |
| 41 Multi-objective fusion | Genre weights, absolute quality and shoot/scene comparisons; optional social overlay | Strengthened | Rank/profile and decimal rating-band tests |
| 43 Pareto alternatives | Identify images not dominated in all quality dimensions within a scene; expose for review | Added | Social overlay/Pareto test and comparison filter test |
| 44 Diverse selection | Scene quotas and near-duplicate suppression; high-rated alternatives retain their ratings | Strengthened | `test_select_tells_the_story_and_skips_near_duplicates` |
| 48 Context adaptation | Portrait, fashion, landscape, group/general criteria plus optional social posting-readiness overlay | Strengthened | Genre/fashion/landscape and social-format tests |

Additional scoped ideas: #25 uses edge/semantic background separation, not object-aware distraction detection;
#36 reports directional edges, not a trained motion-blur diagnosis; #38 measures block-boundary artifacts, not
BRISQUE/NIQE; #42 compares composite scores within bursts and reports the best/runner-up margin, not a learned
pairwise preference model; #45 routes uncertain/close alternatives to review, without claiming calibrated error
probabilities. These are not substitutes for the specialized models proposed in the article.

## Social Media

The **Social Media** preset invokes Cull with a social overlay. The same controls are available in Cull: format
(portrait 4:5, square, vertical 9:16, landscape, original), influence up to 50%, subject priority, unique-view
preservation and alternative-strength explanations. Defaults remain Picks ≥4.5 and Keepers ≥4.0, adjustable in
Quick settings. The overlay combines thumbnail detail, semantic clarity/story, crop-retained area/important faces,
contrast, restrained colorfulness and image resolution. Optional **Learned visual appeal** adds the bundled
MIT-licensed LAION V1 aesthetic head. Its 0–10 prediction maps to a separate component bar and contributes
30% of the Social Media overlay. CLIP jobs reuse viable-photo vectors; SigLIP jobs evaluate up to 256
viable candidates using the separate CLIP tower, reporting any limit. See [model provenance and limits](../backend/app/infrastructure/models/laion_aesthetic/README.md).
The feature works offline, has a Quick settings toggle, and never predicts likes, edits or posts.

[What Makes an Image Popular?](https://people.csail.mit.edu/khosla/papers/www2014_khosla.pdf) studies both image
content and social context on Flickr. It motivates combining visual dimensions, not a claim that these weights predict
modern social engagement. [LaMem](https://people.csail.mit.edu/khosla/papers/iccv2015_khosla.pdf) evaluates memorability
with human observations and a trained network; this app does not bundle MemNet or present its semantic story score as
measured memorability. [CLIP-IQA](https://arxiv.org/abs/2207.12396) motivates paired semantic quality prompts.
[NIMA](https://arxiv.org/abs/1709.05424) motivates keeping technical and aesthetic dimensions distinct; it is not bundled.

## Public workflow inspiration

Aftershoot's public [culling guide](https://support.aftershoot.com/en/articles/5223473-get-started-with-aftershoot-culling)
describes adjustable quality/similarity preferences and manual review of selected and warning groups. Our application
uses its own scoring implementation, adjustable thresholds, separate technical flags and similar-frame alternatives.
Its public [views guide](https://support.aftershoot.com/en/articles/9189985-using-grid-loupe-and-survey-mode-views)
inspired comparison of 2–4 originals, synchronized native-size zoom/pan, face crops, and destination overrides during
comparison. This is a public workflow adaptation, not reproduction of its proprietary models or a claim of feature parity.

## Testing and limits

Controlled tests cover blur, noise-like detail, block artifacts, clipping, face geometry, crop loss, duplicate guards,
scene diversity, uncertainty margins, rating consistency and Apply/Undo. UI tests cover tooltips, controls, filters,
comparison, tags, collapsed settings and manual changes. Real local-model/browser checks supplement these tests.

Preview clipping does not establish RAW recoverability. Edges can be intentional; texture is not proof of focus;
style and expressive intent need human review. No automatic score deletes originals. Professional accuracy remains
unmeasured until a licensed, independently annotated benchmark of complete shoots exists. Keeper recall, false
rejection rate, burst top-1/top-3, scene coverage and NDCG@10 should be evaluated on that benchmark; proposed targets
in the article are not measured results here. Trained BRISQUE/NIQE/NIMA/MUSIQ, body-pose/segmentation models,
photographer preference learning and calibration remain future work.

## Full-screen decision review

The image and persistent score panel share a straight edge on desktop, with rounded outer corners;
mobile stacks them. The panel exposes the score components, selection notes, quality flags, tags,
destination and observable decision evidence. Exactly one Winner badge identifies the strongest
non-flagged recommendation, or the best available with warnings when every image has issues.
Duplicate decisions show fingerprint/visual-group evidence, keeper preference and keeper path.
Recoverable trash remains previewable after Apply/restart; manual overrides retain the original
suggestion. Tests cover collision-safe previews, restart recovery, Undo and source-specific explanations.
