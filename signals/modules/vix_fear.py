"""VIX fear-premium signal — elevated fear is a near-term headwind."""
from signals.base import Signal, SignalContext, FREE
from signals.registry import register


@register
class VixFearSignal(Signal):
    name = "vix_fear"
    description = "VIX fear premium / complacency"
    cost = FREE
    applies_to = ("all",)
    default_weight = 1.0

    def evaluate(self, ctx: SignalContext):
        vix = ctx.macro.get("vix", {})
        val = vix.get("value")
        if val is None:
            return self._result(available=False, narrative="VIX unavailable")

        if val > 35:
            impact = -1.5
        elif val > 25:
            impact = -0.8
        elif val < 13:
            impact = +0.6      # complacency can also signal froth, but mild bullish
        elif val < 16:
            impact = +0.3
        else:
            impact = 0.0

        # Crypto and high-beta react more strongly to fear
        if ctx.asset_class == "crypto":
            impact *= 1.4

        return self._result(
            impact=impact,
            confidence=0.7,
            narrative=f"VIX={val:.0f}",
            vix=val,
        )
