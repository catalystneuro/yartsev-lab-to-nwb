"""Interface for behavioral data from Yartsev lab freely flying bat recordings.

Reads Extracted_Behavior_{date}.mat (MATLAB v5 format) and writes:
- 3D position (x, y, z) as SpatialSeries in a Position container
- 3D velocity (vx, vy, vz) as a TimeSeries
- Absolute velocity magnitude as a TimeSeries
- Binary flight status (0 = resting, 1 = flying) as a TimeSeries
- Flight epochs as TimeIntervals

All spatial data are in meters in room Cartesian coordinates.
The bat's 3D position was tracked at 120 Hz using 16 Motion Analysis
Raptor-12HS cameras via Cortex-64 software.
"""

from pathlib import Path

import numpy as np
import scipy.io
from neuroconv.basedatainterface import BaseDataInterface
from neuroconv.tools.nwb_helpers import get_module
from neuroconv.utils import DeepDict
from pynwb import NWBFile
from pynwb.behavior import BehavioralTimeSeries, Position, SpatialSeries, TimeSeries


class BatBehaviorInterface(BaseDataInterface):
    """Interface for 3D flight behavior from Yartsev lab .mat behavior files."""

    keywords = ["behavior", "position", "flight", "navigation", "free flight"]

    def __init__(self, file_path: str, t_offset: float = 0.0):
        """
        Parameters
        ----------
        file_path : str
            Path to Extracted_Behavior_{date}.mat.
        t_offset : float, optional
            Seconds to add to all timestamps so they are non-negative.
        """
        super().__init__(file_path=file_path)
        self.t_offset = t_offset

    def get_metadata(self) -> DeepDict:
        metadata = super().get_metadata()
        return metadata

    def add_to_nwbfile(self, nwbfile: NWBFile, metadata: dict, stub_test: bool = False):
        behavior_data = scipy.io.loadmat(
            self.source_data["file_path"], struct_as_record=False, squeeze_me=True
        )

        sampling_rate = float(behavior_data["Fs"])
        timestamps = behavior_data["t"]  # shape (T,), already in seconds
        position_xyz = behavior_data["r"]  # shape (T, 3), meters
        velocity_xyz = behavior_data["v"]  # shape (T, 3), m/s
        velocity_abs = behavior_data["v_abs"]  # shape (T,), m/s
        flight_status = behavior_data["bflying"].astype(np.int8)  # shape (T,), 0/1
        flight_sample_indices = behavior_data["f_smp"]  # shape (n_flights, 2)

        if stub_test:
            n_stub = min(1000, len(timestamps))
            timestamps = timestamps[:n_stub]
            position_xyz = position_xyz[:n_stub]
            velocity_xyz = velocity_xyz[:n_stub]
            velocity_abs = velocity_abs[:n_stub]
            flight_status = flight_status[:n_stub]
            # Only keep flights that start within stub window
            flight_sample_indices = flight_sample_indices[
                flight_sample_indices[:, 0] < n_stub
            ]

        starting_time = float(timestamps[0]) + self.t_offset
        rate = float(sampling_rate)

        behavior_module = get_module(nwbfile, "behavior", "Processed behavioral data.")

        # --- 3D Position ---
        position_spatial_series = SpatialSeries(
            name="position",
            description=(
                "3D position of the bat (centroid of three reflective markers on headstage) "
                "in room Cartesian coordinates. Tracked at 120 Hz using 16 Motion Analysis "
                "Raptor-12HS cameras via Cortex-64 software. Columns: x, y, z."
            ),
            data=position_xyz,
            starting_time=starting_time,
            rate=rate,
            reference_frame=(
                "Room Cartesian coordinates in meters. "
                "X: [-2.9, 2.9] m, Y: [-2.6, 2.6] m, Z: [0, 2.3] m."
            ),
            unit="meters",
            resolution=-1.0,
        )
        position_container = Position(name="Position")
        position_container.add_spatial_series(position_spatial_series)
        behavior_module.add(position_container)

        # --- 3D Velocity ---
        velocity_series = TimeSeries(
            name="velocity",
            description=(
                "3D velocity of the bat in room Cartesian coordinates, derived from smoothed "
                "position tracking. Columns: vx, vy, vz. In meters per second."
            ),
            data=velocity_xyz,
            starting_time=starting_time,
            rate=rate,
            unit="meters per second",
            resolution=-1.0,
        )
        velocity_abs_series = TimeSeries(
            name="velocity_magnitude",
            description="Absolute magnitude of 3D velocity vector. In meters per second.",
            data=velocity_abs,
            starting_time=starting_time,
            rate=rate,
            unit="meters per second",
            resolution=-1.0,
        )
        behavioral_time_series = BehavioralTimeSeries(name="BehavioralTimeSeries")
        behavioral_time_series.add_timeseries(velocity_series)
        behavioral_time_series.add_timeseries(velocity_abs_series)

        # --- Flight status ---
        flight_status_series = TimeSeries(
            name="flight_status",
            description=(
                "Binary flight status: 1 = bat is flying, 0 = bat is not flying. "
                "Flight segmentation was based on a velocity threshold of 0.5 m/s."
            ),
            data=flight_status,
            starting_time=starting_time,
            rate=rate,
            unit="no unit",
            resolution=1.0,
        )
        behavioral_time_series.add_timeseries(flight_status_series)
        behavior_module.add(behavioral_time_series)

        # --- Flight epochs (TimeIntervals) ---
        for flight_index, (start_sample, stop_sample) in enumerate(flight_sample_indices):
            start_sample = int(start_sample)
            stop_sample = int(min(stop_sample, len(timestamps) - 1))
            start_time = float(timestamps[start_sample]) + self.t_offset
            stop_time = float(timestamps[stop_sample]) + self.t_offset
            nwbfile.add_epoch(
                start_time=start_time,
                stop_time=stop_time,
                tags=[f"flight_{flight_index + 1}"],
            )
