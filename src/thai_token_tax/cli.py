"""The `ttt` command. Run it from the repository root.

    ttt prepare                          download FLORES-200, normalize, check alignment
    ttt count   [--source S] [--out DIR] count tokens for the models in registry/models.toml
    ttt verify  [--source S] [--dir DIR] [--date D]   recount / check in a second way
    ttt analyze [--dir DIR] [--date D] [--label L]    merge sources: premium, CI, tokens per 1,000 chars
    ttt all     [--out DIR]              prepare -> count -> verify -> analyze
    ttt prices  [--out DIR]              fetch official list prices and the Bank of Thailand rate
    ttt cost    [--dir DIR] [--label L]  measured tokens x price x rate -> baht per scenario
    ttt compare                          FLORES-200 vs FLORES+ (counts in results/floresplus/)
    ttt billing-check [--dry-run]        SPENDS MONEY (a few cents): count_tokens vs billed usage on Claude
    ttt site                             write site/data.json, the only file the web page reads
    ttt docs                             write the README files, methodology, articles and post drafts
                                         from templates/
    ttt card    [--png]                  write the share cards site/card.<lang>.svg (--png: also PNG, needs
                                         an installed Chrome or Edge)

Sources: open (local tokenizers), openai, gemini, anthropic. The API sources read their
key from OPENAI_API_KEY, GEMINI_API_KEY, ANTHROPIC_API_KEY; gated Hugging Face repos need HF_TOKEN.
Result files are never overwritten. To run a source twice on one UTC day, pass --out with a new folder.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import Stop, analyze, billing, card, compare, counters, data, docs, pricing, site, verify


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ttt", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)
    p_prepare = sub.add_parser("prepare")
    p_prepare.add_argument("--dataset", choices=list(data.SOURCE_FILE), default=data.DATASET)
    p_count = sub.add_parser("count")
    p_count.add_argument("--source", choices=counters.SOURCES, action="append", help="default: all")
    p_count.add_argument("--out", type=Path, default=Path("results"))
    p_count.add_argument("--model", action="append", help="only this registry model id (needs --label)")
    p_count.add_argument("--label", help="name of an add-on result set, e.g. llama31")
    p_count.add_argument("--dataset", choices=list(data.SOURCE_FILE), default=data.DATASET)
    for name in ("all", "prices"):
        sub.add_parser(name).add_argument("--out", type=Path, default=Path("results"))
    sub.add_parser("compare")
    sub.add_parser("site")
    sub.add_parser("docs")
    sub.add_parser("card").add_argument("--png", action="store_true", help="also render PNG files")
    p_bill = sub.add_parser("billing-check")
    p_bill.add_argument(
        "--dry-run", action="store_true", help="print the expected cost, send nothing billable"
    )
    p_cost = sub.add_parser("cost")
    p_cost.add_argument("--dir", type=Path, default=Path("results"))
    p_cost.add_argument("--label", help="suffix for the costs name, if one exists already")
    for name in ("verify", "analyze"):
        p = sub.add_parser(name)
        p.add_argument("--dir", type=Path, default=Path("results"))
        p.add_argument("--date", help="run date, YYYY-MM-DD (default: the newest in --dir)")
    sub.choices["verify"].add_argument(
        "--source", action="append", help="exact result-set name, e.g. open or open-llama31"
    )
    sub.choices["analyze"].add_argument("--label", help="suffix for the summary name, if one exists already")
    args = parser.parse_args(argv)

    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to a legacy code page
    root = Path.cwd()
    try:
        if not (root / "registry" / "models.toml").exists():
            raise Stop("run `ttt` from the repository root (registry/models.toml not found here)")
        baseline, targets = data.load_languages(root / "registry" / "languages.toml")
        if args.command == "prepare":
            if args.dataset == "floresplus":
                data.prepare_floresplus(root)
            else:
                data.prepare(root)
        elif args.command == "count":
            counters.run(root, args.out, args.source or counters.SOURCES, only=args.model, label=args.label,
                         dataset=args.dataset)
        elif args.command == "verify":
            for counts_csv in analyze.find_counts(args.dir, args.date):
                if not args.source or analyze.COUNTS_NAME.search(counts_csv.name)[2] in args.source:
                    verify.run(root, counts_csv)
        elif args.command == "analyze":
            analyze.run(analyze.find_counts(args.dir, args.date), baseline, targets, args.dir, args.label)
        elif args.command == "prices":
            pricing.fetch_prices(root, args.out)
        elif args.command == "billing-check":
            billing.run(root, Path("results"), dry_run=args.dry_run)
        elif args.command == "site":
            site.run(root, Path("results"))
        elif args.command == "docs":
            docs.run(root, Path("results"))
        elif args.command == "card":
            card.run(root, png=args.png)
        elif args.command == "compare":
            compare.run(Path("results"), baseline, targets[0])
        elif args.command == "cost":
            pricing.run(root, args.dir, args.label)
        elif args.command == "all":
            data.prepare(root)
            written = counters.run(root, args.out)
            for counts_csv in written:
                verify.run(root, counts_csv)
            analyze.run(written, baseline, targets, args.out)
    except Stop as e:
        print(f"STOP: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
