import pytest
from shadow_matching import (
    normalize_filename, strip_shadow_suffix, build_shadow_map,
    match_shadow_for_sprite, resolve_ambiguous_shadow, process_shadow_matching
)


def test_normalize_filename():
    """Test filename normalization"""
    assert normalize_filename("Sprite Image.PNG") == "sprite_image"
    assert normalize_filename("test-file_name.jpg") == "test_file_name"
    assert normalize_filename("UPPERCASE.gif") == "uppercase"


def test_strip_shadow_suffix():
    """Test shadow suffix removal"""
    assert strip_shadow_suffix("sprite_shadow") == "sprite"
    assert strip_shadow_suffix("sprite-shadow") == "sprite"
    assert strip_shadow_suffix("sprite(shadow)") == "sprite"
    assert strip_shadow_suffix("sprite__shadow") == "sprite"
    assert strip_shadow_suffix("spriteshadow") == "sprite"
    assert strip_shadow_suffix("sprite") == "sprite"  # No suffix


def test_build_shadow_map():
    """Test shadow map building"""
    shadow_files = [
        "sprite1_shadow.png",
        "sprite2-shadow.png",
        "sprite3(shadow).png",
        "sprite1__shadow.png"  # Another shadow for sprite1
    ]
    
    shadow_map = build_shadow_map(shadow_files)
    
    assert "sprite1" in shadow_map
    assert "sprite2" in shadow_map
    assert "sprite3" in shadow_map
    assert len(shadow_map["sprite1"]) == 2  # Two shadows for sprite1


def test_match_shadow_for_sprite():
    """Test shadow matching for individual sprites"""
    shadow_map = {
        "sprite1": ["sprite1_shadow.png"],
        "sprite2": ["sprite2_shadow.png", "sprite2__shadow.png"],
    }
    
    # Test matched
    status, candidates = match_shadow_for_sprite("sprite1.png", shadow_map)
    assert status == "matched"
    assert candidates == ["sprite1_shadow.png"]
    
    # Test missing
    status, candidates = match_shadow_for_sprite("sprite3.png", shadow_map)
    assert status == "missing"
    assert candidates == []
    
    # Test ambiguous
    status, candidates = match_shadow_for_sprite("sprite2.png", shadow_map)
    assert status == "ambiguous"
    assert len(candidates) == 2


def test_resolve_ambiguous_shadow():
    """Test ambiguous shadow resolution"""
    # Test shorter filename wins
    candidates = ["very_long_shadow_name.png", "short.png", "medium_name.png"]
    result = resolve_ambiguous_shadow(candidates)
    assert result == "short.png"
    
    # Test lexicographic order for same length
    candidates = ["zebra.png", "apple.png"]
    result = resolve_ambiguous_shadow(candidates)
    assert result == "apple.png"


def test_process_shadow_matching():
    """Test complete shadow matching process"""
    sprite_files = ["sprite1.png", "sprite2.png", "sprite3.png"]
    shadow_files = [
        "sprite1_shadow.png",
        "sprite2_shadow.png", 
        "sprite2__shadow.png"
    ]
    
    result = process_shadow_matching(sprite_files, shadow_files)
    
    # Check structure
    assert "matches" in result
    assert "missing" in result
    assert "ambiguous" in result
    
    # Check matches
    assert "sprite1.png" in result["matches"]
    assert "sprite2.png" in result["matches"]
    
    # Check missing
    assert "sprite3.png" in result["missing"]
    
    # Check ambiguous (should be resolved automatically)
    assert "sprite2.png" in result["ambiguous"]
    assert len(result["ambiguous"]["sprite2.png"]) == 2


def test_case_insensitive_matching():
    """Test that matching is case insensitive"""
    sprite_files = ["SPRITE1.PNG"]
    shadow_files = ["sprite1_shadow.png"]
    
    result = process_shadow_matching(sprite_files, shadow_files)
    
    assert "SPRITE1.PNG" in result["matches"]
    assert len(result["missing"]) == 0


def test_complex_filename_matching():
    """Test complex filename scenarios"""
    sprite_files = [
        "Complex File Name.PNG",
        "another-file_test.jpg",
        "simple.gif"
    ]
    shadow_files = [
        "complex_file_name_shadow.png",
        "another_file_test-shadow.jpg",
        "simple(shadow).gif"
    ]
    
    result = process_shadow_matching(sprite_files, shadow_files)
    
    # All should match
    assert len(result["matches"]) == 3
    assert len(result["missing"]) == 0
    
    # Check specific matches
    assert "Complex File Name.PNG" in result["matches"]
    assert "another-file_test.jpg" in result["matches"]
    assert "simple.gif" in result["matches"]