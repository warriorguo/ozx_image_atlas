#!/usr/bin/env python3
"""Client for the OZX Image Atlas backend.

Wraps the multipart-form quirks (params is a JSON string field, images is a
repeated file field) and decodes the X-Atlas-Report header. Designed to be
called from the ozx-atlas skill.
"""
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
from pathlib import Path
from typing import Iterable, Optional
from urllib.parse import urljoin, urlparse

import requests

DEFAULT_BASE_URL = os.environ.get(
    "OZX_ATLAS_URL", "https://atlas-editer.local.playquota.com"
)

# We only auto-disable TLS verify for the known dev/private host. Don't widen this.
_PRIVATE_TLS_HOSTS = (".local.playquota.com",)

IMG_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tiff")


def _verify_for(url: str) -> bool:
    host = urlparse(url).hostname or ""
    if host.endswith(_PRIVATE_TLS_HOSTS):
        return False
    return True


def _list_images(folder: Path) -> list[Path]:
    if not folder.exists() or not folder.is_dir():
        raise SystemExit(f"sprite/shadow folder not found or not a directory: {folder}")
    files = sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in IMG_EXTS)
    if not files:
        raise SystemExit(f"no image files found in {folder}")
    return files


def _content_type(path: Path) -> str:
    ct, _ = mimetypes.guess_type(str(path))
    return ct or "image/png"


def _build_files(
    sprites: list[Path],
    shadows: Optional[list[Path]],
    background: Optional[Path],
) -> list[tuple]:
    files: list[tuple] = []
    for p in sprites:
        files.append(("images", (p.name, p.read_bytes(), _content_type(p))))
    if shadows:
        for p in shadows:
            files.append(("shadowImages", (p.name, p.read_bytes(), _content_type(p))))
    if background:
        files.append(("background", (background.name, background.read_bytes(), _content_type(background))))
    return files


def _decode_report(headers) -> dict:
    raw = headers.get("X-Atlas-Report") or headers.get("x-atlas-report")
    if not raw:
        return {}
    try:
        return json.loads(base64.b64decode(raw).decode("utf-8"))
    except Exception as e:
        return {"_decode_error": str(e), "_raw": raw[:200]}


def _summarize_report(report: dict) -> str:
    if not report:
        return "no report header"
    ignored = report.get("ignored", []) or []
    missing = report.get("shadowMissing", []) or []
    ambiguous = report.get("shadowAmbiguous", []) or []
    if not (ignored or missing or ambiguous):
        return "all sprites packed cleanly"
    parts = []
    if ignored:
        reasons: dict[str, int] = {}
        for entry in ignored:
            reasons[entry.get("reason", "?")] = reasons.get(entry.get("reason", "?"), 0) + 1
        breakdown = ", ".join(f"{c} {r}" for r, c in sorted(reasons.items(), key=lambda kv: -kv[1]))
        parts.append(f"{len(ignored)} ignored ({breakdown})")
    if missing:
        parts.append(f"{len(missing)} shadow missing")
    if ambiguous:
        parts.append(f"{len(ambiguous)} shadow ambiguous")
    return ", ".join(parts)


def _params_from_args(args, *, for_export: bool) -> dict:
    params: dict = {}
    if args.params_json:
        params.update(json.loads(args.params_json))
    # Explicit flags override --params-json values
    overrides = {
        "tileSize": args.tile_size,
        "width": args.width,
        "sample": args.sample,
        "outline": args.outline,
        "removeColor": args.remove_color,
        "removeColorThreshold": args.remove_color_threshold,
        "shadowScale": args.shadow_scale,
        "useShadowImages": True if args.use_shadow_images else None,
        "missingShadowPolicy": args.missing_shadow_policy,
        "useBackground": True if args.use_background else None,
        "skipDuplicate": False if args.no_skip_duplicate else None,
        "previewMaxWidth": args.preview_max_width,
    }
    for k, v in overrides.items():
        if v is not None:
            params[k] = v
    return params


def _post_atlas(args, kind: str) -> int:
    base = args.base_url or DEFAULT_BASE_URL
    url = urljoin(base.rstrip("/") + "/", f"v1/atlas/{kind}")

    sprites = _list_images(Path(args.sprites))
    shadows: Optional[list[Path]] = None
    if args.shadows:
        shadows = _list_images(Path(args.shadows))
    background: Optional[Path] = None
    if args.background:
        background = Path(args.background)
        if not background.exists():
            raise SystemExit(f"background file not found: {background}")

    params = _params_from_args(args, for_export=(kind == "export"))
    if args.use_shadow_images and not shadows:
        raise SystemExit("--use-shadow-images set but --shadows directory not provided")
    if args.use_background and not background:
        raise SystemExit("--use-background set but --background file not provided")

    files = _build_files(sprites, shadows, background)
    data = {"params": json.dumps(params)}

    resp = requests.post(url, data=data, files=files, verify=_verify_for(url), timeout=600)
    if resp.status_code != 200:
        sys.stderr.write(f"HTTP {resp.status_code} from {url}\n{resp.text}\n")
        return 2

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(resp.content)

    report = _decode_report(resp.headers)
    summary = {
        "ok": True,
        "endpoint": kind,
        "out": str(out_path),
        "bytes": len(resp.content),
        "input_count": len(sprites),
        "shadow_count": len(shadows) if shadows else 0,
        "params_sent": params,
        "report_summary": _summarize_report(report),
        "report": report,
    }
    # Try to add image dimensions if Pillow is available — purely cosmetic.
    try:
        from PIL import Image
        from io import BytesIO

        with Image.open(BytesIO(resp.content)) as im:
            summary["dimensions"] = f"{im.width}x{im.height}"
    except Exception:
        pass

    json.dump(summary, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


def _check_json_response(resp) -> dict:
    """Detect the SPA-fallback HTML case and produce a useful error."""
    ctype = resp.headers.get("Content-Type", "")
    if "json" not in ctype.lower():
        snippet = resp.text[:200].replace("\n", " ")
        raise SystemExit(
            f"expected JSON from {resp.url} but got Content-Type={ctype!r}. "
            f"This usually means the SPA frontend is intercepting the route. "
            f"Body starts: {snippet}"
        )
    return resp.json()


def _workspace_list(args) -> int:
    base = args.base_url or DEFAULT_BASE_URL
    url = urljoin(base.rstrip("/") + "/", "v1/workspace/list")
    resp = requests.get(url, verify=_verify_for(url), timeout=60)
    if resp.status_code != 200:
        sys.stderr.write(f"HTTP {resp.status_code}: {resp.text}\n")
        return 2
    data = _check_json_response(resp)
    json.dump(data, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


def _workspace_save(args) -> int:
    base = args.base_url or DEFAULT_BASE_URL
    url = urljoin(base.rstrip("/") + "/", "v1/workspace/save")

    if not args.name:
        raise SystemExit("--name is required")

    sprites = _list_images(Path(args.sprites)) if args.sprites else []
    shadows = _list_images(Path(args.shadows)) if args.shadows else []
    background: Optional[Path] = Path(args.background) if args.background else None
    if background and not background.exists():
        raise SystemExit(f"background not found: {background}")

    params = json.loads(args.params_json) if args.params_json else {}

    form = {
        "name": args.name,
        "params": json.dumps(params),
        "exportFilename": args.export_filename or "atlas.png",
    }
    if args.workspace_id:
        form["workspaceId"] = args.workspace_id

    files = _build_files(sprites, shadows or None, background)

    resp = requests.post(url, data=form, files=files, verify=_verify_for(url), timeout=600)
    if resp.status_code != 200:
        sys.stderr.write(f"HTTP {resp.status_code}: {resp.text}\n")
        return 2
    data = _check_json_response(resp)
    json.dump(data, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


def _workspace_load(args) -> int:
    base = args.base_url or DEFAULT_BASE_URL
    url = urljoin(base.rstrip("/") + "/", f"v1/workspace/{args.workspace_id}")
    resp = requests.get(url, verify=_verify_for(url), timeout=120)
    if resp.status_code != 200:
        sys.stderr.write(f"HTTP {resp.status_code}: {resp.text}\n")
        return 2
    data = _check_json_response(resp)

    out_dir = Path(args.out_dir) if args.out_dir else None
    if out_dir:
        sprites_dir = out_dir / "sprites"
        shadows_dir = out_dir / "shadows"
        sprites_dir.mkdir(parents=True, exist_ok=True)
        for entry in data.get("sprites", []):
            (sprites_dir / entry["filename"]).write_bytes(base64.b64decode(entry["data"]))
        if data.get("shadowImages"):
            shadows_dir.mkdir(parents=True, exist_ok=True)
            for entry in data["shadowImages"]:
                (shadows_dir / entry["filename"]).write_bytes(base64.b64decode(entry["data"]))
        bg = data.get("background")
        if bg:
            (out_dir / bg["filename"]).write_bytes(base64.b64decode(bg["data"]))

    summary = {
        "id": data["id"],
        "name": data["name"],
        "params": data["params"],
        "export_filename": data["export_filename"],
        "sprite_count": len(data.get("sprites", [])),
        "shadow_count": len(data.get("shadowImages", [])),
        "has_background": bool(data.get("background")),
        "out_dir": str(out_dir) if out_dir else None,
    }
    json.dump(summary, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


def _workspace_delete(args) -> int:
    base = args.base_url or DEFAULT_BASE_URL
    url = urljoin(base.rstrip("/") + "/", f"v1/workspace/{args.workspace_id}")
    resp = requests.delete(url, verify=_verify_for(url), timeout=60)
    if resp.status_code == 404:
        sys.stderr.write(f"workspace {args.workspace_id} not found\n")
        return 3
    if resp.status_code != 200:
        sys.stderr.write(f"HTTP {resp.status_code}: {resp.text}\n")
        return 2
    data = _check_json_response(resp)
    json.dump(data, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


def _add_atlas_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--sprites", required=True, help="folder of sprite images")
    p.add_argument("--shadows", help="folder of shadow images (with --use-shadow-images)")
    p.add_argument("--background", help="single background image (with --use-background)")
    p.add_argument("--out", required=True, help="output PNG path")
    p.add_argument("--base-url", help="override OZX_ATLAS_URL")
    p.add_argument("--params-json", help="full params dict as JSON; flags below override its keys")
    p.add_argument("--tile-size", type=int)
    p.add_argument("--width", type=int)
    p.add_argument("--sample", type=int)
    p.add_argument("--outline", type=int)
    p.add_argument("--remove-color", help="hex like #ff00ff")
    p.add_argument("--remove-color-threshold", type=int)
    p.add_argument("--shadow-scale", type=float)
    p.add_argument("--use-shadow-images", action="store_true")
    p.add_argument("--missing-shadow-policy", choices=["skipShadow", "ignoreSprite", "fail"])
    p.add_argument("--use-background", action="store_true")
    p.add_argument("--no-skip-duplicate", action="store_true")
    p.add_argument("--preview-max-width", type=int)


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="OZX Image Atlas client")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_prev = sub.add_parser("preview", help="POST /v1/atlas/preview")
    _add_atlas_args(p_prev)

    p_exp = sub.add_parser("export", help="POST /v1/atlas/export")
    _add_atlas_args(p_exp)

    p_ws = sub.add_parser("workspace", help="workspace ops")
    p_ws_sub = p_ws.add_subparsers(dest="ws_cmd", required=True)

    p_list = p_ws_sub.add_parser("list")
    p_list.add_argument("--base-url")

    p_save = p_ws_sub.add_parser("save")
    p_save.add_argument("--name", required=True)
    p_save.add_argument("--sprites")
    p_save.add_argument("--shadows")
    p_save.add_argument("--background")
    p_save.add_argument("--params-json", default="{}")
    p_save.add_argument("--export-filename", default="atlas.png")
    p_save.add_argument("--workspace-id", help="update existing workspace")
    p_save.add_argument("--base-url")

    p_load = p_ws_sub.add_parser("load")
    p_load.add_argument("workspace_id")
    p_load.add_argument("--out-dir", help="write sprites/shadows/background to this dir")
    p_load.add_argument("--base-url")

    p_del = p_ws_sub.add_parser("delete")
    p_del.add_argument("workspace_id")
    p_del.add_argument("--base-url")

    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.cmd == "preview":
        return _post_atlas(args, "preview")
    if args.cmd == "export":
        return _post_atlas(args, "export")
    if args.cmd == "workspace":
        if args.ws_cmd == "list":
            return _workspace_list(args)
        if args.ws_cmd == "save":
            return _workspace_save(args)
        if args.ws_cmd == "load":
            return _workspace_load(args)
        if args.ws_cmd == "delete":
            return _workspace_delete(args)
    parser.error(f"unknown command {args.cmd}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
