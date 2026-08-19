from pulp import LpProblem, LpMaximize, LpVariable, lpSum, LpStatus

MAX_SHARE_PER_CATEGORY = 0.5


def optimize_budget_allocation(df, category_col, value_col, total_budget):
    """
    Allocate total_budget across the categories in category_col to
    maximize total weighted return, using each category's historical
    average of value_col (normalized to a 0-1 relative performance
    score) as a proxy for its expected return per dollar. No single
    category may take more than MAX_SHARE_PER_CATEGORY of the
    budget, so the optimizer has to genuinely trade off between
    categories rather than dumping everything into the single
    best-performing one.
    """
    if total_budget is None or total_budget <= 0:
        return {"status": "error",
                "message": "Budget must be a positive number."}

    grouped = df.groupby(category_col)[value_col].mean()
    categories = grouped.index.tolist()
    raw_weights = grouped.to_dict()

    if len(categories) < 2:
        return {"status": "error",
                "message": (
                    "Need at least 2 categories in "
                    f"'{category_col}' to optimize an allocation "
                    "across."
                )}

    max_weight = max(raw_weights.values()) or 1
    scores = {
        cat: raw_weights[cat] / max_weight for cat in categories}

    max_per_category = total_budget * MAX_SHARE_PER_CATEGORY

    prob = LpProblem("BudgetAllocation", LpMaximize)
    x = {
        cat: LpVariable(f"alloc_{i}", lowBound=0, upBound=max_per_category)
        for i, cat in enumerate(categories)
    }

    prob += lpSum(scores[cat] * x[cat] for cat in categories)
    prob += lpSum(x[cat] for cat in categories) == total_budget

    prob.solve()

    if LpStatus[prob.status] != "Optimal":
        return {"status": "error",
                "message": (
                    "Could not find a feasible allocation — try a "
                    "different budget."
                )}

    allocations = [
        {
            "category": str(cat),
            "amount": round(x[cat].value(), 2),
            "avg_performance": round(raw_weights[cat], 2),
            "priority_score": round(scores[cat], 3),
        }
        for cat in categories
    ]
    allocations.sort(key=lambda a: a["amount"], reverse=True)

    return {
        "status": "ok",
        "allocations": allocations,
        "total_budget": total_budget,
        "category_column": category_col,
        "value_column": value_col,
    }
