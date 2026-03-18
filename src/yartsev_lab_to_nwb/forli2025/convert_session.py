"""Convert a single Yartsev lab bat hippocampus session to NWB.

Session directory structure (one session per directory):
    {session_dir}/
        SU_kilosort4_outdir_probe{1,2,3}.mat   (spike sorting — tables unreadable)
        LFP_probe{1,2,3}.mat                    (LFP, MATLAB v7.3 HDF5)
        RPL_probe{1,2,3}.mat                    (ripple events — table unreadable)
        Extracted_Behavior_{date}.mat           (3D position, velocity, flights)
        IMU_data.mat                            (accelerometer + gyroscope)
        Detected_Clicks_{date}_Mic1.mat         (echolocation clicks)
        BPC_Dataset_*.mat                       (best probe/channel — metadata only)
        merges_Dataset_*.mat                    (unit merge info — not converted)

Session IDs are inferred from the behavior filename:
    Extracted_Behavior_YYMMDD.mat  →  date = YYMMDD
    Subject ID is inferred from the session directory name or BPC filename.

Usage
-----
    python -m yartsev_lab_to_nwb.forli2025.convert_session \\
        --data-dir /path/to/session \\
        --output-dir /path/to/output \\
        --stub-test
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Union
from zoneinfo import ZoneInfo

import scipy.io
from neuroconv.utils import dict_deep_update, load_dict_from_file

from yartsev_lab_to_nwb.forli2025.forli2025nwbconverter import Forli2025NWBConverter


def compute_t_offset(data_dir_path: Path) -> float:
    """Return the number of seconds to add to all timestamps to ensure they are >= 0.

    All data streams are pre-synchronized to the same time axis. The behavior
    time vector can start before t=0 (negative) if behavioral tracking started
    before the neural recording. The offset is the absolute value of the earliest
    timestamp across all streams, which comes from the behavior file.
    """
    behavior_files = sorted(data_dir_path.glob("Extracted_Behavior_*.mat"))
    behavior_data = scipy.io.loadmat(
        behavior_files[0], struct_as_record=False, squeeze_me=True
    )
    t_min = float(behavior_data["t"].min())
    return max(0.0, -t_min)


def parse_session_info(data_dir_path: Path) -> tuple[str, str, str]:
    """Parse session identifier, subject ID, and date from filenames.

    Returns
    -------
    session_id : str
        Full session identifier, e.g. 'Dataset_3_14543_240419'.
    subject_id : str
        Bat ID extracted from the BPC filename, e.g. '14543'.
    date_str : str
        Date in YYMMDD format, e.g. '240419'.
    """
    behavior_files = sorted(data_dir_path.glob("Extracted_Behavior_*.mat"))
    date_match = re.search(r"(\d{6})", behavior_files[0].name)
    date_str = date_match.group(1) if date_match else "unknown"

    bpc_files = sorted(data_dir_path.glob("BPC_Dataset_*.mat"))
    if bpc_files:
        # Filename: BPC_Dataset_3_14543_240419.mat
        parts = bpc_files[0].stem.split("_")
        # Extract subject_id (typically a 5-digit bat ID)
        subject_id = next((p for p in parts if len(p) == 5 and p.isdigit()), "unknown")
        dataset_num = parts[2] if len(parts) > 2 else "unknown"
        session_id = f"Dataset_{dataset_num}_{subject_id}_{date_str}"
    else:
        subject_id = "unknown"
        session_id = f"session_{date_str}"

    return session_id, subject_id, date_str


def session_to_nwb(
    data_dir_path: Union[str, Path],
    output_dir_path: Union[str, Path],
    stub_test: bool = False,
):
    data_dir_path = Path(data_dir_path)
    output_dir_path = Path(output_dir_path)
    if stub_test:
        output_dir_path = output_dir_path / "nwb_stub"
    output_dir_path.mkdir(parents=True, exist_ok=True)

    session_id, subject_id, date_str = parse_session_info(data_dir_path)
    nwbfile_path = output_dir_path / f"{session_id}.nwb"

    t_offset = compute_t_offset(data_dir_path)

    # --- Build source_data ---
    source_data = {}
    conversion_options = {}

    # LFP, spike sorting, and ripples — one interface per probe
    for probe_number in [1, 2, 3]:
        lfp_file = data_dir_path / f"LFP_probe{probe_number}.mat"
        if lfp_file.is_file():
            key = f"LFPProbe{probe_number}"
            source_data[key] = dict(
                file_path=str(lfp_file),
                probe_number=probe_number,
                t_offset=t_offset,
            )
            conversion_options[key] = dict(stub_test=stub_test)

        su_file = data_dir_path / f"SU_kilosort4_outdir_probe{probe_number}.mat"
        if su_file.is_file():
            key = f"SpikeSortingProbe{probe_number}"
            source_data[key] = dict(
                file_path=str(su_file),
                probe_number=probe_number,
                t_offset=t_offset,
            )
            conversion_options[key] = dict(stub_test=stub_test)

        rpl_file = data_dir_path / f"RPL_probe{probe_number}.mat"
        if rpl_file.is_file():
            key = f"RippleProbe{probe_number}"
            source_data[key] = dict(
                file_path=str(rpl_file),
                probe_number=probe_number,
                t_offset=t_offset,
            )
            conversion_options[key] = dict(stub_test=stub_test)

    # Behavior
    behavior_files = sorted(data_dir_path.glob("Extracted_Behavior_*.mat"))
    if behavior_files:
        source_data["Behavior"] = dict(
            file_path=str(behavior_files[0]),
            t_offset=t_offset,
        )
        conversion_options["Behavior"] = dict(stub_test=stub_test)

    # IMU
    imu_file = data_dir_path / "IMU_data.mat"
    if imu_file.is_file():
        source_data["IMU"] = dict(
            file_path=str(imu_file),
            t_offset=t_offset,
        )
        conversion_options["IMU"] = dict(stub_test=stub_test)

    # Echolocation clicks (Mic1 only)
    click_files = sorted(data_dir_path.glob("Detected_Clicks_*_Mic1.mat"))
    if click_files:
        source_data["Echolocation"] = dict(
            file_path=str(click_files[0]),
            t_offset=t_offset,
        )
        conversion_options["Echolocation"] = dict(stub_test=stub_test)

    # --- Create converter ---
    converter = Forli2025NWBConverter(source_data=source_data)

    # --- Metadata ---
    metadata = converter.get_metadata()
    metadata_path = Path(__file__).parent / "metadata.yaml"
    editable_metadata = load_dict_from_file(metadata_path)
    metadata = dict_deep_update(metadata, editable_metadata)

    # Session start time: date from filename, time unknown → use midnight as placeholder
    # Experiments run during dark cycle (07:00–19:00 lights off in housing room)
    # at UC Berkeley (Pacific time). Exact session start time not available.
    tz = ZoneInfo("America/Los_Angeles")
    year = 2000 + int(date_str[:2])
    month = int(date_str[2:4])
    day = int(date_str[4:6])
    session_start_time = datetime(year, month, day, 0, 0, 0, tzinfo=tz)
    # NOTE: The actual session start time within the day is unknown.
    # t=0 in data corresponds to the start of behavioral tracking.
    # t_offset seconds were added to shift all timestamps to be non-negative
    # (behavioral tracking started before neural recording in this session).

    metadata["NWBFile"]["session_start_time"] = session_start_time
    metadata["NWBFile"]["session_id"] = session_id
    metadata["NWBFile"]["session_description"] = (
        f"Freely flying bat hippocampus recording. Session {session_id}. "
        f"Bat performed rewarded spontaneous aerial foraging between two feeders. "
        f"Neuropixels 1.0 probes recorded LFP and single-unit activity from dorsal "
        f"hippocampus (CA1/CA3). 3D position tracked at 120 Hz. IMU and echolocation "
        f"clicks also recorded."
    )
    metadata["Subject"]["subject_id"] = subject_id
    # Exact per-bat weight and age not available in the processed data files.
    # From the paper: all bats were adult males, body weight 151–171 g.
    # age and weight must be set from subject-level records if available.

    # --- Run conversion ---
    converter.run_conversion(
        nwbfile_path=nwbfile_path,
        metadata=metadata,
        conversion_options=conversion_options,
        overwrite=True,
    )
    print(f"Saved: {nwbfile_path}")
    return nwbfile_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Convert a single Yartsev lab session to NWB.")
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--stub-test", action="store_true")
    args = parser.parse_args()

    session_to_nwb(
        data_dir_path=args.data_dir,
        output_dir_path=args.output_dir,
        stub_test=args.stub_test,
    )
