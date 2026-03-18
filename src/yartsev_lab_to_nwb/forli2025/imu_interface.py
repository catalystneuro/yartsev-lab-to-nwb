"""Interface for IMU (inertial measurement unit) data from Yartsev lab recordings.

Reads IMU_data.mat (MATLAB v5 format) and writes 3-axis accelerometer and
3-axis gyroscope TimeSeries. The IMU was mounted on the neural recording
headstage on the bat's head and sampled at ~500 Hz.
"""

import numpy as np
import scipy.io
from neuroconv.basedatainterface import BaseDataInterface
from neuroconv.tools.nwb_helpers import get_module
from neuroconv.utils import DeepDict
from pynwb import NWBFile
from pynwb.behavior import BehavioralTimeSeries, TimeSeries


class BatIMUInterface(BaseDataInterface):
    """Interface for head-mounted IMU data (accelerometer + gyroscope)."""

    keywords = ["IMU", "accelerometer", "gyroscope", "inertial measurement"]

    def __init__(self, file_path: str, t_offset: float = 0.0):
        """
        Parameters
        ----------
        file_path : str
            Path to IMU_data.mat.
        t_offset : float, optional
            Seconds to add to all timestamps so they are non-negative.
        """
        super().__init__(file_path=file_path)
        self.t_offset = t_offset

    def get_metadata(self) -> DeepDict:
        metadata = super().get_metadata()
        return metadata

    def add_to_nwbfile(self, nwbfile: NWBFile, metadata: dict, stub_test: bool = False):
        imu_data = scipy.io.loadmat(
            self.source_data["file_path"], struct_as_record=False, squeeze_me=True
        )
        imu = imu_data["NP_imu"]
        acceleration = imu.acc  # shape (n_timepoints, 3), in units of g
        gyroscope = imu.gyr  # shape (n_timepoints, 3), in deg/s or rad/s
        timestamps = imu.t  # shape (n_timepoints,), in seconds

        sampling_rate = float(imu.Fs)

        if stub_test:
            n_stub = min(1000, len(timestamps))
            timestamps = timestamps[:n_stub]
            acceleration = acceleration[:n_stub]
            gyroscope = gyroscope[:n_stub]

        starting_time = float(timestamps[0]) + self.t_offset

        behavior_module = get_module(nwbfile, "behavior", "Processed behavioral data.")

        imu_container = BehavioralTimeSeries(name="IMU")

        acceleration_series = TimeSeries(
            name="accelerometer",
            description=(
                "3-axis linear acceleration from IMU mounted on the neural recording headstage "
                "on the bat's head. Sampled at ~500 Hz. Columns: x, y, z. "
                "Units are multiples of gravitational acceleration g (9.81 m/s^2)."
            ),
            data=acceleration,
            starting_time=starting_time,
            rate=sampling_rate,
            unit="g",
            resolution=-1.0,
        )
        gyroscope_series = TimeSeries(
            name="gyroscope",
            description=(
                "3-axis angular velocity from IMU mounted on the neural recording headstage "
                "on the bat's head. Sampled at ~500 Hz. Columns: x, y, z."
            ),
            data=gyroscope,
            starting_time=starting_time,
            rate=sampling_rate,
            unit="degrees per second",
            resolution=-1.0,
        )

        imu_container.add_timeseries(acceleration_series)
        imu_container.add_timeseries(gyroscope_series)
        behavior_module.add(imu_container)
