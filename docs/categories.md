# Organizing modes & categories

## Preset
Ready-made folder sets. Each folder is described by a few text prompts, matched against every photo with CLIP.

| Preset | Folders |
|---|---|
| **Lifestyle** | Selfies & portraits · Outfits & fashion · Food & cafés · Travel & vibe · Nature · Aesthetic spaces · Sport & wellness · Music & hobby · Work from home · Pets · Text & captions · Screenshots |
| **People & Style** | Headshots & portraits · Selfies · Full-body outfits · Dresses & formal wear · Casual & streetwear · Outfit details · Runway & editorial · People in scenery · Scenery · Groups & friends · Screenshots |
| **Travel** | Beaches & sea · Mountains & hiking · Cities & streets · Landmarks & monuments · Hotels & stays · Food & markets · Transport & airports · Night life · People & friends · Screenshots & tickets |
| **Creator** | Talking to camera · Outfits & try-ons · Product shots · B-roll scenery · Behind the scenes · Text & captions · Memes · Screenshots |
| **Boudoir & glamour** | Lingerie · studio · Lingerie · bedroom · On the bed · Corset & bodysuit · Stockings & heels · Robe & oversized shirt · Silhouette & implied · Black & white · Details · Glamour portrait · Outdoor & swimwear · Runway & show |
| **Photoshoot themes, Wedding day, Instagram creator, Family & kids, Events, Real estate, Nature & wildlife, Food & product** | see Categories tab |
| **Documents** | Receipts & invoices · IDs & cards · Notes & whiteboards · Slides & charts · Screenshots · Photos (other) |

Presets live in [`backend/app/presets.py`](../backend/app/presets.py). Adding one is a great first PR.

## My categories (custom)
**Settings → Mine → Edit…** opens the editor:
- **Folder name**: becomes the folder on disk (no `/ \ : * ? " < > |`).
- **Describe it** (optional, up to 8 phrases): what the photos *look like*, e.g. for "Dance floor":
  `people dancing at a party`, `disco lights`, `a crowd on a dance floor`. Without a description the name itself is used (`a photo of Dance floor`).
- **Start from preset** copies a preset so you can tweak it.

Tips:
- Describe *visual content*, not intent ("a plate of pasta", not "dinner I liked").
- Folders that look alike (e.g. "Beach" and "Sea") split the vote. Merge them or describe what tells them apart.
- Raise the **confidence threshold** to send ambiguous files to `Unsorted` rather than to a wrong folder. Turn on **AI assist** to let Luna place them.

## Culling (Cull mode, or quality checks with any mode)
See [quality-culling spec](openspec/specs/quality-culling/spec.md). Folders: Keepers · Smiling · Maybe · Blurry · Eyes closed ·
Too dark · Too bright · Burst extras. Tune sharpness, blink and smile thresholds, exposure limits, whose face counts (any vs main
subject), burst window and similarity, and the minimum stars for a keeper. With other modes, rejects go to `_Rejects/<reason>` (or are
only tagged).

## Auto-discover
0. **Context:** the folder's theme is detected (e.g. *Trash the dress*, *Studio fashion*, *Boudoir*, *Halloween*).
1. **Group by** (focus): *auto* clusters raw CLIP embeddings; *scene*, *framing & pose*, *outfit*, *lighting* or *subject* cluster on
   z-scored similarity to a bank of prompts for that aspect, so a studio shoot splits by pose or light instead of "all studio".
   KMeans picks k (2…`max_clusters`) by silhouette; **granularity** coarse / normal / fine shifts it.
2. Naming:
   - **With an OpenAI key**: one request to `gpt-5.6-luna` (`reasoning: low`) with a small contact sheet per group. You get names like
     *Coastal Shores*, *Workspaces*, *Golden Gate*.
   - **Without a key**: each group is named by what makes it stand out within the folder, e.g. *Full-body · Golden hour*.
   - With a key, the AI also sees an overview sheet, the detected theme, the focus and the local names, plus your own *naming instructions*.
3. Groups that end up with the same name are merged.

## By date
`YYYY/MM - Month` (or `YYYY`, or `YYYY/MM/YYYY-MM-DD`) from EXIF `DateTimeOriginal`, the video `creation_time`, or the file date as a fallback.

## Special folders
| Folder | When |
|---|---|
| `Unsorted` | Best match is under the confidence threshold |
| `_Duplicates` | Byte-identical copies and near-duplicates. The best copy (most pixels, then size, then oldest) stays in its folder. |
| `Screenshots` | Filename (`Screenshot…`, `Captura…`) or phone-shaped PNG without camera EXIF, in any set that has a *Screenshots* folder. CLIP alone needs 60% confidence for it. |
