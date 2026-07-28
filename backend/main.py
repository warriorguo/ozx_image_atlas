from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Tuple
from contextlib import asynccontextmanager
import json
import os
import zipfile
from io import BytesIO

from atlas_service import AtlasProcessor, AtlasParams
from database import ensure_database, get_session
from sqlalchemy.ext.asyncio import AsyncSession
import workspace_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    await ensure_database()
    yield


app = FastAPI(title="OZX Image Atlas API", version="1.0.0", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def validate_params(params_json: str) -> AtlasParams:
    """Validate and parse parameters"""
    try:
        params_dict = json.loads(params_json)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in params")
    
    # Validate required parameters
    tile_size = params_dict.get("tileSize", 192)
    width = params_dict.get("width", 6)
    sample = params_dict.get("sample", 1)
    outline = params_dict.get("outline", 0)
    remove_color = params_dict.get("removeColor")
    remove_color_threshold = params_dict.get("removeColorThreshold", 3)
    shadow_scale = params_dict.get("shadowScale", 0.0)
    use_shadow_images = params_dict.get("useShadowImages", False)
    missing_shadow_policy = params_dict.get("missingShadowPolicy", "skipShadow")
    use_background = params_dict.get("useBackground", False)
    skip_duplicate = params_dict.get("skipDuplicate", True)
    preview_max_width = params_dict.get("previewMaxWidth", 1024)
    tile_background_assignments = params_dict.get("tileBackgroundAssignments", {}) or {}
    export_layer_mode = params_dict.get("exportLayerMode", "separate")

    # Validation
    if tile_size <= 0 or tile_size > 512:
        raise HTTPException(status_code=400, detail="tileSize must be between 1 and 512")
    if width <= 0 or width > 20:
        raise HTTPException(status_code=400, detail="width must be between 1 and 20")
    if sample <= 0:
        raise HTTPException(status_code=400, detail="sample must be positive")
    if outline < 0 or outline > 50:
        raise HTTPException(status_code=400, detail="outline must be between 0 and 50")
    if shadow_scale < 0 or shadow_scale > 5:
        raise HTTPException(status_code=400, detail="shadowScale must be between 0 and 5")
    if missing_shadow_policy not in ["skipShadow", "ignoreSprite", "fail"]:
        raise HTTPException(status_code=400, detail="Invalid missingShadowPolicy")
    if remove_color_threshold < 0 or remove_color_threshold > 255:
        raise HTTPException(status_code=400, detail="removeColorThreshold must be between 0 and 255")
    if not isinstance(tile_background_assignments, dict):
        raise HTTPException(status_code=400, detail="tileBackgroundAssignments must be an object")
    if export_layer_mode not in ["separate", "combined"]:
        raise HTTPException(status_code=400, detail="exportLayerMode must be 'separate' or 'combined'")

    return AtlasParams(
        tile_size=tile_size,
        width=width,
        sample=sample,
        outline=outline,
        remove_color=remove_color,
        remove_color_threshold=remove_color_threshold,
        shadow_scale=shadow_scale,
        use_shadow_images=use_shadow_images,
        missing_shadow_policy=missing_shadow_policy,
        use_background=use_background,
        skip_duplicate=skip_duplicate,
        preview_max_width=preview_max_width,
        tile_background_assignments=tile_background_assignments,
        export_layer_mode=export_layer_mode,
    )


def validate_files(images: List[UploadFile]) -> None:
    """Validate uploaded files"""
    if not images or len(images) == 0:
        raise HTTPException(status_code=400, detail="No images provided")
    
    if len(images) > 300:  # Resource limit
        raise HTTPException(status_code=400, detail="Too many images (max 300)")
    
    total_size = 0
    for img in images:
        if img.filename:  # Check if file has content
            if not img.content_type or not img.content_type.startswith('image/'):
                raise HTTPException(status_code=400, detail=f"File {img.filename} is not an image")
            # Read file content to check size
            content = img.file.read()
            total_size += len(content)
            img.file.seek(0)  # Reset file pointer
    
    if total_size > 200 * 1024 * 1024:  # 200MB limit
        raise HTTPException(status_code=400, detail="Total upload size too large (max 200MB)")


async def _read_upload_list(files: List[UploadFile]) -> Tuple[List[BytesIO], List[str]]:
    blobs: List[BytesIO] = []
    names: List[str] = []
    for f in files:
        content = await f.read()
        blobs.append(BytesIO(content))
        names.append(f.filename)
    return blobs, names


@app.post("/v1/atlas/preview")
async def preview_atlas(
    images: List[UploadFile] = File(...),
    params: str = Form(...),
    shadowImages: List[UploadFile] = File(default=[]),
    background: Optional[UploadFile] = File(default=None),
    tileBackgrounds: List[UploadFile] = File(default=[]),
):
    """Generate atlas preview"""
    try:
        atlas_params = validate_params(params)
        validate_files(images)

        image_files, image_names = await _read_upload_list(images)

        shadow_files = shadow_names = None
        if shadowImages:
            shadow_files, shadow_names = await _read_upload_list(shadowImages)

        background_file = None
        if background:
            background_file = BytesIO(await background.read())

        tile_bg_files = tile_bg_names = None
        if tileBackgrounds:
            tile_bg_files, tile_bg_names = await _read_upload_list(tileBackgrounds)

        processor = AtlasProcessor(atlas_params)
        atlas, _report = processor.process_images(
            image_files, image_names, shadow_files, shadow_names, background_file,
            tile_bg_files, tile_bg_names,
        )

        preview = processor.create_preview(atlas)

        img_bytes = BytesIO()
        preview.save(img_bytes, format='PNG')
        img_bytes.seek(0)

        return StreamingResponse(
            BytesIO(img_bytes.read()),
            media_type="image/png",
            headers={"X-Atlas-Report": processor.encode_report()}
        )

    except HTTPException:
        # Validation errors already carry their own status code.
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


def _png_bytes(img) -> bytes:
    buf = BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


def _export_names(export_filename: str) -> Tuple[str, str, str]:
    """Derive (sprite png, shadow png, zip) names from the requested filename."""
    base = os.path.basename((export_filename or "").strip())
    stem = base[:-4] if base.lower().endswith(".png") else base
    if not stem:
        stem = "atlas"
    return f"{stem}.png", f"{stem}_shadow.png", f"{stem}.zip"


@app.post("/v1/atlas/export")
async def export_atlas(
    images: List[UploadFile] = File(...),
    params: str = Form(...),
    exportFilename: str = Form("atlas.png"),
    shadowImages: List[UploadFile] = File(default=[]),
    background: Optional[UploadFile] = File(default=None),
    tileBackgrounds: List[UploadFile] = File(default=[]),
):
    """Export final atlas.

    With `exportLayerMode: "separate"` (the default) the response is a ZIP holding
    the sprite sheet and the shadow sheet; with `"combined"` it is a single PNG.
    """
    try:
        atlas_params = validate_params(params)
        atlas_params.preview_max_width = float('inf')
        validate_files(images)

        image_files, image_names = await _read_upload_list(images)

        shadow_files = shadow_names = None
        if shadowImages:
            shadow_files, shadow_names = await _read_upload_list(shadowImages)

        background_file = None
        if background:
            background_file = BytesIO(await background.read())

        tile_bg_files = tile_bg_names = None
        if tileBackgrounds:
            tile_bg_files, tile_bg_names = await _read_upload_list(tileBackgrounds)

        processor = AtlasProcessor(atlas_params)
        sprite_name, shadow_name, zip_name = _export_names(exportFilename)

        if atlas_params.export_layer_mode == "separate":
            atlas, shadow_atlas, _report = processor.process_layers(
                image_files, image_names, shadow_files, shadow_names, background_file,
                tile_bg_files, tile_bg_names,
            )

            zip_bytes = BytesIO()
            # Stored, not deflated: PNGs are already compressed, and it keeps the
            # archive trivial for the frontend to unpack without a zip library.
            with zipfile.ZipFile(zip_bytes, "w", zipfile.ZIP_STORED) as archive:
                archive.writestr(sprite_name, _png_bytes(atlas))
                archive.writestr(shadow_name, _png_bytes(shadow_atlas))
            zip_bytes.seek(0)

            return StreamingResponse(
                zip_bytes,
                media_type="application/zip",
                headers={
                    "Content-Disposition": f"attachment; filename={zip_name}",
                    "X-Atlas-Report": processor.encode_report(),
                }
            )

        atlas, _report = processor.process_images(
            image_files, image_names, shadow_files, shadow_names, background_file,
            tile_bg_files, tile_bg_names,
        )

        return StreamingResponse(
            BytesIO(_png_bytes(atlas)),
            media_type="image/png",
            headers={
                "Content-Disposition": f"attachment; filename={sprite_name}",
                "X-Atlas-Report": processor.encode_report(),
            }
        )

    except HTTPException:
        # Validation errors already carry their own status code.
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "OZX Image Atlas API is running"}


# ── Workspace endpoints ──────────────────────────────────────────────

@app.post("/v1/workspace/save")
async def save_workspace(
    params: str = Form(...),
    name: str = Form(...),
    exportFilename: str = Form("atlas.png"),
    workspaceId: Optional[str] = Form(None),
    images: List[UploadFile] = File(default=[]),
    shadowImages: List[UploadFile] = File(default=[]),
    background: Optional[UploadFile] = File(default=None),
    tileBackgrounds: List[UploadFile] = File(default=[]),
    session: AsyncSession = Depends(get_session),
):
    """Save current workspace to database."""
    try:
        params_dict = json.loads(params)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in params")

    sprites = []
    for img in images:
        content = await img.read()
        sprites.append((img.filename, content))

    shadows = []
    for img in shadowImages:
        content = await img.read()
        shadows.append((img.filename, content))

    bg = None
    if background:
        content = await background.read()
        bg = (background.filename, content)

    tile_bgs = []
    for img in tileBackgrounds:
        content = await img.read()
        tile_bgs.append((img.filename, content))

    try:
        result = await workspace_service.save_workspace(
            session, name, params_dict, exportFilename,
            sprites, shadows, bg, workspaceId, tile_bgs,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/workspace/list")
async def list_workspaces(session: AsyncSession = Depends(get_session)):
    """List all saved workspaces."""
    return await workspace_service.list_workspaces(session)


@app.get("/v1/workspace/{workspace_id}")
async def load_workspace(workspace_id: str, session: AsyncSession = Depends(get_session)):
    """Load a workspace with all data."""
    try:
        return await workspace_service.load_workspace(session, workspace_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.delete("/v1/workspace/{workspace_id}")
async def delete_workspace(workspace_id: str, session: AsyncSession = Depends(get_session)):
    """Delete a workspace."""
    deleted = await workspace_service.delete_workspace(session, workspace_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return {"deleted": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)