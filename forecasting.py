import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

MIN_POINTS = 4


def _linear_forecast(y, periods):
    x = np.arange(len(y))
    slope, intercept = np.polyfit(x, y, 1)
    future_x = np.arange(len(y), len(y) + periods)
    return slope * future_x + intercept


def generate_forecast(df, time_col, value_col, periods=3):
    """
    Aggregate value_col by time_col, fit a simple trend model, and
    forecast `periods` steps ahead. Returns a dict with the actual
    series, forecast series, and whether real dates were used.

    Returns {"status": "error", "message": ...} if there isn't
    enough data to forecast meaningfully.
    """
    working = df[[time_col, value_col]].dropna()
    if working.empty:
        return {"status": "error",
                "message": "No usable data in the selected columns."}

    grouped = working.groupby(time_col, as_index=False)[value_col].sum()

    parsed_dates = pd.to_datetime(grouped[time_col], errors="coerce")
    used_real_dates = parsed_dates.notna().all()

    if used_real_dates:
        grouped = grouped.assign(_t=parsed_dates).sort_values("_t")
        labels = grouped["_t"].dt.strftime("%Y-%m-%d").tolist()
    else:
        grouped = grouped.reset_index(drop=True)
        labels = [str(v) for v in grouped[time_col].tolist()]

    y = grouped[value_col].astype(float).values

    if len(y) < MIN_POINTS:
        return {"status": "error",
                "message": (
                    f"Need at least {MIN_POINTS} time points to "
                    f"forecast — found {len(y)}."
                )}

    try:
        model = ExponentialSmoothing(y, trend="add", seasonal=None)
        fit = model.fit()
        forecast_values = fit.forecast(periods)
    except Exception:
        forecast_values = _linear_forecast(y, periods)

    if used_real_dates:
        last_date = grouped["_t"].iloc[-1]
        freq = pd.infer_freq(grouped["_t"]) or "MS"
        future_dates = pd.date_range(
            last_date, periods=periods + 1, freq=freq)[1:]
        forecast_labels = future_dates.strftime("%Y-%m-%d").tolist()
    else:
        forecast_labels = [
            f"Forecast {i + 1}" for i in range(periods)]

    return {
        "status": "ok",
        "actual_labels": labels,
        "actual_values": y.tolist(),
        "forecast_labels": forecast_labels,
        "forecast_values": [float(v) for v in forecast_values],
        "used_real_dates": used_real_dates,
    }
