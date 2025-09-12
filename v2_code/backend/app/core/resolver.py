from typing import Optional, Dict, Any, Tuple, List

def resolve_range(test_record: Dict[str, Any], age: int, sex: str) -> Optional[Dict[str, Any]]:
    ranges = test_record.get("ranges", [])
    candidates: List[Tuple[bool, float, Dict[str, Any]]] = []
    for r in ranges:
        a = r.get("applies", {})
        sex_ok = a.get("sex", "any") in (sex, "any")
        age_min = a.get("age_min", float("-inf"))
        age_max = a.get("age_max", float("inf"))
        age_ok = (age >= age_min) and (age <= age_max)
        if sex_ok and age_ok:
            span = (age_max - age_min) if age_max != float("inf") and age_min != float("-inf") else 1e9
            candidates.append((a.get("sex", "any") == "any", span, r))
    if not candidates:
        return None
    candidates.sort(key=lambda t: (t[0], t[1]))  # exact sex before "any", then narrowest span
    return candidates[0][2]
