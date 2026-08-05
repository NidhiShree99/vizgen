import pandas as pd

OPERATORS = {
    "==": lambda s, v: s == v,
    "!=": lambda s, v: s != v,
    ">": lambda s, v: s > v,
    "<": lambda s, v: s < v,
    ">=": lambda s, v: s >= v,
    "<=": lambda s, v: s <= v,
    "contains": lambda s, v: s.astype(str).str.contains(
        str(v), case=False, na=False),
    "not_contains": lambda s, v: ~s.astype(str).str.contains(
        str(v), case=False, na=False),
    "in": lambda s, v: s.isin(v if isinstance(v, list) else [v]),
}


def apply_filters(df, filter_config):
    if not filter_config or filter_config.get("status") != "ok":
        return df

    conditions = filter_config.get("conditions", [])
    logic = filter_config.get("logic", "AND").upper()
    if not conditions:
        return df

    masks = []
    for cond in conditions:
        col = cond.get("column")
        op = cond.get("operator")
        val = cond.get("value")
        fn = OPERATORS.get(op)
        if col not in df.columns or fn is None:
            continue
        try:
            masks.append(fn(df[col], val))
        except Exception:
            continue

    if not masks:
        return df

    combined = masks[0]
    for m in masks[1:]:
        combined = (combined & m) if logic == "AND" else (combined | m)

    return df[combined]
