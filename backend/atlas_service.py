from PIL import Image
from io import BytesIO
import hashlib
from typing import List, Dict, Optional, Tuple, Union
from dataclasses import dataclass
import base64
import json

from atlas_core import (
    make_transparent, add_soft_outline, add_shadow_scale, add_shadow_file,
    round_half_up, image_equal, find_position, map_height
)
from shadow_matching import process_shadow_matching


@dataclass
class AtlasParams:
    tile_size: int = 52
    width: int = 6
    sample: int = 1
    outline: int = 0
    remove_color: Optional[str] = None
    shadow_scale: float = 0.0
    use_shadow_images: bool = False
    missing_shadow_policy: str = "skipShadow"  # "skipShadow", "ignoreSprite", "fail"
    use_background: bool = False
    preview_max_width: int = 1024


class AtlasProcessor:
    def __init__(self, params: AtlasParams):
        self.params = params
        self.report = {
            "ignored": [],
            "shadowMissing": [],
            "shadowAmbiguous": []
        }

    def parse_remove_color(self, color_str: str) -> Tuple[int, int, int]:
        """Parse hex color string to RGB tuple"""
        if color_str.startswith('#'):
            color_str = color_str[1:]
        return tuple(int(color_str[i:i+2], 16) for i in (0, 2, 4))

    def process_sprite(self, img: Image.Image, shadow_img: Optional[Image.Image] = None) -> Image.Image:
        """Process a single sprite with all effects"""
        # Remove color if specified
        if self.params.remove_color:
            remove_color = self.parse_remove_color(self.params.remove_color)
            img = make_transparent(img, remove_color)

        # Add outline if specified
        if self.params.outline > 0:
            img = add_soft_outline(img, outline_width=self.params.outline, feather=1)

        # Add shadow
        if self.params.use_shadow_images and shadow_img:
            img = add_shadow_file(img, shadow_img)
        elif self.params.shadow_scale > 0:
            img = add_shadow_scale(img, shadow_scale=self.params.shadow_scale)

        # Resize to tile alignment
        scale = round_half_up(img.size[1] / img.size[0])
        new_size = (self.params.tile_size, self.params.tile_size * scale)
        img = img.resize(new_size, Image.LANCZOS)

        return img

    def process_images(self, image_files: List[BytesIO], image_names: List[str], 
                      shadow_files: Optional[List[BytesIO]] = None, 
                      shadow_names: Optional[List[str]] = None,
                      background_file: Optional[BytesIO] = None) -> Tuple[Image.Image, Dict]:
        """Process all images and create atlas"""
        
        # Load and process shadow matching if needed
        shadow_matches = {}
        if self.params.use_shadow_images and shadow_files and shadow_names:
            shadow_matching_result = process_shadow_matching(image_names, shadow_names)
            
            # Load shadow images into memory
            shadow_images = {}
            for i, (shadow_file, shadow_name) in enumerate(zip(shadow_files, shadow_names)):
                shadow_file.seek(0)
                shadow_images[shadow_name] = Image.open(shadow_file).convert("RGBA")
            
            # Process shadow matching results
            for sprite_name, shadow_name in shadow_matching_result['matches'].items():
                shadow_matches[sprite_name] = shadow_images[shadow_name]
            
            self.report["shadowMissing"] = shadow_matching_result['missing']
            self.report["shadowAmbiguous"] = [
                {"sprite": sprite, "candidates": candidates}
                for sprite, candidates in shadow_matching_result['ambiguous'].items()
            ]

        # Load background if specified
        bg_tile = None
        if self.params.use_background and background_file:
            background_file.seek(0)
            bg = Image.open(background_file).convert("RGBA")
            bg_tile = bg.resize((self.params.tile_size, self.params.tile_size), Image.LANCZOS)

        # Process sprites
        processed_images = {}
        tile_map = {}
        last_image = None

        for i, (image_file, image_name) in enumerate(zip(image_files, image_names)):
            # Sample filter
            if self.params.sample > 1 and i % self.params.sample != 0:
                continue

            try:
                image_file.seek(0)
                img = Image.open(image_file).convert("RGBA")
                
                # Skip duplicate images
                if last_image and image_equal(last_image, img):
                    self.report["ignored"].append({"name": image_name, "reason": "duplicate"})
                    continue
                
                last_image = img

                # Get corresponding shadow if needed
                shadow_img = None
                if self.params.use_shadow_images:
                    if image_name in shadow_matches:
                        shadow_img = shadow_matches[image_name]
                    else:
                        if self.params.missing_shadow_policy == "ignoreSprite":
                            self.report["ignored"].append({"name": image_name, "reason": "missing shadow"})
                            continue
                        elif self.params.missing_shadow_policy == "fail":
                            raise ValueError(f"Missing shadow for {image_name}")

                # Process the sprite
                img = self.process_sprite(img, shadow_img)

                # Check tile alignment
                if img.size[0] % self.params.tile_size != 0 or img.size[1] % self.params.tile_size != 0:
                    self.report["ignored"].append({"name": image_name, "reason": "size alignment"})
                    continue

                w = int(img.size[0] / self.params.tile_size)
                h = int(img.size[1] / self.params.tile_size)

                # Check width constraint
                if w > self.params.width:
                    self.report["ignored"].append({"name": image_name, "reason": "too wide"})
                    continue

                # Apply background if needed
                if bg_tile:
                    if h > 1:
                        # Create tiled background for multi-tile sprites
                        bg_full = Image.new("RGBA", img.size, (0, 0, 0, 0))
                        for y in range(h):
                            bg_full.paste(bg_tile, (0, y * self.params.tile_size))
                        img = Image.alpha_composite(bg_full, img)
                    else:
                        # Single tile background
                        bg_resized = bg_tile.resize(img.size, Image.LANCZOS)
                        img = Image.alpha_composite(bg_resized, img)

                # Find position in atlas
                loc = find_position(tile_map, self.params.width, w, h)
                processed_images[loc] = img

            except Exception as e:
                self.report["ignored"].append({"name": image_name, "reason": f"processing error: {str(e)}"})
                continue

        if not processed_images:
            raise ValueError("No images to process")

        # Create final atlas
        atlas_height = map_height(tile_map, self.params.width)
        atlas = Image.new("RGBA", (self.params.tile_size * self.params.width, 
                                  self.params.tile_size * atlas_height))

        for loc, img in processed_images.items():
            atlas.paste(img, (self.params.tile_size * loc[0], self.params.tile_size * loc[1]))

        return atlas, self.report

    def create_preview(self, atlas: Image.Image) -> Image.Image:
        """Create a preview-sized version of the atlas"""
        if atlas.width <= self.params.preview_max_width:
            return atlas
        
        scale = self.params.preview_max_width / atlas.width
        new_height = int(atlas.height * scale)
        return atlas.resize((self.params.preview_max_width, new_height), Image.LANCZOS)

    def encode_report(self) -> str:
        """Encode report as base64 JSON string for HTTP header"""
        return base64.b64encode(json.dumps(self.report).encode()).decode()