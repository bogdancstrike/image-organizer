# Getting started

## 1. Run it
```bash
git clone https://github.com/bogdancstrike/image-organizer.git
cd image-organizer
cp .env.example .env          # optional: add OPENAI_API_KEY, narrow LIBRARY_PATH
docker compose up -d --build  # first build takes a few minutes (bundles the CLIP model)
```
Open **http://localhost:8080**.

By default your **home folder** is mounted into the container at `/library`, so the app can browse
any folder under it. To limit what the app can touch, set `LIBRARY_PATH` in `.env`, for example `LIBRARY_PATH=/home/me/Pictures`.

> No photos at hand? `./scripts/download-samples.sh` (landscapes, duplicates, a screenshot, short clips) and
> `python3 scripts/download-portraits.py` (200 openly licensed portraits, outfits and selfies from Wikimedia Commons)
> fill `./sample-library/`.

## 2. Choose the working folder
Click the folder name in the headline (*Sorting my **Downloads ▾** folder*) or the path under it.
Browse with the breadcrumbs, then press **Use this folder** (or double-click a folder).

The sorted folders are created **inside the folder you choose**:

```
Downloads/
├── Organized/                 ← "In a subfolder" (default, the name is configurable)
│   ├── Photos/
│   │   ├── Food & cafés/
│   │   └── Travel & vibe/
│   ├── Videos/
│   │   └── Selfies & portraits/
│   └── _Duplicates/
└── (anything that was not a photo or video stays where it was)
```
Choose **Directly in the folder** in Settings to skip the `Organized/` level. Turn off **Include subfolders** to sort only the
files that sit directly in the folder.

## 3. Pick how to organize
Open **Settings** (sliders icon):

| Mode | Use it when |
|---|---|
| **Preset** | You want good folders right away: *Lifestyle*, *People & Style* (outfits, scenery, headshots…), *Travel*, *Creator*, *Documents* |
| **Mine** | You know the folders you want: create them in **Edit…** and describe each one in a few words |
| **Auto** | You don't know what's in there: the app finds the groups and names them |
| **Date** | You want `2025/07 - July` style folders |

See [categories.md](categories.md) for details and tips.

## 4. Sort, review, apply
1. Press **Sort**. Thumbnails pile up in the middle while files are analyzed, then fly into their folders.
2. Click any folder card to see its files (and why each one landed there).
3. Nothing has moved yet. Press **Apply · move files** (or *copy files*, chosen in Settings).
4. Changed your mind? Press **Undo** in the notice, or open **History** (clock icon) at any time later.

## 5. Themes
Three themes: **Graphite** (dark, shadcn/ui-style, default), **Light** and **Lavender**. Switch them with the
swatches in the header or in Settings → Appearance. Your choice is remembered.
