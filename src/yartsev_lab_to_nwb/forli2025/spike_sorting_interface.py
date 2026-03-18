"""Interface for Kilosort4 spike sorting data from Yartsev lab recordings.

Reads SU_kilosort4_outdir_probe{N}.mat using the matio library, which correctly
decodes MATLAB table objects (MCOS format) into pandas DataFrames. Per-unit
spike times and quality labels are added to the NWB Units table.

Each .mat file contains:
- good_units (MATLAB table → DataFrame): cluster_id, spikeTimes_usec,
  localSpikeTimes_usec, spikePos_um, template
- mua_units (same structure): multi-unit activity clusters

Spike times are in microseconds in the global (synchronized) time reference.
"""

from pathlib import Path

import numpy as np
from matio import load_from_mat
from neuroconv.basedatainterface import BaseDataInterface
from neuroconv.utils import DeepDict
from pynwb import NWBFile


class BatSpikeSortingInterface(BaseDataInterface):
    """Interface for Kilosort4 spike sorting results from a single Neuropixels probe."""

    keywords = ["spike sorting", "Kilosort4", "single units", "hippocampus", "Neuropixels"]

    def __init__(self, file_path: str, probe_number: int, t_offset: float = 0.0):
        """
        Parameters
        ----------
        file_path : str
            Path to SU_kilosort4_outdir_probe{N}.mat.
        probe_number : int
            Probe index (1, 2, or 3).
        t_offset : float, optional
            Seconds to add to all timestamps so they are non-negative.
        """
        super().__init__(file_path=file_path)
        self.probe_number = probe_number
        self.t_offset = t_offset

    def get_metadata(self) -> DeepDict:
        return super().get_metadata()

    def add_to_nwbfile(self, nwbfile: NWBFile, metadata: dict, stub_test: bool = False):
        data = load_from_mat(self.source_data["file_path"])
        out = data["out"]

        good_units = out["good_units"].item()
        mua_units = out["mua_units"].item()
        probe_id = str(out["probe_id"].item()[0])
        curation_date = str(out["curation_date"].item()[0])

        group_name = f"probe{self.probe_number}"
        electrode_group = nwbfile.electrode_groups.get(group_name)

        # Add custom columns to Units table on first call (only once)
        if nwbfile.units is None or "unit_quality" not in nwbfile.units.colnames:
            nwbfile.add_unit_column(
                name="unit_quality",
                description=(
                    "Unit quality label from Kilosort4 + Phy curation. "
                    "'good' = single unit; 'mua' = multi-unit activity."
                ),
            )
            nwbfile.add_unit_column(
                name="cluster_id",
                description="Kilosort4 cluster ID within the probe.",
            )
            nwbfile.add_unit_column(
                name="probe_id",
                description="Probe identifier string (e.g. 'kilosort4_outdir_probe1').",
            )
            nwbfile.add_unit_column(
                name="curation_date",
                description="Date of Kilosort4 extraction and Phy curation (YYMMDD_HHMM format).",
            )
            if electrode_group is not None:
                nwbfile.add_unit_column(
                    name="electrode_group",
                    description="Neuropixels probe from which this unit was recorded.",
                )

        for units_dataframe, quality_label in [(good_units, "good"), (mua_units, "mua")]:
            if stub_test:
                units_dataframe = units_dataframe.iloc[:3]

            for _, row in units_dataframe.iterrows():
                spike_times_usec = row["spikeTimes_usec"].flatten()
                spike_times_sec = np.sort(spike_times_usec / 1e6 + self.t_offset)

                # NWB requires non-negative spike times
                spike_times_sec = spike_times_sec[spike_times_sec >= 0.0]

                unit_kwargs = dict(
                    spike_times=spike_times_sec,
                    unit_quality=quality_label,
                    cluster_id=float(row["cluster_id"]),
                    probe_id=probe_id,
                    curation_date=curation_date,
                )
                if electrode_group is not None:
                    unit_kwargs["electrode_group"] = electrode_group

                nwbfile.add_unit(**unit_kwargs)
