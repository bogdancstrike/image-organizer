"""Observable decision evidence for preview, history and manual overrides."""
from __future__ import annotations


def explain_plan(plan: list[dict], request: dict) -> None:
    by_id = {p["file_id"]: p for p in plan}
    options = request.get("options") or {}
    quality = options.get("quality") or {}
    for item in plan:
        source = item.get("source", "unknown")
        category = item.get("category", "Unsorted")
        evidence = []
        previous = (item.get("decision") or {}).get("previous")
        action = "categorize"
        if source == "manual":
            action, explanation = "manual", f"You placed this photo in {category}."
            evidence.append("The category is a manual override; algorithm scores are retained for comparison.")
        elif item.get("duplicate_of"):
            action = "duplicate"
            explanation = "This file belongs to a duplicate group; another file was selected to keep."
            evidence.extend(item.get("duplicate_evidence") or ["Duplicate-group membership was recorded; detailed pair evidence is unavailable for this older run."])
            policy = options.get("duplicate_keep", "best")
            evidence.append({"best": "Keeper preference: highest resolution, then file size, then oldest capture time.",
                             "oldest": "Keeper preference: oldest capture time.", "newest": "Keeper preference: newest capture time."}.get(policy, f"Keeper preference: {policy}."))
        elif source == "quality":
            action = "recommend"
            explanation = f"Photo quality and selection checks recommended {category}."
            pick = item.get("pick") or {}
            q = item.get("quality") or {}
            rating = pick.get("rating", q.get("rating"))
            if rating is not None:
                evidence.append(f"Recommendation {rating:.2f}/5; Picks ≥{quality.get('pick_min_rating', 4.5):g}/5; Keepers ≥{quality.get('keeper_min_rating', 4.0):g}/5.")
            evidence.extend(f"Quality flag: {flag}." for flag in q.get("flags", []))
            evidence.extend(pick.get("reasons") or [])
            burst = item.get("burst")
            if burst:
                evidence.append(f"Similar sequence: {burst['size']} frames; {'best-ranked frame' if burst['best'] else 'another frame ranked higher'}.")
        elif source in ("faces", "appearance"):
            explanation = ("Matched using face identity references." if source == "faces" else
                           "Matched using appearance references learned from this folder's face-confirmed photos.")
            if item.get("category_id") in ("other-people", "no-people", "groups"):
                explanation = {"other-people": "A person is visible, but the available identity evidence was insufficient or conflicting.",
                               "no-people": "No usable face or supported person-presence match was found.",
                               "groups": "Multiple sizable faces met your group-photo setting."}[item["category_id"]]
            evidence.extend(item.get("person_evidence") or [])
            if source == "appearance":
                evidence.append("Appearance can vary with clothing, pose and background; review ambiguous identities.")
        elif source == "ocr":
            explanation = f"Detected text matched the document-like category {category}."
            evidence.append(f"OCR thresholds: {options.get('ocr_min_chars', 25)} characters and {options.get('ocr_min_coverage', .03):.0%} text coverage.")
        elif source == "date":
            explanation = "Grouped by the recorded capture date, with file modification time as fallback."
        elif source == "rule":
            explanation = f"Your prompt rules matched {category}."
            evidence.append("AI compiled your instructions into category rules; local image/text matching applied those rules.")
        elif source == "ai":
            explanation = f"The configured AI assistant suggested {category}."
        elif source in ("clip", "cluster"):
            explanation = f"Local visual matching suggested {category}."
            evidence.append(f"Embedding model: {options.get('model', 'clip')}; match strength {item.get('confidence', 0):.3f}, not a calibrated probability.")
        else:
            explanation = f"The {request.get('strategy', 'selected')} strategy proposed {category}."
        if ".aio-trash" in item.get("destination", "").split("/"):
            action = "recoverable-trash"
            explanation += " This file is designated for recoverable trash."
            evidence.append("Apply uses the hidden trash folder. Undo can restore moved files until trash is explicitly emptied.")
        decision = {"action": action, "explanation": explanation, "evidence": list(dict.fromkeys(evidence))}
        keeper = by_id.get(item.get("duplicate_of"))
        if keeper:
            decision.update(kept_path=keeper["rel_path"], kept_preview_path=keeper.get("preview_path", keeper["rel_path"]))
        if previous:
            decision["previous"] = previous
        item["decision"] = decision


def duplicate_evidence(analysis, keeper_analysis, embedding, keeper_embedding) -> list[str]:
    """Describe direct measurements without pretending a transitive group is a direct match."""
    if analysis.sha256 == keeper_analysis.sha256:
        return ["Matching content fingerprint (large files use a sampled fingerprint)."]
    evidence = ["Same near-duplicate group; similarity links may pass through another group member."]
    if analysis.phash and keeper_analysis.phash:
        evidence.append(f"Perceptual hash distance to keeper: {(int(analysis.phash,16)^int(keeper_analysis.phash,16)).bit_count()} bits.")
    if analysis.dhash and keeper_analysis.dhash:
        evidence.append(f"Gradient hash distance to keeper: {(int(analysis.dhash,16)^int(keeper_analysis.dhash,16)).bit_count()} bits.")
    evidence.append(f"Visual embedding cosine to keeper: {float(embedding @ keeper_embedding):.4f}.")
    return evidence
