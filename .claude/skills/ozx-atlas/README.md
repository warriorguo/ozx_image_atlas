# ozx-atlas — Usage

A Claude Code skill that turns a folder of sprite PNGs into a tile-aligned atlas (sprite sheet) by calling the OZX Image Atlas backend (`/v1/atlas/*` and `/v1/workspace/*`).

The skill ships with this repo at `.claude/skills/ozx-atlas/` and is auto-discovered by Claude Code when you open the project. There is also a Python CLI you can run directly without Claude.

---

## Two ways to use it

### 1. Through Claude Code (intended path)

Just describe the task in natural language. The skill triggers on any of these (and many phrasings around them):

- "pack these sprites into an atlas"
- "make a sprite sheet from `~/Downloads/hero_frames/`"
- "preview an atlas with tile size 128, 4 wide, outline 3"
- "export the final atlas to `assets/hero.png`, match shadows from `~/Downloads/shadows/`"
- "list my saved atlas workspaces"
- "load workspace `<id>` and re-pack with tile size 256"

Claude will read `SKILL.md`, ask for any missing pieces (sprite folder, output path, key params), call the helper, and then summarize the result — including which sprites were ignored (duplicates, size mismatch, missing shadows). The base64 `X-Atlas-Report` header is decoded for you.

### 2. Direct CLI (for scripts, CI, manual runs)

```bash
# Preview at low res
python3 .claude/skills/ozx-atlas/scripts/atlas_client.py preview \
    --sprites ~/Downloads/hero_frames \
    --out /tmp/preview.png \
    --tile-size 192 --width 6 --outline 4 --shadow-scale 1.1

# Final export, with shadow matching and a background tile
python3 .claude/skills/ozx-atlas/scripts/atlas_client.py export \
    --sprites ~/Downloads/hero_frames \
    --shadows ~/Downloads/hero_shadows \
    --background ~/Downloads/grass.png \
    --use-shadow-images --use-background --shadow-scale 1.1 \
    --out assets/hero_atlas.png
```

The script prints a JSON summary to stdout on success:

```json
{
  "ok": true,
  "endpoint": "preview",
  "out": "/tmp/preview.png",
  "bytes": 184213,
  "input_count": 24,
  "shadow_count": 24,
  "params_sent": { "tileSize": 192, "width": 6, "outline": 4, "shadowScale": 1.1 },
  "report_summary": "1 ignored (1 duplicate), 0 shadow missing",
  "report": { "ignored": [...], "shadowMissing": [], "shadowAmbiguous": [] },
  "dimensions": "1152x768"
}
```

Non-zero exit code on failure, with the server's error body on stderr.

---

## Workspaces (save / load / delete)

The backend persists workspaces (params + sprite/shadow/background blobs) in PostgreSQL.

```bash
# List
python3 .claude/skills/ozx-atlas/scripts/atlas_client.py workspace list

# Save (or update an existing one with --workspace-id <uuid>)
python3 .claude/skills/ozx-atlas/scripts/atlas_client.py workspace save \
    --name "Hero set v3" \
    --sprites ~/Downloads/hero_frames \
    --shadows ~/Downloads/hero_shadows \
    --background ~/Downloads/grass.png \
    --params-json '{"tileSize":192,"width":6,"outline":4,"shadowScale":1.1,"useShadowImages":true,"useBackground":true}' \
    --export-filename hero_atlas.png

# Load — writes sprites/shadows/background back to disk and prints params
python3 .claude/skills/ozx-atlas/scripts/atlas_client.py workspace load <uuid> \
    --out-dir ~/restored

# Delete
python3 .claude/skills/ozx-atlas/scripts/atlas_client.py workspace delete <uuid>
```

---

## Parameters cheat sheet

| Flag                          | JSON key               | Default        | Notes                                                    |
|-------------------------------|------------------------|----------------|----------------------------------------------------------|
| `--tile-size N`               | `tileSize`             | `192`          | 1–512. Pixel size of a grid cell.                        |
| `--width N`                   | `width`                | `6`            | 1–20. Tiles per row.                                     |
| `--sample N`                  | `sample`               | `1`            | Use every Nth sprite (handy for animation strips).       |
| `--outline N`                 | `outline`              | `0`            | 0–50. Soft outline width in px.                          |
| `--remove-color #rrggbb`      | `removeColor`          | none           | Replace this color with transparency.                    |
| `--remove-color-threshold N`  | `removeColorThreshold` | `3`            | 0–255. RGB tolerance for the chroma key.                 |
| `--shadow-scale F`            | `shadowScale`          | `0.0`          | 0–5. `0` = no shadow.                                    |
| `--use-shadow-images`         | `useShadowImages`      | `false`        | Pair sprites with files in `--shadows/` by filename.     |
| `--missing-shadow-policy P`   | `missingShadowPolicy`  | `skipShadow`   | `skipShadow` / `ignoreSprite` / `fail`.                  |
| `--use-background`            | `useBackground`        | `false`        | Tile `--background` under each sprite.                   |
| `--no-skip-duplicate`         | `skipDuplicate`        | true           | By default consecutive identical inputs are skipped.     |
| `--preview-max-width N`       | `previewMaxWidth`      | `1024`         | Preview-only downscale ceiling.                          |
| `--params-json '{...}'`       | (whole dict)           | —              | Apply a full params dict; flags above override its keys. |

### Shadow filename matching

When `--use-shadow-images` is set, the server pairs sprites with shadows by normalized filename: lowercase, dashes/spaces → underscores, then strip a trailing shadow suffix (`__shadow`, `_shadow`, `-shadow`, `(shadow)`, or bare `shadow`). So `Hero-A.png` matches `hero_a_shadow.png` or `Hero A (shadow).png`. Multiple matches auto-resolve to shortest-then-lex-smallest and are reported as ambiguous.

---

## Configuration

| Variable / flag         | Default                                          | Purpose                              |
|-------------------------|--------------------------------------------------|--------------------------------------|
| `OZX_ATLAS_URL` env var | `https://atlas-editer.local.playquota.com`       | Backend base URL                     |
| `--base-url URL`        | inherits from env                                | Per-call override                    |

TLS verification is auto-disabled **only** for hosts ending in `.local.playquota.com` (private cert). Don't widen this — never bypass TLS on public hosts.

---

## Where the files live

```
ozx_image_atlas/
└── .claude/
    └── skills/
        └── ozx-atlas/
            ├── SKILL.md          ← Claude reads this when triggered
            ├── README.md         ← this document (humans)
            └── scripts/
                └── atlas_client.py
```

The maintainer also has a symlink so the skill is available globally:

```
~/.claude/skills/ozx-atlas → <repo>/.claude/skills/ozx-atlas
```

If you want the same on your machine:

```bash
ln -s "$PWD/.claude/skills/ozx-atlas" ~/.claude/skills/ozx-atlas
```

---

## Requirements

- **Python 3.9+** with `requests`. `Pillow` is optional — if installed, the script reports atlas dimensions in its summary.
- Backend reachable at `OZX_ATLAS_URL`. The default host uses a private cert; verify your machine resolves `.local.playquota.com`.

---

## Troubleshooting

**`HTTP 405 Not Allowed` on POST `/v1/atlas/preview`**
The frontend nginx is fielding the request instead of forwarding it to the FastAPI backend. Check that the proxy in front of `atlas-editer.local.playquota.com` includes the `/v1/ → backend:8000` rule (the docker-compose `nginx/nginx.conf` already has it).

**GET `/v1/workspace/list` returns the React `index.html`**
Same cause as above — SPA fallback intercepts the route. The script detects `Content-Type: text/html` on a JSON endpoint and surfaces a clear error.

**`InsecureRequestWarning` from urllib3**
Expected for `.local.playquota.com` (we disable verify there). Harmless.

**`HTTP 400 — Too many images (max 300)` / `Total upload size too large (max 200MB)`**
Server limits. Sample down with `--sample 2` or split your run.

**`HTTP 400 — tileSize must be between 1 and 512`** / similar
Param out of range. See the cheat sheet above.

**Sprites silently dropped from the output**
Check the `report` field in the JSON summary. Common reasons:
- `duplicate` — pixel-identical to the previous input. Pass `--no-skip-duplicate` to keep them.
- `size alignment` — after effects, dimensions weren't a multiple of `tileSize`.
- `too wide` — wider than `--width` tiles after alignment.
- `missing shadow` — only when `--missing-shadow-policy ignoreSprite`.

---

## Updating the skill

The skill is just text and a script — edit and commit:

```bash
$EDITOR .claude/skills/ozx-atlas/SKILL.md
$EDITOR .claude/skills/ozx-atlas/scripts/atlas_client.py
git commit -am "[OIA-N] update ozx-atlas skill: <what changed>"
```

Because `~/.claude/skills/ozx-atlas` is a symlink to this directory, changes are picked up immediately by Claude Code anywhere on your machine — no reinstall needed.

The canonical issue for the skill itself is **OIA-8**. File follow-up tickets in the OIA project (Memory Flow) for any additions.
