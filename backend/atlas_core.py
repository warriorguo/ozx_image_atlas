from PIL import Image, ImageFilter, ImageChops
import math


def reset_alpha_and_blackify(img, threshold=180):
    """Convert light pixels to transparent and dark pixels to black with alpha"""
    pixels = img.load()
    width, height = img.size

    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]

            if r > threshold and g > threshold and b > threshold:
                pixels[x, y] = (0, 0, 0, 0)
            else:
                gray = int(0.299 * r + 0.587 * g + 0.114 * b)
                darkness = 255 - gray
                alpha = int(darkness)
                pixels[x, y] = (0, 0, 0, alpha)

    return img


def check_if_took(map_dict, x, y):
    """Check if a position in the tile map is occupied"""
    return (x * 100 + y) in map_dict


def took(map_dict, x, y):
    """Mark a position in the tile map as occupied"""
    map_dict[x * 100 + y] = 1


def map_height(map_dict, width):
    """Calculate the height of the tile map"""
    for y in range(1000):
        stop = True
        for x in range(width):
            if check_if_took(map_dict, x, y):
                stop = False
        if stop:
            return y


def find_position(map_dict, width, w, h):
    """Find a position in the tile map for an image of size w x h"""
    for y in range(1000):
        for x in range(width):
            if check_if_took(map_dict, x, y):
                continue
            if w + x > width:
                continue
            
            ok = True
            for xoffset in range(w):
                for yoffset in range(h):
                    if check_if_took(map_dict, x + xoffset, y + yoffset):
                        ok = False
                        break
                if not ok:
                    break
            
            if not ok:
                continue

            for xoffset in range(w):
                for yoffset in range(h):
                    took(map_dict, x + xoffset, y + yoffset)

            return (x, y)


def add_soft_outline(img, outline_color=(0, 0, 0, 255), outline_width=10, feather=5):
    """Add a soft outline to an image"""
    alpha = img.getchannel('A')
    expanded_alpha = alpha.filter(ImageFilter.MaxFilter(outline_width * 2 + 1))
    edge = ImageChops.difference(expanded_alpha, alpha)
    soft_edge = edge.filter(ImageFilter.GaussianBlur(feather))
    outline = Image.new("RGBA", img.size, outline_color)
    outline.putalpha(soft_edge)
    result = Image.alpha_composite(outline, img)
    return result


def round_half_up(n):
    """Round number using half-up rounding"""
    return int(n + 0.5) if n >= 0 else int(n - 0.5)


def image_equal(img1, img2):
    """Check if two images are identical"""
    if img1.mode != img2.mode or img1.size != img2.size:
        return False
    
    # Convert to same format for comparison
    if img1.mode != 'RGBA':
        img1 = img1.convert('RGBA')
    if img2.mode != 'RGBA':
        img2 = img2.convert('RGBA')
    
    diff = ImageChops.difference(img1, img2)
    bbox = diff.getbbox()
    return bbox is None


def is_roughly_same(a, b, threshold=3):
    """Check if two RGB colors are roughly the same within threshold"""
    return abs(a[0] - b[0]) <= threshold and abs(a[1] - b[1]) <= threshold and abs(a[2] - b[2]) <= threshold


def make_transparent(img, replace_color):
    """Replace a specific color with transparency"""
    data = img.getdata()
    transparent = (0, 0, 0, 0)
    new_data = []

    for item in data:
        if is_roughly_same(replace_color, item):
            new_data.append(transparent)
        else:
            new_data.append(item)

    img.putdata(new_data)
    return img


def add_shadow_scale(original, offset=(0, 0), background_color=(255, 255, 255, 0), 
                    shadow_color=(0, 0, 0), blur_radius=10, shadow_scale=1.1):
    """Add a scaled shadow to an image"""
    alpha = original.split()[3]
    shadow_size = (int(original.size[0] * shadow_scale), int(original.size[1] * shadow_scale))
    shadow_mask = alpha.resize(shadow_size, Image.LANCZOS)

    shadow = Image.new("RGBA", shadow_size, shadow_color + (255,))
    shadow.putalpha(shadow_mask)
    shadow = shadow.filter(ImageFilter.GaussianBlur(blur_radius))

    background = Image.new("RGBA", original.size, background_color)
    original_pos = ((original.size[0] - shadow_size[0]) // 2, (original.size[1] - shadow_size[1]) // 2)

    background.paste(shadow, original_pos, shadow)
    background.paste(original, (0, 0), original)

    return background


def add_shadow_file(img, shadow_img):
    """Add a shadow from another image"""
    shadow_processed = reset_alpha_and_blackify(shadow_img.copy())
    
    if shadow_processed.size != img.size:
        shadow_processed = shadow_processed.resize(img.size, Image.LANCZOS)

    background = Image.new("RGBA", img.size, (0, 0, 0, 0))
    background.paste(shadow_processed, (0, 0), shadow_processed)
    background.paste(img, (0, 0), img)

    return background