import os
import re
from typing import List, Dict, Tuple, Optional


def normalize_filename(filename: str) -> str:
    """Normalize filename for matching"""
    # Remove extension
    name = os.path.splitext(filename)[0]
    # Convert to lowercase
    name = name.lower()
    # Replace spaces with underscores
    name = name.replace(' ', '_')
    # Unify dashes to underscores
    name = name.replace('-', '_')
    return name


def strip_shadow_suffix(filename: str) -> str:
    """Remove shadow-related suffixes from filename"""
    suffixes = ['__shadow', '_shadow', '-shadow', '(shadow)', 'shadow']  # Longest first
    name = filename
    
    for suffix in suffixes:
        if name.endswith(suffix):
            name = name[:-len(suffix)]
            break
    
    return name


def build_shadow_map(shadow_filenames: List[str]) -> Dict[str, List[str]]:
    """Build a mapping from normalized sprite names to shadow filenames"""
    shadow_map = {}
    
    for shadow_filename in shadow_filenames:
        normalized = normalize_filename(shadow_filename)
        stripped = strip_shadow_suffix(normalized)
        
        if stripped not in shadow_map:
            shadow_map[stripped] = []
        shadow_map[stripped].append(shadow_filename)
    
    return shadow_map


def match_shadow_for_sprite(sprite_filename: str, shadow_map: Dict[str, List[str]]) -> Tuple[str, List[str]]:
    """
    Match a shadow file for a sprite.
    Returns (status, candidates) where:
    - status: 'matched', 'missing', or 'ambiguous'
    - candidates: list of matching shadow filenames
    """
    sprite_key = normalize_filename(sprite_filename)
    
    if sprite_key not in shadow_map:
        return 'missing', []
    
    candidates = shadow_map[sprite_key]
    
    if len(candidates) == 1:
        return 'matched', candidates
    else:
        return 'ambiguous', candidates


def resolve_ambiguous_shadow(candidates: List[str]) -> str:
    """
    Resolve ambiguous shadow matches using deterministic rules:
    1. Shorter filename wins
    2. Lexicographically smaller name wins if same length
    """
    if not candidates:
        return None
    
    # Sort by length first, then lexicographically
    sorted_candidates = sorted(candidates, key=lambda x: (len(x), x))
    return sorted_candidates[0]


def process_shadow_matching(sprite_filenames: List[str], shadow_filenames: List[str]) -> Dict:
    """
    Process shadow matching for all sprites and return a comprehensive report.
    """
    shadow_map = build_shadow_map(shadow_filenames)
    
    results = {
        'matches': {},  # sprite_filename -> shadow_filename
        'missing': [],  # sprite filenames without matches
        'ambiguous': {},  # sprite_filename -> [candidates]
    }
    
    for sprite_filename in sprite_filenames:
        status, candidates = match_shadow_for_sprite(sprite_filename, shadow_map)
        
        if status == 'matched':
            results['matches'][sprite_filename] = candidates[0]
        elif status == 'missing':
            results['missing'].append(sprite_filename)
        elif status == 'ambiguous':
            results['ambiguous'][sprite_filename] = candidates
            # Auto-resolve using rules
            resolved = resolve_ambiguous_shadow(candidates)
            results['matches'][sprite_filename] = resolved
    
    return results