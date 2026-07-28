from PIL import Image
from io import BytesIO
import hashlib
from typing import List, Dict, Optional, Tuple, Union
from dataclasses import dataclass, field
import base64
import json

from atlas_core import (
    make_transparent, add_soft_outline, add_shadow_scale, add_shadow_file,
    render_shadow_scale, render_shadow_file,
    round_half_up, image_equal, find_position, map_height
)
from shadow_matching import process_shadow_matching


@dataclass
class AtlasParams:
    tile_size: int = 192
    width: int = 6
    sample: int = 1
    outline: int = 0
    remove_color: Optional[str] = None
    remove_color_threshold: int = 3
    shadow_scale: float = 0.0
    use_shadow_images: bool = False
    missing_shadow_policy: str = "skipShadow"  # "skipShadow", "ignoreSprite", "fail"
    use_background: bool = False
    skip_duplicate: bool = True
    preview_max_width: int = 1024
    # "separate": export sprite sheet and shadow sheet as two aligned images
    # (background rides along with the shadow layer). "combined": one merged
    # sheet. Only affects export — previews are always merged.
    export_layer_mode: str = "separate"
    # Map of sprite filename -> tile-background filename. Per-tile background
    # overrides the global background for those sprites.
    tile_background_assignments: Dict[str, str] = field(default_factory=dict)


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

    def _apply_sprite_effects(self, img: Image.Image) -> Image.Image:
        """Apply the sprite-only effects (color removal, outline)."""
        # Remove color if specified
        if self.params.remove_color:
            remove_color = self.parse_remove_color(self.params.remove_color)
            img = make_transparent(img, remove_color, self.params.remove_color_threshold)

        # Add outline if specified
        if self.params.outline > 0:
            img = add_soft_outline(img, outline_width=self.params.outline, feather=1)

        return img

    def _resize_to_tile(self, img: Image.Image, scale: Optional[int] = None) -> Image.Image:
        """Resize to tile alignment. Pass `scale` to force a sprite's tile height."""
        if scale is None:
            scale = round_half_up(img.size[1] / img.size[0])
        new_size = (self.params.tile_size, self.params.tile_size * scale)
        return img.resize(new_size, Image.LANCZOS)

    def process_sprite(self, img: Image.Image, shadow_img: Optional[Image.Image] = None) -> Image.Image:
        """Process a single sprite with all effects, shadow merged in."""
        img = self._apply_sprite_effects(img)

        # Add shadow
        if self.params.use_shadow_images and shadow_img:
            scale = self.params.shadow_scale if self.params.shadow_scale > 0 else 1.0
            img = add_shadow_file(img, shadow_img, shadow_scale=scale)
        elif self.params.shadow_scale > 0:
            img = add_shadow_scale(img, shadow_scale=self.params.shadow_scale)

        # Resize to tile alignment
        return self._resize_to_tile(img)

    def process_sprite_layers(self, img: Image.Image,
                              shadow_img: Optional[Image.Image] = None
                              ) -> Tuple[Image.Image, Image.Image]:
        """Process a sprite into two aligned layers: (sprite, shadow).

        The shadow layer carries no sprite pixels; both layers share the sprite's
        tile geometry so the two sheets line up cell for cell. A sprite with no
        shadow still yields a fully transparent shadow layer.
        """
        base = self._apply_sprite_effects(img)

        if self.params.use_shadow_images and shadow_img:
            scale = self.params.shadow_scale if self.params.shadow_scale > 0 else 1.0
            shadow_layer = render_shadow_file(base, shadow_img, shadow_scale=scale)
        elif self.params.shadow_scale > 0:
            shadow_layer = render_shadow_scale(base, shadow_scale=self.params.shadow_scale)
        else:
            shadow_layer = Image.new("RGBA", base.size, (0, 0, 0, 0))

        # Both layers use the sprite's tile scale so the sheets stay aligned.
        tile_scale = round_half_up(base.size[1] / base.size[0])
        return (self._resize_to_tile(base, tile_scale),
                self._resize_to_tile(shadow_layer, tile_scale))

    def _composite_background_tile(self, img: Image.Image, bg_tile: Image.Image, h: int) -> Image.Image:
        """Composite a single-tile background under a (possibly multi-tile) sprite."""
        if h > 1:
            bg_full = Image.new("RGBA", img.size, (0, 0, 0, 0))
            for y in range(h):
                bg_full.paste(bg_tile, (0, y * self.params.tile_size))
            return Image.alpha_composite(bg_full, img)
        if bg_tile.size != img.size:
            bg_tile = bg_tile.resize(img.size, Image.LANCZOS)
        return Image.alpha_composite(bg_tile, img)

    def process_images(self, image_files: List[BytesIO], image_names: List[str],
                      shadow_files: Optional[List[BytesIO]] = None,
                      shadow_names: Optional[List[str]] = None,
                      background_file: Optional[BytesIO] = None,
                      tile_background_files: Optional[List[BytesIO]] = None,
                      tile_background_names: Optional[List[str]] = None) -> Tuple[Image.Image, Dict]:
        """Process all images into a single merged atlas (sprite + shadow + background)."""
        atlas, _shadow_atlas, report = self._build_atlas(
            image_files, image_names, shadow_files, shadow_names, background_file,
            tile_background_files, tile_background_names, separate_layers=False,
        )
        return atlas, report

    def process_layers(self, image_files: List[BytesIO], image_names: List[str],
                       shadow_files: Optional[List[BytesIO]] = None,
                       shadow_names: Optional[List[str]] = None,
                       background_file: Optional[BytesIO] = None,
                       tile_background_files: Optional[List[BytesIO]] = None,
                       tile_background_names: Optional[List[str]] = None
                       ) -> Tuple[Image.Image, Image.Image, Dict]:
        """Process all images into two aligned atlases: (sprite sheet, shadow sheet).

        Backgrounds are composited into the shadow sheet, under the shadows.
        """
        return self._build_atlas(
            image_files, image_names, shadow_files, shadow_names, background_file,
            tile_background_files, tile_background_names, separate_layers=True,
        )

    def _build_atlas(self, image_files: List[BytesIO], image_names: List[str],
                     shadow_files: Optional[List[BytesIO]] = None,
                     shadow_names: Optional[List[str]] = None,
                     background_file: Optional[BytesIO] = None,
                     tile_background_files: Optional[List[BytesIO]] = None,
                     tile_background_names: Optional[List[str]] = None,
                     separate_layers: bool = False
                     ) -> Tuple[Image.Image, Optional[Image.Image], Dict]:
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

        # Load per-tile backgrounds (keyed by filename) for assignments
        tile_bg_tiles: Dict[str, Image.Image] = {}
        if tile_background_files and tile_background_names:
            for tb_file, tb_name in zip(tile_background_files, tile_background_names):
                tb_file.seek(0)
                tb_img = Image.open(tb_file).convert("RGBA")
                tile_bg_tiles[tb_name] = tb_img.resize(
                    (self.params.tile_size, self.params.tile_size), Image.LANCZOS
                )

        # Process sprites
        processed_images = {}
        processed_shadows = {}
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
                if self.params.skip_duplicate and last_image and image_equal(last_image, img):
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
                shadow_tile = None
                if separate_layers:
                    img, shadow_tile = self.process_sprite_layers(img, shadow_img)
                else:
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

                # Apply background: per-tile assignment takes precedence over global.
                # In layered mode the background rides with the shadow layer.
                assigned_bg_name = self.params.tile_background_assignments.get(image_name)
                per_tile_bg = tile_bg_tiles.get(assigned_bg_name) if assigned_bg_name else None
                effective_bg = per_tile_bg or bg_tile
                if effective_bg:
                    if separate_layers:
                        shadow_tile = self._composite_background_tile(shadow_tile, effective_bg, h)
                    else:
                        img = self._composite_background_tile(img, effective_bg, h)

                # Find position in atlas
                loc = find_position(tile_map, self.params.width, w, h)
                processed_images[loc] = img
                if separate_layers:
                    processed_shadows[loc] = shadow_tile

            except Exception as e:
                self.report["ignored"].append({"name": image_name, "reason": f"processing error: {str(e)}"})
                continue

        if not processed_images:
            raise ValueError("No images to process")

        # Create final atlas
        atlas_height = map_height(tile_map, self.params.width)
        atlas_size = (self.params.tile_size * self.params.width,
                      self.params.tile_size * atlas_height)
        atlas = Image.new("RGBA", atlas_size)

        for loc, img in processed_images.items():
            atlas.paste(img, (self.params.tile_size * loc[0], self.params.tile_size * loc[1]))

        if not separate_layers:
            return atlas, None, self.report

        # Same grid, same cells — only the contents differ.
        shadow_atlas = Image.new("RGBA", atlas_size)
        for loc, img in processed_shadows.items():
            shadow_atlas.paste(img, (self.params.tile_size * loc[0], self.params.tile_size * loc[1]))

        return atlas, shadow_atlas, self.report

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