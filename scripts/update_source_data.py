"""Dikembangkan oleh Ikhwan Arief (ikhwan[at]unand.ac.id)
Lisensi aplikasi: Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
BUILD_DIR = ROOT / "build"
BACKUP_ROOT = BUILD_DIR / "dataset-backups"

SCIMAGO_TARGET = RAW_DIR / "scimagojr.csv"
WOS_TARGET = RAW_DIR / "scimagojr_wos.csv"
DOAJ_TARGET = RAW_DIR / "doaj.csv"
SINTA_TARGET = RAW_DIR / "sinta.csv"

BUILD_SCRIPT = ROOT / "scripts" / "build_site.py"
VALIDATE_SCRIPT = ROOT / "scripts" / "validate_generated_data.py"
SMOKE_TEST_SCRIPT = ROOT / "scripts" / "smoke_test_search_loading.py"


def existing_file(value: str) -> Path:
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"File not found: {value}")
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Safely replace the active raw source files, rebuild the site, validate the output, "
            "and optionally run the browser smoke test."
        )
    )
    parser.add_argument("--scimago", required=True, type=existing_file, help="Path to the replacement scimagojr.csv file.")
    parser.add_argument("--wos", required=True, type=existing_file, help="Path to the replacement scimagojr_wos.csv file.")
    parser.add_argument("--sinta", required=True, type=existing_file, help="Path to the replacement sinta.csv file.")
    parser.add_argument("--doaj", type=existing_file, help="Optional path to the replacement doaj.csv file.")
    parser.add_argument(
        "--skip-smoke-test",
        action="store_true",
        help="Skip the Playwright smoke test after rebuild and validation.",
    )
    return parser.parse_args()


def run_python_script(script_path: Path) -> None:
    subprocess.run([sys.executable, str(script_path)], cwd=ROOT, check=True)


def backup_targets(targets: list[Path], backup_dir: Path) -> dict[Path, bool]:
    backup_dir.mkdir(parents=True, exist_ok=True)
    state: dict[Path, bool] = {}
    for target in targets:
        state[target] = target.exists()
        if target.exists():
            shutil.copy2(target, backup_dir / target.name)
    return state


def restore_targets(previous_state: dict[Path, bool], backup_dir: Path) -> None:
    for target, existed in previous_state.items():
        backup_path = backup_dir / target.name
        if existed and backup_path.exists():
            shutil.copy2(backup_path, target)
        elif not existed and target.exists():
            target.unlink()


def copy_update_plan(update_plan: dict[Path, Path]) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for source_path, target_path in update_plan.items():
        if source_path.resolve() == target_path.resolve():
            continue
        shutil.copy2(source_path, target_path)


def main() -> int:
    args = parse_args()

    update_plan: dict[Path, Path] = {
        args.scimago: SCIMAGO_TARGET,
        args.wos: WOS_TARGET,
        args.sinta: SINTA_TARGET,
    }
    if args.doaj:
        update_plan[args.doaj] = DOAJ_TARGET

    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    backup_dir = BACKUP_ROOT / timestamp
    targets = list(update_plan.values())

    previous_state = backup_targets(targets, backup_dir)

    try:
        copy_update_plan(update_plan)
        run_python_script(BUILD_SCRIPT)
        run_python_script(VALIDATE_SCRIPT)
        if not args.skip_smoke_test:
            run_python_script(SMOKE_TEST_SCRIPT)
    except subprocess.CalledProcessError as error:
        restore_targets(previous_state, backup_dir)
        try:
            run_python_script(BUILD_SCRIPT)
            run_python_script(VALIDATE_SCRIPT)
        except subprocess.CalledProcessError:
            raise SystemExit(
                "Dataset update failed and the automatic rollback rebuild did not complete cleanly. "
                "The raw source files were restored; rerun the standard build manually to confirm docs output."
            ) from error

        raise SystemExit(
            f"Dataset update failed during step: {error.cmd[-1]}. Raw files were restored and the previous build was regenerated."
        ) from error

    print("Dataset update completed successfully.")
    print(f"Active Scimago file: {SCIMAGO_TARGET}")
    print(f"Active WoS file: {WOS_TARGET}")
    print(f"Active SINTA file: {SINTA_TARGET}")
    if args.doaj:
        print(f"Active DOAJ file: {DOAJ_TARGET}")
    print(f"Backup snapshot: {backup_dir}")
    if args.skip_smoke_test:
        print("Browser smoke test: skipped")
    else:
        print("Browser smoke test: passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
