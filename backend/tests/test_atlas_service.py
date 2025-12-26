import pytest
from PIL import Image
from io import BytesIO
from atlas_service import AtlasProcessor, AtlasParams


def create_test_image_file(size=(52, 52), color=(255, 0, 0, 255)):
    """Create a test image file in BytesIO"""
    img = Image.new('RGBA', size, color)
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes


def test_atlas_params_defaults():
    """Test AtlasParams default values"""
    params = AtlasParams()
    assert params.tile_size == 52
    assert params.width == 6
    assert params.sample == 1
    assert params.outline == 0
    assert params.remove_color is None
    assert params.shadow_scale == 0.0
    assert params.use_shadow_images == False
    assert params.missing_shadow_policy == "skipShadow"
    assert params.use_background == False
    assert params.preview_max_width == 1024


def test_parse_remove_color():
    """Test hex color parsing"""
    processor = AtlasProcessor(AtlasParams())
    
    # Test with #
    assert processor.parse_remove_color("#ff0000") == (255, 0, 0)
    
    # Test without #
    assert processor.parse_remove_color("00ff00") == (0, 255, 0)
    
    # Test blue
    assert processor.parse_remove_color("0000ff") == (0, 0, 255)


def test_process_sprite_basic():
    """Test basic sprite processing"""
    params = AtlasParams(tile_size=52)
    processor = AtlasProcessor(params)
    
    img = Image.new('RGBA', (52, 52), (255, 0, 0, 255))
    result = processor.process_sprite(img)
    
    assert result.size == (52, 52)
    assert result.mode == 'RGBA'


def test_process_sprite_with_outline():
    """Test sprite processing with outline"""
    params = AtlasParams(tile_size=52, outline=2)
    processor = AtlasProcessor(params)
    
    img = Image.new('RGBA', (52, 52), (255, 0, 0, 255))
    result = processor.process_sprite(img)
    
    assert result.size == (52, 52)
    assert result.mode == 'RGBA'


def test_process_sprite_with_remove_color():
    """Test sprite processing with color removal"""
    params = AtlasParams(tile_size=52, remove_color="ff0000")
    processor = AtlasProcessor(params)
    
    img = Image.new('RGBA', (52, 52), (255, 0, 0, 255))
    result = processor.process_sprite(img)
    
    # Red pixels should become transparent
    pixel = result.getpixel((26, 26))
    assert pixel[3] == 0  # Alpha should be 0


def test_process_sprite_with_shadow_scale():
    """Test sprite processing with shadow scale"""
    params = AtlasParams(tile_size=52, shadow_scale=1.1)
    processor = AtlasProcessor(params)
    
    img = Image.new('RGBA', (52, 52), (255, 0, 0, 255))
    result = processor.process_sprite(img)
    
    assert result.size == (52, 52)
    assert result.mode == 'RGBA'


def test_process_images_single():
    """Test processing single image"""
    params = AtlasParams(tile_size=52, width=6)
    processor = AtlasProcessor(params)
    
    image_file = create_test_image_file((52, 52), (255, 0, 0, 255))
    image_files = [image_file]
    image_names = ["test1.png"]
    
    atlas, report = processor.process_images(image_files, image_names)
    
    assert atlas.size == (52 * 6, 52 * 1)  # Width=6, height=1
    assert len(report["ignored"]) == 0


def test_process_images_multiple():
    """Test processing multiple images"""
    params = AtlasParams(tile_size=52, width=3)
    processor = AtlasProcessor(params)
    
    # Create 3 test images
    image_files = [
        create_test_image_file((52, 52), (255, 0, 0, 255)),
        create_test_image_file((52, 52), (0, 255, 0, 255)),
        create_test_image_file((52, 52), (0, 0, 255, 255))
    ]
    image_names = ["red.png", "green.png", "blue.png"]
    
    atlas, report = processor.process_images(image_files, image_names)
    
    assert atlas.size == (52 * 3, 52 * 1)  # All fit in one row
    assert len(report["ignored"]) == 0


def test_process_images_with_sample():
    """Test processing with sample rate"""
    params = AtlasParams(tile_size=52, width=6, sample=2)
    processor = AtlasProcessor(params)
    
    # Create 4 test images, but sample=2 means only 2 will be processed
    image_files = [
        create_test_image_file((52, 52), (255, 0, 0, 255)),
        create_test_image_file((52, 52), (0, 255, 0, 255)),
        create_test_image_file((52, 52), (0, 0, 255, 255)),
        create_test_image_file((52, 52), (255, 255, 0, 255))
    ]
    image_names = ["img1.png", "img2.png", "img3.png", "img4.png"]
    
    atlas, report = processor.process_images(image_files, image_names)
    
    # Only images at index 0 and 2 should be processed
    assert atlas.size == (52 * 6, 52 * 1)


def test_process_images_too_wide():
    """Test processing images that are too wide"""
    params = AtlasParams(tile_size=52, width=2)
    processor = AtlasProcessor(params)
    
    # Create an image that's 3 tiles wide (too wide for width=2)
    image_file = create_test_image_file((52 * 3, 52), (255, 0, 0, 255))
    image_files = [image_file]
    image_names = ["wide.png"]
    
    atlas, report = processor.process_images(image_files, image_names)
    
    assert len(report["ignored"]) == 1
    assert report["ignored"][0]["reason"] == "too wide"


def test_create_preview():
    """Test preview creation with scaling"""
    params = AtlasParams(preview_max_width=100)
    processor = AtlasProcessor(params)
    
    # Create a large atlas
    atlas = Image.new('RGBA', (200, 200), (255, 0, 0, 255))
    
    preview = processor.create_preview(atlas)
    
    # Should be scaled down
    assert preview.width == 100
    assert preview.height == 100  # Maintains aspect ratio


def test_create_preview_no_scaling():
    """Test preview creation without scaling needed"""
    params = AtlasParams(preview_max_width=1024)
    processor = AtlasProcessor(params)
    
    # Create a small atlas
    atlas = Image.new('RGBA', (200, 200), (255, 0, 0, 255))
    
    preview = processor.create_preview(atlas)
    
    # Should not be scaled
    assert preview.size == atlas.size


def test_encode_report():
    """Test report encoding"""
    processor = AtlasProcessor(AtlasParams())
    processor.report = {
        "ignored": [{"name": "test.png", "reason": "test reason"}],
        "shadowMissing": ["missing.png"],
        "shadowAmbiguous": []
    }
    
    encoded = processor.encode_report()
    
    # Should be valid base64
    import base64
    import json
    decoded = json.loads(base64.b64decode(encoded).decode())
    
    assert "ignored" in decoded
    assert "shadowMissing" in decoded
    assert "shadowAmbiguous" in decoded