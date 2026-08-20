from __future__ import annotations

from html import escape


# In the North Indian chart the houses are fixed. Once Lagna is placed in the
# top diamond (house 1), the signs must continue sequentially counterclockwise:
# 1 -> 2 -> 3 -> ... -> 12, wrapping after Pisces back to Aries.
COUNTERCLOCKWISE_HOUSE_SEQUENCE = (
    1,
    2,
    3,
    4,
    5,
    6,
    7,
    8,
    9,
    10,
    11,
    12,
)

HOUSE_LAYOUTS = {
    1: {"sign": (286.0, 221.0), "box": {"x": 240.0, "y": 99.0, "width": 86.0, "height": 74.0}},
    2: {"sign": (149.0, 108.0), "box": {"x": 106.0, "y": 16.0, "width": 86.0, "height": 74.0}},
    3: {"sign": (117.0, 136.0), "box": {"x": 14.0, "y": 99.0, "width": 86.0, "height": 74.0}},
    4: {"sign": (241.0, 266.0), "box": {"x": 93.0, "y": 221.0, "width": 86.0, "height": 75.0}},
    5: {"sign": (117.0, 395.0), "box": {"x": 14.0, "y": 357.0, "width": 86.0, "height": 74.0}},
    6: {"sign": (149.0, 423.0), "box": {"x": 101.0, "y": 441.0, "width": 86.0, "height": 74.0}},
    7: {"sign": (286.0, 310.0), "box": {"x": 240.0, "y": 366.0, "width": 86.0, "height": 74.0}},
    8: {"sign": (423.0, 423.0), "box": {"x": 383.0, "y": 441.0, "width": 87.0, "height": 74.0}},
    9: {"sign": (455.0, 395.0), "box": {"x": 476.0, "y": 366.0, "width": 86.0, "height": 74.0}},
    10: {"sign": (331.0, 266.0), "box": {"x": 371.0, "y": 221.0, "width": 86.0, "height": 75.0}},
    11: {"sign": (455.0, 136.0), "box": {"x": 476.0, "y": 99.0, "width": 86.0, "height": 74.0}},
    12: {"sign": (423.0, 108.0), "box": {"x": 383.0, "y": 16.0, "width": 87.0, "height": 74.0}},
}


def build_sign_sequence(lagna_sign_number: int) -> dict[int, int]:
    normalized_lagna = ((lagna_sign_number - 1) % 12) + 1
    return {
        house_number: ((normalized_lagna + offset - 1) % 12) + 1
        for offset, house_number in enumerate(COUNTERCLOCKWISE_HOUSE_SEQUENCE)
    }


# Класическа граха дришти (whole-sign, 0-базови отмествания в знаци).
GRAHA_DRISHTI_OFFSETS = {
    "Sun": (6,),
    "Moon": (6,),
    "Mercury": (6,),
    "Venus": (6,),
    "Mars": (3, 6, 7),
    "Jupiter": (4, 6, 8),
    "Saturn": (2, 6, 9),
    "Rahu": (4, 6, 8),
    "Ketu": (),
}

GRAHA_LABEL_TO_KEY = {
    "Сл": "Sun",
    "Лу": "Moon",
    "Ме": "Mercury",
    "Ве": "Venus",
    "Ма": "Mars",
    "Юп": "Jupiter",
    "Са": "Saturn",
    "Ра": "Rahu",
    "Ке": "Ketu",
}


def _graha_key_from_label(item: str) -> str | None:
    return GRAHA_LABEL_TO_KEY.get(item.strip("()"))


def _group_items(items: list[str], horizontal: bool = False) -> list[list[str]]:
    count = len(items)
    if count == 0:
        return []
    if count == 1:
        return [items]
    if horizontal:
        return [items[index:index + 2] for index in range(0, count, 2)]
    if count in (2, 3, 4):
        return [[item] for item in items]
    return [items[index:index + 2] for index in range(0, count, 2)]


def _line_y_positions(box: dict[str, float], line_count: int) -> list[float]:
    center_y = box["y"] + (box["height"] / 2)
    if line_count <= 3:
        line_gap = 20.0
    elif line_count == 4:
        line_gap = 18.0
    else:
        line_gap = 16.0
    first_y = center_y - ((line_count - 1) * line_gap / 2)
    return [first_y + (index * line_gap) for index in range(line_count)]


def _line_x_positions(box: dict[str, float], item_count: int) -> list[float]:
    center_x = box["x"] + (box["width"] / 2)
    if item_count == 1:
        return [center_x]

    spread = min(20.0, box["width"] * 0.22)
    return [center_x - spread, center_x + spread]


def _item_positions(house_number: int, items: list[str], degrees=None) -> list[tuple[str, float, float]]:
    box = HOUSE_LAYOUTS[house_number]["box"]
    positions, _line_count, _font = _layout_items(box, NORTH_POLYGONS[house_number], items, degrees or {})
    return positions


DEGREE_FONT_SIZE = 14.0
SAFE_PADDING = 8.0
VERTICAL_MARGIN = 0.0

# Реалните polygon-и на 12-те северни дома (viewBox 0 0 572 531).
# Всеки дом е изпъкнал многоъгълник, ограден от диагоналите и рамката.
NORTH_POLYGONS = {
    1: [(286.0, 10.0), (424.5, 137.75), (285.573, 267.162), (147.5, 137.75)],
    2: [(9.0, 10.0), (286.0, 10.0), (147.5, 137.75)],
    3: [(9.0, 10.0), (147.5, 137.75), (9.0, 265.5)],
    4: [(9.0, 265.5), (147.5, 137.75), (311.0, 291.0), (311.0, 240.0), (147.5, 393.25)],
    5: [(9.0, 265.5), (147.5, 393.25), (9.0, 521.0)],
    6: [(9.0, 521.0), (147.5, 393.25), (286.0, 521.0)],
    7: [(286.0, 521.0), (147.5, 393.25), (285.573, 263.838), (424.5, 393.25)],
    8: [(286.0, 521.0), (424.5, 393.25), (563.0, 521.0)],
    9: [(563.0, 521.0), (424.5, 393.25), (563.0, 265.5)],
    10: [(563.0, 265.5), (424.5, 137.75), (260.0, 291.0), (260.0, 240.0), (424.5, 393.25)],
    11: [(563.0, 265.5), (563.0, 10.0), (424.5, 137.75)],
    12: [(286.0, 10.0), (424.5, 137.75), (563.0, 10.0)],
}


def _polygon_x_range(polygon, y: float):
    xs = []
    count = len(polygon)
    for index in range(count):
        x1, y1 = polygon[index]
        x2, y2 = polygon[(index + 1) % count]
        if y1 == y2:
            continue
        if (y1 <= y <= y2) or (y2 <= y <= y1):
            t = (y - y1) / (y2 - y1)
            xs.append(x1 + t * (x2 - x1))
    if not xs:
        return None
    return min(xs), max(xs)


def _planet_font_size(line_count: int) -> float:
    if line_count >= 5:
        return 17.0
    if line_count == 4:
        return 19.0
    return 22.0


def _estimate_item_width(item: str, degree_text: object | None, planet_font_size: float) -> float:
    total = 4.0  # safety allowance за целия item
    for character in item:
        total += 0.34 * planet_font_size if character in "()" else 0.68 * planet_font_size
    if degree_text is not None:
        total += 3.0  # internal degree gap
        total += len(str(degree_text)) * 0.56 * DEGREE_FONT_SIZE
    return total


def _min_horizontal_gap(planet_font_size: float) -> float:
    return max(14.0, planet_font_size * 0.72)


def _line_height(planet_font_size: float) -> float:
    return planet_font_size * 1.15


def _packings(count: int):
    if count <= 0:
        yield []
        return
    for rest in _packings(count - 1):
        yield [1] + rest
    if count >= 2:
        for rest in _packings(count - 2):
            yield [2] + rest


def _adaptive_groups(items, degrees, available_width):
    count = len(items)
    if count <= 4:
        return [[item] for item in items]

    best = None  # (rows, -free_space, packing)
    for packing in _packings(count):
        rows = len(packing)
        font = _planet_font_size(rows)
        gap = _min_horizontal_gap(font)
        ok = True
        free = 0.0
        index = 0
        for size in packing:
            if size == 2:
                w1 = _estimate_item_width(items[index], degrees.get(items[index]), font)
                w2 = _estimate_item_width(items[index + 1], degrees.get(items[index + 1]), font)
                required = w1 + gap + w2
                if required > available_width:
                    ok = False
                    break
                free += available_width - required
            index += size
        if ok:
            key = (rows, -free)
            if best is None or key < best[0]:
                best = (key, packing)

    if best is None:
        return [[item] for item in items]

    groups = []
    index = 0
    for size in best[1]:
        groups.append(items[index:index + size])
        index += size
    return groups


def _adaptive_groups_polygon(items, degrees, polygon, center_y):
    count = len(items)
    if count <= 4:
        return [[item] for item in items]

    polygon_top = min(vertex[1] for vertex in polygon)
    polygon_bottom = max(vertex[1] for vertex in polygon)

    best = None  # (rows, -free_space, packing)
    for packing in _packings(count):
        rows = len(packing)
        font = _planet_font_size(rows)
        line_h = _line_height(font)
        block_h = (rows - 1) * line_h + font
        first_y = center_y - block_h / 2 + font / 2

        if block_h > (polygon_bottom - polygon_top) - 2 * VERTICAL_MARGIN:
            continue

        gap = _min_horizontal_gap(font)
        ok = True
        free = 0.0
        index = 0
        for row_index, size in enumerate(packing):
            y = first_y + row_index * line_h
            x_range = _polygon_x_range(polygon, y)
            if x_range is None:
                ok = False
                break
            x_left, x_right = x_range
            row_center = (x_left + x_right) / 2
            safe_left = x_left + SAFE_PADDING
            safe_right = x_right - SAFE_PADDING
            if size == 2:
                w1 = _estimate_item_width(items[index], degrees.get(items[index]), font)
                w2 = _estimate_item_width(items[index + 1], degrees.get(items[index + 1]), font)
                total = w1 + gap + w2
                pair_left = row_center - total / 2
                pair_right = row_center + total / 2
                if pair_left < safe_left or pair_right > safe_right:
                    ok = False
                    break
                free += (safe_right - safe_left) - total
            else:
                w = _estimate_item_width(items[index], degrees.get(items[index]), font)
                if w > safe_right - safe_left:
                    ok = False
                    break
            index += size
        if ok:
            key = (rows, -free)
            if best is None or key < best[0]:
                best = (key, packing)

    if best is None:
        return [[item] for item in items]

    groups = []
    index = 0
    for size in best[1]:
        groups.append(items[index:index + size])
        index += size
    return groups


def _layout_items(box, polygon, items, degrees):
    if not items:
        return [], 0, 22.0

    center_y = box["y"] + box["height"] / 2
    box_center_x = box["x"] + box["width"] / 2

    if polygon is not None:
        groups = _adaptive_groups_polygon(items, degrees, polygon, center_y)
    else:
        groups = _adaptive_groups(items, degrees, box["width"] - 2 * SAFE_PADDING)

    line_count = len(groups)
    font = _planet_font_size(line_count)
    line_h = _line_height(font)
    block_h = (line_count - 1) * line_h + font
    first_y = center_y - block_h / 2 + font / 2

    if polygon is not None:
        polygon_top = min(vertex[1] for vertex in polygon)
        polygon_bottom = max(vertex[1] for vertex in polygon)
        block_top = first_y - font / 2
        block_bottom = first_y + (line_count - 1) * line_h + font / 2
        if block_top < polygon_top + VERTICAL_MARGIN:
            first_y += (polygon_top + VERTICAL_MARGIN) - block_top
        elif block_bottom > polygon_bottom - VERTICAL_MARGIN:
            first_y -= block_bottom - (polygon_bottom - VERTICAL_MARGIN)

    positions = []
    for row_index, group in enumerate(groups):
        y = first_y + row_index * line_h
        if polygon is not None:
            x_range = _polygon_x_range(polygon, y)
            row_center = (x_range[0] + x_range[1]) / 2 if x_range is not None else box_center_x
        else:
            row_center = box_center_x
        if len(group) == 1:
            positions.append((group[0], row_center, y))
        else:
            w1 = _estimate_item_width(group[0], degrees.get(group[0]), font)
            w2 = _estimate_item_width(group[1], degrees.get(group[1]), font)
            gap = _min_horizontal_gap(font)
            total = w1 + gap + w2
            start_x = row_center - total / 2
            positions.append((group[0], start_x + w1 / 2, y))
            positions.append((group[1], start_x + w1 + gap + w2 / 2, y))

    return positions, line_count, font


def _line_positions(house_number: int, items: list[str]) -> list[tuple[str, float, float]]:
    box = HOUSE_LAYOUTS[house_number]["box"]
    groups = _group_items(items)
    center_x = box["x"] + (box["width"] / 2)
    y_positions = _line_y_positions(box, len(groups))
    return [(" ".join(group), center_x, y_pos) for group, y_pos in zip(groups, y_positions)]


def _is_arudha_label(item: str) -> bool:
    return item == "Ал" or (item.startswith("А") and item[1:].isdigit())


def _text_class(item: str, line_count: int) -> str:
    class_names = ["chart-content"]
    if item in {"Ур", "Не", "Пл"}:
        class_names.append("chart-content--outer")
    elif item in {"Ас", "Àñ"} or _is_arudha_label(item):
        class_names.append("chart-content--asc")
    elif "(" in item:
        class_names.append("chart-content--retro")
    if line_count >= 5:
        class_names.append("chart-content--tight")
    elif line_count == 4:
        class_names.append("chart-content--dense")
    return " ".join(class_names)


def _sign_class(sign_number: object) -> str:
    class_names = ["chart-sign-label"]
    if len(str(sign_number)) >= 2:
        class_names.append("chart-sign-label--double")
    return " ".join(class_names)


def _center_title_class(title: object) -> str:
    del title
    return "chart-center-title"


def _render_chart_item(item: str, degree: object | None) -> str:
    label = escape(item)
    if degree is None:
        return label
    return f'<tspan>{label}</tspan><tspan class="chart-degree" dx="3">{escape(str(degree))}</tspan>'


def _degree_sort_value(value: object | None) -> float:
    import re
    parts = re.findall(r"\d+(?:[.,]\d+)?", str(value or ""))
    if not parts:
        return float("inf")
    numbers = [float(part.replace(",", ".")) for part in parts[:3]]
    numbers.extend([0.0] * (3 - len(numbers)))
    return numbers[0] + numbers[1] / 60.0 + numbers[2] / 3600.0


def _sorted_degree_items(items: list[str], item_degrees: dict[str, object]) -> list[str]:
    indexed = list(enumerate(items))
    return [
        item
        for _, item in sorted(
            indexed,
            key=lambda pair: (
                0 if pair[1] in {"Ас", "ГЂГ±"} else 1,
                _degree_sort_value(item_degrees.get(pair[1])),
                pair[0],
            ),
        )
    ]


def render_north_chart(chart: dict[str, object], *, show_degrees: bool = False) -> str:
    raw_title = str(chart["title"])
    title = escape(raw_title)
    subtitle = escape(str(chart["subtitle"]))
    aria_title = escape(str(chart.get("aria_title", chart["title"])))
    chart_id = "".join(
        character.lower()
        for character in f"{chart['title']}-{chart['subtitle']}"
        if character.isascii() and character.isalnum()
    ) or "chart"
    bg_id = f"chartBg-{chart_id}"
    center_id = f"centerGlow-{chart_id}"
    line_mask_id = f"lineMask-{chart_id}"

    sign_parts: list[str] = []
    item_parts: list[str] = []
    sign_field_parts: list[str] = []
    item_degrees = chart.get("item_degrees", {}) if show_degrees else {}

    for house in chart["houses"]:
        house_number = house["house"]
        sign_x, sign_y = HOUSE_LAYOUTS[house_number]["sign"]
        field_points = " ".join(f"{x:.2f},{y:.2f}" for x, y in NORTH_POLYGONS[house_number])
        sign_field_parts.append(
            f'<polygon class="chart-sign-field" data-sign="{house["sign_number"]}" points="{field_points}"></polygon>'
        )
        sign_parts.append(
            f'<text class="{_sign_class(house["sign_number"])}" x="{sign_x:.1f}" y="{sign_y:.1f}" '
            f'data-sign="{house["sign_number"]}" '
            f'text-anchor="middle" dominant-baseline="middle">{house["sign_number"]}</text>'
        )

        items = _sorted_degree_items(list(house["items"]), item_degrees) if show_degrees else house["items"]
        positions, line_count, _font = _layout_items(HOUSE_LAYOUTS[house_number]["box"], NORTH_POLYGONS[house_number], items, item_degrees)
        for item, x_pos, y_pos in positions:
            graha_key = _graha_key_from_label(item)
            graha_attrs = (
                f' data-graha-key="{graha_key}" data-graha-sign="{house["sign_number"]}"'
                if graha_key is not None
                else ""
            )
            item_parts.append(
                f'<text class="{_text_class(item, line_count)}" x="{x_pos:.1f}" y="{y_pos:.1f}" '
                f'text-anchor="middle" dominant-baseline="middle"{graha_attrs}>'
                f'{_render_chart_item(item, item_degrees.get(item))}</text>'
            )

    return f"""
<svg class="north-chart-svg" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 572 531" role="img" aria-label="{aria_title}">
  <defs>
    <linearGradient id="{bg_id}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#fffef9" />
      <stop offset="100%" stop-color="#f4eedb" />
    </linearGradient>
    <linearGradient id="{center_id}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#ddd2a5" />
      <stop offset="100%" stop-color="#c5b175" />
    </linearGradient>
    <mask id="{line_mask_id}">
      <rect width="572" height="531" fill="white" />
      <rect x="248" y="231" width="76" height="70" rx="18" fill="black" />
    </mask>
  </defs>
  <rect width="572" height="531" rx="18" fill="url(#{bg_id})" />
  <g mask="url(#{line_mask_id})">
    <rect x="9" y="10" width="554" height="511" fill="none" stroke="#4e7b4a" stroke-width="2"/>
    <line x1="286" y1="10" x2="563" y2="265.5" stroke="#4e7b4a" stroke-width="2"/>
    <line x1="563" y1="265.5" x2="286" y2="521" stroke="#4e7b4a" stroke-width="2"/>
    <line x1="286" y1="521" x2="9" y2="265.5" stroke="#4e7b4a" stroke-width="2"/>
    <line x1="9" y1="265.5" x2="286" y2="10" stroke="#4e7b4a" stroke-width="2"/>
    <line x1="9" y1="10" x2="147.5" y2="137.75" stroke="#4e7b4a" stroke-width="2"/>
    <line x1="147.5" y1="137.75" x2="311" y2="291" stroke="#4e7b4a" stroke-width="2"/>
    <line x1="563" y1="10" x2="424.5" y2="137.75" stroke="#4e7b4a" stroke-width="2"/>
    <line x1="424.5" y1="137.75" x2="260" y2="291" stroke="#4e7b4a" stroke-width="2"/>
    <line x1="9" y1="521" x2="147.5" y2="393.25" stroke="#4e7b4a" stroke-width="2"/>
    <line x1="147.5" y1="393.25" x2="311" y2="240" stroke="#4e7b4a" stroke-width="2"/>
    <line x1="563" y1="521" x2="424.5" y2="393.25" stroke="#4e7b4a" stroke-width="2"/>
    <line x1="424.5" y1="393.25" x2="260" y2="240" stroke="#4e7b4a" stroke-width="2"/>
  </g>
  <rect x="255" y="238" width="62" height="56" rx="12" fill="url(#{center_id})" stroke="#4e7b4a" stroke-width="2"/>
  <text x="286" y="275.5" text-anchor="middle" class="{_center_title_class(raw_title)}">{title}</text>
  {"".join(sign_field_parts)}
  {"".join(sign_parts)}
  {"".join(item_parts)}
</svg>
""".strip()


def render_transit_overlay_chart(
    natal_chart: dict[str, object],
    transit_chart: dict[str, object],
    *,
    show_outer_planets: bool = False,
) -> str:
    """Render a smaller natal chart inside a larger transit chart."""
    width = 1200.0
    height = 400.0
    inner_x, inner_y = 205.0, 70.0
    inner_width, inner_height = 790.0, 260.0
    outer_labels = {"Ур", "Не", "Пл"}
    natal_degrees = natal_chart.get("item_degrees", {})
    transit_degrees = transit_chart.get("item_degrees", {})
    transit_by_sign = {
        int(sign_number): list(items)
        for sign_number, items in transit_chart.get("sign_items", {}).items()
    }

    def visible(items: list[str]) -> list[str]:
        if show_outer_planets:
            return items
        return [item for item in items if item not in outer_labels]

    def sorted_visible(items: list[str], degrees: dict[str, object]) -> list[str]:
        return _sorted_degree_items(visible(items), degrees)

    def inner_point(x: float, y: float) -> tuple[float, float]:
        return inner_x + (x / 572.0 * inner_width), inner_y + (y / 531.0 * inner_height)

    def item_markup(item: str, degrees: dict[str, object]) -> str:
        return (
            f'<tspan>{escape(item)}</tspan>'
            f'<tspan class="transit-overlay-degree" dx="2">{escape(str(degrees.get(item, "")))}</tspan>'
        )

    def natal_items(house_number: int, items: list[str]) -> list[str]:
        chart_items = sorted_visible(items, natal_degrees)
        groups = _group_items(chart_items)
        item_count = len(chart_items)
        parts = []
        box = HOUSE_LAYOUTS[house_number]["box"]
        center_x, center_y = inner_point(
            box["x"] + box["width"] / 2,
            box["y"] + box["height"] / 2,
        )
        line_gap = 19.0 if len(groups) <= 3 else 16.0 if len(groups) <= 5 else 14.0
        density_class = (
            " transit-overlay-item--dense"
            if item_count >= 7
            else " transit-overlay-item--compact"
            if item_count >= 5
            else ""
        )
        first_y = center_y - ((len(groups) - 1) * line_gap / 2)
        for group_index, group in enumerate(groups):
            y = first_y + group_index * line_gap
            horizontal_gap = 31.0 if item_count >= 7 else 35.0
            xs = [center_x] if len(group) == 1 else [center_x - horizontal_gap, center_x + horizontal_gap]
            for item, x in zip(group, xs):
                parts.append(
                    f'<text class="transit-overlay-item transit-overlay-item--natal'
                    f'{density_class}{" transit-overlay-item--outer" if item in outer_labels else ""}" '
                    f'x="{x:.1f}" y="{y:.1f}" text-anchor="middle" dominant-baseline="middle">'
                    f'{item_markup(item, natal_degrees)}</text>'
                )
        return parts

    transit_anchors = {
        1: (600, 28), 2: (345, 31), 3: (100, 84), 4: (82, 200),
        5: (100, 316), 6: (345, 369), 7: (600, 372), 8: (855, 369),
        9: (1100, 316), 10: (1118, 200), 11: (1100, 84), 12: (855, 31),
    }

    def transit_items(house_number: int, items: list[str]) -> list[str]:
        groups = _group_items(sorted_visible(items, transit_degrees))
        anchor_x, anchor_y = transit_anchors[house_number]
        gap = 19.0
        first_y = anchor_y - ((len(groups) - 1) * gap / 2)
        parts = []
        for group_index, group in enumerate(groups):
            y = first_y + group_index * gap
            xs = [anchor_x] if len(group) == 1 else [anchor_x - 28, anchor_x + 28]
            for item, x in zip(group, xs):
                parts.append(
                    f'<text class="transit-overlay-item transit-overlay-item--transit'
                    f'{" transit-overlay-item--outer" if item in outer_labels else ""}" '
                    f'x="{x:.1f}" y="{y:.1f}" text-anchor="middle" dominant-baseline="middle">'
                    f'{item_markup(item, transit_degrees)}</text>'
                )
        return parts

    sign_parts: list[str] = []
    item_parts: list[str] = []
    for house in natal_chart["houses"]:
        house_number = int(house["house"])
        sign_number = int(house["sign_number"])
        sign_x, sign_y = HOUSE_LAYOUTS[house_number]["sign"]
        inner_sign_x, inner_sign_y = inner_point(sign_x, sign_y)
        sign_parts.append(
            f'<text class="chart-sign-label" x="{inner_sign_x:.1f}" y="{inner_sign_y:.1f}" '
            f'text-anchor="middle" dominant-baseline="middle">{sign_number}</text>'
        )
        item_parts.extend(natal_items(house_number, list(house["items"])))
        item_parts.extend(transit_items(house_number, transit_by_sign.get(sign_number, [])))

    return f"""
<svg class="transit-overlay-svg" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 400" role="img" aria-label="Наслагване на рождена Раши и транзити">
  <defs>
    <linearGradient id="transitOverlayBg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#fffef9" />
      <stop offset="100%" stop-color="#f3edda" />
    </linearGradient>
    <linearGradient id="transitOverlayNatalBg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#f3f5e9" />
      <stop offset="100%" stop-color="#e6ecd8" />
    </linearGradient>
  </defs>
  <rect width="1200" height="400" rx="10" fill="url(#transitOverlayBg)" />
  <rect x="{inner_x:.1f}" y="{inner_y:.1f}" width="{inner_width:.1f}" height="{inner_height:.1f}" fill="url(#transitOverlayNatalBg)" fill-opacity="0.76" />
  <rect class="transit-overlay-line transit-overlay-line--frame" x="0.8" y="0.8" width="1198.4" height="398.4" rx="9" />
  <rect class="transit-overlay-line transit-overlay-line--natal-frame" x="{inner_x:.1f}" y="{inner_y:.1f}" width="{inner_width:.1f}" height="{inner_height:.1f}" />
  <line class="transit-overlay-line transit-overlay-line--continuation" x1="0" y1="0" x2="1200" y2="400" />
  <line class="transit-overlay-line transit-overlay-line--continuation" x1="1200" y1="0" x2="0" y2="400" />
  <line class="transit-overlay-line transit-overlay-line--continuation" x1="387.3" y1="0" x2="1200" y2="267.5" />
  <line class="transit-overlay-line transit-overlay-line--continuation" x1="1200" y1="132.5" x2="387.3" y2="400" />
  <line class="transit-overlay-line transit-overlay-line--continuation" x1="812.7" y1="400" x2="0" y2="132.5" />
  <line class="transit-overlay-line transit-overlay-line--continuation" x1="0" y1="267.5" x2="812.7" y2="0" />
  <g class="transit-overlay-labels">{"".join(sign_parts)}{"".join(item_parts)}</g>
</svg>
""".strip()
