"""Heuristics for classifying cards and extracting structured fields."""
from __future__ import annotations

import re
from typing import Dict, List, Tuple

from image_search_app.classes.card import Card


def _as_lines(text_val) -> List[str]:
    if text_val is None:
        return []
    if isinstance(text_val, list):
        return [ln.strip() for ln in text_val if isinstance(ln, str) and ln.strip()]
    return [ln.strip() for ln in str(text_val).splitlines() if ln.strip()]


def _is_meta(line: str) -> bool:
    if not line:
        return True
    if "©" in line or ".psd" in line.lower():
        return True
    if re.match(r"^[vV]\d+", line):
        return True
    if re.match(r"^\d+/\d+", line):
        return True
    if line in {"EN", "SYS", "HMW"}:
        return True
    return False


def _extract_ints(lines: List[str]) -> List[int]:
    nums: List[int] = []
    for ln in lines:
        m = re.match(r"^[+−-]?\d+$", ln.replace("−", "-"))
        if m:
            nums.append(int(m.group(0)))
    return nums


def _split_traits(line: str) -> List[str]:
    parts = [p.strip() for p in re.split(r"[•\u2022]", line) if p.strip()]
    # Split all-caps with separators like "FORCE PILOT" into individual tokens.
    if not parts and line.isupper():
        parts = line.split()
    return parts


def _pick_name_and_sub(lines: List[str]) -> Tuple[str, str]:
    filtered = [ln for ln in lines if not _is_meta(ln) and not _extract_ints([ln])]
    if not filtered:
        return "", ""
    name = filtered[-1]
    sub = filtered[-2] if len(filtered) > 1 and filtered[-2].isupper() else ""
    return name, sub


def detect_type(card: Card) -> str:
    lines = _as_lines(card.text)
    lowered = [ln.lower() for ln in lines]
    if any("leader unit" in ln for ln in lowered) or any("leader" == ln for ln in lowered):
        return "Leader"
    if any("upgrade" in ln for ln in lowered) or any("fortification" in ln for ln in lowered):
        return "Upgrade"
    if any("event" in ln for ln in lowered):
        return "Event"
    if any("base" == ln for ln in lowered):
        return "Base"
    if any("unit" in ln for ln in lowered):
        return "Unit"
    return card.type or "Card"


def _parse_unit(card: Card, lines: List[str]) -> Dict[str, object]:
    arena = next((ln for ln in lines if ln.upper() in {"GROUND", "SPACE"}), "")
    nums = _extract_ints(lines)
    cost = nums[0] if len(nums) > 0 else None
    health = nums[1] if len(nums) > 1 else None
    power = nums[2] if len(nums) > 2 else None

    traits: List[str] = []
    for ln in lines:
        if "•" in ln or ln.isupper():
            traits.extend(_split_traits(ln))
    traits = [t for t in traits if t and t.upper() not in {"UNIT", "GROUND", "SPACE"}]

    name, sub = _pick_name_and_sub(lines)

    ban = {"GROUND", "SPACE", "UNIT"}
    effect_lines = [
        ln
        for ln in lines
        if ln not in ban
        and not _is_meta(ln)
        and ln not in traits
        and ln not in {name, sub}
        and ln not in [str(cost or ""), str(health or ""), str(power or "")]
    ]
    effect_text = " ".join(effect_lines).strip()

    return {
        "name": name,
        "subname": sub,
        "arena": arena,
        "traits": traits or [],
        "cost": cost,
        "health": health,
        "power": power,
        "effect_text": effect_text,
    }


def _parse_upgrade(card: Card, lines: List[str]) -> Dict[str, object]:
    nums = _extract_ints(lines)
    cost = nums[0] if nums else None
    traits: List[str] = []
    for ln in lines:
        if "•" in ln or ln.isupper():
            traits.extend(_split_traits(ln))
    traits = [t for t in traits if t and t.upper() not in {"UPGRADE"}]

    name, sub = _pick_name_and_sub(lines)
    effect_lines = [
        ln
        for ln in lines
        if not _is_meta(ln)
        and ln not in traits
        and ln not in {name, sub}
        and ln.upper() != "UPGRADE"
        and not re.match(r"^[+−-]?\d+$", ln.replace("−", "-"))
    ]
    effect_text = " ".join(effect_lines).strip()
    return {
        "name": name,
        "subname": sub,
        "traits": traits or [],
        "cost": cost,
        "effect_text": effect_text,
    }


def _parse_event(card: Card, lines: List[str]) -> Dict[str, object]:
    nums = _extract_ints(lines)
    cost = nums[0] if nums else None
    traits: List[str] = []
    for ln in lines:
        if "•" in ln or ln.isupper():
            traits.extend(_split_traits(ln))
    traits = [t for t in traits if t and t.upper() not in {"EVENT"}]
    name, _ = _pick_name_and_sub(lines)
    effect_lines = [
        ln
        for ln in lines
        if not _is_meta(ln)
        and ln not in traits
        and ln.upper() != "EVENT"
        and ln != name
        and not re.match(r"^[+−-]?\d+$", ln.replace("−", "-"))
    ]
    effect_text = " ".join(effect_lines).strip()
    return {
        "name": name,
        "traits": traits or [],
        "cost": cost,
        "effect_text": effect_text,
    }


def _parse_base(card: Card, lines: List[str]) -> Dict[str, object]:
    nums = _extract_ints(lines)
    health = nums[0] if nums else None
    traits: List[str] = []
    for ln in lines:
        if ln.isupper() and ln not in {"BASE"}:
            traits.extend(ln.split())
    name, _ = _pick_name_and_sub(lines)
    effect_lines = [
        ln
        for ln in lines
        if not _is_meta(ln) and ln.upper() != "BASE" and ln not in traits and ln != name and not re.match(r"^[+−-]?\d+$", ln.replace("−", "-"))
    ]
    effect_text = " ".join(effect_lines).strip()
    return {
        "name": name,
        "traits": traits or [],
        "health": health,
        "effect_text": effect_text,
    }


def _parse_leader(card: Card, lines: List[str]) -> Dict[str, object]:
    nums = _extract_ints(lines)
    cost = nums[0] if nums else None
    health = nums[1] if len(nums) > 1 else None
    power = nums[2] if len(nums) > 2 else None

    traits: List[str] = []
    for ln in lines:
        if "•" in ln or ln.isupper():
            traits.extend(_split_traits(ln))
    traits = [t for t in traits if t and t.upper() not in {"LEADER", "LEADER UNIT"}]

    name, sub = _pick_name_and_sub(lines)
    effect_lines = [
        ln
        for ln in lines
        if not _is_meta(ln)
        and ln.upper() not in {"LEADER", "LEADER UNIT"}
        and ln not in traits
        and ln not in {name, sub}
        and not re.match(r"^[+−-]?\d+$", ln.replace("−", "-"))
    ]
    effect_text = " ".join(effect_lines).strip()

    return {
        "name": name,
        "subname": sub,
        "traits": traits or [],
        "cost": cost,
        "health": health,
        "power": power,
        "effect_text": effect_text,
    }


def classify_card(card: Card) -> Dict[str, object]:
    """
    Inspect the card text and return a structured dict keyed by type.

    Falls back to generic Card dict if no mapping is found.
    """
    lines = _as_lines(card.text)
    detected = detect_type(card)
    base = {
        "file_path": card.file_path,
        "size_bytes": card.size_bytes,
        "modified_ts": card.modified_ts,
        "type": detected,
    }

    if detected == "Unit":
        base.update(_parse_unit(card, lines))
        return {"unit": base}
    if detected == "Upgrade":
        base.update(_parse_upgrade(card, lines))
        return {"upgrade": base}
    if detected == "Event":
        base.update(_parse_event(card, lines))
        return {"event": base}
    if detected == "Base":
        base.update(_parse_base(card, lines))
        return {"base": base}
    if detected == "Leader":
        base.update(_parse_leader(card, lines))
        return {"leader": base}

    # Generic fallback
    base.update({"text": lines})
    return {"card": base}
