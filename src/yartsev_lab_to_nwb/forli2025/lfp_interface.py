"""Interface for reading LFP data from Yartsev lab Neuropixels recordings.

LFP is stored in HDF5-format .mat files (LFP_probe{N}.mat) with int16 raw
values and a voltage_scaling factor that converts to microvolts. Three probes
were implanted in dorsal hippocampus (CA1/CA3) of freely flying Egyptian fruit
bats.

Note: Per-unit spike times were stored in MATLAB table objects (MCOS format)
which Python cannot read from MATLAB v5 .mat files. Only LFP is included here.
"""

from pathlib import Path

import h5py
import numpy as np
from hdmf.backends.hdf5.h5_utils import H5DataIO
from neuroconv.basedatainterface import BaseDataInterface
from neuroconv.utils import DeepDict
from pynwb import NWBFile
from pynwb.device import Device
from pynwb.ecephys import ElectricalSeries, LFP, ElectrodeGroup


class BatLFPInterface(BaseDataInterface):
    """Interface for a single Neuropixels probe LFP from Yartsev lab .mat files.

    Reads LFP_probe{probe_number}.mat (MATLAB v7.3 / HDF5 format) and writes
    an ElectricalSeries into the 'ecephys' processing module LFP container.
    The voltage_scaling field converts raw int16 to microvolts; stored values
    are int16 with conversion=voltage_scaling*1e-6 so the SI unit (volts) is
    preserved without transforming the data.
    """

    keywords = ["extracellular electrophysiology", "LFP", "Neuropixels", "hippocampus"]

    def __init__(self, file_path: str, probe_number: int, t_offset: float = 0.0):
        """
        Parameters
        ----------
        file_path : str
            Path to LFP_probe{N}.mat (MATLAB v7.3 / HDF5 format).
        probe_number : int
            Probe index (1, 2, or 3).
        t_offset : float, optional
            Seconds to add to all timestamps so they are non-negative.
            Computed from the behavior time vector minimum.
        """
        super().__init__(file_path=file_path)
        self.probe_number = probe_number
        self.t_offset = t_offset

    def get_metadata(self) -> DeepDict:
        metadata = super().get_metadata()
        probe_name = f"NeuropixelsProbe{self.probe_number}"
        group_name = f"probe{self.probe_number}"
        metadata["Ecephys"] = {
            "Device": [
                {
                    "name": probe_name,
                    "description": "Neuropixels 1.0 probe implanted in dorsal hippocampus (CA1/CA3).",
                    "manufacturer": "IMEC",
                }
            ],
            "ElectrodeGroup": [
                {
                    "name": group_name,
                    "description": (
                        f"Neuropixels 1.0 probe {self.probe_number} targeting dorsal hippocampus "
                        "(CA1 and CA3 pyramidal layers). Channel selection was guided by "
                        "ripple detection and multi-unit activity during a pre-session rest."
                    ),
                    "location": "dorsal hippocampus",
                    "device": probe_name,
                }
            ],
        }
        return metadata

    def add_to_nwbfile(self, nwbfile: NWBFile, metadata: dict, stub_test: bool = False):
        probe_name = f"NeuropixelsProbe{self.probe_number}"
        group_name = f"probe{self.probe_number}"

        # --- Device and ElectrodeGroup ---
        if probe_name not in nwbfile.devices:
            device_meta = next(
                d for d in metadata["Ecephys"]["Device"] if d["name"] == probe_name
            )
            device = Device(
                name=device_meta["name"],
                description=device_meta["description"],
                manufacturer=device_meta["manufacturer"],
            )
            nwbfile.add_device(device)
        else:
            device = nwbfile.devices[probe_name]

        if group_name not in nwbfile.electrode_groups:
            group_meta = next(
                g for g in metadata["Ecephys"]["ElectrodeGroup"] if g["name"] == group_name
            )
            electrode_group = ElectrodeGroup(
                name=group_meta["name"],
                description=group_meta["description"],
                location=group_meta["location"],
                device=device,
            )
            nwbfile.add_electrode_group(electrode_group)
        else:
            electrode_group = nwbfile.electrode_groups[group_name]

        # --- Read LFP data ---
        with h5py.File(self.source_data["file_path"]) as lfp_file:
            red_out = lfp_file["red_out"]
            voltage_scaling = float(red_out["voltage_scaling"][0, 0])
            sampling_frequency = float(red_out["sampling_freq"][0, 0])
            channel_ids = red_out["channelID"][:, 0].astype(int)
            channel_positions = red_out["channelPositions"][:]  # shape (2, n_channels)
            timestamps = red_out["t_ds"][:, 0]  # shape (n_timepoints,)
            lfp_raw = red_out["lfp"]  # shape (n_channels, n_timepoints), int16

            n_channels = lfp_raw.shape[0]
            n_timepoints = lfp_raw.shape[1]

            if stub_test:
                n_stub = min(100, n_timepoints)
                timestamps = timestamps[:n_stub]
                lfp_data = lfp_raw[:, :n_stub].T  # (n_stub, n_channels)
            else:
                lfp_data = lfp_raw[:].T  # (n_timepoints, n_channels) — time-first

        # --- Add electrodes ---
        # Track the starting electrode index for this probe's DynamicTableRegion
        electrode_start_index = len(nwbfile.electrodes) if nwbfile.electrodes is not None else 0

        # Add rel_x and rel_y columns if not already present
        if nwbfile.electrodes is None or "rel_x" not in nwbfile.electrodes.colnames:
            nwbfile.add_electrode_column(name="rel_x", description="X position on probe shank in micrometers.")
            nwbfile.add_electrode_column(name="rel_y", description="Y position along probe shank in micrometers (0 = tip).")

        for channel_index in range(n_channels):
            nwbfile.add_electrode(
                group=electrode_group,
                location="dorsal hippocampus",
                rel_x=float(channel_positions[0, channel_index]),
                rel_y=float(channel_positions[1, channel_index]),
            )

        electrode_indices = list(range(electrode_start_index, electrode_start_index + n_channels))
        electrode_table_region = nwbfile.create_electrode_table_region(
            region=electrode_indices,
            description=f"Channels from Neuropixels probe {self.probe_number}.",
        )

        # --- Apply time offset and compute rate ---
        starting_time = float(timestamps[0]) + self.t_offset

        # --- Create ElectricalSeries ---
        # conversion: int16 * voltage_scaling * 1e-6 → volts
        lfp_series = ElectricalSeries(
            name=f"LFP_probe{self.probe_number}",
            description=(
                f"Local field potential from Neuropixels 1.0 probe {self.probe_number} "
                "targeting dorsal hippocampus (CA1/CA3). Raw int16 values stored in volts "
                "via conversion factor (voltage_scaling * 1e-6). Recorded at ~1250 Hz via "
                "SpikeGadgets wireless headstage. Bandpass: 0.5–200 Hz."
            ),
            data=H5DataIO(data=lfp_data, compression="gzip", compression_opts=4),
            starting_time=starting_time,
            rate=sampling_frequency,
            electrodes=electrode_table_region,
            conversion=voltage_scaling * 1e-6,
            filtering="Bandpass 0.5–200 Hz",
            resolution=-1.0,
        )

        # --- Add to ecephys processing module LFP container ---
        from neuroconv.tools.nwb_helpers import get_module

        ecephys_module = get_module(
            nwbfile, "ecephys", "Processed extracellular electrophysiology data."
        )

        if "LFP" not in ecephys_module.data_interfaces:
            lfp_container = LFP(name="LFP")
            ecephys_module.add(lfp_container)
        else:
            lfp_container = ecephys_module.data_interfaces["LFP"]

        lfp_container.add_electrical_series(lfp_series)
