from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import json
from io import BytesIO

from atlas_service import AtlasProcessor, AtlasParams

app = FastAPI(title="OZX Image Atlas API", version="1.0.0")

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
    tile_size = params_dict.get("tileSize", 52)
    width = params_dict.get("width", 6)
    sample = params_dict.get("sample", 1)
    outline = params_dict.get("outline", 0)
    remove_color = params_dict.get("removeColor")
    shadow_scale = params_dict.get("shadowScale", 0.0)
    use_shadow_images = params_dict.get("useShadowImages", False)
    missing_shadow_policy = params_dict.get("missingShadowPolicy", "skipShadow")
    use_background = params_dict.get("useBackground", False)
    preview_max_width = params_dict.get("previewMaxWidth", 1024)
    
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
    
    return AtlasParams(
        tile_size=tile_size,
        width=width,
        sample=sample,
        outline=outline,
        remove_color=remove_color,
        shadow_scale=shadow_scale,
        use_shadow_images=use_shadow_images,
        missing_shadow_policy=missing_shadow_policy,
        use_background=use_background,
        preview_max_width=preview_max_width
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


@app.post("/v1/atlas/preview")
async def preview_atlas(
    images: List[UploadFile] = File(...),
    params: str = Form(...),
    shadowImages: Optional[List[UploadFile]] = File(None),
    background: Optional[UploadFile] = File(None)
):
    """Generate atlas preview"""
    try:
        # Validate inputs
        atlas_params = validate_params(params)
        validate_files(images)
        
        # Convert uploaded files to BytesIO
        image_files = []
        image_names = []
        for img in images:
            content = await img.read()
            image_files.append(BytesIO(content))
            image_names.append(img.filename)
        
        shadow_files = None
        shadow_names = None
        if shadowImages:
            shadow_files = []
            shadow_names = []
            for shadow in shadowImages:
                content = await shadow.read()
                shadow_files.append(BytesIO(content))
                shadow_names.append(shadow.filename)
        
        background_file = None
        if background:
            content = await background.read()
            background_file = BytesIO(content)
        
        # Process atlas
        processor = AtlasProcessor(atlas_params)
        atlas, report = processor.process_images(
            image_files, image_names, shadow_files, shadow_names, background_file
        )
        
        # Create preview
        preview = processor.create_preview(atlas)
        
        # Convert to PNG bytes
        img_bytes = BytesIO()
        preview.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        # Encode report for header
        report_header = processor.encode_report()
        
        return StreamingResponse(
            BytesIO(img_bytes.read()),
            media_type="image/png",
            headers={"X-Atlas-Report": report_header}
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/v1/atlas/export")
async def export_atlas(
    images: List[UploadFile] = File(...),
    params: str = Form(...),
    shadowImages: Optional[List[UploadFile]] = File(None),
    background: Optional[UploadFile] = File(None)
):
    """Export final atlas"""
    try:
        # Validate inputs
        atlas_params = validate_params(params)
        atlas_params.preview_max_width = float('inf')  # No preview scaling for export
        validate_files(images)
        
        # Convert uploaded files to BytesIO
        image_files = []
        image_names = []
        for img in images:
            content = await img.read()
            image_files.append(BytesIO(content))
            image_names.append(img.filename)
        
        shadow_files = None
        shadow_names = None
        if shadowImages:
            shadow_files = []
            shadow_names = []
            for shadow in shadowImages:
                content = await shadow.read()
                shadow_files.append(BytesIO(content))
                shadow_names.append(shadow.filename)
        
        background_file = None
        if background:
            content = await background.read()
            background_file = BytesIO(content)
        
        # Process atlas
        processor = AtlasProcessor(atlas_params)
        atlas, report = processor.process_images(
            image_files, image_names, shadow_files, shadow_names, background_file
        )
        
        # Convert to PNG bytes
        img_bytes = BytesIO()
        atlas.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        return StreamingResponse(
            BytesIO(img_bytes.read()),
            media_type="image/png",
            headers={"Content-Disposition": "attachment; filename=atlas.png"}
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "OZX Image Atlas API is running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)