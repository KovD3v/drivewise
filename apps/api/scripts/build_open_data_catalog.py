"""Fetch EEA and RDW open data into a run directory, then build catalog v2 bundles."""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from pydantic import ValidationError

from app.core.config import PROJECT_ROOT
from app.ingestion import open_data

DATA = PROJECT_ROOT / "data" / "open-data"
USER_AGENT = "open-data-catalog-builder/1 (python-urllib)"


def http_get(url: str, *, attempts: int = 4, pause: float = 1.0) -> bytes:
    """One request per second (the RDW robots file asks for it); retry what can heal."""
    for attempt in range(1, attempts + 1):
        time.sleep(pause)
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            if error.code < 500 and error.code != 429:
                raise
            failure = error
        except (urllib.error.URLError, TimeoutError) as error:
            failure = error
        if attempt == attempts:
            raise failure
        time.sleep(2**attempt)
    raise AssertionError("unreachable")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def _json(data) -> str:
    return json.dumps(data, indent=1, ensure_ascii=False) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["fetch", "build"])
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--names", type=Path, default=DATA / "car-names.it.json")
    parser.add_argument(
        "--two-wheelers", type=Path, default=DATA / "two-wheelers.it.json"
    )
    parser.add_argument(
        "--register-dir",
        type=Path,
        help="Also write the gap register here (the committed copy lives in docs/).",
    )
    args = parser.parse_args(argv)
    name_map = json.loads(args.names.read_text())
    two_wheelers = json.loads(args.two_wheelers.read_text())
    run = open_data.Run(args.run_dir)
    try:
        if args.command == "fetch":
            fetched = open_data.fetch(run, name_map, two_wheelers, http_get)
            print(f"Fetched {fetched} responses; the run holds {len(run.manifest)}.")
            return 0
        cars, car_report = open_data.build_cars(run, name_map)
        bikes, bike_report = open_data.build_two_wheelers(run, two_wheelers)
        register = open_data.gap_register(run, car_report, bike_report)
        outputs = {
            "cars.catalog-v2.json": cars,
            "two-wheelers.catalog-v2.json": bikes,
            "report.json": {"cars": car_report, "two_wheelers": bike_report},
        }
        for name, data in outputs.items():
            if data is not None:
                _write(args.run_dir / name, _json(data))
        for directory in filter(None, [args.run_dir, args.register_dir]):
            _write(directory / "open-data-gaps.json", _json(register))
            _write(
                directory / "open-data-gaps.md",
                open_data.gap_register_markdown(register),
            )
        for label, bundle in (("cars", cars), ("two-wheelers", bikes)):
            if bundle:
                print(
                    f"{label}: {len(bundle['vehicles'])} vehicles, "
                    f"{len(bundle['variants'])} variants, "
                    f"{len(bundle['observations'])} observations"
                )
        print(
            f"gaps: {len(register['gaps'])} per-model, "
            f"{len(register['dataset_gaps'])} for every model"
        )
        return 0
    except (open_data.OpenDataError, ValidationError, OSError, ValueError) as error:
        print(
            f"Open-data {args.command} failed: {type(error).__name__}: {error}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
