"""
Script to generate a professional Hearthstone Arena AI Master icon (app.ico and app.png).
"""

import math
from PIL import Image, ImageDraw, ImageFilter

def create_hearthstone_icon(size=256):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    center = size / 2
    r_outer = size * 0.46

    # 1. Outer Gold Beveled Ring
    for r in range(int(r_outer), int(r_outer - size * 0.08), -1):
        ratio = (r - (r_outer - size * 0.08)) / (size * 0.08)
        # Gold gradient from light gold to darker bronze
        r_c = int(245 * ratio + 180 * (1 - ratio))
        g_c = int(175 * ratio + 120 * (1 - ratio))
        b_c = int(35 * ratio + 20 * (1 - ratio))
        draw.ellipse([center - r, center - r, center + r, center + r], outline=(r_c, g_c, b_c, 255), width=2)

    # 2. Inner Deep Arcane Midnight Medallion
    r_inner = r_outer - size * 0.075
    for r in range(int(r_inner), 0, -2):
        frac = r / r_inner
        # Radial gradient from bright cyan-violet center to deep obsidian
        r_c = int(15 * (1 - frac) + 12 * frac)
        g_c = int(23 * (1 - frac) + 38 * frac)
        b_c = int(42 * (1 - frac) + 75 * frac)
        draw.ellipse([center - r, center - r, center + r, center + r], fill=(r_c, g_c, b_c, 255))

    # 3. Hearthstone Golden 8-Pointed Star / Arena Compass Points
    star_outer_r = r_inner * 0.95
    star_inner_r = r_inner * 0.52
    points = []
    num_points = 8
    for i in range(num_points * 2):
        angle = i * math.pi / num_points - math.pi / 2
        r = star_outer_r if i % 2 == 0 else star_inner_r
        x = center + r * math.cos(angle)
        y = center + r * math.sin(angle)
        points.append((x, y))

    # Draw star with gold / brass gradient feel
    draw.polygon(points, fill=(217, 119, 6, 230), outline=(251, 191, 36, 255))

    # Inner secondary faceted diamond
    diamond_r = r_inner * 0.65
    d_points = [
        (center, center - diamond_r),
        (center + diamond_r * 0.8, center),
        (center, center + diamond_r),
        (center - diamond_r * 0.8, center),
    ]
    draw.polygon(d_points, fill=(30, 27, 75, 240), outline=(245, 158, 11, 255))

    # 4. Central Glowing Arcane Swirl / Mana Crystal (The Hearthstone Soul)
    crystal_r = size * 0.22
    # Draw glowing cyan/azure crystal facets
    facet_top = [
        (center, center - crystal_r * 1.2),
        (center + crystal_r * 0.85, center - crystal_r * 0.1),
        (center, center + crystal_r * 0.35),
        (center - crystal_r * 0.85, center - crystal_r * 0.1),
    ]
    draw.polygon(facet_top, fill=(14, 165, 233, 255), outline=(56, 189, 248, 255))

    facet_bottom = [
        (center - crystal_r * 0.85, center - crystal_r * 0.1),
        (center, center + crystal_r * 0.35),
        (center, center + crystal_r * 1.2),
        (center - crystal_r * 0.5, center + crystal_r * 0.4),
    ]
    draw.polygon(facet_bottom, fill=(2, 132, 199, 255), outline=(56, 189, 248, 255))

    facet_bottom_right = [
        (center + crystal_r * 0.85, center - crystal_r * 0.1),
        (center, center + crystal_r * 0.35),
        (center, center + crystal_r * 1.2),
        (center + crystal_r * 0.5, center + crystal_r * 0.4),
    ]
    draw.polygon(facet_bottom_right, fill=(3, 105, 161, 255), outline=(56, 189, 248, 255))

    # Center spiral / core energy highlight
    core_highlight = [
        (center - crystal_r * 0.35, center - crystal_r * 0.3),
        (center + crystal_r * 0.2, center - crystal_r * 0.4),
        (center + crystal_r * 0.35, center + crystal_r * 0.1),
        (center - crystal_r * 0.1, center + crystal_r * 0.25),
    ]
    draw.polygon(core_highlight, fill=(186, 230, 253, 255))

    # 5. Top 12-Win Laurel Leaves (竞技场12胜月桂金冠装饰)
    crown_y = center - r_outer * 0.72
    crown_r = size * 0.12
    crown_pts = [
        (center - crown_r, crown_y),
        (center - crown_r * 0.6, crown_y - crown_r * 0.7),
        (center, crown_y - crown_r * 0.2),
        (center + crown_r * 0.6, crown_y - crown_r * 0.7),
        (center + crown_r, crown_y),
        (center + crown_r * 0.7, crown_y + crown_r * 0.3),
        (center, crown_y + crown_r * 0.1),
        (center - crown_r * 0.7, crown_y + crown_r * 0.3),
    ]
    draw.polygon(crown_pts, fill=(253, 224, 71, 255), outline=(234, 179, 8, 255))

    # 6. Bottom "AI" badge (High-tech arena ribbon)
    badge_w = size * 0.32
    badge_h = size * 0.16
    badge_x = center - badge_w / 2
    badge_y = center + r_outer * 0.55
    draw.rounded_rectangle(
        [badge_x, badge_y, badge_x + badge_w, badge_y + badge_h],
        radius=8,
        fill=(15, 23, 42, 240),
        outline=(245, 158, 11, 255),
        width=2,
    )

    # Draw "AI" text with primitives to look crisp without font dependency
    # Letter 'A'
    a_left = center - badge_w * 0.26
    a_top = badge_y + badge_h * 0.2
    a_bot = badge_y + badge_h * 0.8
    a_w = badge_w * 0.22
    draw.line([(a_left, a_bot), (a_left + a_w / 2, a_top)], fill=(56, 189, 248, 255), width=3)
    draw.line([(a_left + a_w / 2, a_top), (a_left + a_w, a_bot)], fill=(56, 189, 248, 255), width=3)
    draw.line([(a_left + a_w * 0.25, a_top + (a_bot - a_top) * 0.58), (a_left + a_w * 0.75, a_top + (a_bot - a_top) * 0.58)], fill=(56, 189, 248, 255), width=3)

    # Letter 'I'
    i_x = center + badge_w * 0.18
    draw.line([(i_x, a_top), (i_x, a_bot)], fill=(56, 189, 248, 255), width=3)
    draw.line([(i_x - 5, a_top), (i_x + 5, a_top)], fill=(56, 189, 248, 255), width=2)
    draw.line([(i_x - 5, a_bot), (i_x + 5, a_bot)], fill=(56, 189, 248, 255), width=2)

    return img


if __name__ == "__main__":
    icon = create_hearthstone_icon(256)
    icon.save("app.png", format="PNG")
    # Save multi-size .ico
    icon.save(
        "app.ico",
        format="ICO",
        sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)],
    )
    print("Generated app.png and app.ico successfully!")
