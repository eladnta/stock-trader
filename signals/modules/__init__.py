"""
Signal modules — auto-discovered by the registry.

Importing this package registers every signal. To add a new signal,
drop a new file here that subclasses Signal and uses @register, then
add it to the import list below.
"""
from signals.modules import macro_regime      # noqa: F401
from signals.modules import vix_fear          # noqa: F401
from signals.modules import alternatives_impact  # noqa: F401
from signals.modules import news_events       # noqa: F401
from signals.modules import trend_confirmation  # noqa: F401
from signals.modules import llm_thesis          # noqa: F401  (LLM tier — off by default)
