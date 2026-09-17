"""Plan, run or resume a bounded manufacturer-document collection job."""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pydantic import ValidationError  # noqa: E402

from app.core.config import PROJECT_ROOT, load_env_file  # noqa: E402
from app.ingestion.scraping import Collector, RunPaused  # noqa: E402
from app.ingestion.scraping_contract import ScrapingConfig  # noqa: E402
from app.ingestion.scraping_providers import (  # noqa: E402
    Firecrawl,
    OpenRouter,
    ProviderError,
    Tinyfish,
    TinyfishFetch,
)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--env-file", type=Path, default=PROJECT_ROOT / ".env")
    parser.add_argument(
        "--provider",
        choices=("tinyfish", "firecrawl"),
        default="tinyfish",
        help="Document acquisition provider (default: Tinyfish Search/Fetch)",
    )
    parser.add_argument(
        "--tinyfish-agent",
        "--tinyfish",
        dest="tinyfish_agent",
        action="store_true",
        help="Enable optional paid Tinyfish Agent navigation",
    )
    parser.add_argument(
        "--model", help="OpenRouter model ID; overrides OPENROUTER_MODEL"
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--run",
        action="store_true",
        help="Make provider requests; resume automatically",
    )
    mode.add_argument(
        "--status",
        action="store_true",
        help="Read saved progress without network access",
    )
    args = parser.parse_args(argv)
    if (args.run or args.status) and not args.run_dir:
        parser.error("--run-dir is required for --run/--status")
    try:
        config = ScrapingConfig.model_validate_json(args.config.read_text())
        if args.status:
            state = json.loads((args.run_dir / "state.json").read_text())
            print(
                json.dumps(
                    {
                        "provider": state.get("provider", "firecrawl"),
                        **{
                            key: state[key]
                            for key in (
                                "phase",
                                "model_calls",
                                "browser_calls",
                                "gaps",
                                "failures",
                            )
                        },
                    },
                    indent=2,
                )
            )
            return 0
        if not args.run:
            print(config.model_dump_json(indent=2))
            print(f"Document provider: {args.provider}.")
            if args.tinyfish_agent:
                print("Paid Tinyfish Agent navigation enabled for this plan.")
            print("Plan only. Add --run and --run-dir to start collection.")
            return 0
        load_env_file(
            args.env_file,
            frozenset(
                {
                    "OPENROUTER_API_KEY",
                    "OPENROUTER_MODEL",
                    "FIRECRAWL_API_KEY",
                    "TINYFISH_API_KEY",
                }
            ),
        )
        model = args.model or os.getenv("OPENROUTER_MODEL", "")
        router_key = os.getenv("OPENROUTER_API_KEY")
        browser_key_name = (
            "TINYFISH_API_KEY" if args.provider == "tinyfish" else "FIRECRAWL_API_KEY"
        )
        browser_key = os.getenv(browser_key_name)
        tinyfish_key = os.getenv("TINYFISH_API_KEY")
        required = {
            "OPENROUTER_API_KEY": router_key,
            "OPENROUTER_MODEL": model,
            browser_key_name: browser_key,
        }
        if args.tinyfish_agent:
            required["TINYFISH_API_KEY"] = tinyfish_key
        missing = [key for key, value in required.items() if not value]
        if missing:
            print(
                "Configure " + ", ".join(missing) + " before --run.",
                file=sys.stderr,
            )
            return 1
        report = Collector(
            config,
            args.run_dir,
            OpenRouter(router_key, model),
            TinyfishFetch(browser_key)
            if args.provider == "tinyfish"
            else Firecrawl(browser_key),
            Tinyfish(tinyfish_key) if args.tinyfish_agent else None,
        ).run()
        print(json.dumps(report, indent=2))
        return 0
    except ValidationError as error:
        locations = [
            ".".join(map(str, item["loc"]))
            for item in error.errors(include_input=False)
        ]
        print("Invalid collection config: " + ", ".join(locations), file=sys.stderr)
    except RunPaused as error:
        print(str(error), file=sys.stderr)
        return 2
    except (ProviderError, ValueError) as error:
        print(
            str(error)
            if isinstance(error, ProviderError)
            else "Invalid config or saved state; inspect local artifacts.",
            file=sys.stderr,
        )
    except OSError:
        print("Cannot read/write collection files.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
