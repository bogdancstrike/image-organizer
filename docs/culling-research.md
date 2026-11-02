# Photo selection: criteria and implementation

This is an assisted first edit: scores recommend frames for review. They are not an objective measure of beauty,
and no aesthetic or expression score deletes a file. Explicit quality checks control technical rejects.

## Evidence translated into signals

| Context | Evidence | Algorithm choice |
|---|---|---|
| Portrait | [Nikon portrait guidance](https://www.nikonusa.com/learn-and-explore/c/tips-and-techniques/quick-tips-for-taking-better-portraits) emphasizes focus on the eyes, lighting and subject/background separation. | Measure sharpness in eye regions, weight readable expression and flattering light, and compare nearby alternatives. Intentional shallow depth of field is acceptable. |
| Fashion/modeling | [Sony fashion guidance](https://www.sony.co.uk/alphauniverse/alpha-academy/articles/top-tips-fashion-photography) distinguishes showing clothing/style from capturing a person's expression. | Weight garment/pose presentation, coherent styling and lighting more strongly. Direct eye contact and a smile are optional. No claims about body attractiveness or ideal body shape. |
| Landscape | [Canon landscape guidance](https://www.canon.ca/en/Articles/2023/Photography-Tips-Landscapes) describes foreground depth, leading lines, horizon placement and clear focal points. | Combine detail, highlight retention, horizon consistency and semantic composition/depth signals. Lack of a face has no penalty. Centered symmetry can be intentional. |
| Groups | Everyone important should have a usable expression, while distant background faces are incidental. | Aggregate the worst and average expression of sizable faces; honor the main-face setting and avoid letting tiny background detections dominate. |
| A useful selection | [Adobe's distinct-content guidance](https://helpx.adobe.com/stock/contributor/submit-your-content/submit-distinct-content/distinct-photo-submission-best-practices.html) values meaningful differences in scene, angle, mood and story over tiny variations. | Cover distinct scenes, discourage redundant frames and avoid selecting several almost identical high-scoring images. |

The group rule is a product heuristic, rather than a claim derived from the linked photography guides.

## Quality is multidimensional

[NIMA](https://arxiv.org/abs/1709.05424) separates technical and aesthetic assessment and models human rating
distributions. It motivates keeping the dimensions inspectable rather than presenting a single infallible verdict.
We do not bundle NIMA or claim its validation results.

[CLIP-IQA](https://arxiv.org/abs/2207.12396) studies paired natural-language descriptions for visual quality.
The implementation uses the existing CLIP/SigLIP embeddings with paired descriptions of lighting, composition,
and genre-specific presentation. This is a lightweight heuristic inspired by the approach, not the published trained
model. Scores have not been calibrated against expert ratings on this application's photo libraries.

## Ranking and keeper policy

- Detect a likely genre locally or use the photographer's explicit profile: portrait, fashion/modeling, landscape or general.
- Blend technical quality, expression when relevant, composition, lighting and semantic presentation with profile-specific weights.
- Combine absolute signal values with relative ranking within the shoot and scene. Relative winners in a uniformly poor shoot should not automatically receive excellent ratings.
- Treat clipped highlights and crushed shadows as evidence of exposure problems. A low-key photograph is not bad simply because its average brightness is low.
- Use the same recommendation score for keeper star thresholds, displayed recommendations, top picks and exported XMP stars.
- Honor enabled reject checks and the main-face/group-face preference. Scene variety never overrides a technical rejection or minimum recommendation quality.
- Map the recommendation to a decimal 1–5 rating. Default Picks start at 4.5; Keepers span 4.0–under 4.5. Both thresholds are adjustable in Quick settings. Put high-rated redundant frames in Similar alternatives.
- Add multiscale edge persistence to discount noise masquerading as detail, gradient-centroid/border balance, and subject/background edge separation. These are weak pixel heuristics, combined with genre semantics; they do not measure depth or artistic intent directly.
- Show concise reasons, component values and the scoring profile alongside each recommendation.

## Validation

Deterministic tests cover relative sharpness, group expressions, small background faces, fashion poses without direct gaze,
landscape highlight retention, intentional dark exposure, scene diversity, rejected-frame exclusion, and rating consistency.
Real model/GPU smoke checks verify inference wiring; neither coverage percentages nor those smoke checks establish
agreement with professional photographers. A future benchmark should use a licensed set with multiple independent
photographer ratings and measure top-k agreement per genre.

## Identity grouping validation

[OpenCV's SFace tutorial](https://docs.opencv.org/4.11.0/d0/dd4/tutorial_dnn_face.html) gives 0.363 as a pair-verification
threshold on LFW. Applying it as a fixed clustering cut can split the same person across poses and lighting.
We retain that conservative starting cut, use clearer faces as anchors, and accept consolidation only when
[cosine silhouette](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.silhouette_score.html)
shows a material improvement with adequate separation. Same-photo reliable identities constrain consolidation.
Partial/occluded faces match multi-view galleries with an ambiguity margin rather than seeding new identities.

On the reported 1,029-photo folder, a read-only rerun produced four distinct representative identities instead of
29, with 48 uncertain face matches and 135 uncertain faceless photos retained in Other people. This is a regression observation on one library,
not a ground-truth accuracy estimate. No expected person count was supplied or hardcoded.
