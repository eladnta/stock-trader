"""Macro regime signal — risk_on/risk_off/crisis adjustment."""
from signals.base import Signal, SignalContext, FREE
from signals.registry import register

REGIME_IMPACT = {
    "crisis": -2.0, "risk_off": -1.0, "late_cycle": -0.5,
    "neutral": 0.0, "risk_on": +0.5,
}
DEFENSIVE_SECTORS = {"Consumer Defensive", "Utilities", "Healthcare"}


@register
class MacroRegimeSignal(Signal):
    name = "macro_regime"
    description = "Market regime (risk_on/off/crisis) from VIX + yield curve"
    cost = FREE
    applies_to = ("all",)
    default_weight = 1.0

    def evaluate(self, ctx: SignalContext):
        regime = ctx.macro.get("regime", {}).get("regime", "neutral")
        impact = REGIME_IMPACT.get(regime, 0.0)

        # Defensive sectors are less exposed to risk-off swings
        if ctx.sector in DEFENSIVE_SECTORS:
            impact *= 0.4

        # Bonds and gold behave inversely in risk-off
        if ctx.asset_class in ("bond",) and impact < 0:
            impact = abs(impact) * 0.5   # flight to safety helps bonds

        return self._result(
            impact=impact,
            confidence=0.8 if regime != "neutral" else 0.3,
            narrative=f"regime={regime}",
            regime=regime,
        )
