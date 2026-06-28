"""News & event-tag signal — per-stock news sentiment and event classification."""
from signals.base import Signal, SignalContext, FREE
from signals.registry import register
from signals.stock_impact import EVENT_SECTOR_IMPACT


@register
class NewsEventsSignal(Signal):
    name = "news_events"
    description = "Per-stock news sentiment + event-type impact (earnings, M&A, regulatory...)"
    cost = FREE
    applies_to = ("equity",)   # news mainly meaningful for single stocks
    default_weight = 1.0

    def evaluate(self, ctx: SignalContext):
        news = ctx.news
        if not news:
            return self._result(available=False, narrative="news unavailable")

        impact = 0.0
        event_details = {}

        # Event-tag impacts (sector-aware)
        for tag in news.get("event_tags", []):
            tag_impact = EVENT_SECTOR_IMPACT.get(tag, {})
            val = tag_impact.get(ctx.sector, tag_impact.get("all", 0))
            impact += val
            if val:
                event_details[tag] = val

        # Raw news sentiment score (5 = neutral)
        news_score = news.get("news_score", 5)
        impact += (news_score - 5) * 0.3

        impact = max(-2.5, min(2.5, impact))

        # Confidence scales with how many articles backed it
        n_articles = news.get("article_count", 0)
        confidence = min(0.9, 0.3 + n_articles * 0.06)

        tags = list(event_details.keys())
        narrative = (f"score={news_score}, " + ", ".join(t.replace("_", " ") for t in tags[:3])
                     if tags else f"score={news_score}")

        return self._result(impact=impact, confidence=confidence,
                            narrative=narrative, news_score=news_score,
                            events=event_details)
