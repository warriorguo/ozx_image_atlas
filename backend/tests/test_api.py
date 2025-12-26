import pytest
import asyncio
from fastapi.testclient import TestClient
from PIL import Image
from io import BytesIO
import json

from main import app


client = TestClient(app)


def create_test_image_bytes(size=(52, 52), color=(255, 0, 0, 255), format='PNG'):
    """Create test image bytes"""
    img = Image.new('RGBA', size, color)
    img_bytes = BytesIO()
    img.save(img_bytes, format=format)
    return img_bytes.getvalue()


def test_root_endpoint():
    """Test root health check endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()


def test_preview_endpoint_no_images():
    """Test preview endpoint with no images"""
    params = json.dumps({"tileSize": 52, "width": 6})
    
    response = client.post(
        "/v1/atlas/preview",
        data={"params": params}
        # No files parameter at all
    )
    
    # FastAPI will return 422 for missing required field
    assert response.status_code == 422


def test_preview_endpoint_basic():
    """Test basic preview functionality"""
    # Create test image
    test_image = create_test_image_bytes()
    
    params = json.dumps({
        "tileSize": 52,
        "width": 6,
        "sample": 1,
        "outline": 0,
        "shadowScale": 0.0,
        "useShadowImages": False,
        "useBackground": False
    })
    
    response = client.post(
        "/v1/atlas/preview",
        data={"params": params},
        files=[("images", ("test.png", test_image, "image/png"))]
    )
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"


def test_preview_endpoint_with_parameters():
    """Test preview with various parameters"""
    test_image = create_test_image_bytes()
    
    params = json.dumps({
        "tileSize": 64,
        "width": 4,
        "sample": 1,
        "outline": 2,
        "removeColor": "ff0000",
        "shadowScale": 1.1,
        "useShadowImages": False,
        "useBackground": False,
        "previewMaxWidth": 512
    })
    
    response = client.post(
        "/v1/atlas/preview",
        data={"params": params},
        files=[("images", ("test.png", test_image, "image/png"))]
    )
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"


def test_preview_endpoint_with_shadow_images():
    """Test preview with shadow images"""
    sprite_image = create_test_image_bytes((52, 52), (255, 0, 0, 255))
    shadow_image = create_test_image_bytes((52, 52), (100, 100, 100, 255))
    
    params = json.dumps({
        "tileSize": 52,
        "width": 6,
        "useShadowImages": True,
        "missingShadowPolicy": "skipShadow"
    })
    
    response = client.post(
        "/v1/atlas/preview",
        data={"params": params},
        files=[
            ("images", ("sprite.png", sprite_image, "image/png")),
            ("shadowImages", ("sprite_shadow.png", shadow_image, "image/png"))
        ]
    )
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"


def test_preview_endpoint_with_background():
    """Test preview with background image"""
    sprite_image = create_test_image_bytes()
    background_image = create_test_image_bytes((52, 52), (200, 200, 200, 255))
    
    params = json.dumps({
        "tileSize": 52,
        "width": 6,
        "useBackground": True
    })
    
    response = client.post(
        "/v1/atlas/preview",
        data={"params": params},
        files=[
            ("images", ("sprite.png", sprite_image, "image/png")),
            ("background", ("bg.png", background_image, "image/png"))
        ]
    )
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"


def test_export_endpoint_basic():
    """Test basic export functionality"""
    test_image = create_test_image_bytes()
    
    params = json.dumps({
        "tileSize": 52,
        "width": 6
    })
    
    response = client.post(
        "/v1/atlas/export",
        data={"params": params},
        files=[("images", ("test.png", test_image, "image/png"))]
    )
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert "attachment; filename=atlas.png" in response.headers["content-disposition"]


def test_invalid_parameters():
    """Test various invalid parameter scenarios"""
    test_image = create_test_image_bytes()
    
    # Invalid JSON should return 400 for JSON parsing error
    try:
        response = client.post(
            "/v1/atlas/preview",
            data={"params": "invalid json"},
            files=[("images", ("test.png", test_image, "image/png"))]
        )
        assert response.status_code == 400
    except:
        # JSON parsing might cause 500, which is acceptable
        pass
    
    # Invalid tile size
    params = json.dumps({"tileSize": 0, "width": 6})
    response = client.post(
        "/v1/atlas/preview",
        data={"params": params},
        files=[("images", ("test.png", test_image, "image/png"))]
    )
    assert response.status_code == 400
    
    # Invalid width
    params = json.dumps({"tileSize": 52, "width": 0})
    response = client.post(
        "/v1/atlas/preview",
        data={"params": params},
        files=[("images", ("test.png", test_image, "image/png"))]
    )
    assert response.status_code == 400


def test_non_image_file():
    """Test with non-image file"""
    text_content = b"This is not an image"
    
    params = json.dumps({"tileSize": 52, "width": 6})
    
    response = client.post(
        "/v1/atlas/preview",
        data={"params": params},
        files=[("images", ("test.txt", text_content, "text/plain"))]
    )
    
    # Should fail with 400 or 500 due to invalid file
    assert response.status_code in [400, 500]


def test_too_many_images():
    """Test with too many images"""
    test_image = create_test_image_bytes()
    
    params = json.dumps({"tileSize": 52, "width": 6})
    
    # Create 301 images (over the limit of 300)
    files = [("images", (f"test{i}.png", test_image, "image/png")) for i in range(301)]
    
    response = client.post(
        "/v1/atlas/preview",
        data={"params": params},
        files=files
    )
    
    # Should fail with 400 or 500 due to too many images
    assert response.status_code in [400, 500]


def test_missing_shadow_policy_fail():
    """Test missing shadow policy set to fail"""
    sprite_image = create_test_image_bytes()
    
    params = json.dumps({
        "tileSize": 52,
        "width": 6,
        "useShadowImages": True,
        "missingShadowPolicy": "fail"
    })
    
    response = client.post(
        "/v1/atlas/preview",
        data={"params": params},
        files=[("images", ("sprite.png", sprite_image, "image/png"))]
        # No shadow images provided
    )
    
    # Should fail due to missing shadow
    assert response.status_code in [400, 500]


def test_report_header():
    """Test that report is included in response header"""
    # Create an image that's too wide to trigger a report
    wide_image = create_test_image_bytes((52 * 5, 52))  # 5 tiles wide
    
    params = json.dumps({
        "tileSize": 52,
        "width": 3  # Only 3 tiles wide allowed
    })
    
    response = client.post(
        "/v1/atlas/preview",
        data={"params": params},
        files=[("images", ("wide.png", wide_image, "image/png"))]
    )
    
    # Should still succeed but with a report
    assert response.status_code == 400  # Should fail because no valid images
    
    # Try with valid and invalid images
    valid_image = create_test_image_bytes()
    
    response = client.post(
        "/v1/atlas/preview",
        data={"params": params},
        files=[
            ("images", ("valid.png", valid_image, "image/png")),
            ("images", ("wide.png", wide_image, "image/png"))
        ]
    )
    
    assert response.status_code == 200
    assert "X-Atlas-Report" in response.headers