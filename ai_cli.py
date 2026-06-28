#!/usr/bin/env python3
"""
AI layer CLI — inspect providers, test a completion, view spend.

  python ai_cli.py providers          # list providers + availability
  python ai_cli.py test "prompt"      # run on default (or --provider X)
  python ai_cli.py cost               # show accumulated token spend
"""
import sys, os, argparse
sys.path.insert(0, os.path.dirname(__file__))

from rich.console import Console
from rich.table import Table
from rich import box

import ai

console = Console()


def cmd_providers(args):
    t = Table(title="AI Providers", box=box.ROUNDED)
    t.add_column("Provider", style="cyan")
    t.add_column("Tier")
    t.add_column("Default model")
    t.add_column("Available", justify="center")
    t.add_column("Description")
    for r in ai.registry_summary():
        tier_color = "green" if r["cost_tier"] == "local" else "yellow"
        avail = "[green]✓[/]" if r["available"] else "[dim]✗ (no key/SDK)[/]"
        t.add_row(r["name"], f"[{tier_color}]{r['cost_tier']}[/]",
                  r["default_model"], avail, r["description"])
    console.print(t)
    active = ai.get_provider()
    console.print(f"\n  Active default: [bold]{active.name if active else 'none configured'}[/]")
    console.print("[dim]Set AI_PROVIDER, or a provider's API key, to enable. "
                  "Run a local model with Ollama for zero-cost use.[/]")


def cmd_test(args):
    console.print(f"[dim]Provider: {args.provider or 'default'}[/]")
    resp = ai.complete(args.prompt, provider=args.provider)
    if not resp.ok:
        console.print(f"[red]{resp.error}[/]")
        return
    console.print(f"[bold]{resp.provider} / {resp.model}[/]")
    console.print(resp.text)
    console.print(f"\n[dim]tokens in/out: {resp.input_tokens}/{resp.output_tokens}  "
                  f"cost: ${resp.cost_usd:.6f}[/]")


def cmd_cost(args):
    log = ai.cost_summary()
    console.print(f"[bold]Total AI spend:[/] ${log.get('total_usd', 0):.6f}  "
                  f"({log.get('calls', 0)} calls)")
    for prov, d in log.get("by_provider", {}).items():
        console.print(f"  {prov}: ${d['usd']:.6f}  ({d['calls']} calls, "
                      f"{d['input_tokens']}+{d['output_tokens']} tokens)")


def main():
    parser = argparse.ArgumentParser(description="AI layer CLI")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("providers", help="List providers + availability")
    p_test = sub.add_parser("test", help="Run a completion")
    p_test.add_argument("prompt")
    p_test.add_argument("--provider", default=None)
    sub.add_parser("cost", help="Show accumulated spend")

    args = parser.parse_args()
    dispatch = {"providers": cmd_providers, "test": cmd_test, "cost": cmd_cost}
    fn = dispatch.get(args.command)
    if fn:
        fn(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
