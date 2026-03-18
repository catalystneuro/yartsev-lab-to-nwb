"""Interface for sharp-wave ripple (SWR) events from Yartsev lab recordings.

Reads RPL_probe{N}.mat using the matio library, which decodes the MATLAB
table object (MCOS format) into a pandas DataFrame. Ripple events are stored
as a TimeIntervals table in the 'ecephys' processing module.

Each .mat file contains:
- RPL_out.table (MATLAB table → DataFrame): t (peak time, s), amp (z-score),
  ch (channel), dur (duration, s), brst (burst initiator flag), row (probe row),
  corr (correlation with template)
- RPL_out.LFP_trace: full-session LFP on the best SWR channel
- RPL_out.time_vector: timestamps for LFP_trace

Ripple detection: LFP bandpass-filtered 100–200 Hz, Hilbert envelope z-scored,
peaks > threshold (default 3) detected after excluding flight epochs.
"""

import numpy as np
from matio import load_from_mat
from neuroconv.basedatainterface import BaseDataInterface
from neuroconv.tools.nwb_helpers import get_module
from neuroconv.utils import DeepDict
from pynwb import NWBFile
from pynwb.epoch import TimeIntervals


class BatRippleInterface(BaseDataInterface):
    """Interface for sharp-wave ripple events detected from a single probe."""

    keywords = ["sharp-wave ripples", "SWR", "hippocampus", "LFP", "sleep replay"]

    def __init__(self, file_path: str, probe_number: int, t_offset: float = 0.0):
        """
        Parameters
        ----------
        file_path : str
            Path to RPL_probe{N}.mat.
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
        rpl = data["RPL_out"]

        detection_threshold = float(rpl["th"].flat[0].flat[0])
        rpl_table = rpl["table"].flat[0]

        if stub_test:
            rpl_table = rpl_table.iloc[:20]

        peak_times = rpl_table["t"].to_numpy(dtype=float) + self.t_offset
        durations = rpl_table["dur"].to_numpy(dtype=float)
        amplitudes = rpl_table["amp"].to_numpy(dtype=float)
        channels = rpl_table["ch"].to_numpy(dtype=float)
        is_burst_initiator = rpl_table["brst"].to_numpy(dtype=bool)
        probe_rows = rpl_table["row"].to_numpy(dtype=float)
        template_correlations = rpl_table["corr"].to_numpy(dtype=float)

        start_times = peak_times - durations / 2.0
        stop_times = peak_times + durations / 2.0

        # Clip to non-negative
        start_times = np.clip(start_times, 0.0, None)
        stop_times = np.clip(stop_times, 0.0, None)

        ripple_intervals = TimeIntervals(
            name=f"SWR_probe{self.probe_number}",
            description=(
                f"Sharp-wave ripple (SWR) events detected on Neuropixels probe {self.probe_number}. "
                f"Detection: LFP bandpass 100–200 Hz, Hilbert envelope z-scored, "
                f"peaks > {detection_threshold} SD, excluding flight epochs, "
                f"minimum peak distance 50 ms, minimum width 10 ms. "
                f"Events filtered by minimum template correlation 0.2."
            ),
        )
        ripple_intervals.add_column(name="peak_time", description="Time of the ripple power peak in seconds.")
        ripple_intervals.add_column(name="amplitude_zscore", description="Ripple power amplitude at peak, in z-score units.")
        ripple_intervals.add_column(name="channel", description="Channel ID on which the ripple was detected.")
        ripple_intervals.add_column(name="is_burst_initiator", description="True if this SWR was the initiating event in a ripple burst.")
        ripple_intervals.add_column(name="probe_row", description="Probe row of the detection channel.")
        ripple_intervals.add_column(
            name="template_correlation",
            description=(
                "Pearson correlation between this SWR's across-channel waveform "
                "and the mean SWR template."
            ),
        )

        for i, (start, stop) in enumerate(zip(start_times.tolist(), stop_times.tolist())):
            ripple_intervals.add_row(
                start_time=start,
                stop_time=stop,
                peak_time=float(peak_times[i]),
                amplitude_zscore=float(amplitudes[i]),
                channel=float(channels[i]),
                is_burst_initiator=bool(is_burst_initiator[i]),
                probe_row=float(probe_rows[i]),
                template_correlation=float(template_correlations[i]),
            )

        ecephys_module = get_module(
            nwbfile, "ecephys", "Processed extracellular electrophysiology data."
        )
        ecephys_module.add(ripple_intervals)
