"""
Alternative-asset impact signal — maps moves in gold/oil/copper/crypto/bonds/
dollar to a SPECIFIC instrument via per-ticker (or per-sector) sensitivities.
"""
from signals.base import Signal, SignalContext, FREE
from signals.registry import register
from signals.stock_impact import TICKER_SENSITIVITIES, SECTOR_SENSITIVITIES


@register
class AlternativesImpactSignal(Signal):
    name = "alternatives_impact"
    description = "Per-stock sensitivity to gold/oil/copper/crypto/bonds/dollar"
    cost = FREE
    applies_to = ("all",)
    default_weight = 1.0

    def evaluate(self, ctx: SignalContext):
        alt = ctx.alternatives
        if not alt:
            return self._result(available=False, narrative="alternatives unavailable")

        sensitivities = TICKER_SENSITIVITIES.get(
            ctx.symbol, SECTOR_SENSITIVITIES.get(ctx.sector, {})
        )
        if not sensitivities:
            return self._result(impact=0.0, confidence=0.3,
                                narrative="no asset sensitivities mapped")

        total = 0.0
        details = {}
        for asset_key, sensitivity in sensitivities.items():
            asset = alt.get(asset_key, {})
            if not isinstance(asset, dict) or "change_1d_pct" not in asset:
                continue
            d1 = asset["change_1d_pct"] / 100
            impact = sensitivity * d1 * 20
            impact = max(-1.5, min(1.5, impact))
            total += impact
            if abs(impact) > 0.1:
                details[asset_key] = round(impact, 2)

        total = max(-2.0, min(2.0, total))
        narrative = (", ".join(f"{k}{v:+.1f}" for k, v in details.items())
                     if details else "neutral")
        return self._result(impact=total, confidence=0.6,
                            narrative=narrative, **details)
