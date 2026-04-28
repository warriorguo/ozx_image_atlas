---
name: ozx-atlas
description: Pack a folder of sprite images into a tile-aligned atlas (sprite sheet) PNG via the OZX Image Atlas backend. Use this skill whenever the user wants to generate, preview, or export a sprite atlas; pack/combine sprites into a sheet; auto-match shadow images to sprites by filename; or save/load/list/delete atlas workspaces. Trigger on phrases like "pack these sprites", "make a sprite atlas", "generate atlas from this folder", "build a sprite sheet", "match shadows to sprites", "preview atlas", "export atlas", "save my atlas workspace", "load workspace", or any request that involves combining multiple sprite PNGs into a single grid-aligned atlas image — even if the user does not explicitly say "atlas".
---

# OZX Image Atlas — Backend Client Skill

This skill wraps the OZX Image Atlas HTTP API. It turns a directory of sprite PNGs into a tile-aligned atlas image, with optional outline, shadow, background, color-removal, and dedupe effects, and persists workspaces in PostgreSQL via the backend.

## Endpoint

The base URL for the API is:

```
https://atlas-editer.local.playquota.com
```

Override with the `OZX_ATLAS_URL` environment variable when calling the helper script. Use `-k`/`verify=False` to skip TLS verification only on `.local.playquota.com` (it's a private cert); never bypass TLS on public hosts.

The frontend SPA also lives at this host. Routes:

| Method | Path                       | Purpose                              |
|--------|----------------------------|--------------------------------------|
| POST   | `/v1/atlas/preview`        | Returns a downscaled preview PNG     |
| POST   | `/v1/atlas/export`         | Returns the full-resolution atlas    |
| POST   | `/v1/workspace/save`       | Save (or update) a workspace         |
| GET    | `/v1/workspace/list`       | List saved workspaces                |
| GET    | `/v1/workspace/{id}`       | Load a workspace + its image blobs   |
| DELETE | `/v1/workspace/{id}`       | Delete a workspace                   |

Both atlas endpoints respond with a PNG body. Preview also returns an `X-Atlas-Report` header containing a base64-encoded JSON object describing what was ignored, what shadows were missing, and which were ambiguous — surface this report to the user when packing fails or seems incomplete; it's the only feedback they get on rejected sprites.

## How to use this skill

The skill ships a Python helper at `scripts/atlas_client.py` that handles multipart upload, PNG saving, and report decoding. Prefer calling this script over reinventing curl invocations, because the multipart form has a few non-obvious shapes (the `params` field is a JSON-string form field, *not* JSON body; `images` is a repeated file field; `shadowImages` and `background` are optional file fields).

Typical flow:

1. Resolve the user's input — a directory of sprite PNGs, optionally a directory of shadow PNGs, optionally a single background image. If the user has already given you a path or a glob, use it; otherwise ask once.
2. Decide preview vs. export. If unspecified: preview first when the user is iterating on params, export when they say "save", "export", "final", or specify an output filename.
3. Build the params dict (see "Parameters" below). Start from sane defaults and only override what the user mentioned.
4. Run the helper script. Save the PNG where the user expects it (default: alongside the sprite folder as `atlas.png`). Decode and report the `X-Atlas-Report` summary.
5. If sprites were ignored or shadow matches were missing/ambiguous, tell the user concretely (filenames + reason). Do not silently drop them.

## Parameters

The `params` JSON object accepted by `/v1/atlas/preview` and `/v1/atlas/export`:

| Key                     | Type    | Default       | Range/Notes                                                      |
|-------------------------|---------|---------------|------------------------------------------------------------------|
| `tileSize`              | int     | `192`         | 1–512. Pixel size of one grid cell. Output sprites are resized to a multiple of this. |
| `width`                 | int     | `6`           | 1–20. Number of tiles per row in the atlas.                      |
| `sample`                | int     | `1`           | Use every Nth input sprite (skip animation frames).              |
| `outline`               | int     | `0`           | 0–50. Soft-outline width in pixels. `0` = no outline.            |
| `removeColor`           | string? | `null`        | Hex like `"#ff00ff"`. Replaces this color with transparency.     |
| `removeColorThreshold`  | int     | `3`           | 0–255. RGB tolerance for `removeColor`.                          |
| `shadowScale`           | float   | `0.0`         | 0–5. `0` = no shadow. >0 with `useShadowImages=false` synthesizes a soft drop shadow scaled by this factor; with `useShadowImages=true` it scales the matched shadow image. |
| `useShadowImages`       | bool    | `false`       | When true, expect a `shadowImages` upload set and auto-match by filename. |
| `missingShadowPolicy`   | string  | `"skipShadow"`| One of `skipShadow`, `ignoreSprite`, `fail`.                     |
| `useBackground`         | bool    | `false`       | When true, expect a `background` file and tile it under each sprite. |
| `skipDuplicate`         | bool    | `true`        | Skip an input image if it's pixel-identical to the previous one. |
| `previewMaxWidth`       | int     | `1024`        | Preview-only — maximum output width before downscale.            |

For export, `previewMaxWidth` is forced to infinity by the server, so leaving it at the default is fine.

## Shadow matching (when `useShadowImages=true`)

Shadow files are paired with sprites by normalized filename: lowercase, dashes/spaces → underscores, then strip a trailing shadow suffix (`__shadow`, `_shadow`, `-shadow`, `(shadow)`, or bare `shadow`). So `Hero-A.png` matches `hero_a_shadow.png` or `Hero A (shadow).png`.

If multiple shadows match one sprite, the server auto-resolves to the shortest filename (then lex-smallest), and reports the case in `shadowAmbiguous`. Sprites with no match land in `shadowMissing` and are handled per `missingShadowPolicy`.

When the user provides a separate shadow folder, pass every PNG in it as `shadowImages` — the server does the matching.

## Calling the helper

Quick usage from this skill's directory:

```bash
python scripts/atlas_client.py preview \
    --sprites /path/to/sprites \
    --out /tmp/atlas_preview.png \
    --tile-size 192 --width 6 --outline 4 --shadow-scale 1.1
```

Export with shadow images and a background:

```bash
python scripts/atlas_client.py export \
    --sprites /path/to/sprites \
    --shadows /path/to/shadows \
    --background /path/to/bg.png \
    --use-shadow-images --shadow-scale 1.1 --use-background \
    --out /path/to/atlas.png
```

The script prints a JSON summary to stdout after a successful call:

```json
{
  "ok": true,
  "out": "/tmp/atlas_preview.png",
  "bytes": 184213,
  "report": {"ignored": [...], "shadowMissing": [...], "shadowAmbiguous": [...]}
}
```

On failure it exits non-zero and prints the server's error body. Pass `--base-url` (or set `OZX_ATLAS_URL`) to target a different deployment.

For workspace ops:

```bash
python scripts/atlas_client.py workspace list
python scripts/atlas_client.py workspace save --name "My Set" \
    --sprites /path/to/sprites --params-json '{"tileSize":192,"width":6}'
python scripts/atlas_client.py workspace load <id> --out-dir /tmp/loaded
python scripts/atlas_client.py workspace delete <id>
```

`workspace load` writes the sprites/shadows/background back to disk and prints the workspace `params` so you can re-pack with the same settings.

## Server limits & gotchas

- **Max 300 input images** per request, **200 MB total upload**. Above that the server 400s.
- **Atlas height** is capped by `map_height`'s 1000-row search ceiling — at the default tile size, that's already an absurdly tall image, so this rarely matters, but a tile size of 32 with thousands of large sprites could in theory hit it.
- **Image order matters** for `skipDuplicate` (only consecutive duplicates are dropped) and for `sample` (every Nth in input order). Sort the input directory deterministically (lexicographic by filename) before uploading; that's what users expect and what the frontend does.
- **TLS**: the production host uses a private cert. The helper passes `verify=False` only when the URL host ends with `.local.playquota.com`. Don't widen that.
- **Workspace SPA fallback**: at the configured host, plain GETs to `/v1/workspace/...` may be intercepted by the SPA and return the index HTML. The helper detects an `text/html` response on a JSON endpoint and surfaces a clear error rather than parsing it as JSON. If the user reports list/load failures while preview/export work, this is the cause — the API path needs a backend-only host or a routing fix.

## When the user is iterating

Atlas params are the kind of thing users tune in a tight loop. Default to the **preview** endpoint while they're tweaking, and only switch to **export** when they explicitly say so or ask for a specific output filename. Don't re-upload identical sprite sets between iterations within one conversation if you can avoid it — but note the API is stateless, so each call must re-upload.

When the user changes only one parameter, re-run with that single param swapped; don't reset the others unless asked.

## What to surface back to the user

After a successful pack:
- The output path and file size
- Atlas dimensions if you can read them (the helper prints `width × height`)
- A one-line summary of the report: `"3 ignored (2 duplicate, 1 too wide), 1 shadow missing"` — concrete, not just "see report"
- The full `report` JSON only if they ask for details

After a failure:
- HTTP status + the server's error message verbatim
- For 400s: which validation rule likely tripped (too many images, bad tileSize range, missing shadow with `fail` policy, etc.)
