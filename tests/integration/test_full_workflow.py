#!/usr/bin/env python3
"""
Integration test for the full atlas generation workflow
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../backend'))

import asyncio
import json
from io import BytesIO
from PIL import Image
import httpx
import pytest


def create_test_image(size=(52, 52), color=(255, 0, 0, 255)):
    """Create a test image in memory"""
    img = Image.new('RGBA', size, color)
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes.getvalue()


@pytest.mark.asyncio
async def test_basic_atlas_generation():
    """Test basic atlas generation workflow"""
    base_url = "http://localhost:8000"
    
    # Create test images
    red_img = create_test_image((52, 52), (255, 0, 0, 255))
    green_img = create_test_image((52, 52), (0, 255, 0, 255))
    blue_img = create_test_image((52, 52), (0, 0, 255, 255))
    
    params = {
        "tileSize": 52,
        "width": 3,
        "sample": 1,
        "outline": 0,
        "shadowScale": 0.0,
        "useShadowImages": False,
        "useBackground": False
    }
    
    async with httpx.AsyncClient() as client:
        # Test preview endpoint
        files = {
            "images": [
                ("red.png", red_img, "image/png"),
                ("green.png", green_img, "image/png"),
                ("blue.png", blue_img, "image/png")
            ]
        }
        data = {"params": json.dumps(params)}
        
        response = await client.post(f"{base_url}/v1/atlas/preview", files=files, data=data)
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
        
        # Verify image size
        result_image = Image.open(BytesIO(response.content))
        expected_width = 52 * 3  # 3 tiles wide
        expected_height = 52 * 1  # 1 tile high
        assert result_image.size == (expected_width, expected_height)


@pytest.mark.asyncio
async def test_atlas_with_shadows():
    """Test atlas generation with shadow images"""
    base_url = "http://localhost:8000"
    
    # Create sprite and shadow images
    sprite_img = create_test_image((52, 52), (255, 0, 0, 255))
    shadow_img = create_test_image((52, 52), (100, 100, 100, 255))
    
    params = {
        "tileSize": 52,
        "width": 3,
        "useShadowImages": True,
        "missingShadowPolicy": "skipShadow"
    }
    
    async with httpx.AsyncClient() as client:
        files = {
            "images": [("sprite.png", sprite_img, "image/png")],
            "shadowImages": [("sprite_shadow.png", shadow_img, "image/png")]
        }
        data = {"params": json.dumps(params)}
        
        response = await client.post(f"{base_url}/v1/atlas/preview", files=files, data=data)
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
        
        # Check report header
        report_header = response.headers.get("X-Atlas-Report")
        if report_header:
            import base64
            report = json.loads(base64.b64decode(report_header).decode())
            assert "ignored" in report
            assert "shadowMissing" in report
            assert "shadowAmbiguous" in report


@pytest.mark.asyncio
async def test_atlas_with_background():
    """Test atlas generation with background image"""
    base_url = "http://localhost:8000"
    
    # Create sprite and background images
    sprite_img = create_test_image((52, 52), (255, 0, 0, 255))
    bg_img = create_test_image((52, 52), (200, 200, 200, 255))
    
    params = {
        "tileSize": 52,
        "width": 3,
        "useBackground": True
    }
    
    async with httpx.AsyncClient() as client:
        files = {
            "images": [("sprite.png", sprite_img, "image/png")],
            "background": ("bg.png", bg_img, "image/png")
        }
        data = {"params": json.dumps(params)}
        
        response = await client.post(f"{base_url}/v1/atlas/preview", files=files, data=data)
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"


@pytest.mark.asyncio
async def test_export_vs_preview():
    """Test that export and preview produce consistent results"""
    base_url = "http://localhost:8000"
    
    # Create test image
    test_img = create_test_image((52, 52), (255, 0, 0, 255))
    
    params = {
        "tileSize": 52,
        "width": 3,
        "previewMaxWidth": 9999  # Set high to avoid scaling
    }
    
    async with httpx.AsyncClient() as client:
        files = {"images": [("test.png", test_img, "image/png")]}
        data = {"params": json.dumps(params)}
        
        # Get preview
        preview_response = await client.post(f"{base_url}/v1/atlas/preview", files=files, data=data)
        assert preview_response.status_code == 200
        
        # Get export
        export_response = await client.post(f"{base_url}/v1/atlas/export", files=files, data=data)
        assert export_response.status_code == 200
        assert "attachment; filename=atlas.png" in export_response.headers["content-disposition"]
        
        # Compare sizes
        preview_img = Image.open(BytesIO(preview_response.content))
        export_img = Image.open(BytesIO(export_response.content))
        
        # Should be same size when no scaling
        assert preview_img.size == export_img.size


@pytest.mark.asyncio
async def test_error_handling():
    """Test various error conditions"""
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient() as client:
        # Test invalid JSON params
        files = {"images": [("test.png", create_test_image(), "image/png")]}
        data = {"params": "invalid json"}
        
        response = await client.post(f"{base_url}/v1/atlas/preview", files=files, data=data)
        assert response.status_code in [400, 500]
        
        # Test invalid parameters
        params = {"tileSize": 0, "width": 6}
        data = {"params": json.dumps(params)}
        
        response = await client.post(f"{base_url}/v1/atlas/preview", files=files, data=data)
        assert response.status_code == 400


if __name__ == "__main__":
    print("Integration tests require the backend server to be running on localhost:8000")
    print("Start the server with: cd backend && uvicorn main:app --reload")
    print("\nRunning basic connectivity test...")
    
    async def test_connectivity():
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:8000/")
                if response.status_code == 200:
                    print("✅ Backend server is reachable")
                    return True
                else:
                    print(f"❌ Backend server returned status {response.status_code}")
                    return False
        except Exception as e:
            print(f"❌ Cannot connect to backend server: {e}")
            return False
    
    if asyncio.run(test_connectivity()):
        print("Ready for integration testing!")
    else:
        print("Please start the backend server first.")