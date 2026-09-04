function decimalToDms(value) {
  const totalSeconds = Math.round(Math.abs(value) * 3600);
  const degrees = Math.floor(totalSeconds / 3600);
  const remainder = totalSeconds % 3600;
  const minutes = Math.floor(remainder / 60);
  const seconds = remainder % 60;
  return { degrees, minutes, seconds };
}

function persistUserSetting(name, value) {
  fetch("/api/user-settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ [name]: value }),
  }).catch(() => {
    // Настройката остава приложена в текущото отваряне дори при дискова грешка.
  });
}

const NORTH_CHART_LAYOUTS = {
  1: { sign: [286.0, 221.0], box: { x: 240.0, y: 99.0, width: 86.0, height: 74.0 } },
  2: { sign: [149.0, 108.0], box: { x: 106.0, y: 16.0, width: 86.0, height: 74.0 } },
  3: { sign: [117.0, 136.0], box: { x: 14.0, y: 99.0, width: 86.0, height: 74.0 } },
  4: { sign: [241.0, 266.0], box: { x: 93.0, y: 221.0, width: 86.0, height: 75.0 } },
  5: { sign: [117.0, 395.0], box: { x: 14.0, y: 357.0, width: 86.0, height: 74.0 } },
  6: { sign: [149.0, 423.0], box: { x: 101.0, y: 441.0, width: 86.0, height: 74.0 } },
  7: { sign: [286.0, 310.0], box: { x: 240.0, y: 366.0, width: 86.0, height: 74.0 } },
  8: { sign: [423.0, 423.0], box: { x: 383.0, y: 441.0, width: 87.0, height: 74.0 } },
  9: { sign: [455.0, 395.0], box: { x: 476.0, y: 366.0, width: 86.0, height: 74.0 } },
  10: { sign: [331.0, 266.0], box: { x: 371.0, y: 221.0, width: 86.0, height: 75.0 } },
  11: { sign: [455.0, 136.0], box: { x: 476.0, y: 99.0, width: 86.0, height: 74.0 } },
  12: { sign: [423.0, 108.0], box: { x: 383.0, y: 16.0, width: 87.0, height: 74.0 } },
};

const SOUTH_SIGN_LAYOUTS = {
  12: { box: { x: 14.9, y: 14.9, width: 135.5, height: 135.5 } },
  1: { box: { x: 150.5, y: 14.9, width: 135.5, height: 135.5 } },
  2: { box: { x: 286.0, y: 14.9, width: 135.5, height: 135.5 } },
  3: { box: { x: 421.5, y: 14.9, width: 135.5, height: 135.5 } },
  4: { box: { x: 421.5, y: 150.5, width: 135.5, height: 135.5 } },
  5: { box: { x: 421.5, y: 286.0, width: 135.5, height: 135.5 } },
  6: { box: { x: 421.5, y: 421.5, width: 135.5, height: 135.5 } },
  7: { box: { x: 286.0, y: 421.5, width: 135.5, height: 135.5 } },
  8: { box: { x: 150.5, y: 421.5, width: 135.5, height: 135.5 } },
  9: { box: { x: 14.9, y: 421.5, width: 135.5, height: 135.5 } },
  10: { box: { x: 14.9, y: 286.0, width: 135.5, height: 135.5 } },
  11: { box: { x: 14.9, y: 150.5, width: 135.5, height: 135.5 } },
};

const OUTER_PLANET_CHART_LABELS = new Set(["Ур", "Не", "Пл"]);
let showOuterPlanetsInCharts = false;

const GRAHA_DRISHTI_OFFSETS = {
  Sun: [6],
  Moon: [6],
  Mercury: [6],
  Venus: [6],
  Mars: [3, 6, 7],
  Jupiter: [4, 6, 8],
  Saturn: [2, 6, 9],
  Rahu: [4, 6, 8],
  Ketu: [],
};

const GRAHA_LABEL_TO_KEY = {
  "Сл": "Sun",
  "Лу": "Moon",
  "Ме": "Mercury",
  "Ве": "Venus",
  "Ма": "Mars",
  "Юп": "Jupiter",
  "Са": "Saturn",
  "Ра": "Rahu",
  "Ке": "Ketu",
};

function grahaKeyFromLabel(item) {
  return GRAHA_LABEL_TO_KEY[String(item).replace(/[()]/g, "")];
}

const RASHI_MOVABLE = new Set([1, 4, 7, 10]);
const RASHI_FIXED = new Set([2, 5, 8, 11]);
const RASHI_DUAL = new Set([3, 6, 9, 12]);

function rashiDrishtiTargets(sign) {
  if (RASHI_DUAL.has(sign)) {
    return [...RASHI_DUAL].filter((item) => item !== sign);
  }
  if (RASHI_MOVABLE.has(sign)) {
    const exclude = sign + 1;
    return [...RASHI_FIXED].filter((item) => item !== exclude);
  }
  const exclude = sign - 1;
  return [...RASHI_MOVABLE].filter((item) => item !== exclude);
}

function visibleChartItems(items) {
  if (showOuterPlanetsInCharts) {
    return items || [];
  }
  return (items || []).filter((item) => !OUTER_PLANET_CHART_LABELS.has(item));
}

/* Reconcile combustion directly from the longitudes displayed in the main
   table.  This is deliberately a second guard after the Python calculation:
   it keeps the marker correct after in-place time navigation and DOM morphs. */
function reconcileDesktopCombustionBadges(root = document) {
  const table = root.querySelector(".desktop-position-table");
  if (!table) return;
  const rows = Array.from(table.querySelectorAll("tbody tr[data-graha-key][data-absolute-longitude]"));
  const sun = rows.find((row) => row.dataset.grahaKey === "Sun");
  const sunLongitude = Number(sun?.dataset.absoluteLongitude);
  if (!Number.isFinite(sunLongitude)) return;
  const input = document.getElementById("combustionOrbDegrees");
  const parsedOrb = Number(input?.value);
  const orb = Number.isFinite(parsedOrb) && parsedOrb > 0
    ? Math.min(30, parsedOrb)
    : 5;
  const eligible = new Set(["Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]);

  rows.forEach((row) => {
    const cell = row.querySelector(".desktop-graha-cell");
    if (!cell) return;
    const longitude = Number(row.dataset.absoluteLongitude);
    const rawDifference = Math.abs(longitude - sunLongitude) % 360;
    const separation = Math.min(rawDifference, 360 - rawDifference);
    const shouldShow = eligible.has(row.dataset.grahaKey) && Number.isFinite(longitude) && separation <= orb + 1e-9;
    let badge = cell.querySelector(".combustion-badge");
    if (shouldShow && !badge) {
      badge = document.createElement("span");
      badge.className = "combustion-badge";
      badge.textContent = "☀";
      badge.setAttribute("aria-label", "Горяща планета");
      cell.prepend(badge);
    }
    if (shouldShow && badge) badge.title = `Горяща планета — ${separation.toFixed(2)}° от Слънцето`;
    if (!shouldShow && badge) badge.remove();
  });
}

/* Ганданта се изчислява върху абсолютната сидерична дължина само за Д-1 и
   транзитната карта (защото там има градуси). */
function reconcileDesktopGandantaBadges(root = document) {
  const eligible = new Set(["Ascendant", "Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Rahu", "Ketu", "Uranus", "Neptune", "Pluto"]);
  const waterSigns = new Set([3, 7, 11]);
  const fireSigns = new Set([0, 4, 8]);
  const WATER_START = 26 + 40 / 60;
  const FIRE_END = 3 + 20 / 60;
  root.querySelectorAll(".desktop-position-table, .desktop-transit-position-table").forEach((table) => {
    table.querySelectorAll("tbody tr[data-graha-key][data-absolute-longitude]").forEach((row) => {
      const cell = row.querySelector(".desktop-graha-cell");
      if (!cell) return;
      const longitude = Number(row.dataset.absoluteLongitude);
      let inGandanta = false;
      if (eligible.has(row.dataset.grahaKey) && Number.isFinite(longitude)) {
        const normalized = ((longitude % 360) + 360) % 360;
        const sign = Math.floor(normalized / 30);
        const degree = normalized % 30;
        inGandanta = (waterSigns.has(sign) && degree >= WATER_START) || (fireSigns.has(sign) && degree < FIRE_END);
      }
      let badge = cell.querySelector(".gandanta-badge");
      if (inGandanta && !badge) {
        badge = document.createElement("span");
        badge.className = "gandanta-badge";
        badge.textContent = "🔥";
        badge.title = "В Ганданта";
        badge.setAttribute("aria-label", "В Ганданта");
        cell.append(badge);
      }
      if (!inGandanta && badge) badge.remove();
    });
  });
}

/* Planetary war is derived again in the browser so time navigation and the
   annual/transit tables cannot retain stale arrows after an in-place update. */
function reconcileDesktopPlanetaryWar(root = document) {
  const eligible = new Set(["Mercury", "Venus", "Mars", "Jupiter", "Saturn"]);
  root.querySelectorAll(".desktop-position-table, .desktop-transit-position-table").forEach((table) => {
    const rows = Array.from(table.querySelectorAll("tbody tr[data-graha-key][data-absolute-longitude]"));
    const state = new Map();
    rows.forEach((row) => state.set(row, { wins: [], losses: [], distances: [] }));

    for (let firstIndex = 0; firstIndex < rows.length; firstIndex += 1) {
      const first = rows[firstIndex];
      if (!eligible.has(first.dataset.grahaKey)) continue;
      const firstLongitude = Number(first.dataset.absoluteLongitude);
      if (!Number.isFinite(firstLongitude)) continue;
      for (let secondIndex = firstIndex + 1; secondIndex < rows.length; secondIndex += 1) {
        const second = rows[secondIndex];
        if (!eligible.has(second.dataset.grahaKey)) continue;
        const secondLongitude = Number(second.dataset.absoluteLongitude);
        if (!Number.isFinite(secondLongitude)) continue;
        if (Math.floor(firstLongitude / 30) !== Math.floor(secondLongitude / 30)) continue;
        const distance = Math.abs(firstLongitude - secondLongitude);
        if (distance >= 1 - 1e-12) continue;
        const [winner, loser] = firstLongitude < secondLongitude ? [first, second] : [second, first];
        state.get(winner).wins.push(loser.dataset.grahaKey);
        state.get(loser).losses.push(winner.dataset.grahaKey);
        state.get(winner).distances.push(distance);
        state.get(loser).distances.push(distance);
      }
    }

    rows.forEach((row) => {
      const cell = row.querySelector(".desktop-graha-cell");
      if (!cell) return;
      const outcome = state.get(row);
      const active = Boolean(outcome && (outcome.wins.length || outcome.losses.length));
      const result = active && outcome.losses.length ? "loser" : active ? "winner" : "";
      cell.classList.toggle("is-planetary-war", active);
      cell.classList.toggle("is-war-winner", result === "winner");
      cell.classList.toggle("is-war-loser", result === "loser");
      let badge = cell.querySelector(".planetary-war-badge");
      if (active && !badge) {
        badge = document.createElement("span");
        badge.className = "planetary-war-badge";
        cell.append(badge);
      }
      if (active && badge) {
        badge.textContent = result === "winner" ? "↑" : "↓";
        badge.title = `Планетарна война — ${result === "winner" ? "печели" : "губи"}`;
      }
      if (!active && badge) badge.remove();
    });
  });
}

function reconcileDesktopEclipseMarkers(root = document) {
  const validStates = new Set(["window", "near", "day"]);
  root.querySelectorAll("tr[data-eclipse-state]").forEach((row) => {
    const cell = row.querySelector(".desktop-graha-cell");
    if (!cell) return;
    const state = row.dataset.eclipseState || "";
    cell.classList.remove("is-eclipse", "is-eclipse-window", "is-eclipse-near", "is-eclipse-day");
    if (validStates.has(state)) {
      cell.classList.add("is-eclipse", `is-eclipse-${state}`);
    }
  });
}

function chartDegreeValue(value) {
  const text = String(value ?? "").replace(",", ".");
  const parts = text.match(/\d+(?:\.\d+)?/g) || [];
  if (!parts.length) return Number.POSITIVE_INFINITY;
  return (Number(parts[0]) || 0) + ((Number(parts[1]) || 0) / 60) + ((Number(parts[2]) || 0) / 3600);
}

function sortedChartItems(items, itemDegrees, showDegrees) {
  const visible = visibleChartItems(items);
  if (!showDegrees || !itemDegrees) return visible;
  return visible
    .map((item, index) => ({ item, index, degree: chartDegreeValue(itemDegrees[item]) }))
    .sort((left, right) => {
      const leftAsc = left.item === "Ас";
      const rightAsc = right.item === "Ас";
      if (leftAsc !== rightAsc) return leftAsc ? -1 : 1;
      return (left.degree - right.degree) || (left.index - right.index);
    })
    .map(({ item }) => item);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function groupChartItems(items, horizontal = false) {
  const count = items.length;
  if (count === 0) {
    return [];
  }
  if (count === 1) {
    return [items];
  }
  if (horizontal) {
    const groups = [];
    for (let index = 0; index < count; index += 2) {
      groups.push(items.slice(index, index + 2));
    }
    return groups;
  }
  if (count === 2 || count === 3 || count === 4) {
    return items.map((item) => [item]);
  }
  const groups = [];
  for (let index = 0; index < count; index += 2) {
    groups.push(items.slice(index, index + 2));
  }
  return groups;
}

function chartLineYPositions(box, lineCount) {
  const centerY = box.y + box.height / 2;
  let lineGap;
  if (lineCount <= 3) {
    lineGap = 20.0;
  } else if (lineCount === 4) {
    lineGap = 18.0;
  } else {
    lineGap = 16.0;
  }
  const firstY = centerY - (((lineCount - 1) * lineGap) / 2);
  return Array.from({ length: lineCount }, (_, index) => firstY + index * lineGap);
}

function chartLineXPositions(box, itemCount) {
  const centerX = box.x + box.width / 2;
  if (itemCount === 1) {
    return [centerX];
  }

  const spread = Math.min(20.0, box.width * 0.22);
  return [centerX - spread, centerX + spread];
}

const DEGREE_FONT_SIZE = 14.0;
const SAFE_PADDING = 8.0;
const VERTICAL_MARGIN = 0.0;

// Реалните polygon-и на 12-те северни дома (viewBox 0 0 572 531).
const NORTH_POLYGONS = {
  1: [[286.0, 10.0], [424.5, 137.75], [285.573, 267.162], [147.5, 137.75]],
  2: [[9.0, 10.0], [286.0, 10.0], [147.5, 137.75]],
  3: [[9.0, 10.0], [147.5, 137.75], [9.0, 265.5]],
  4: [[9.0, 265.5], [147.5, 137.75], [311.0, 291.0], [311.0, 240.0], [147.5, 393.25]],
  5: [[9.0, 265.5], [147.5, 393.25], [9.0, 521.0]],
  6: [[9.0, 521.0], [147.5, 393.25], [286.0, 521.0]],
  7: [[286.0, 521.0], [147.5, 393.25], [285.573, 263.838], [424.5, 393.25]],
  8: [[286.0, 521.0], [424.5, 393.25], [563.0, 521.0]],
  9: [[563.0, 521.0], [424.5, 393.25], [563.0, 265.5]],
  10: [[563.0, 265.5], [424.5, 137.75], [260.0, 291.0], [260.0, 240.0], [424.5, 393.25]],
  11: [[563.0, 265.5], [563.0, 10.0], [424.5, 137.75]],
  12: [[286.0, 10.0], [424.5, 137.75], [563.0, 10.0]],
};

function polygonXRange(polygon, y) {
  const xs = [];
  const count = polygon.length;
  for (let index = 0; index < count; index++) {
    const [x1, y1] = polygon[index];
    const [x2, y2] = polygon[(index + 1) % count];
    if (y1 === y2) continue;
    if ((y1 <= y && y <= y2) || (y2 <= y && y <= y1)) {
      const t = (y - y1) / (y2 - y1);
      xs.push(x1 + t * (x2 - x1));
    }
  }
  if (xs.length === 0) return null;
  return [Math.min(...xs), Math.max(...xs)];
}

function planetFontSize(lineCount) {
  if (lineCount >= 5) return 17.0;
  if (lineCount === 4) return 19.0;
  return 22.0;
}

function estimateItemWidth(item, degreeText, planetFontSizeValue) {
  let total = 4.0;
  for (const character of String(item)) {
    total += (character === "(" || character === ")") ? 0.34 * planetFontSizeValue : 0.68 * planetFontSizeValue;
  }
  if (degreeText !== null && degreeText !== undefined) {
    total += 3.0;
    total += String(degreeText).length * 0.56 * DEGREE_FONT_SIZE;
  }
  return total;
}

function minHorizontalGap(planetFontSizeValue) {
  return Math.max(14.0, planetFontSizeValue * 0.72);
}

function lineHeightValue(planetFontSizeValue) {
  return planetFontSizeValue * 1.15;
}

function packings(count) {
  if (count <= 0) return [[]];
  const result = [];
  for (const rest of packings(count - 1)) result.push([1].concat(rest));
  if (count >= 2) for (const rest of packings(count - 2)) result.push([2].concat(rest));
  return result;
}

function adaptiveGroups(items, degrees, availableWidth) {
  const count = items.length;
  if (count <= 4) return items.map((item) => [item]);

  let best = null;
  for (const packing of packings(count)) {
    const rows = packing.length;
    const font = planetFontSize(rows);
    const gap = minHorizontalGap(font);
    let ok = true;
    let free = 0;
    let index = 0;
    for (const size of packing) {
      if (size === 2) {
        const w1 = estimateItemWidth(items[index], degrees ? degrees[items[index]] : null, font);
        const w2 = estimateItemWidth(items[index + 1], degrees ? degrees[items[index + 1]] : null, font);
        const required = w1 + gap + w2;
        if (required > availableWidth) { ok = false; break; }
        free += availableWidth - required;
      }
      index += size;
    }
    if (ok) {
      if (best === null || rows < best.rows || (rows === best.rows && free > best.free)) {
        best = { rows, free, packing };
      }
    }
  }
  if (best === null) return items.map((item) => [item]);

  const groups = [];
  let index = 0;
  for (const size of best.packing) {
    groups.push(items.slice(index, index + size));
    index += size;
  }
  return groups;
}

function adaptiveGroupsPolygon(items, degrees, polygon, centerY) {
  const count = items.length;
  if (count <= 4) return items.map((item) => [item]);

  const polygonTop = Math.min(...polygon.map((v) => v[1]));
  const polygonBottom = Math.max(...polygon.map((v) => v[1]));

  let best = null;
  for (const packing of packings(count)) {
    const rows = packing.length;
    const font = planetFontSize(rows);
    const lineH = lineHeightValue(font);
    const blockH = (rows - 1) * lineH + font;
    const firstY = centerY - blockH / 2 + font / 2;

    if (blockH > (polygonBottom - polygonTop) - 2 * VERTICAL_MARGIN) continue;

    const gap = minHorizontalGap(font);
    let ok = true;
    let free = 0;
    let index = 0;
    for (let rowIndex = 0; rowIndex < packing.length; rowIndex++) {
      const size = packing[rowIndex];
      const y = firstY + rowIndex * lineH;
      const xRange = polygonXRange(polygon, y);
      if (xRange === null) { ok = false; break; }
      const [xLeft, xRight] = xRange;
      const rowCenter = (xLeft + xRight) / 2;
      const safeLeft = xLeft + SAFE_PADDING;
      const safeRight = xRight - SAFE_PADDING;
      if (size === 2) {
        const w1 = estimateItemWidth(items[index], degrees ? degrees[items[index]] : null, font);
        const w2 = estimateItemWidth(items[index + 1], degrees ? degrees[items[index + 1]] : null, font);
        const total = w1 + gap + w2;
        const pairLeft = rowCenter - total / 2;
        const pairRight = rowCenter + total / 2;
        if (pairLeft < safeLeft || pairRight > safeRight) { ok = false; break; }
        free += (safeRight - safeLeft) - total;
      } else {
        const w = estimateItemWidth(items[index], degrees ? degrees[items[index]] : null, font);
        if (w > safeRight - safeLeft) { ok = false; break; }
      }
      index += size;
    }
    if (ok) {
      if (best === null || rows < best.rows || (rows === best.rows && free > best.free)) {
        best = { rows, free, packing };
      }
    }
  }
  if (best === null) return items.map((item) => [item]);

  const groups = [];
  let index = 0;
  for (const size of best.packing) {
    groups.push(items.slice(index, index + size));
    index += size;
  }
  return groups;
}

function layoutChartItems(box, polygon, items, degrees) {
  if (items.length === 0) return { positions: [], lineCount: 0, fontSize: 22.0 };

  const centerY = box.y + box.height / 2;
  const boxCenterX = box.x + box.width / 2;

  const groups = polygon !== null && polygon !== undefined
    ? adaptiveGroupsPolygon(items, degrees, polygon, centerY)
    : adaptiveGroups(items, degrees, box.width - 2 * SAFE_PADDING);

  const lineCount = groups.length;
  const font = planetFontSize(lineCount);
  const lineH = lineHeightValue(font);
  const blockH = (lineCount - 1) * lineH + font;
  let firstY = centerY - blockH / 2 + font / 2;

  if (polygon !== null && polygon !== undefined) {
    const polygonTop = Math.min(...polygon.map((v) => v[1]));
    const polygonBottom = Math.max(...polygon.map((v) => v[1]));
    const blockTop = firstY - font / 2;
    const blockBottom = firstY + (lineCount - 1) * lineH + font / 2;
    if (blockTop < polygonTop + VERTICAL_MARGIN) {
      firstY += (polygonTop + VERTICAL_MARGIN) - blockTop;
    } else if (blockBottom > polygonBottom - VERTICAL_MARGIN) {
      firstY -= blockBottom - (polygonBottom - VERTICAL_MARGIN);
    }
  }

  const positions = [];
  groups.forEach((group, rowIndex) => {
    const y = firstY + rowIndex * lineH;
    let rowCenter = boxCenterX;
    if (polygon !== null && polygon !== undefined) {
      const xRange = polygonXRange(polygon, y);
      if (xRange !== null) rowCenter = (xRange[0] + xRange[1]) / 2;
    }
    if (group.length === 1) {
      positions.push([group[0], rowCenter, y]);
    } else {
      const w1 = estimateItemWidth(group[0], degrees ? degrees[group[0]] : null, font);
      const w2 = estimateItemWidth(group[1], degrees ? degrees[group[1]] : null, font);
      const gap = minHorizontalGap(font);
      const total = w1 + gap + w2;
      const startX = rowCenter - total / 2;
      positions.push([group[0], startX + w1 / 2, y]);
      positions.push([group[1], startX + w1 + gap + w2 / 2, y]);
    }
  });

  return { positions, lineCount, fontSize: font };
}

function chartItemPositions(displayHouse, items, degrees) {
  const box = NORTH_CHART_LAYOUTS[displayHouse].box;
  return layoutChartItems(box, NORTH_POLYGONS[displayHouse], items, degrees).positions;
}

function southChartLineYPositions(box, lineCount) {
  const centerY = box.y + box.height / 2;
  let lineGap;
  if (lineCount <= 2) {
    lineGap = 24.0;
  } else if (lineCount <= 4) {
    lineGap = 22.0;
  } else {
    lineGap = 18.0;
  }
  const firstY = centerY - (((lineCount - 1) * lineGap) / 2);
  return Array.from({ length: lineCount }, (_, index) => firstY + index * lineGap);
}

function southChartLineXPositions(box, itemCount) {
  const centerX = box.x + box.width / 2;
  if (itemCount === 1) {
    return [centerX];
  }

  const spread = Math.min(26.0, box.width * 0.18);
  return [centerX - spread, centerX + spread];
}

function southChartItemPositions(signNumber, items, degrees) {
  const box = SOUTH_SIGN_LAYOUTS[signNumber].box;
  return layoutChartItems(box, null, items, degrees).positions;
}

function isArudhaLabel(item) {
  return item === "Ал" || (item.startsWith("А") && /^\d+$/.test(item.slice(1)));
}

function chartTextClass(item, lineCount) {
  const classNames = ["chart-content"];
  if (OUTER_PLANET_CHART_LABELS.has(item)) {
    classNames.push("chart-content--outer");
  } else if (item === "Ас" || isArudhaLabel(item)) {
    classNames.push("chart-content--asc");
  } else if (item.includes("(")) {
    classNames.push("chart-content--retro");
  }
  if (lineCount >= 5) {
    classNames.push("chart-content--tight");
  } else if (lineCount === 4) {
    classNames.push("chart-content--dense");
  }
  return classNames.join(" ");
}

function chartSignClass(signNumber) {
  return String(signNumber).length >= 2 ? "chart-sign-label chart-sign-label--double" : "chart-sign-label";
}

function chartCenterTitleClass(title) {
  void title;
  return "chart-center-title";
}

function chartItemMarkup(item, degree, showDegrees) {
  const label = escapeHtml(item);
  if (!showDegrees || degree == null) {
    return label;
  }
  return `<tspan>${label}</tspan><tspan class="chart-degree" dx="3">${escapeHtml(degree)}</tspan>`;
}

function rotateHouseToDisplayPosition(actualHouse, firstHouse) {
  return ((actualHouse - firstHouse + 12) % 12) + 1;
}

function renderNorthChartSvg(chartPayload, firstHouse, chartKey, showDegrees = false) {
  const title = escapeHtml(chartPayload.title);
  const ariaTitle = escapeHtml(chartPayload.aria_title || chartPayload.title);
  const chartId = `${chartKey}-${firstHouse}`;
  const bgId = `chartBg-${chartId}`;
  const centerId = `centerGlow-${chartId}`;
  const lineMaskId = `lineMask-${chartId}`;

  const signParts = [];
  const itemParts = [];
  const hitParts = [];
  const signFieldParts = [];

  chartPayload.houses.forEach((house) => {
    const displayHouse = rotateHouseToDisplayPosition(house.house, firstHouse);
    const [signX, signY] = NORTH_CHART_LAYOUTS[displayHouse].sign;
    const box = NORTH_CHART_LAYOUTS[displayHouse].box;

    const fieldPoints = NORTH_POLYGONS[displayHouse]
      .map(([x, y]) => `${x.toFixed(2)},${y.toFixed(2)}`)
      .join(" ");
    signFieldParts.push(
      `<polygon class="chart-sign-field" data-sign="${house.sign_number}" points="${fieldPoints}"></polygon>`,
    );

    signParts.push(
      `<text class="${chartSignClass(house.sign_number)}" x="${signX.toFixed(1)}" y="${signY.toFixed(1)}" data-sign="${house.sign_number}" text-anchor="middle" dominant-baseline="middle">${house.sign_number}</text>`,
    );

    const items = sortedChartItems(house.items, chartPayload.item_degrees, showDegrees);
    const layout = layoutChartItems(box, NORTH_POLYGONS[displayHouse], items, chartPayload.item_degrees);
    layout.positions.forEach(([itemText, xPos, yPos]) => {
      const degree = chartPayload.item_degrees?.[itemText];
      const grahaKey = grahaKeyFromLabel(itemText);
      const grahaAttrs = grahaKey ? ` data-graha-key="${grahaKey}" data-graha-sign="${house.sign_number}"` : "";
      itemParts.push(
        `<text class="${chartTextClass(itemText, layout.lineCount)}" x="${xPos.toFixed(1)}" y="${yPos.toFixed(1)}" text-anchor="middle" dominant-baseline="middle"${grahaAttrs}>${chartItemMarkup(itemText, degree, showDegrees)}</text>`,
      );
    });

    hitParts.push(
      `<rect class="chart-house-target" data-house-target="${house.house}" x="${box.x.toFixed(1)}" y="${box.y.toFixed(1)}" width="${box.width.toFixed(1)}" height="${box.height.toFixed(1)}" rx="12"></rect>`,
    );
  });

  return `
<svg class="north-chart-svg" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 572 531" role="img" aria-label="${ariaTitle}">
  <defs>
    <linearGradient id="${bgId}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#fffef9" />
      <stop offset="100%" stop-color="#f4eedb" />
    </linearGradient>
    <linearGradient id="${centerId}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#ddd2a5" />
      <stop offset="100%" stop-color="#c5b175" />
    </linearGradient>
    <mask id="${lineMaskId}">
      <rect width="572" height="531" fill="white" />
      <rect x="248" y="231" width="76" height="70" rx="18" fill="black" />
    </mask>
  </defs>
  <rect width="572" height="531" rx="18" fill="url(#${bgId})" />
  <g mask="url(#${lineMaskId})">
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
  <rect x="255" y="238" width="62" height="56" rx="12" fill="url(#${centerId})" stroke="#4e7b4a" stroke-width="2"/>
  <text x="286" y="275.5" text-anchor="middle" class="${chartCenterTitleClass(chartPayload.title)}">${title}</text>
  ${signFieldParts.join("")}
  ${signParts.join("")}
  ${itemParts.join("")}
  ${hitParts.join("")}
</svg>`.trim();
}

function renderSouthChartSvg(chartPayload, chartKey, showDegrees = false) {
  const title = escapeHtml(chartPayload.title);
  const ariaTitle = escapeHtml(chartPayload.aria_title || chartPayload.title);
  const chartId = `${chartKey}-south`;
  const bgId = `southChartBg-${chartId}`;
  const centerId = `southCenterGlow-${chartId}`;

  const signItems = new Map();
  const directSignItems = chartPayload.sign_items || null;
  if (directSignItems) {
    Object.entries(directSignItems).forEach(([signNumber, items]) => {
      signItems.set(Number(signNumber), sortedChartItems(items, chartPayload.item_degrees, showDegrees));
    });
  } else {
    chartPayload.houses.forEach((house) => {
      signItems.set(Number(house.sign_number), sortedChartItems(house.items, chartPayload.item_degrees, showDegrees));
    });
  }

  const itemParts = [];
  const signFieldParts = [];
  Object.keys(SOUTH_SIGN_LAYOUTS)
    .map((signNumber) => Number(signNumber))
    .sort((left, right) => left - right)
    .forEach((signNumber) => {
      const signBox = SOUTH_SIGN_LAYOUTS[signNumber].box;
      signFieldParts.push(
        `<rect class="chart-sign-field" data-sign="${signNumber}" x="${signBox.x.toFixed(2)}" y="${signBox.y.toFixed(2)}" width="${signBox.width.toFixed(2)}" height="${signBox.height.toFixed(2)}"></rect>`,
      );
      const items = signItems.get(signNumber) || [];
      const layout = layoutChartItems(SOUTH_SIGN_LAYOUTS[signNumber].box, null, items, chartPayload.item_degrees);
      layout.positions.forEach(([itemText, xPos, yPos]) => {
        const degree = chartPayload.item_degrees?.[itemText];
        const grahaKey = grahaKeyFromLabel(itemText);
        const grahaAttrs = grahaKey ? ` data-graha-key="${grahaKey}" data-graha-sign="${signNumber}"` : "";
        itemParts.push(
          `<text class="${chartTextClass(itemText, layout.lineCount)}" x="${xPos.toFixed(1)}" y="${yPos.toFixed(1)}" text-anchor="middle" dominant-baseline="middle"${grahaAttrs}>${chartItemMarkup(itemText, degree, showDegrees)}</text>`,
        );
      });
    });

  return `
<svg class="south-chart-svg" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 572 572" role="img" aria-label="${ariaTitle}">
  <defs>
    <linearGradient id="${bgId}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#fffef9" />
      <stop offset="100%" stop-color="#f4eedb" />
    </linearGradient>
    <linearGradient id="${centerId}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#ddd2a5" />
      <stop offset="100%" stop-color="#c5b175" />
    </linearGradient>
  </defs>
  <rect width="572" height="572" fill="url(#${bgId})" />
  <rect x="14.9" y="14.9" width="542.2" height="542.2" fill="none" stroke="#4e7b4a" stroke-width="2.4" />
  <line x1="150.5" y1="14.9" x2="150.5" y2="557.1" stroke="#4e7b4a" stroke-width="2.4" />
  <line x1="421.5" y1="14.9" x2="421.5" y2="557.1" stroke="#4e7b4a" stroke-width="2.4" />
  <line x1="286.0" y1="14.9" x2="286.0" y2="150.5" stroke="#4e7b4a" stroke-width="2.4" />
  <line x1="286.0" y1="421.5" x2="286.0" y2="557.1" stroke="#4e7b4a" stroke-width="2.4" />
  <line x1="14.9" y1="150.5" x2="557.1" y2="150.5" stroke="#4e7b4a" stroke-width="2.4" />
  <line x1="14.9" y1="421.5" x2="557.1" y2="421.5" stroke="#4e7b4a" stroke-width="2.4" />
  <line x1="14.9" y1="286.0" x2="150.5" y2="286.0" stroke="#4e7b4a" stroke-width="2.4" />
  <line x1="421.5" y1="286.0" x2="557.1" y2="286.0" stroke="#4e7b4a" stroke-width="2.4" />
  <rect x="247.0" y="250.0" width="78.0" height="72.0" rx="14" fill="url(#${centerId})" stroke="#4e7b4a" stroke-width="2.4" />
  <text x="286" y="294" text-anchor="middle" class="${chartCenterTitleClass(chartPayload.title)}">${title}</text>
  ${signFieldParts.join("")}
  ${itemParts.join("")}
</svg>`.trim();
}

let chartDrishtiMarkerSeq = 0;

function ensureChartDrishtiLayer(frame) {
  let layer = frame.querySelector(".chart-drishti-layer");
  if (layer) return layer;
  const chartSvg = frame.querySelector(".north-chart-svg, .south-chart-svg");
  const viewBox = chartSvg?.getAttribute("viewBox") || "0 0 572 531";
  layer = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  layer.setAttribute("class", "chart-drishti-layer");
  layer.setAttribute("viewBox", viewBox);
  layer.setAttribute("aria-hidden", "true");
  frame.appendChild(layer);
  return layer;
}

function chartSignCenter(frame, signNumber) {
  const signText = frame.querySelector(`.north-chart-svg .chart-sign-label[data-sign="${signNumber}"]`);
  if (signText) {
    return {
      x: Number(signText.getAttribute("x")),
      y: Number(signText.getAttribute("y")),
    };
  }
  const layout = SOUTH_SIGN_LAYOUTS[signNumber];
  if (layout) {
    return {
      x: layout.box.x + layout.box.width / 2,
      y: layout.box.y + layout.box.height / 2,
    };
  }
  return null;
}

function clearChartDrishti(layer) {
  if (!layer) return;
  layer.replaceChildren();
  delete layer.dataset.activeGraha;
}

function drawChartDrishti(layer, source, targets) {
  const ns = "http://www.w3.org/2000/svg";
  layer.replaceChildren();
  chartDrishtiMarkerSeq += 1;
  const markerId = `chartDrishtiArrow-${chartDrishtiMarkerSeq}`;

  const defs = document.createElementNS(ns, "defs");
  const marker = document.createElementNS(ns, "marker");
  marker.setAttribute("id", markerId);
  marker.setAttribute("viewBox", "0 0 10 10");
  marker.setAttribute("refX", "7.5");
  marker.setAttribute("refY", "5");
  marker.setAttribute("markerWidth", "4.5");
  marker.setAttribute("markerHeight", "4.5");
  marker.setAttribute("orient", "auto-start-reverse");
  const arrowPath = document.createElementNS(ns, "path");
  arrowPath.setAttribute("d", "M 0 0 L 10 5 L 0 10 z");
  arrowPath.setAttribute("fill", "rgba(190, 62, 72, 0.62)");
  marker.appendChild(arrowPath);
  defs.appendChild(marker);
  layer.appendChild(defs);

  targets.forEach((target, index) => {
    const dx = target.x - source.x;
    const dy = target.y - source.y;
    const bend = (index - (targets.length - 1) / 2) * 9;
    const cx = source.x + dx / 2 - dy * 0.08 + bend;
    const cy = source.y + dy / 2 + dx * 0.08 + bend;
    const path = document.createElementNS(ns, "path");
    path.setAttribute("class", "chart-drishti-line");
    path.setAttribute(
      "d",
      `M ${source.x.toFixed(1)} ${source.y.toFixed(1)} Q ${cx.toFixed(1)} ${cy.toFixed(1)} ${target.x.toFixed(1)} ${target.y.toFixed(1)}`,
    );
    path.setAttribute("marker-end", `url(#${markerId})`);
    layer.appendChild(path);
  });

  const dot = document.createElementNS(ns, "circle");
  dot.setAttribute("class", "chart-drishti-point");
  dot.setAttribute("cx", source.x.toFixed(1));
  dot.setAttribute("cy", source.y.toFixed(1));
  dot.setAttribute("r", "3");
  layer.appendChild(dot);
}

function toggleChartDrishti(frame, key, sourceSign) {
  const layer = ensureChartDrishtiLayer(frame);
  if (layer.dataset.activeGraha === key) {
    clearChartDrishti(layer);
    return;
  }
  clearChartDrishti(layer);
  const offsets = GRAHA_DRISHTI_OFFSETS[key];
  if (!offsets || !offsets.length) return;
  const source = chartSignCenter(frame, sourceSign);
  if (!source) return;
  const targets = offsets
    .map((offset) => ((sourceSign - 1 + offset) % 12) + 1)
    .map((sign) => chartSignCenter(frame, sign))
    .filter(Boolean);
  if (!targets.length) return;
  drawChartDrishti(layer, source, targets);
  layer.dataset.activeGraha = key;
}

function clearChartRashiDrishti(frame) {
  frame.querySelectorAll(".chart-sign-field.is-rashi-source, .chart-sign-field.is-rashi-target").forEach((field) => {
    field.classList.remove("is-rashi-source", "is-rashi-target");
  });
}

function toggleChartRashiDrishti(frame, sourceSign) {
  const sourceField = frame.querySelector(`.chart-sign-field[data-sign="${sourceSign}"]`);
  if (!sourceField) return;
  if (sourceField.classList.contains("is-rashi-source")) {
    clearChartRashiDrishti(frame);
    return;
  }
  clearChartRashiDrishti(frame);
  const targets = rashiDrishtiTargets(sourceSign);
  sourceField.classList.add("is-rashi-source");
  targets.forEach((targetSign) => {
    frame.querySelector(`.chart-sign-field[data-sign="${targetSign}"]`)?.classList.add("is-rashi-target");
  });
}

function bindChartDrishti() {
  document.addEventListener("mousedown", (event) => {
    if (event.target.closest?.(".north-chart-svg text, .south-chart-svg text")) {
      event.preventDefault();
    }
  });

  let lastDrishtiClick = { element: null, time: 0 };

  document.addEventListener("click", (event) => {
    const grahaText = event.target.closest?.("[data-graha-key]");
    const signEl = grahaText ? null : event.target.closest?.("[data-sign]");
    const hitElement = grahaText || signEl;
    if (!hitElement) {
      lastDrishtiClick = { element: null, time: 0 };
      return;
    }
    const now = Date.now();
    if (lastDrishtiClick.element === hitElement && now - lastDrishtiClick.time < 350) {
      lastDrishtiClick = { element: null, time: 0 };
      if (grahaText) {
        const frame = grahaText.closest(".chart-frame");
        const key = grahaText.getAttribute("data-graha-key");
        const sign = Number(grahaText.getAttribute("data-graha-sign"));
        if (frame && key && sign) toggleChartDrishti(frame, key, sign);
      } else if (signEl) {
        const frame = signEl.closest(".chart-frame");
        const sign = Number(signEl.getAttribute("data-sign"));
        if (frame && sign) toggleChartRashiDrishti(frame, sign);
      }
    } else {
      lastDrishtiClick = { element: hitElement, time: now };
    }
  });
}

function bindCitySync(config) {
  const cityInput = document.getElementById(config.citySelectId);
  if (!cityInput) {
    return () => {};
  }

  const sync = () => {
    const selected = window.CITY_DATA.find((city) => city.name === cityInput.value.trim());
    if (!selected) {
      return;
    }

    const lat = decimalToDms(selected.lat);
    const lon = decimalToDms(selected.lon);

    document.getElementById(config.latitudeDegreesId).value = lat.degrees;
    document.getElementById(config.latitudeMinutesId).value = lat.minutes;
    document.getElementById(config.latitudeSecondsId).value = lat.seconds;
    document.getElementById(config.latitudeHemisphereId).value = selected.lat >= 0 ? "N" : "S";
    document.getElementById(config.longitudeDegreesId).value = lon.degrees;
    document.getElementById(config.longitudeMinutesId).value = lon.minutes;
    document.getElementById(config.longitudeSecondsId).value = lon.seconds;
    document.getElementById(config.longitudeHemisphereId).value = selected.lon >= 0 ? "E" : "W";
  };

  cityInput.addEventListener("change", sync);
  cityInput.addEventListener("blur", sync);
  return sync;
}

function bindTimezoneMode(selectId, containerId) {
  const modeSelect = document.getElementById(selectId);
  const manualFields = document.getElementById(containerId);
  if (!modeSelect || !manualFields) {
    return;
  }

  const sync = () => {
    manualFields.classList.toggle("is-hidden", modeSelect.value !== "manual");
  };

  modeSelect.addEventListener("change", sync);
  sync();
}

function ensureChartZoomButton(frame) {
  if (!frame || frame.querySelector(".chart-zoom-button")) return;
  const button = document.createElement("button");
  button.type = "button";
  button.className = "chart-zoom-button";
  button.textContent = "Увеличи";
  button.setAttribute("aria-label", "Увеличи картата");
  frame.appendChild(button);
}

function bindChartLightbox() {
  const lightbox = document.getElementById("chartLightbox");
  const content = document.getElementById("chartLightboxContent");
  const title = document.getElementById("chartLightboxTitle");
  const closeButton = document.getElementById("chartLightboxClose");
  const zoomableFrames = document.querySelectorAll(".chart-frame--zoomable");

  if (!lightbox || !content || !title || !closeButton || !zoomableFrames.length) {
    return;
  }

  let lastActiveFrame = null;

  const close = () => {
    lightbox.classList.remove("is-open");
    lightbox.setAttribute("aria-hidden", "true");
    document.body.classList.remove("lightbox-open");
    content.innerHTML = "";
    try { sessionStorage.removeItem("rohini.transitZoomSlot"); } catch (_error) { /* current page only */ }

    if (lastActiveFrame) {
      lastActiveFrame.focus();
      lastActiveFrame = null;
    }
  };

  const open = (frame) => {
    const chartSvg = frame.querySelector(".north-chart-svg, .south-chart-svg, .transit-overlay-svg");
    if (!chartSvg) {
      return;
    }

    lastActiveFrame = frame;
    title.textContent = frame.dataset.chartTitle || "Увеличена карта";
    content.innerHTML = chartSvg.outerHTML;
    lightbox.classList.add("is-open");
    lightbox.setAttribute("aria-hidden", "false");
    document.body.classList.add("lightbox-open");
    const transitCard = frame.closest(".desktop-transit-workspace .desktop-chart[data-chart-slot]");
    try {
      if (transitCard) sessionStorage.setItem("rohini.transitZoomSlot", transitCard.dataset.chartSlot || "");
      else sessionStorage.removeItem("rohini.transitZoomSlot");
    } catch (_error) { /* current page only */ }
    closeButton.focus();
  };

  zoomableFrames.forEach((frame) => {
    ensureChartZoomButton(frame);
    frame.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        open(frame);
      }
    });
  });

  document.addEventListener("click", (event) => {
    const button = event.target.closest?.(".chart-zoom-button");
    if (!button) return;
    const frame = button.closest(".chart-frame--zoomable");
    if (!frame || frame.classList.contains("is-selecting-house")) return;
    open(frame);
  });

  lightbox.addEventListener("click", (event) => {
    if (event.target === lightbox || event.target.hasAttribute("data-close-lightbox")) {
      close();
    }
  });

  closeButton.addEventListener("click", close);

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && lightbox.classList.contains("is-open")) {
      close();
    }
  });
}

function bindChartRotation() {
  const chartCards = document.querySelectorAll(".chart-card");
  if (!chartCards.length) {
    return;
  }

  const groupStyles = {};
  const outerPlanetsToggle = document.getElementById("showOuterPlanets");
  const boardAccessLinks = [...document.querySelectorAll(".board-access__button")];
  showOuterPlanetsInCharts = !!outerPlanetsToggle?.checked;
  const syncBoardOuterPlanets = () => {
    boardAccessLinks.forEach((boardAccessLink) => {
      const boardUrl = new URL(boardAccessLink.getAttribute("href"), window.location.href);
      boardUrl.searchParams.set("outer", showOuterPlanetsInCharts ? "1" : "0");
      boardAccessLink.href = `${boardUrl.pathname}${boardUrl.search}`;
    });
  };
  const syncTransitOverlayOuterPlanets = () => {
    document.querySelectorAll(".transit-overlay-frame").forEach((frame) => {
      frame.classList.toggle("show-outer-planets", showOuterPlanetsInCharts);
      frame.querySelector(".transit-overlay-svg")?.classList.toggle("show-outer-planets", showOuterPlanetsInCharts);
    });
  };
  document.addEventListener("outer-planets-visibility-change", syncTransitOverlayOuterPlanets);
  syncBoardOuterPlanets();
  syncTransitOverlayOuterPlanets();
  const switchers = document.querySelectorAll(".chart-style-switch");
  switchers.forEach((switcher) => {
    groupStyles[switcher.dataset.chartStyleGroup] = switcher.dataset.defaultStyle || "north";
  });

  const controllers = [];

  chartCards.forEach((card, index) => {
    const frame = card.querySelector(".chart-frame--rotatable");
    const payloadNode = card.querySelector(".chart-payload");
    const toggleButton = card.querySelector(".chart-rotate-toggle");
    const resetButton = card.querySelector(".chart-rotate-reset");
    const tools = card.querySelector(".chart-tools");
    const styleGroup = card.dataset.chartStyleGroup || `chart-group-${index + 1}`;

    if (!frame || !payloadNode || !toggleButton || !resetButton) {
      return;
    }

    let chartPayload;
    try {
      chartPayload = JSON.parse(payloadNode.textContent);
    } catch (_error) {
      return;
    }

    const chartKey = `chart-${index + 1}`;
    const showDegrees = frame.dataset.showDegrees === "true";
    let currentFirstHouse = 1;
    let selectingHouse = false;

    const updateControls = () => {
      const currentStyle = groupStyles[styleGroup] || "north";
      const isNorthStyle = currentStyle === "north";

      card.dataset.currentStyle = currentStyle;
      if (tools) {
        tools.classList.toggle("is-hidden", !isNorthStyle);
      }

      if (!isNorthStyle) {
        selectingHouse = false;
        toggleButton.classList.remove("is-active");
        resetButton.classList.add("is-hidden");
        frame.classList.remove("is-selecting-house");
        return;
      }

      toggleButton.textContent = selectingHouse ? "Избери дом..." : "Гледай от друг дом";
      toggleButton.classList.toggle("is-active", selectingHouse);
      resetButton.classList.toggle("is-hidden", currentFirstHouse === 1);
      frame.classList.toggle("is-selecting-house", selectingHouse);
    };

    const render = () => {
      const currentStyle = groupStyles[styleGroup] || "north";
      if (currentStyle === "south") {
        selectingHouse = false;
        frame.innerHTML = renderSouthChartSvg(chartPayload, chartKey, showDegrees);
      } else {
        frame.innerHTML = renderNorthChartSvg(chartPayload, currentFirstHouse, chartKey, showDegrees);
      }
      frame.dataset.currentFirstHouse = String(currentFirstHouse);
      ensureChartZoomButton(frame);
      updateControls();
    };

    toggleButton.addEventListener("click", () => {
      selectingHouse = !selectingHouse;
      updateControls();
    });

    resetButton.addEventListener("click", () => {
      currentFirstHouse = 1;
      selectingHouse = false;
      render();
    });

    frame.addEventListener("click", (event) => {
      if ((groupStyles[styleGroup] || "north") !== "north" || !selectingHouse) {
        return;
      }

      const target = event.target.closest("[data-house-target]");
      event.preventDefault();
      event.stopImmediatePropagation();
      event.stopPropagation();

      if (!target) {
        return;
      }

      currentFirstHouse = Number(target.getAttribute("data-house-target")) || 1;
      selectingHouse = false;
      render();
    }, true);

    const controller = {
      group: styleGroup,
      render,
      setPayload(newPayload) {
        chartPayload = newPayload;
        currentFirstHouse = 1;
        selectingHouse = false;
        render();
      },
    };

    card.__chartController = controller;
    controllers.push(controller);
  });

  switchers.forEach((switcher) => {
    const groupName = switcher.dataset.chartStyleGroup;
    const buttons = switcher.querySelectorAll(".chart-style-button");

    const syncButtons = () => {
      const currentStyle = groupStyles[groupName] || "north";
      buttons.forEach((button) => {
        const isActive = button.dataset.chartStyle === currentStyle;
        button.classList.toggle("is-active", isActive);
        button.setAttribute("aria-pressed", isActive ? "true" : "false");
      });
    };

    buttons.forEach((button) => {
      button.addEventListener("click", () => {
        groupStyles[groupName] = button.dataset.chartStyle || "north";
        syncButtons();
        controllers
          .filter((controller) => controller.group === groupName)
          .forEach((controller) => controller.render());
      });
    });

    syncButtons();
  });

  controllers.forEach((controller) => controller.render());

  outerPlanetsToggle?.addEventListener("change", () => {
    showOuterPlanetsInCharts = outerPlanetsToggle.checked;
    controllers.forEach((controller) => controller.render());
    syncBoardOuterPlanets();
    syncTransitOverlayOuterPlanets();
    document.dispatchEvent(new CustomEvent("outer-planets-visibility-change"));
  });
  document.addEventListener("rohini:open-chart", (event) => {
    const frame = event.target.closest?.(".chart-frame--zoomable");
    if (frame) open(frame);
  });
}

function bindDivisionalChartSelector() {
  const selectors = document.querySelectorAll(".divisional-chart-selector");
  if (!selectors.length) {
    return;
  }

  selectors.forEach((selector) => {
    const card = selector.closest(".chart-card");
    const registryNode = card?.querySelector(".divisional-chart-registry");
    const payloadNode = card?.querySelector(".chart-payload");
    const frame = card?.querySelector(".chart-frame");
    const note = card?.querySelector(".divisional-card-note");
    const controller = card?.__chartController;

    if (!card || !registryNode || !payloadNode || !frame || !controller) {
      return;
    }

    let divisionalRegistry;
    try {
      divisionalRegistry = JSON.parse(registryNode.textContent);
    } catch (_error) {
      return;
    }

    const selectedStorageKey = "rohini.selectedDivisionalChart";
    let storedSelection = "";
    try {
      storedSelection = sessionStorage.getItem(selectedStorageKey) || "";
    } catch (_error) {
      storedSelection = "";
    }
    let selectedDivisionalChart = divisionalRegistry[storedSelection]
      ? storedSelection
      : (selector.value || "D9");

    const renderAmshaTable = (selected) => {
      const title = document.getElementById("amshaTableChartTitle");
      const size = document.getElementById("amshaSizeLabel");
      const body = document.getElementById("amshaTableRows");
      if (!title || !size || !body) return;

      title.textContent = selected.amsha_title || selected.card_title || selected.selector_label || selected.code;
      size.textContent = selected.amsha_size_label || "—";
      const visibleRows = (selected.amsha_rows || []).filter((row) => (
        showOuterPlanetsInCharts || !["Uranus", "Neptune", "Pluto"].includes(row.key)
      ));
      body.innerHTML = visibleRows.map((row) => `
        <tr class="${row.label === "Ас" ? "planet-row planet-row--asc" : "planet-row"}">
          <td>${escapeHtml(row.name)} (${escapeHtml(row.label)})</td>
          <td>${escapeHtml(row.degree_dms)}</td>
          <td>${escapeHtml(row.amsha_number)}</td>
          <td>${escapeHtml(row.amsha_sign_name)} (${escapeHtml(row.amsha_sign_number)})</td>
          <td><span class="amsha-percentage">${escapeHtml(row.percentage)}%</span></td>
        </tr>
      `).join("");
    };

    const applySelection = () => {
      const selected = divisionalRegistry[selectedDivisionalChart] || divisionalRegistry.D9;
      if (!selected) {
        return;
      }

      selector.value = selected.code || "D9";
      payloadNode.textContent = JSON.stringify(selected.payload);
      frame.dataset.chartTitle = selected.card_title;
      frame.setAttribute("aria-label", `Увеличи ${selected.card_title}`);
      if (note) {
        note.hidden = !!selected.implemented;
        note.textContent = selected.note || "";
      }
      controller.setPayload(selected.payload);
      renderAmshaTable(selected);
    };

    selector.__refreshDivisionalRegistry = () => {
      try {
        divisionalRegistry = JSON.parse(registryNode.textContent);
      } catch (_error) {
        return;
      }
      selectedDivisionalChart = divisionalRegistry[selectedDivisionalChart]
        ? selectedDivisionalChart
        : (selector.value || "D9");
      applySelection();
    };

    selector.addEventListener("change", () => {
      selectedDivisionalChart = selector.value || "D9";
      try {
        sessionStorage.setItem(selectedStorageKey, selectedDivisionalChart);
      } catch (_error) {
        // The chart still works when storage is unavailable.
      }
      applySelection();
    });

    document.addEventListener("outer-planets-visibility-change", () => {
      const selected = divisionalRegistry[selectedDivisionalChart] || divisionalRegistry.D9;
      if (selected) renderAmshaTable(selected);
    });

    applySelection();
  });

  const details = document.getElementById("amshaTableDetails");
  const toggleLabel = details?.querySelector(".amsha-toggle-label");
  details?.addEventListener("toggle", () => {
    if (toggleLabel) toggleLabel.textContent = details.open ? "Скрий таблицата" : "Покажи таблицата";
  });
}

function bindTableScrollAssist() {
  const scrollAreas = document.querySelectorAll(".table-scroll");
  if (!scrollAreas.length) {
    return;
  }

  scrollAreas.forEach((scrollArea, index) => {
    const table = scrollArea.querySelector("table");
    if (!table || scrollArea.previousElementSibling?.classList.contains("table-scroll-assist")) {
      return;
    }

    const assist = document.createElement("div");
    assist.className = "table-scroll-assist";
    assist.hidden = true;
    assist.innerHTML = `
      <div class="table-scroll-assist__label">Плъзни таблицата наляво и надясно</div>
      <div class="table-scroll-assist__track" aria-hidden="true">
        <div class="table-scroll-assist__thumb"></div>
      </div>
    `.trim();

    scrollArea.parentNode.insertBefore(assist, scrollArea);

    const track = assist.querySelector(".table-scroll-assist__track");
    const thumb = assist.querySelector(".table-scroll-assist__thumb");
    const assistKey = `table-scroll-assist-${index + 1}`;
    let dragging = false;
    let startX = 0;
    let startScrollLeft = 0;
    let activePointerId = null;

    const update = () => {
      const maxScroll = scrollArea.scrollWidth - scrollArea.clientWidth;
      const isScrollable = maxScroll > 6;
      assist.hidden = !isScrollable;

      if (!isScrollable) {
        return;
      }

      const trackWidth = track.clientWidth;
      const thumbWidth = Math.max(trackWidth * (scrollArea.clientWidth / scrollArea.scrollWidth), 54);
      const maxThumbOffset = Math.max(trackWidth - thumbWidth, 0);
      const thumbOffset = maxScroll > 0 ? (scrollArea.scrollLeft / maxScroll) * maxThumbOffset : 0;

      assist.dataset.assistKey = assistKey;
      thumb.style.width = `${thumbWidth}px`;
      thumb.style.transform = `translateX(${thumbOffset}px)`;
    };

    const beginDrag = (event) => {
      dragging = true;
      activePointerId = event.pointerId;
      startX = event.clientX;
      startScrollLeft = scrollArea.scrollLeft;
      track.classList.add("is-dragging");
      if (track.setPointerCapture) {
        track.setPointerCapture(activePointerId);
      }
      event.preventDefault();
    };

    const endDrag = () => {
      dragging = false;
      track.classList.remove("is-dragging");
      if (activePointerId !== null && track.releasePointerCapture) {
        track.releasePointerCapture(activePointerId);
      }
      activePointerId = null;
    };

    track.addEventListener("pointerdown", (event) => {
      const rect = track.getBoundingClientRect();
      const thumbRect = thumb.getBoundingClientRect();
      const clickedThumb = event.clientX >= thumbRect.left && event.clientX <= thumbRect.right;

      if (!clickedThumb) {
        const trackWidth = rect.width;
        const thumbWidth = thumb.offsetWidth;
        const maxThumbOffset = Math.max(trackWidth - thumbWidth, 1);
        const targetOffset = Math.min(Math.max((event.clientX - rect.left) - (thumbWidth / 2), 0), maxThumbOffset);
        const maxScroll = Math.max(scrollArea.scrollWidth - scrollArea.clientWidth, 0);
        scrollArea.scrollLeft = (targetOffset / maxThumbOffset) * maxScroll;
        update();
      }

      beginDrag(event);
    });

    track.addEventListener("pointermove", (event) => {
      if (!dragging) {
        return;
      }

      const maxScroll = scrollArea.scrollWidth - scrollArea.clientWidth;
      const maxThumbOffset = Math.max(track.clientWidth - thumb.offsetWidth, 1);
      const deltaX = event.clientX - startX;
      const scrollDelta = (deltaX / maxThumbOffset) * maxScroll;

      scrollArea.scrollLeft = startScrollLeft + scrollDelta;
      update();
    });

    track.addEventListener("pointerup", endDrag);
    track.addEventListener("pointercancel", endDrag);
    track.addEventListener("lostpointercapture", endDrag);
    scrollArea.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);

    if ("ResizeObserver" in window) {
      const observer = new ResizeObserver(update);
      observer.observe(scrollArea);
      observer.observe(table);
    }

    update();
  });
}

function bindSegmentedDateTimeControls() {
  const controls = document.querySelectorAll("[data-segmented-date], [data-segmented-time]");

  controls.forEach((control) => {
    const target = document.getElementById(control.dataset.target);
    const inputs = Array.from(control.querySelectorAll("input[data-part]"));
    const isDate = control.hasAttribute("data-segmented-date");

    if (!target || inputs.length === 0) {
      return;
    }

    if (!isDate) {
      const preciseTime = target.value.match(/^\d{2}:\d{2}:\d{2}(\.\d+)$/);
      target.dataset.subsecond = preciseTime?.[1] || "";
    }

    const validateInput = (input) => {
      const value = input.value.trim();
      const ranges = {
        day: [1, 31, "Денят трябва да бъде между 1 и 31."],
        month: [1, 12, "Месецът трябва да бъде между 1 и 12."],
        hour: [0, 23, "Часът трябва да бъде между 0 и 23."],
        minute: [0, 59, "Минутите трябва да бъдат между 0 и 59."],
        second: [0, 59, "Секундите трябва да бъдат между 0 и 59."],
      };

      input.setCustomValidity("");
      if (!value || !ranges[input.dataset.part]) {
        return;
      }

      const [minimum, maximum, message] = ranges[input.dataset.part];
      const numericValue = Number(value);
      if (numericValue < minimum || numericValue > maximum) {
        input.setCustomValidity(message);
      }
    };

    const syncTarget = () => {
      const values = Object.fromEntries(inputs.map((input) => [input.dataset.part, input.value.trim()]));
      const allFilled = inputs.every((input) => input.value.trim() !== "");

      if (!allFilled) {
        target.value = "";
        return;
      }

      if (isDate) {
        const year = values.year.padStart(4, "0");
        target.value = `${year}-${values.month.padStart(2, "0")}-${values.day.padStart(2, "0")}`;
      } else {
        target.value = `${values.hour.padStart(2, "0")}:${values.minute.padStart(2, "0")}:${values.second.padStart(2, "0")}${target.dataset.subsecond || ""}`;
      }
    };

    inputs.forEach((input, index) => {
      input.addEventListener("input", () => {
        input.value = input.value.replace(/\D/g, "");
        if (!isDate) target.dataset.subsecond = "";
        validateInput(input);
        syncTarget();

        if (input.maxLength > 0 && input.value.length >= input.maxLength && inputs[index + 1]) {
          inputs[index + 1].focus();
          inputs[index + 1].select();
        }
      });

      input.addEventListener("blur", () => {
        if (input.value && input.dataset.part !== "year") {
          input.value = input.value.padStart(2, "0");
        }
        validateInput(input);
        syncTarget();
      });
    });

    syncTarget();
  });

  document.getElementById("birthForm")?.addEventListener("submit", () => {
    controls.forEach((control) => {
      control.querySelector("input[data-part]")?.dispatchEvent(new Event("blur"));
    });
  });
}

function bindDesktopWorkingPosition() {
  const form = document.getElementById("birthForm");
  const storageKey = "rohini.desktopWorkingPosition.v1";

  if ("scrollRestoration" in history) {
    history.scrollRestoration = "manual";
  }

  form?.addEventListener("submit", (event) => {
    try {
      sessionStorage.setItem(storageKey, JSON.stringify({
        path: window.location.pathname,
        jumpToTransit: event.submitter?.name === "buildMode" && event.submitter?.value === "transit",
        x: Math.round(window.scrollX),
        y: Math.round(window.scrollY),
        leftPane: Math.round(document.querySelector(".birth-form")?.scrollTop || 0),
        rightPane: Math.round(document.querySelector(".results-panel")?.scrollTop || 0),
      }));
    } catch (_error) {
      // The calculation still works if the browser refuses session storage.
    }
  });

  let savedPosition = null;
  try {
    savedPosition = JSON.parse(sessionStorage.getItem(storageKey) || "null");
  } catch (_error) {
    savedPosition = null;
  }

  if (!savedPosition || savedPosition.path !== window.location.pathname) return;
  try {
    sessionStorage.removeItem(storageKey);
  } catch (_error) {
    // Nothing else is required.
  }

  if (savedPosition.jumpToTransit) {
    const scrollToTransit = () => {
      const target = document.getElementById("transitResult");
      if (!target) return;
      const top = window.scrollY + target.getBoundingClientRect().top - 18;
      window.scrollTo({ left: 0, top, behavior: "auto" });
    };
    scrollToTransit();
    requestAnimationFrame(() => requestAnimationFrame(scrollToTransit));
    window.setTimeout(scrollToTransit, 120);
    document.fonts?.ready.then(scrollToTransit).catch(() => {});
    return;
  }

  const restore = () => window.scrollTo({
    left: Number(savedPosition.x) || 0,
    top: Number(savedPosition.y) || 0,
    behavior: "auto",
  });
  const restorePanes = () => {
    const leftPane = document.querySelector(".birth-form");
    const rightPane = document.querySelector(".results-panel");
    if (leftPane) leftPane.scrollTop = Number(savedPosition.leftPane) || 0;
    if (rightPane) rightPane.scrollTop = Number(savedPosition.rightPane) || 0;
  };
  restore();
  restorePanes();
  requestAnimationFrame(() => requestAnimationFrame(() => { restore(); restorePanes(); }));
  window.setTimeout(() => { restore(); restorePanes(); }, 120);
  document.fonts?.ready.then(() => { restore(); restorePanes(); }).catch(() => {});
}

function bindCollapsibleSettings() {
  const form = document.getElementById("birthForm");
  const sections = [...document.querySelectorAll(".compact-settings[id]")];
  const transitCard = document.getElementById("transitCard");
  try {
    sessionStorage.removeItem("rohini.collapsibleSettings.v1");
  } catch (_error) {
    // The sections do not depend on browser storage.
  }

  sections.forEach((section) => {
    section.open = false;
  });

  // The transit inputs are a permanent working column on the Data sheet.
  // They must never collapse after rebuilding only the natal chart.
  if (transitCard) transitCard.open = true;

  form?.addEventListener("invalid", (event) => {
    let parent = event.target.closest("details");
    while (parent) {
      parent.open = true;
      parent = parent.parentElement?.closest("details");
    }
  }, true);
}

function exportItemPositions(box, items) {
  const groups = groupChartItems(items);
  const lineCount = groups.length;
  const gap = lineCount <= 3 ? 34 : lineCount === 4 ? 26 : 20;
  const centerY = box.y + box.height / 2;
  const firstY = centerY - ((lineCount - 1) * gap) / 2;
  const positions = [];
  groups.forEach((group, groupIndex) => {
    const centerX = box.x + box.width / 2;
    const xs = group.length === 1 ? [centerX] : [centerX - 23, centerX + 23];
    group.forEach((item, itemIndex) => positions.push([item, xs[itemIndex], firstY + groupIndex * gap]));
  });
  return positions;
}

function drawExportNorthChart(context, payload, x, y, size) {
  const scaleX = size / 572;
  const scaleY = size / 531;
  context.save();
  context.translate(x, y);
  context.strokeStyle = "#161616";
  context.fillStyle = "#111";
  context.lineWidth = Math.max(2, size / 320);
  context.strokeRect(0, 0, size, size);
  context.beginPath();
  context.moveTo(0, 0); context.lineTo(size / 2, size / 2); context.lineTo(size, 0);
  context.moveTo(0, size); context.lineTo(size / 2, size / 2); context.lineTo(size, size);
  context.moveTo(size / 2, 0); context.lineTo(size, size / 2); context.lineTo(size / 2, size); context.lineTo(0, size / 2); context.closePath();
  context.stroke();

  (payload.houses || []).forEach((house) => {
    const layout = NORTH_CHART_LAYOUTS[Number(house.house)];
    if (!layout) return;
    context.textAlign = "center";
    context.textBaseline = "middle";
    context.font = `700 ${Math.round(size * 0.031)}px Arial`;
    context.fillStyle = "#555";
    context.fillText(String(house.sign_number), layout.sign[0] * scaleX, layout.sign[1] * scaleY);

    const items = visibleChartItems(house.items || []);
    const positions = exportItemPositions(layout.box, items);
    context.font = `700 ${Math.round(size * (items.length >= 5 ? 0.046 : 0.056))}px Arial`;
    context.fillStyle = "#111";
    positions.forEach(([item, itemX, itemY]) => context.fillText(String(item), itemX * scaleX, itemY * scaleY));
  });
  context.restore();
}

function drawExportSouthChart(context, payload, x, y, size) {
  context.save();
  context.translate(x, y);
  context.strokeStyle = "#161616";
  context.fillStyle = "#111";
  context.lineWidth = Math.max(2, size / 320);
  context.strokeRect(0, 0, size, size);
  context.beginPath();
  [0.25, 0.75].forEach((ratio) => {
    context.moveTo(size * ratio, 0); context.lineTo(size * ratio, size);
    context.moveTo(0, size * ratio); context.lineTo(size, size * ratio);
  });
  context.moveTo(size * 0.5, 0); context.lineTo(size * 0.5, size * 0.25);
  context.moveTo(size * 0.5, size * 0.75); context.lineTo(size * 0.5, size);
  context.moveTo(0, size * 0.5); context.lineTo(size * 0.25, size * 0.5);
  context.moveTo(size * 0.75, size * 0.5); context.lineTo(size, size * 0.5);
  context.stroke();

  (payload.houses || []).forEach((house) => {
    const sign = Number(house.sign_number);
    const layout = SOUTH_SIGN_LAYOUTS[sign];
    if (!layout) return;
    const scale = size / 572;
    const box = layout.box;
    const items = visibleChartItems(house.items || []);
    const positions = exportItemPositions(box, items);
    context.textAlign = "center";
    context.textBaseline = "middle";
    context.fillStyle = "#111";
    context.font = `700 ${Math.round(size * (items.length >= 5 ? 0.045 : 0.055))}px Arial`;
    positions.forEach(([item, itemX, itemY]) => context.fillText(String(item), itemX * scale, itemY * scale));
  });
  context.restore();
}

function compactExportDegree(value) {
  const match = String(value || "").match(/(\d+)\s*°\s*(\d+)\s*[′']/);
  return match ? `${match[1]}°${match[2]}′` : String(value || "");
}

function exportSignAbbreviation(signName) {
  const abbreviations = {
    "Овен": "Ове", "Телец": "Тел", "Близнаци": "Бли", "Рак": "Рак",
    "Лъв": "Лъв", "Дева": "Дев", "Везни": "Вез", "Скорпион": "Ско",
    "Стрелец": "Стр", "Козирог": "Коз", "Водолей": "Вод", "Риби": "Риб",
  };
  return abbreviations[signName] || String(signName || "").slice(0, 3);
}

async function createChartExportPng(exportData, choices, imageName) {
  const canvas = document.createElement("canvas");
  canvas.width = 1800;
  canvas.height = 1185;
  const context = canvas.getContext("2d");
  context.fillStyle = "#fff";
  context.fillRect(0, 0, canvas.width, canvas.height);

  context.fillStyle = "#111";
  context.font = "700 38px Arial";
  context.textAlign = "left";
  context.fillText(imageName || "Рохини Астро карта", 35, 45);
  if (!choices.hideBirthData) {
    context.textAlign = "right";
    context.font = "400 22px Arial";
    context.fillText(exportData.title || "", 1765, 43);
  }
  context.strokeStyle = "#222";
  context.lineWidth = 2;
  context.beginPath(); context.moveTo(30, 62); context.lineTo(1770, 62); context.stroke();

  let logo = null;
  const logoSource = document.querySelector(".brand-logo")?.src;
  if (logoSource) {
    try {
      logo = new Image();
      logo.src = logoSource;
      await logo.decode();
    } catch (_error) {
      logo = null;
    }
  }

  const northChart = exportData.charts.find((item) => item.code === choices.northCode) || exportData.charts[0];
  const southChart = exportData.charts.find((item) => item.code === choices.southCode) || exportData.charts[1] || exportData.charts[0];
  const chartSize = 855;
  const chartY = 108;
  const chartXs = [30, 915];
  context.fillStyle = "#111";
  context.textAlign = "center";
  context.font = "700 34px Arial";
  context.fillText(`${northChart.label} • СЕВЕРЕН СТИЛ`, chartXs[0] + chartSize / 2, 91);
  context.fillText(`${southChart.label} • ${choices.layout === "mixed" ? "ЮЖЕН" : "СЕВЕРЕН"} СТИЛ`, chartXs[1] + chartSize / 2, 91);
  drawExportNorthChart(context, northChart.payload, chartXs[0], chartY, chartSize);
  if (choices.layout === "mixed") drawExportSouthChart(context, southChart.payload, chartXs[1], chartY, chartSize);
  else drawExportNorthChart(context, southChart.payload, chartXs[1], chartY, chartSize);

  context.fillStyle = "#f1e6c8";
  context.fillRect(30, 976, 1740, 72);
  context.strokeStyle = "#9b7528";
  context.lineWidth = 2;
  context.strokeRect(30, 976, 1740, 72);
  if (logo) context.drawImage(logo, 48, 982, 60, 60);
  context.fillStyle = "#1d3825";
  context.textAlign = "left";
  context.font = "700 29px Arial";
  context.fillText("ROHINI ASTRO", 125, 1007);
  context.fillStyle = "#76581f";
  context.font = "700 19px Arial";
  context.fillText("rohiniastrobg.com • Ведическа астрология и обучения", 125, 1033);
  context.textAlign = "right";
  context.fillStyle = "#1d3825";
  context.font = "700 25px Arial";
  context.fillText("АСЦЕНДЕНТ И 9 ГРАХИ • ГРАДУСИ В D-1", 1745, 1019);

  const rows = exportData.degree_rows || [];
  rows.forEach((row, index) => {
    const column = index % 5;
    const rowIndex = Math.floor(index / 5);
    const cellWidth = 342;
    const x = 45 + column * cellWidth;
    const y = 1092 + rowIndex * 54;
    context.strokeStyle = "#b8b8b8";
    context.lineWidth = 1.5;
    context.beginPath(); context.moveTo(x, y + 18); context.lineTo(x + cellWidth - 16, y + 18); context.stroke();
    context.fillStyle = "#111";
    context.textAlign = "left";
    context.font = "700 35px Arial";
    context.fillText(`${row.label}:`, x, y);
    context.font = "700 35px Arial";
    const compactDegree = compactExportDegree(row.degree_dms);
    const degreeX = x + 72;
    context.fillText(compactDegree, degreeX, y);
    const degreeWidth = context.measureText(compactDegree).width;
    context.font = "700 35px Arial";
    context.fillText(exportSignAbbreviation(row.sign_name), degreeX + degreeWidth + 14, y);
  });
  return canvas;
}

function bindChartPngExport() {
  const openButton = document.getElementById("chartExportOpen");
  const modal = document.getElementById("chartExportModal");
  const dataNode = document.getElementById("chartExportData");
  if (!openButton || !modal || !dataNode) return;

  let exportData;
  try {
    exportData = JSON.parse(dataNode.textContent);
  } catch (_error) {
    return;
  }
  if (!exportData.charts?.length) return;

  const refreshExportData = () => {
    try {
      exportData = JSON.parse(dataNode.textContent);
    } catch (_error) {
      // Keep the last valid export payload.
    }
  };

  const layoutSelect = document.getElementById("chartExportLayout");
  const northSelect = document.getElementById("chartExportNorth");
  const southSelect = document.getElementById("chartExportSouth");
  const mixedFields = document.getElementById("chartExportMixedFields");
  const northLabel = document.getElementById("chartExportNorthLabel");
  const southLabel = document.getElementById("chartExportSouthLabel");
  const hideBirthData = document.getElementById("chartExportHideBirthData");
  const nameInput = document.getElementById("chartExportName");
  const closeButton = document.getElementById("chartExportClose");
  const downloadButton = document.getElementById("chartExportDownload");
  exportData.charts.forEach((chart) => {
    [northSelect, southSelect].forEach((select) => {
      const option = document.createElement("option");
      option.value = chart.code;
      option.textContent = chart.label;
      select.appendChild(option);
    });
  });
  northSelect.value = "D1";
  southSelect.value = exportData.charts.find((chart) => chart.code === "D9")?.code
    || exportData.charts[1]?.code
    || exportData.charts[0].code;

  const syncLayoutFields = () => {
    const mixed = layoutSelect.value === "mixed";
    mixedFields.hidden = false;
    northLabel.textContent = mixed ? "Северна карта" : "Първа карта • северен стил";
    southLabel.textContent = mixed ? "Южна карта" : "Втора карта • северен стил";
  };
  layoutSelect.addEventListener("change", syncLayoutFields);
  syncLayoutFields();

  const close = () => {
    modal.classList.remove("is-open");
    modal.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
  };
  openButton.addEventListener("click", () => {
    refreshExportData();
    modal.classList.add("is-open");
    modal.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
    nameInput.focus();
    nameInput.select();
  });
  closeButton.addEventListener("click", close);
  modal.querySelector("[data-close-chart-export]").addEventListener("click", close);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && modal.classList.contains("is-open")) close();
  });
  downloadButton.addEventListener("click", async () => {
    refreshExportData();
    downloadButton.disabled = true;
    downloadButton.textContent = "Подготвям PNG…";
    try {
      const canvas = await createChartExportPng(exportData, {
        layout: layoutSelect.value,
        northCode: northSelect.value,
        southCode: southSelect.value,
        hideBirthData: hideBirthData.checked,
      }, nameInput.value.trim());
      const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      const safeName = (nameInput.value.trim() || "Rohini-Astro-karta").replace(/[<>:"/\\|?*\x00-\x1F]/g, "-");
      link.href = url;
      link.download = `${safeName}.png`;
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      close();
    } finally {
      downloadButton.disabled = false;
      downloadButton.textContent = "Свали PNG";
    }
  });
}

function bindDesktopDaivaWorkspace() {
  const workspace = document.querySelector(".desktop-chakra-workspace");
  const transitWorkspace = document.getElementById("desktopTransitWorkspace");
  const aboutWorkspace = document.getElementById("desktopAboutWorkspace");
  const form = document.getElementById("birthForm");
  if (!workspace || !form) return;

  const body = document.body;
  const menuTabs = [...document.querySelectorAll(".desktop-menu-tab[data-desktop-view]")];
  const transitDetails = document.getElementById("transitCard");
  const gocharToggle = document.getElementById("desktopGocharToggle");
  const globalStyleButtons = [...document.querySelectorAll("[data-global-chart-style]")];
  const outerPlanetsToggle = document.getElementById("showOuterPlanets");
  const desktopTimeUnit = document.getElementById("desktopTimeUnit");
  const TIME_UNIT_STORAGE_KEY = "rohini.desktopTimeUnit";
  try {
    const rememberedUnit = localStorage.getItem(TIME_UNIT_STORAGE_KEY);
    if (rememberedUnit && desktopTimeUnit && [...desktopTimeUnit.options].some((option) => option.value === rememberedUnit)) {
      desktopTimeUnit.value = rememberedUnit;
    }
  } catch (_error) { /* the default year unit remains selected */ }
  desktopTimeUnit?.addEventListener("change", () => {
    try { localStorage.setItem(TIME_UNIT_STORAGE_KEY, desktopTimeUnit.value); } catch (_error) { /* current session only */ }
  });

  let globalChartStyle = body.dataset.persistentChartStyle;
  if (!['north', 'south'].includes(globalChartStyle)) {
    try {
      globalChartStyle = localStorage.getItem("rohini.globalChartStyle") === "south" ? "south" : "north";
    } catch (_error) {
      globalChartStyle = "north";
    }
  }

  const renderDesktopCharts = (style) => {
    document.querySelectorAll(".desktop-chakra-workspace .desktop-chart, .desktop-transit-workspace .desktop-chart").forEach((card, index) => {
      const payloadNode = card.querySelector(".chart-payload");
      const frame = card.querySelector(".chart-frame");
      if (!payloadNode || !frame) return;

      try {
        const payload = JSON.parse(payloadNode.textContent);
        const showDegrees = frame.dataset.showDegrees === "true";
        const firstHouse = Math.max(1, Math.min(12, Number(card.dataset.contextFirstHouse) || 1));
        frame.innerHTML = style === "south"
          ? renderSouthChartSvg(payload, `desktop-global-${index + 1}`, showDegrees)
          : renderNorthChartSvg(payload, firstHouse, `desktop-global-${index + 1}`, showDegrees);
        frame.dataset.currentStyle = style;
        ensureChartZoomButton(frame);
      } catch (_error) {
        // Keep the server-rendered chart if a payload is unavailable.
      }
    });
  };

  const applyGlobalChartStyle = (style, persist = true) => {
    globalChartStyle = style === "south" ? "south" : "north";
    document.body.dataset.globalChartStyle = globalChartStyle;
    globalStyleButtons.forEach((button) => {
      const active = button.dataset.globalChartStyle === globalChartStyle;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-pressed", active ? "true" : "false");
    });

    document.querySelectorAll(".chart-style-switch").forEach((switcher) => {
      const styleButton = switcher.querySelector(`[data-chart-style="${globalChartStyle}"]`);
      if (styleButton && !styleButton.classList.contains("is-active")) styleButton.click();
    });
    renderDesktopCharts(globalChartStyle);

    if (persist) {
      try {
        localStorage.setItem("rohini.globalChartStyle", globalChartStyle);
      } catch (_error) {
        // The selected style still applies for the current session.
      }
      persistUserSetting("chart_style", globalChartStyle);
    }
  };

  globalStyleButtons.forEach((button) => {
    button.addEventListener("click", () => applyGlobalChartStyle(button.dataset.globalChartStyle));
  });

  outerPlanetsToggle?.addEventListener("change", () => {
    body.classList.toggle("show-desktop-outer-planets", outerPlanetsToggle.checked);
    renderDesktopCharts(globalChartStyle);
  });

  document.getElementById("desktopOuterPlanetsSave")?.addEventListener("click", () => {
    const keepTransitPair = Boolean(document.querySelector("#desktopTransitPrimaryChart .chart-payload"));
    const buildMode = keepTransitPair ? "transit" : "natal";
    try { sessionStorage.setItem("rohini.desktopActiveView", "data"); } catch (_error) { /* state is only a convenience */ }
    const submitter = form.querySelector(`button[name="buildMode"][value="${buildMode}"]`);
    form.requestSubmit(submitter);
  });

  applyGlobalChartStyle(globalChartStyle, false);

  const setActiveTab = (name) => {
    menuTabs.forEach((tab) => tab.classList.toggle("is-active", tab.dataset.desktopView === name));
    try { sessionStorage.setItem("rohini.desktopActiveView", name); } catch (_error) { /* current page only */ }
  };

  menuTabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const view = tab.dataset.desktopView;
      if (view === "chakra") {
        body.classList.remove("is-data-panel-open");
        if (transitWorkspace) transitWorkspace.hidden = true;
        workspace.hidden = false;
        if (aboutWorkspace) aboutWorkspace.hidden = true;
      } else if (view === "data") {
        body.classList.add("is-data-panel-open");
        if (transitWorkspace) transitWorkspace.hidden = true;
        workspace.hidden = false;
        if (aboutWorkspace) aboutWorkspace.hidden = true;
        if (transitDetails) transitDetails.open = true;
      } else if (view === "transits") {
        body.classList.remove("is-data-panel-open");
        workspace.hidden = true;
        if (transitWorkspace) transitWorkspace.hidden = false;
        if (aboutWorkspace) aboutWorkspace.hidden = true;
      } else if (view === "about") {
        body.classList.remove("is-data-panel-open");
        workspace.hidden = true;
        if (transitWorkspace) transitWorkspace.hidden = true;
        if (aboutWorkspace) aboutWorkspace.hidden = false;
      }
      setActiveTab(view);
    });
  });

  const analysisField = document.getElementById("desktopAnalysisField");
  const analysisEmpty = analysisField?.querySelector(".desktop-analysis-empty");
  const analysisViews = [...(analysisField?.querySelectorAll("[data-desktop-analysis-view]") || [])];
  const analysisButtons = [...(analysisField?.querySelectorAll("[data-desktop-analysis]") || [])];
  const ANALYSIS_STATE_KEY = "rohini.desktopAnalysisState.v1";
  const appSessionId = body.dataset.appSessionId || "";
  const validAnalysisNames = new Set(analysisViews.map((view) => view.dataset.desktopAnalysisView));
  let currentAnalysisName = "";
  let rememberedDashaSystem = "";
  let restoredAnalysisState = null;

  try {
    const candidate = JSON.parse(sessionStorage.getItem(ANALYSIS_STATE_KEY) || "null");
    if (candidate?.sessionId === appSessionId && validAnalysisNames.has(candidate.view)) {
      restoredAnalysisState = candidate;
      rememberedDashaSystem = String(candidate.dashaSystem || "");
    } else {
      sessionStorage.removeItem(ANALYSIS_STATE_KEY);
    }
  } catch (_error) {
    try { sessionStorage.removeItem(ANALYSIS_STATE_KEY); } catch (_storageError) { /* текуща страница */ }
  }

  const rememberAnalysis = () => {
    if (!currentAnalysisName) {
      try { sessionStorage.removeItem(ANALYSIS_STATE_KEY); } catch (_error) { /* текуща страница */ }
      return;
    }
    try {
      sessionStorage.setItem(ANALYSIS_STATE_KEY, JSON.stringify({
        sessionId: appSessionId,
        view: currentAnalysisName,
        dashaSystem: rememberedDashaSystem,
      }));
    } catch (_error) { /* текуща страница */ }
  };

  const clearAnalysis = () => {
    currentAnalysisName = "";
    rememberedDashaSystem = "";
    analysisViews.forEach((view) => { view.hidden = true; });
    analysisButtons.forEach((button) => button.classList.remove("is-active"));
    if (analysisEmpty) analysisEmpty.hidden = false;
    rememberAnalysis();
  };

  const showAnalysis = (name) => {
    if (!validAnalysisNames.has(name)) return;
    currentAnalysisName = name;
    analysisViews.forEach((view) => { view.hidden = view.dataset.desktopAnalysisView !== name; });
    analysisButtons.forEach((button) => button.classList.toggle("is-active", button.dataset.desktopAnalysis === name));
    if (analysisEmpty) analysisEmpty.hidden = true;
    rememberAnalysis();
  };

  const analysisMenus = [...(analysisField?.querySelectorAll(".desktop-analysis-menu, .desktop-dasha-menu") || [])];

  const collapseAnalysisMenus = () => {
    analysisMenus.forEach((menu) => menu.classList.add("is-collapsed"));
  };

  analysisButtons.forEach((button) => {
    button.addEventListener("click", () => {
      showAnalysis(button.dataset.desktopAnalysis);
      collapseAnalysisMenus();
      button.blur();
    });
  });

  analysisMenus.forEach((menu) => {
    menu.addEventListener("mouseleave", () => menu.classList.remove("is-collapsed"));
  });

  const dashaButtons = [...document.querySelectorAll("[data-dasha-system]")];
  const dashaMenu = document.querySelector(".desktop-dasha-menu");
  const dashaTable = document.getElementById("desktopDashaTable");
  const dashaRows = document.getElementById("desktopDashaRows");
  const dashaTitle = document.getElementById("desktopDashaTitle");
  const dashaPath = document.getElementById("desktopDashaPath");
  const dashaStatus = document.getElementById("desktopDashaStatus");
  const dashaYear = document.getElementById("desktopDashaYear");
  const dashaBack = document.getElementById("desktopDashaBack");
  const birthForm = document.getElementById("birthForm");
  const dashaLevelNames = ["Махадаша", "Антардаша", "Пратянтардаша", "Сукшма", "Прана"];
  const dashaState = { system: "", title: "", maxLevel: 0, yearDays: null, parents: [] };

  const formPayload = () => {
    const values = {};
    if (!birthForm) return values;
    new FormData(birthForm).forEach((value, key) => { values[key] = value; });
    birthForm.querySelectorAll("input[type='checkbox']").forEach((input) => {
      values[input.name] = input.checked ? (input.value || "on") : "";
    });
    return values;
  };

  const dashaDate = (value) => {
    if (Array.isArray(value)) {
      const [year, month, day, decimalHour = 0] = value;
      const seconds = Math.round(Number(decimalHour) * 3600);
      return new Date(Date.UTC(Number(year), Number(month) - 1, Number(day), 0, 0, seconds));
    }
    return new Date(String(value).replace(" ", "T"));
  };

  const renderDashaRows = (payload) => {
    const level = dashaState.parents.length + 1;
    const pathLabels = dashaState.parents.map((row) => row.label);
    dashaTitle.textContent = `${payload.title} — ${dashaLevelNames[level - 1] || `Ниво ${level}`}`;
    dashaPath.textContent = pathLabels.length ? pathLabels.join(" — ") : "Главни периоди";
    if (payload.year_days) dashaState.yearDays = payload.year_days;
    dashaYear.textContent = dashaState.yearDays ? `Средна тропическа соларна година: ${Number(dashaState.yearDays).toFixed(5)} дни` : "";
    dashaRows.replaceChildren();
    const now = new Date();
    payload.rows.forEach((row) => {
      const tr = document.createElement("tr");
      const active = dashaDate(row.start) <= now && now < dashaDate(row.end);
      if (active) tr.classList.add("is-current");
      tr.innerHTML = `<th>${row.label}</th><td>${row.start_label}</td><td>${row.end_label}</td>`;
      tr.title = level < dashaState.maxLevel ? "Двоен клик за подпериодите" : "Последно ниво";
      if (level < dashaState.maxLevel) {
        tr.classList.add("can-open");
        tr.addEventListener("dblclick", () => {
          dashaState.parents.push(row);
          loadDashaLevel();
        });
      }
      dashaRows.appendChild(tr);
    });
    dashaBack.hidden = dashaState.parents.length === 0;
    dashaTable.hidden = false;
    dashaStatus.hidden = true;
  };

  const loadDashaLevel = async () => {
    if (!dashaState.system) return;
    showAnalysis("dashas");
    dashaTable.hidden = true;
    dashaStatus.hidden = false;
    dashaStatus.textContent = "Изчисляване на периодите…";
    const parent = dashaState.parents.at(-1);
    try {
      const response = await fetch("/api/dashas", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          system: dashaState.system,
          path: parent?.path || [],
          start: parent?.start || null,
          end: parent?.end || null,
          form: formPayload(),
        }),
      });
      const payload = await response.json();
      if (!response.ok || !payload.ok) throw new Error(payload.error || "Дашата не може да бъде изчислена.");
      dashaState.title = payload.title;
      dashaState.maxLevel = Number(payload.max_level) || 1;
      renderDashaRows(payload);
    } catch (error) {
      dashaStatus.hidden = false;
      dashaStatus.textContent = error.message;
    }
  };

  dashaButtons.forEach((button) => {
    button.addEventListener("click", () => {
      dashaState.system = button.dataset.dashaSystem;
      rememberedDashaSystem = dashaState.system;
      dashaState.yearDays = null;
      dashaState.parents = [];
      loadDashaLevel();
      dashaMenu?.classList.add("is-closed");
      collapseAnalysisMenus();
      button.blur();
    });
  });

  dashaMenu?.addEventListener("mouseleave", () => {
    dashaMenu.classList.remove("is-closed");
  });

  dashaBack?.addEventListener("click", () => {
    dashaState.parents.pop();
    loadDashaLevel();
  });

  if (restoredAnalysisState) {
    if (
      restoredAnalysisState.view === "dashas"
      && dashaButtons.some((button) => button.dataset.dashaSystem === rememberedDashaSystem)
    ) {
      dashaState.system = rememberedDashaSystem;
      dashaState.yearDays = null;
      dashaState.parents = [];
      loadDashaLevel();
    } else {
      showAnalysis(restoredAnalysisState.view);
    }
  }

  let lastRightClick = 0;
  analysisField?.addEventListener("contextmenu", (event) => {
    if (!analysisViews.some((view) => !view.hidden)) return;
    event.preventDefault();
    const now = Date.now();
    if (now - lastRightClick <= 520) {
      clearAnalysis();
      lastRightClick = 0;
    } else {
      lastRightClick = now;
    }
  });

  gocharToggle?.addEventListener("change", () => {
    // Gochar changes only the target of the time arrows; it must not change pages.
  });

  document.getElementById("desktopTransitMomentEdit")?.addEventListener("click", () => {
    const dataTab = document.querySelector('.desktop-menu-tab[data-desktop-view="data"]');
    dataTab?.click();
    if (transitDetails) transitDetails.open = true;
  });

  const overlay = document.getElementById("desktopTransitOverlay");
  document.getElementById("desktopTransitOverlayOpen")?.addEventListener("click", () => {
    if (overlay) overlay.hidden = false;
    try { sessionStorage.setItem("rohini.transitOverlayOpen", "true"); } catch (_error) { /* current page only */ }
  });
  document.getElementById("desktopTransitOverlayClose")?.addEventListener("click", () => {
    if (overlay) overlay.hidden = true;
    try { sessionStorage.setItem("rohini.transitOverlayOpen", "false"); } catch (_error) { /* current page only */ }
  });
  overlay?.addEventListener("click", (event) => {
    if (event.target === overlay) {
      overlay.hidden = true;
      try { sessionStorage.setItem("rohini.transitOverlayOpen", "false"); } catch (_error) { /* current page only */ }
    }
  });

  const updateSegmentedValue = (hiddenId, value, type) => {
    const hidden = document.getElementById(hiddenId);
    if (hidden) {
      hidden.value = value;
      if (type === "time") {
        const preciseTime = value.match(/^\d{2}:\d{2}:\d{2}(\.\d+)$/);
        hidden.dataset.subsecond = preciseTime?.[1] || "";
      }
    }
    const control = document.querySelector(`[data-segmented-${type}][data-target="${hiddenId}"]`);
    if (!control) return;
    const parts = type === "date"
      ? { year: value.slice(0, 4), month: value.slice(5, 7), day: value.slice(8, 10) }
      : { hour: value.slice(0, 2), minute: value.slice(3, 5), second: value.slice(6, 8) };
    Object.entries(parts).forEach(([part, partValue]) => {
      const input = control.querySelector(`[data-part="${part}"]`);
      if (input) input.value = partValue;
    });
  };

  document.querySelectorAll(".desktop-time-step").forEach((button) => {
    button.addEventListener("click", async () => {
      const transitMode = Boolean(gocharToggle?.checked);
      const dateId = transitMode ? "transitDate" : "birthDate";
      const timeId = transitMode ? "transitTime" : "birthTime";
      const date = document.getElementById(dateId)?.value;
      const time = document.getElementById(timeId)?.value;
      if (!date || !time) return;
      button.disabled = true;
      try {
        const response = await fetch("/api/time-dynamics/shift", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            date,
            time,
            amount: 1,
            unit: document.getElementById("desktopTimeUnit")?.value || "year",
            forward: button.dataset.desktopTimeDirection === "forward",
          }),
        });
        if (!response.ok) throw new Error("Преместването във времето не можа да бъде изчислено.");
        const shifted = await response.json();
        updateSegmentedValue(dateId, shifted.date, "date");
        updateSegmentedValue(timeId, shifted.time, "time");
        try {
          const transitViewOpen = !transitWorkspace?.hidden;
          sessionStorage.setItem("rohini.desktopActiveView", transitViewOpen ? "transits" : "chakra");
          sessionStorage.setItem("rohini.transitOverlayOpen", String(transitMode && transitViewOpen && overlay && !overlay.hidden));
        } catch (_error) { /* state is only a convenience */ }
        const transitPairExists = Boolean(document.querySelector("#desktopTransitPrimaryChart .chart-payload"));
        const requestedBuildMode = transitMode || (!transitWorkspace?.hidden && transitPairExists) ? "transit" : "natal";
        const submitter = form.querySelector(`button[name="buildMode"][value="${requestedBuildMode}"]`);
        form.requestSubmit(submitter);
      } catch (error) {
        window.alert(error.message || "Преместването във времето не можа да бъде изчислено.");
        button.disabled = false;
      }
    });
  });

  try {
    const storedView = sessionStorage.getItem("rohini.desktopActiveView");
    if (storedView === "transits") {
      body.classList.remove("is-data-panel-open");
      workspace.hidden = true;
      if (transitWorkspace) transitWorkspace.hidden = false;
      setActiveTab("transits");
      if (sessionStorage.getItem("rohini.transitOverlayOpen") === "true" && overlay?.querySelector(".transit-overlay-frame")) {
        overlay.hidden = false;
      }
      const storedZoomSlot = sessionStorage.getItem("rohini.transitZoomSlot");
      if (storedZoomSlot && overlay?.hidden !== false) {
        const zoomFrame = transitWorkspace?.querySelector(`.desktop-chart[data-chart-slot="${storedZoomSlot}"] .chart-frame--zoomable`);
        if (zoomFrame) window.setTimeout(() => zoomFrame.querySelector(".chart-zoom-button")?.click(), 0);
      }
    } else if (storedView === "data") {
      body.classList.add("is-data-panel-open");
      if (transitWorkspace) transitWorkspace.hidden = true;
      workspace.hidden = false;
      if (aboutWorkspace) aboutWorkspace.hidden = true;
      if (transitDetails) transitDetails.open = true;
      setActiveTab("data");
    } else if (storedView === "about") {
      body.classList.remove("is-data-panel-open");
      workspace.hidden = true;
      if (transitWorkspace) transitWorkspace.hidden = true;
      if (aboutWorkspace) aboutWorkspace.hidden = false;
      setActiveTab("about");
    }
  } catch (_error) { /* default to Rohini Chakra */ }

  const contextMenu = document.getElementById("desktopChartContextMenu");
  const contextTitle = document.getElementById("chartContextLagnaTitle");
  const contextTimes = document.getElementById("chartContextLagnaTimes");
  const contextChoices = document.getElementById("chartContextChartChoices");
  const contextRotationChoices = document.getElementById("chartContextRotationChoices");
  const chartCards = [...document.querySelectorAll(".desktop-chakra-workspace .desktop-chart, .desktop-transit-workspace .desktop-chart")];
  let contextCard = null;
  let contextBoundary = null;

  const readJson = (node, fallback = {}) => {
    try { return node ? JSON.parse(node.textContent) : fallback; } catch (_error) { return fallback; }
  };

  const formatDuration = (seconds) => {
    // Keep sub-second precision for the actual move, but show students a
    // simple whole-second duration in the context menu.
    const total = Math.max(0, Math.round(Number(seconds) || 0));
    const hours = Math.floor(total / 3600);
    const minutes = Math.floor((total % 3600) / 60);
    const secs = total % 60;
    return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
  };

  const chartRegistryFor = (card) => {
    const special = readJson(card.querySelector(".desktop-chart-registry"));
    const divisional = readJson(card.querySelector(".divisional-chart-registry"));
    return { ...special, ...divisional };
  };

  const contextFirstHouse = (card) => Math.max(1, Math.min(12, Number(card.dataset.contextFirstHouse) || 1));

  const contextShowDegrees = (card) => card.dataset.chartCode === "D1";

  const paintContextCard = (card) => {
    const payload = readJson(card.querySelector(".chart-payload"), null);
    const frame = card.querySelector(".chart-frame");
    if (!payload || !frame) return;
    const slot = card.dataset.chartSlot || "chart";
    const code = card.dataset.chartCode || "D1";
    const showDegrees = contextShowDegrees(card);
    frame.innerHTML = globalChartStyle === "south"
      ? renderSouthChartSvg(payload, `context-${slot}-${code}`, showDegrees)
      : renderNorthChartSvg(payload, contextFirstHouse(card), `context-${slot}-${code}`, showDegrees);
    ensureChartZoomButton(frame);
  };

  const renderContextCard = (card, code, persist = true) => {
    const registry = chartRegistryFor(card);
    const selected = registry[code];
    if (!selected?.payload) return;
    const payloadNode = card.querySelector(".chart-payload");
    const frame = card.querySelector(".chart-frame");
    payloadNode.textContent = JSON.stringify(selected.payload);
    card.dataset.chartCode = code;
    frame.dataset.chartTitle = selected.card_title || selected.selector_label || code;
    frame.dataset.showDegrees = code === "D1" ? "true" : "false";
    paintContextCard(card);
    const slot = card.dataset.chartSlot || "chart";
    if (persist) {
      try { localStorage.setItem(`rohini.desktopChart.${slot}`, code); } catch (_error) { /* session only */ }
    }
  };

  chartCards.forEach((card) => {
    const slot = card.dataset.chartSlot || "chart";
    try {
      const storedRotation = Number(localStorage.getItem(`rohini.desktopChartRotation.${slot}`));
      if (storedRotation >= 1 && storedRotation <= 12) {
        card.dataset.contextFirstHouse = String(storedRotation);
        card.dataset.contextRotationActive = "true";
      }
      const stored = localStorage.getItem(`rohini.desktopChart.${slot}`);
      if (stored && chartRegistryFor(card)[stored]) renderContextCard(card, stored, false);
      else paintContextCard(card);
    } catch (_error) { /* keep server selection */ }
  });

  const populateContextChoices = (card) => {
    if (!contextChoices) return;
    contextChoices.innerHTML = "";
    const registry = chartRegistryFor(card);
    const completeVargaOrder = ["D2", "D3", "D4", "D7", "D9", "D10", "D12", "D24"];
    const remaining = Object.keys(registry).filter((code) => !["D1", "JAI", ...completeVargaOrder].includes(code));
    const order = ["D1", ...completeVargaOrder, ...remaining, "JAI"];
    order.forEach((code) => {
      const entry = registry[code];
      if (!entry?.payload) return;
      const button = document.createElement("button");
      button.type = "button";
      button.dataset.contextChartCode = code;
      button.classList.toggle("is-selected", card.dataset.chartCode === code);
      button.textContent = code === "JAI" ? "Джаймини" : (entry.selector_label || entry.card_title || code);
      button.addEventListener("click", () => {
        renderContextCard(card, code);
        contextMenu.hidden = true;
      });
      contextChoices.appendChild(button);
    });
  };

  const populateRotationChoices = (card) => {
    if (!contextRotationChoices) return;
    contextRotationChoices.innerHTML = "";
    contextRotationChoices.classList.toggle("is-disabled", globalChartStyle !== "north");
    const payload = readJson(card.querySelector(".chart-payload"), {});
    const houses = Array.isArray(payload.houses) ? payload.houses : [];
    const signNames = ["Овен", "Телец", "Близнаци", "Рак", "Лъв", "Дева", "Везни", "Скорпион", "Стрелец", "Козирог", "Водолей", "Риби"];
    const current = contextFirstHouse(card);
    const rotationActive = card.dataset.contextRotationActive === "true";
    const entries = [{ label: "По подразбиране", firstHouse: 1, isDefault: true }];
    houses
      .slice()
      .sort((left, right) => Number(left.sign_number) - Number(right.sign_number))
      .forEach((house) => entries.push({
        label: `${signNames[Number(house.sign_number) - 1] || "Знак"} (${house.sign_number})`,
        firstHouse: Number(house.house) || 1,
      }));
    entries.forEach((entry) => {
      const button = document.createElement("button");
      button.type = "button";
      button.classList.toggle("is-selected", entry.isDefault ? !rotationActive : rotationActive && current === entry.firstHouse);
      button.textContent = entry.label;
      button.addEventListener("click", () => {
        card.dataset.contextFirstHouse = String(entry.firstHouse);
        card.dataset.contextRotationActive = entry.isDefault ? "false" : "true";
        paintContextCard(card);
        const slot = card.dataset.chartSlot || "chart";
        try {
          if (entry.isDefault) localStorage.removeItem(`rohini.desktopChartRotation.${slot}`);
          else localStorage.setItem(`rohini.desktopChartRotation.${slot}`, String(entry.firstHouse));
        } catch (_error) { /* session only */ }
        contextMenu.hidden = true;
      });
      contextRotationChoices.appendChild(button);
    });
  };

  const formObject = () => Object.fromEntries(new FormData(form).entries());

  const loadContextBoundary = async (card) => {
    contextBoundary = null;
    if (contextTitle) contextTitle.textContent = "Изчисляване на лагна…";
    if (contextTimes) contextTimes.textContent = "Моля, изчакай.";
    try {
      const response = await fetch("/api/chart-context/lagna-boundaries", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ form: formObject(), chart_code: card.dataset.chartCode || "D1", prefix: card.dataset.chartPrefix === "transit" ? "transit" : "natal" }),
      });
      const result = await response.json();
      if (!response.ok || !result.ok) throw new Error(result.error || "Границата не може да се изчисли.");
      contextBoundary = result;
      if (contextTitle) contextTitle.textContent = `Лагна в картата: ${result.sign_name} (${result.sign_number})`;
      if (contextTimes) contextTimes.textContent = `Напред + ${formatDuration(result.forward_seconds)} / назад − ${formatDuration(result.backward_seconds)}`;
    } catch (error) {
      if (contextTitle) contextTitle.textContent = "Лагна";
      if (contextTimes) contextTimes.textContent = error.message || "Неуспешно изчисление.";
    }
  };

  const openContextMenu = (event, card) => {
    if (!contextMenu) return;
    event.preventDefault();
    contextCard = card;
    populateContextChoices(card);
    populateRotationChoices(card);
    contextMenu.hidden = false;
    const menuRect = contextMenu.getBoundingClientRect();
    const left = Math.max(6, Math.min(event.clientX, window.innerWidth - menuRect.width - 6));
    const top = Math.max(6, Math.min(event.clientY, window.innerHeight - menuRect.height - 54));
    contextMenu.style.left = `${left}px`;
    contextMenu.style.top = `${top}px`;
    loadContextBoundary(card);
  };

  chartCards.forEach((card) => card.addEventListener("contextmenu", (event) => openContextMenu(event, card)));

  const moveToBoundary = async (forward) => {
    if (!contextBoundary || !contextCard) return;
    const transitTarget = contextCard.dataset.chartPrefix === "transit";
    const dateId = transitTarget ? "transitDate" : "birthDate";
    const timeId = transitTarget ? "transitTime" : "birthTime";
    const boundary = forward ? contextBoundary.forward : contextBoundary.backward;
    if (!boundary?.date || !boundary?.time) return;
    updateSegmentedValue(dateId, boundary.date, "date");
    updateSegmentedValue(timeId, boundary.time, "time");
    try {
      const transitViewOpen = !transitWorkspace?.hidden;
      sessionStorage.setItem("rohini.desktopActiveView", transitViewOpen ? "transits" : "chakra");
      sessionStorage.setItem("rohini.transitOverlayOpen", String(transitViewOpen && overlay && !overlay.hidden));
    } catch (_error) { /* state is only a convenience */ }
    const keepTransitPair = Boolean(document.querySelector("#desktopTransitPrimaryChart .chart-payload"));
    const buildMode = transitTarget || keepTransitPair ? "transit" : "natal";
    form.requestSubmit(form.querySelector(`button[name="buildMode"][value="${buildMode}"]`));
  };

  contextMenu?.querySelectorAll("[data-chart-context-action]").forEach((button) => {
    button.addEventListener("click", () => {
      const action = button.dataset.chartContextAction;
      if (action === "shift-forward") moveToBoundary(true);
      else if (action === "shift-backward") moveToBoundary(false);
      else if (action === "toggle-style") applyGlobalChartStyle(globalChartStyle === "north" ? "south" : "north");
      else if (action === "toggle-outer" && outerPlanetsToggle) {
        outerPlanetsToggle.checked = !outerPlanetsToggle.checked;
        outerPlanetsToggle.dispatchEvent(new Event("change", { bubbles: true }));
      } else if (action === "save-png") {
        document.getElementById("chartExportOpen")?.click();
      }
      if (!["shift-forward", "shift-backward"].includes(action)) contextMenu.hidden = true;
    });
  });

  document.addEventListener("pointerdown", (event) => {
    if (contextMenu && !contextMenu.hidden && !contextMenu.contains(event.target)) contextMenu.hidden = true;
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && contextMenu) contextMenu.hidden = true;
  });
}

document.addEventListener("DOMContentLoaded", () => {
  const syncNatalCity = bindCitySync({
    citySelectId: "cityName",
    latitudeDegreesId: "latitudeDegrees",
    latitudeMinutesId: "latitudeMinutes",
    latitudeSecondsId: "latitudeSeconds",
    latitudeHemisphereId: "latitudeHemisphere",
    longitudeDegreesId: "longitudeDegrees",
    longitudeMinutesId: "longitudeMinutes",
    longitudeSecondsId: "longitudeSeconds",
    longitudeHemisphereId: "longitudeHemisphere",
  });

  const syncTransitCity = bindCitySync({
    citySelectId: "transitCityName",
    latitudeDegreesId: "transitLatitudeDegrees",
    latitudeMinutesId: "transitLatitudeMinutes",
    latitudeSecondsId: "transitLatitudeSeconds",
    latitudeHemisphereId: "transitLatitudeHemisphere",
    longitudeDegreesId: "transitLongitudeDegrees",
    longitudeMinutesId: "transitLongitudeMinutes",
    longitudeSecondsId: "transitLongitudeSeconds",
    longitudeHemisphereId: "transitLongitudeHemisphere",
  });

  const maybeSyncIfBlank = (fieldIds, syncFn) => {
    const shouldSync = fieldIds.some((fieldId) => {
      const field = document.getElementById(fieldId);
      return field && field.value.trim() === "";
    });

    if (shouldSync) {
      syncFn();
    }
  };

  maybeSyncIfBlank(
    [
      "latitudeDegrees",
      "latitudeMinutes",
      "latitudeSeconds",
      "latitudeHemisphere",
      "longitudeDegrees",
      "longitudeMinutes",
      "longitudeSeconds",
      "longitudeHemisphere",
    ],
    syncNatalCity,
  );

  maybeSyncIfBlank(
    [
      "transitLatitudeDegrees",
      "transitLatitudeMinutes",
      "transitLatitudeSeconds",
      "transitLatitudeHemisphere",
      "transitLongitudeDegrees",
      "transitLongitudeMinutes",
      "transitLongitudeSeconds",
      "transitLongitudeHemisphere",
    ],
    syncTransitCity,
  );

  bindTimezoneMode("timezoneMode", "manualTimezoneFields");
  bindTimezoneMode("transitTimezoneMode", "transitManualTimezoneFields");
  bindSegmentedDateTimeControls();
  bindTableScrollAssist();
  bindChartRotation();
  bindDivisionalChartSelector();
  bindChartLightbox();
  bindChartPngExport();
  bindChartDrishti();
  bindCollapsibleSettings();
  bindDesktopWorkingPosition();
  bindDesktopDaivaWorkspace();
  initChartSaveOpen();
  initGlobalNodeMode();
  bindWindowControls();
  bindTransitRowSizing();

  const combustionOrbInput = document.getElementById("combustionOrbDegrees");
  if (combustionOrbInput) {
    combustionOrbInput.addEventListener("change", () => {
      const parsedValue = Number(combustionOrbInput.value);
      const value = Number.isFinite(parsedValue) && parsedValue > 0
        ? Math.min(30, parsedValue)
        : 5;
      combustionOrbInput.value = String(value);
      // Keep one persisted source. A stale localStorage value used to replace
      // the server value here and remove valid markers after rendering.
      document.cookie = `rohini_combustion_orb=${encodeURIComponent(value)}; Max-Age=31536000; Path=/; SameSite=Lax`;
      persistUserSetting("combustion_orb", value);
      reconcileDesktopCombustionBadges();
      reconcileDesktopGandantaBadges();
      reconcileDesktopPlanetaryWar();
      reconcileDesktopEclipseMarkers();
    });
    combustionOrbInput.form?.addEventListener("submit", () => combustionOrbInput.dispatchEvent(new Event("change")));
  }
  reconcileDesktopCombustionBadges();
  reconcileDesktopGandantaBadges();
  reconcileDesktopPlanetaryWar();
  reconcileDesktopEclipseMarkers();
});

function initChartSaveOpen() {
  const saveButton = document.getElementById("saveChartBtn");
  const openButton = document.getElementById("openChartBtn");
  if (!saveButton && !openButton) return;

  saveButton?.addEventListener("click", async () => {
    const ids = [
      "birthDate", "birthTime", "cityName",
      "latitudeDegrees", "latitudeMinutes", "latitudeSeconds", "latitudeHemisphere",
      "longitudeDegrees", "longitudeMinutes", "longitudeSeconds", "longitudeHemisphere",
      "timezoneMode", "nodeMode", "manualTzSign", "manualTzHours", "manualTzMinutes", "manualTzSeconds",
      "combustionOrbDegrees", "showOuterPlanets",
    ];
    const values = {};
    ids.forEach((id) => {
      const element = document.getElementById(id);
      if (element) {
        values[id] = element.type === "checkbox" ? (element.checked ? "on" : "") : element.value;
      }
    });

    saveButton.disabled = true;
    try {
      const response = await fetch("/api/save-chart", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(values),
      });
      const data = await response.json();
      if (data.ok) {
        window.alert(`Картата е запазена:\n${data.path}`);
      } else if (!data.cancelled) {
        window.alert(`Грешка: ${data.error || "неуспешно запазване"}`);
      }
    } catch (error) {
      window.alert(`Грешка при запазване: ${error}`);
    } finally {
      saveButton.disabled = false;
    }
  });

  openButton?.addEventListener("click", async () => {
    openButton.disabled = true;
    try {
      const response = await fetch("/api/open-chart", { method: "POST" });
      const data = await response.json();
      if (data.ok) {
        try { sessionStorage.setItem("rohini.desktopActiveView", "chakra"); } catch (_error) { /* текуща сесия */ }
        window.location.href = "/?restore=1";
      } else if (!data.cancelled) {
        window.alert(`Грешка: ${data.error || "неуспешно отваряне"}`);
      }
    } catch (error) {
      window.alert(`Грешка при отваряне: ${error}`);
    } finally {
      openButton.disabled = false;
    }
  });
}

function bindWindowControls() {
  const minimizeButton = document.querySelector('[data-window-action="minimize"]');
  const maximizeButton = document.querySelector('[data-window-action="maximize"]');
  const closeButton = document.querySelector('[data-window-action="close"]');

  const nativeApi = () => {
    if (typeof window.pywebview === "undefined" || !window.pywebview.api) return null;
    return window.pywebview.api;
  };

  const refreshMaximizeIcon = (isMaximized = Boolean(document.fullscreenElement)) => {
    if (!maximizeButton) return;
    maximizeButton.textContent = isMaximized ? "\uE923" : "\uE922";
    maximizeButton.title = isMaximized ? "Възстановяване" : "Увеличаване";
    maximizeButton.setAttribute("aria-label", maximizeButton.title);
  };

  const invokeWindowAction = async (action) => {
    try {
      const response = await fetch(`/__rohini_window/${action}`, { method: "POST" });
      if (response.ok) return await response.json();
    } catch (_error) {
      // The browser development mode has no native-window endpoint.
    }

    const api = nativeApi();
    const method = action === "maximize" ? "toggle_maximize" : action;
    if (api && typeof api[method] === "function") {
      const maximized = await api[method]();
      return { ok: true, maximized: Boolean(maximized) };
    }
    return null;
  };

  minimizeButton?.addEventListener("click", async () => {
    if (await invokeWindowAction("minimize")) return;
    if (document.fullscreenElement) {
      document.exitFullscreen().catch(() => {});
    }
  });

  maximizeButton?.addEventListener("click", async () => {
    const result = await invokeWindowAction("maximize");
    if (result) {
      refreshMaximizeIcon(Boolean(result.maximized));
      return;
    }
    if (document.fullscreenElement) {
      document.exitFullscreen().catch(() => {});
    } else {
      document.documentElement.requestFullscreen?.().catch(() => {});
    }
  });

  closeButton?.addEventListener("click", async () => {
    if (await invokeWindowAction("close")) return;
    window.close();
  });

  document.addEventListener("fullscreenchange", () => refreshMaximizeIcon());
  invokeWindowAction("state").then((result) => {
    refreshMaximizeIcon(result ? Boolean(result.maximized) : false);
  });
}

function bindTransitRowSizing() {
  const configs = [
    { selector: ".desktop-transit-position-table", scroll: ".desktop-transit-table-scroll", variable: "--transit-row-height", min: 26, max: 40 },
    { selector: ".desktop-panchanga-table", scroll: ".desktop-panchanga-wrap", variable: "--panchanga-row-height", min: 34, max: 90 },
  ];

  const entries = [];
  configs.forEach((config) => {
    document.querySelectorAll(config.selector).forEach((table) => {
      entries.push({ table, config });
    });
  });

  const panchangaPair = document.querySelector(".desktop-transit-panchanga-pair");
  const transitPanchangaTables = panchangaPair
    ? [...panchangaPair.querySelectorAll(".desktop-transit-panchanga-table")]
    : [];

  const clamp = (raw, min, max) => Math.min(Math.max(raw, min), max);

  const sizeTable = ({ table, config }) => {
    const scrollArea = table.closest(config.scroll);
    if (!scrollArea) return;
    const thead = table.querySelector("thead");
    const rows = table.querySelectorAll("tbody tr");
    if (!thead || !rows.length) return;

    const available = scrollArea.clientHeight - thead.offsetHeight;
    table.style.setProperty(config.variable, `${clamp(Math.floor(available / rows.length), config.min, config.max)}px`);
  };

  const sizeTransitPanchangaPair = () => {
    if (!transitPanchangaTables.length) return;
    let minAvailable = Infinity;
    transitPanchangaTables.forEach((table) => {
      const block = table.closest(".desktop-transit-panchanga-block");
      const thead = table.querySelector("thead");
      if (!block || !thead) return;
      minAvailable = Math.min(minAvailable, block.clientHeight - thead.offsetHeight);
    });
    if (!isFinite(minAvailable)) return;
    const height = clamp(Math.floor(minAvailable / 7), 26, 90);
    transitPanchangaTables.forEach((table) => {
      table.style.setProperty("--transit-row-height", `${height}px`);
    });
  };

  const updateAll = () => {
    entries.forEach(sizeTable);
    sizeTransitPanchangaPair();
  };

  const observeTargets = entries
    .map(({ table, config }) => table.closest(config.scroll))
    .filter(Boolean);
  if (panchangaPair) observeTargets.push(panchangaPair);

  if ("ResizeObserver" in window) {
    observeTargets.forEach((el) => new ResizeObserver(updateAll).observe(el));
  }
  window.addEventListener("resize", updateAll);
  updateAll();
}

function initGlobalNodeMode() {
  const globalNodeMode = document.getElementById("globalNodeMode");
  if (!globalNodeMode) return;
  globalNodeMode.addEventListener("change", () => {
    const value = globalNodeMode.value;
    const natalNode = document.getElementById("nodeMode");
    const transitNode = document.getElementById("transitNodeMode");
    if (natalNode) natalNode.value = value;
    if (transitNode) transitNode.value = value;
    try {
      document.cookie = `rohini_node_mode=${value}; path=/; max-age=31536000`;
    } catch (_error) { /* текуща сесия */ }
    persistUserSetting("node_mode", value);
  });
}
