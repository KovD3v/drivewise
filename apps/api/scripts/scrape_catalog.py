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
)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--env-file", type=Path, default=PROJECT_ROOT / ".env")
    parser.add_argument(
        "--tinyfish",
        action="store_true",
        help="Enable optional Tinyfish document navigation",
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
                        key: state[key]
                        for key in (
                            "phase",
                            "model_calls",
                            "browser_calls",
                            "gaps",
                            "failures",
                        )
                    },
                    indent=2,
                )
            )
            return 0
        if not args.run:
            print(config.model_dump_json(indent=2))
            if args.tinyfish:
                print("Tinyfish document navigation enabled for this plan.")
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
        router_key, browser_key = (
            os.getenv("OPENROUTER_API_KEY"),
            os.getenv("FIRECRAWL_API_KEY"),
        )
        tinyfish_key = os.getenv("TINYFISH_API_KEY")
        if (
            not model
            or not router_key
            or not browser_key
            or (args.tinyfish and not tinyfish_key)
        ):
            print(
                "Configure OPENROUTER_API_KEY, OPENROUTER_MODEL and FIRECRAWL_API_KEY"
                + (", plus TINYFISH_API_KEY for --tinyfish" if args.tinyfish else "")
                + " before --run.",
                file=sys.stderr,
            )
            return 1
        report = Collector(
            config,
            args.run_dir,
            OpenRouter(router_key, model),
            Firecrawl(browser_key),
            Tinyfish(tinyfish_key) if args.tinyfish else None,
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
