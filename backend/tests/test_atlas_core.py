import pytest
from PIL import Image
import atlas_core


def create_test_image(size=(100, 100), color=(255, 0, 0, 255)):
    """Create a test RGBA image"""
    return Image.new('RGBA', size, color)


def test_round_half_up():
    """Test round_half_up function"""
    assert atlas_core.round_half_up(2.5) == 3
    assert atlas_core.round_half_up(2.4) == 2
    assert atlas_core.round_half_up(-2.5) == -3
    assert atlas_core.round_half_up(-2.4) == -2


def test_is_roughly_same():
    """Test is_roughly_same color comparison"""
    assert atlas_core.is_roughly_same((255, 0, 0), (255, 0, 0))
    assert atlas_core.is_roughly_same((255, 0, 0), (252, 1, 2))
    assert not atlas_core.is_roughly_same((255, 0, 0), (200, 0, 0))


def test_image_equal():
    """Test image equality comparison"""
    img1 = create_test_image((50, 50), (255, 0, 0, 255))
    img2 = create_test_image((50, 50), (255, 0, 0, 255))
    img3 = create_test_image((50, 50), (0, 255, 0, 255))
    
    assert atlas_core.image_equal(img1, img2)
    assert not atlas_core.image_equal(img1, img3)


def test_tile_map_functions():
    """Test tile mapping functions"""
    tile_map = {}
    
    # Test basic operations
    assert not atlas_core.check_if_took(tile_map, 0, 0)
    
    atlas_core.took(tile_map, 0, 0)
    assert atlas_core.check_if_took(tile_map, 0, 0)
    
    # Test find_position
    pos1 = atlas_core.find_position(tile_map, 6, 2, 1)  # 2x1 tile
    pos2 = atlas_core.find_position(tile_map, 6, 1, 1)  # 1x1 tile
    
    assert pos1 == (1, 0)  # Should place after the occupied (0,0)
    assert pos2 == (3, 0)  # Should place after the 2x1 tile
    
    # Test map_height
    height = atlas_core.map_height(tile_map, 6)
    assert height == 1  # Only one row used


def test_make_transparent():
    """Test color transparency replacement"""
    img = create_test_image((10, 10), (255, 0, 0, 255))
    result = atlas_core.make_transparent(img, (255, 0, 0))
    
    # Check that red pixels became transparent
    pixel = result.getpixel((5, 5))
    assert pixel[3] == 0  # Alpha should be 0 (transparent)


def test_add_soft_outline():
    """Test soft outline addition"""
    img = create_test_image((52, 52), (255, 0, 0, 255))
    outlined = atlas_core.add_soft_outline(img, outline_width=2)
    
    # Result should have same size
    assert outlined.size == img.size
    # Should be RGBA
    assert outlined.mode == 'RGBA'


def test_add_shadow_scale():
    """Test scaled shadow addition"""
    img = create_test_image((52, 52), (255, 0, 0, 255))
    shadowed = atlas_core.add_shadow_scale(img, shadow_scale=1.2)
    
    # Result should have same size as original
    assert shadowed.size == img.size
    assert shadowed.mode == 'RGBA'


def test_add_shadow_file():
    """Test shadow from file addition"""
    img = create_test_image((52, 52), (255, 0, 0, 255))
    shadow = create_test_image((52, 52), (100, 100, 100, 255))
    
    result = atlas_core.add_shadow_file(img, shadow)
    
    assert result.size == img.size
    assert result.mode == 'RGBA'


def test_reset_alpha_and_blackify():
    """Test shadow processing function"""
    # Create image with light and dark pixels
    img = Image.new('RGBA', (10, 10), (255, 255, 255, 255))  # White
    
    # Add some dark pixels
    pixels = img.load()
    for x in range(5):
        for y in range(5):
            pixels[x, y] = (50, 50, 50, 255)  # Dark gray
    
    result = atlas_core.reset_alpha_and_blackify(img)
    
    # Check that light pixels became transparent
    light_pixel = result.getpixel((9, 9))
    assert light_pixel[3] == 0  # Should be transparent
    
    # Check that dark pixels became black with alpha
    dark_pixel = result.getpixel((2, 2))
    assert dark_pixel[:3] == (0, 0, 0)  # Should be black
    assert dark_pixel[3] > 0  # Should have some alpha