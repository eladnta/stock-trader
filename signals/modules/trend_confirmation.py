"""
Trend-confirmation signal — a free, price-only momentum confirmation.

Example of how easy it is to add a new signal: this whole file is a new,
independently-weighted input to the system. It rewards instruments trading
above their moving averages with positive 3-month momentum, and penalizes
those breaking down — applied across ALL asset classes.
"""
import pandas as pd
from signals.base import Signal, SignalContext, FREE
from signals.registry import register


@register
class TrendConfirmationSignal(Signal):
    name = "trend_confirmation"
    description = "Price-based trend/momentum confirmation (MA50/MA200 + 3M momentum)"
    cost = FREE
    applies_to = ("all",)
    default_weight = 0.8

    def evaluate(self, ctx: SignalContext):
        hist = ctx.history
        if hist is None or getattr(hist, "empty", True):
            return self._result(available=False, narrative="no price history")

        try:
            close = hist["Close"].dropna().astype(float)
        except Exception:
            return self._result(available=False, narrative="no close prices")

        if len(close) < 50:
            return self._result(available=False, narrative="insufficient history")

        price = float(close.iloc[-1])
        ma50 = float(close.tail(50).mean())
        ma200 = float(close.tail(200).mean()) if len(close) >= 200 else float(close.mean())

        mom_3m = 0.0
        if len(close) >= 63:
            mom_3m = (price - float(close.iloc[-63])) / float(close.iloc[-63])

        impact = 0.0
        if price > ma50 > ma200:
            impact += 1.0          # confirmed uptrend
        elif price < ma50 < ma200:
            impact -= 1.0          # confirmed downtrend
        impact += max(-1.0, min(1.0, mom_3m * 6))

        impact = max(-1.5, min(1.5, impact))
        trend = ("uptrend" if price > ma200 else "downtrend")

        return self._result(
            impact=impact, confidence=0.7,
            narrative=f"{trend}, 3M {mom_3m*100:+.0f}%",
            trend=trend, mom_3m=round(mom_3m, 3),
        )
