"""Fetch EEA and RDW open data into a run directory, then build catalog v2 bundles."""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import ValidationError

from app.core.config import PROJECT_ROOT
from app.ingestion import open_data

DATA = PROJECT_ROOT / "data" / "open-data"
USER_AGENT = "open-data-catalog-builder/1 (python-urllib)"
CARS, TWO_WHEELERS = "cars.catalog-v2.json", "two-wheelers.catalog-v2.json"
# Only the registries the builder asks, over HTTPS, may answer or redirect.
ALLOWED_HOSTS = frozenset(
    urlsplit(url).hostname
    for url in (open_data.EEA_URL, open_data.RDW_URL, open_data.MOTOSPECDB_URL)
)
# The largest response kept; the MotoSpecDB dataset, the biggest, is far below it.
MAX_RESPONSE_BYTES = 50 * 1024 * 1024
CHUNK_BYTES = 1024 * 1024


class UnsafeResponse(open_data.OpenDataError):
    """A response that must not become evidence; retrying cannot heal it."""


def check_url(url: str) -> str:
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname not in ALLOWED_HOSTS:
        raise UnsafeResponse(
            f"Refused a request outside the approved registries: {url}"
        )
    return url


class ApprovedRedirects(urllib.request.HTTPRedirectHandler):
    """Follow a redirect only over HTTPS to an approved registry host."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        check_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _opener() -> urllib.request.OpenerDirector:
    return urllib.request.build_opener(ApprovedRedirects())


def read_capped(response, limit: int | None = None) -> bytes:
    """The whole body, refused as soon as it passes the limit."""
    limit = MAX_RESPONSE_BYTES if limit is None else limit
    declared = response.headers.get("Content-Length") if response.headers else None
    if declared and declared.isdigit() and int(declared) > limit:
        raise UnsafeResponse(
            f"Response declares {declared} bytes; the limit is {limit}."
        )
    chunks, size = [], 0
    while chunk := response.read(CHUNK_BYTES):
        size += len(chunk)
        if size > limit:
            raise UnsafeResponse(f"Response exceeds {limit} bytes.")
        chunks.append(chunk)
    return b"".join(chunks)


def http_get(url: str, *, attempts: int = 4, pause: float = 1.0) -> bytes:
    """One request per second (the RDW robots file asks for it); retry what can heal."""
    check_url(url)
    opener = _opener()
    for attempt in range(1, attempts + 1):
        time.sleep(pause)
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with opener.open(request, timeout=90) as response:
                check_url(response.geturl())
                return read_capped(response)
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
    """Replace the file whole: readers see the old file or the new one, never half."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(text)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _previous_bundles(previous: Path, artifact_root: Path) -> dict:
    """The published bundles of the previous run; refused when there are none."""
    if not previous.is_dir():
        raise open_data.OpenDataError(
            f"--previous {previous} is not a run folder; the history would be lost."
        )
    if previous.resolve().parent != artifact_root:
        raise open_data.OpenDataError(
            "Keep the previous run next to the new one: evidence paths are "
            "relative to their common folder."
        )
    earlier = {
        name: json.loads((previous / name).read_text())
        for name in (CARS, TWO_WHEELERS)
        if (previous / name).is_file()
    }
    if not earlier:
        raise open_data.OpenDataError(
            f"--previous {previous} holds no {CARS} or {TWO_WHEELERS}; refusing to "
            "build without the published history."
        )
    return {CARS: None, TWO_WHEELERS: None} | earlier


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
    parser.add_argument(
        "--previous",
        type=Path,
        help="The run directory whose bundles are already published. The new bundles "
        "then keep its vehicles, variants and history, and add only what changed.",
    )
    args = parser.parse_args(argv)
    if args.previous and args.previous.resolve() == args.run_dir.resolve():
        # Building into the published run would rewrite its bundles and report.
        print(
            "Open-data build failed: --previous and --run-dir are the same run folder; "
            "fetch into a new run folder.",
            file=sys.stderr,
        )
        return 1
    name_map = json.loads(args.names.read_text())
    two_wheelers = json.loads(args.two_wheelers.read_text())
    run = open_data.Run(args.run_dir)
    try:
        if args.command == "fetch":
            fetched = open_data.fetch(run, name_map, two_wheelers, http_get)
            print(f"Fetched {fetched} responses; the run holds {len(run.manifest)}.")
            return 0
        earlier = {CARS: None, TWO_WHEELERS: None}
        if args.previous:
            earlier = _previous_bundles(args.previous, run.artifact_root)
        # The previous bundles go in first: a copied response keeps its snapshot.
        cars, car_report = open_data.build_cars(run, name_map, earlier[CARS])
        bikes, bike_report = open_data.build_two_wheelers(
            run, two_wheelers, earlier[TWO_WHEELERS]
        )
        report = {"cars": car_report, "two_wheelers": bike_report}
        if args.previous:
            report["update"] = {}
            for label, name in (("cars", CARS), ("two_wheelers", TWO_WHEELERS)):
                if earlier[name] is None:
                    continue
                fresh, fresh_report = (
                    (cars, car_report) if label == "cars" else (bikes, bike_report)
                )
                merged, update = open_data.continue_bundle(
                    earlier[name], fresh, fresh_report
                )
                report["update"][label] = update
                if label == "cars":
                    cars = merged
                else:
                    bikes = merged
                print(
                    f"{label} update: {len(update['revised'])} values revised, "
                    f"{update['unchanged']} unchanged, "
                    f"{len(update['new_variants'])} new variants, "
                    f"{len(update['identity_differs'])} identities differ, "
                    f"{len(update['identity_review'])} additions held for review"
                )
        # Coverage describes the bundles written, so after --previous the merged ones.
        covered = {
            "cars": open_data.coverage(cars),
            "two_wheelers": open_data.coverage(bikes),
        }
        register = open_data.gap_register(run, car_report, bike_report, covered)
        # Everything is serialised before the first file is replaced.
        texts = {
            args.run_dir / name: _json(data)
            for name, data in {
                CARS: cars,
                TWO_WHEELERS: bikes,
                "report.json": report,
            }.items()
            if data is not None
        }
        markdown = open_data.gap_register_markdown(register)
        for directory in filter(None, [args.run_dir, args.register_dir]):
            texts[directory / "open-data-gaps.json"] = _json(register)
            texts[directory / "open-data-gaps.md"] = markdown
        for path, text in texts.items():
            _write(path, text)
        for name, bundle in ((CARS, cars), (TWO_WHEELERS, bikes)):
            if bundle is None:
                # A bundle from an earlier build of this folder no longer matches it.
                (args.run_dir / name).unlink(missing_ok=True)
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
        print(f"artifact root for the import: {run.artifact_root}")
        return 0
    except (open_data.OpenDataError, ValidationError, OSError, ValueError) as error:
        print(
            f"Open-data {args.command} failed: {type(error).__name__}: {error}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
