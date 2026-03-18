"""Convert all Yartsev lab bat hippocampus sessions to NWB.

Expected dataset directory structure:
    {data_root}/
        {session_dir}/               # one directory per session
            LFP_probe{1,2,3}.mat
            Extracted_Behavior_{date}.mat
            IMU_data.mat
            Detected_Clicks_{date}_Mic1.mat
            ...

Session directories are identified by the presence of an
Extracted_Behavior_*.mat file.

Usage
-----
    python -m yartsev_lab_to_nwb.forli2025.convert_all_sessions \\
        --data-dir /path/to/dataset_root \\
        --output-dir /path/to/output \\
        --num-workers 4 \\
        --stub-test
"""

from __future__ import annotations

import traceback
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Union

from .convert_session import session_to_nwb


def get_session_paths(data_dir_path: Path) -> list[Path]:
    """Return paths to all session directories under data_dir_path."""
    # A session directory contains an Extracted_Behavior_*.mat file
    session_paths = [
        path.parent
        for path in data_dir_path.rglob("Extracted_Behavior_*.mat")
    ]
    return sorted(set(session_paths))


def safe_session_to_nwb(
    data_dir_path: Path,
    output_dir_path: Path,
    stub_test: bool,
    exception_file_path: Path,
):
    try:
        session_to_nwb(
            data_dir_path=data_dir_path,
            output_dir_path=output_dir_path,
            stub_test=stub_test,
        )
    except Exception:
        exception_file_path.write_text(traceback.format_exc())


def dataset_to_nwb(
    data_dir_path: Union[str, Path],
    output_dir_path: Union[str, Path],
    num_workers: int = 1,
    stub_test: bool = False,
):
    data_dir_path = Path(data_dir_path)
    output_dir_path = Path(output_dir_path)
    exception_dir = output_dir_path / "exceptions"
    exception_dir.mkdir(parents=True, exist_ok=True)

    session_paths = get_session_paths(data_dir_path)
    print(f"Found {len(session_paths)} sessions.")

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        for session_path in session_paths:
            session_name = session_path.name
            executor.submit(
                safe_session_to_nwb,
                data_dir_path=session_path,
                output_dir_path=output_dir_path,
                stub_test=stub_test,
                exception_file_path=exception_dir / f"{session_name}.txt",
            )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Convert all Yartsev lab sessions to NWB.")
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--num-workers", type=int, default=1)
    parser.add_argument("--stub-test", action="store_true")
    args = parser.parse_args()

    dataset_to_nwb(
        data_dir_path=args.data_dir,
        output_dir_path=args.output_dir,
        num_workers=args.num_workers,
        stub_test=args.stub_test,
    )
