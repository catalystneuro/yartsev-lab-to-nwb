"""Interface for echolocation click data from Yartsev lab recordings.

Reads Detected_Clicks_{date}_Mic{N}.mat (MATLAB v5 format) and writes:
- Click timestamps and waveform snippets as a TimeSeries
- Click amplitude as a TimeSeries
- Click power spectral density as a TimeSeries

Echolocation clicks were detected from one of four environment microphones
(Mic1 shown here) sampling the bat's ultrasonic vocalizations at 96 kHz.
"""

import numpy as np
import scipy.io
from neuroconv.basedatainterface import BaseDataInterface
from neuroconv.tools.nwb_helpers import get_module
from neuroconv.utils import DeepDict
from pynwb import NWBFile
from pynwb.behavior import BehavioralTimeSeries, TimeSeries


class BatEcholocationInterface(BaseDataInterface):
    """Interface for detected echolocation clicks from room microphone recordings."""

    keywords = ["echolocation", "bat", "vocalization", "ultrasonic", "microphone"]

    def __init__(self, file_path: str, t_offset: float = 0.0):
        """
        Parameters
        ----------
        file_path : str
            Path to Detected_Clicks_{date}_Mic{N}.mat.
        t_offset : float, optional
            Seconds to add to all timestamps so they are non-negative.
        """
        super().__init__(file_path=file_path)
        self.t_offset = t_offset

    def get_metadata(self) -> DeepDict:
        metadata = super().get_metadata()
        return metadata

    def add_to_nwbfile(self, nwbfile: NWBFile, metadata: dict, stub_test: bool = False):
        clicks_data = scipy.io.loadmat(
            self.source_data["file_path"], struct_as_record=False, squeeze_me=True
        )
        detected_clicks = clicks_data["Detected_Clicks"]
        click_times = detected_clicks.times.flatten()  # shape (n_clicks,), in seconds
        click_waveforms = detected_clicks.shape  # shape (n_clicks, 96), raw audio
        click_amplitude = detected_clicks.amp.flatten()  # shape (n_clicks,), mV
        click_power = detected_clicks.power  # shape (n_clicks, 65), PSD
        audio_sampling_rate = float(detected_clicks.fs)  # 96000 Hz

        if stub_test:
            n_stub = min(50, len(click_times))
            click_times = click_times[:n_stub]
            click_waveforms = click_waveforms[:n_stub]
            click_amplitude = click_amplitude[:n_stub]
            click_power = click_power[:n_stub]

        timestamps_shifted = click_times + self.t_offset

        behavior_module = get_module(nwbfile, "behavior", "Processed behavioral data.")

        echolocation_container = BehavioralTimeSeries(name="Echolocation")

        waveform_series = TimeSeries(
            name="echolocation_click_waveforms",
            description=(
                "Waveform snippets of detected echolocation clicks recorded from room microphone 1. "
                "Each row is a single click; columns are 96 samples at the microphone sampling rate "
                f"({audio_sampling_rate:.0f} Hz). Timestamps are the time of the click peak."
            ),
            data=click_waveforms,
            timestamps=timestamps_shifted,
            unit="volts",
            resolution=-1.0,
        )
        amplitude_series = TimeSeries(
            name="echolocation_click_amplitude",
            description=(
                "Peak amplitude of each detected echolocation click in millivolts, "
                "as recorded by room microphone 1."
            ),
            data=click_amplitude,
            timestamps=timestamps_shifted,
            unit="millivolts",
            resolution=-1.0,
        )
        power_series = TimeSeries(
            name="echolocation_click_power_spectrum",
            description=(
                "Power spectral density of each detected echolocation click. "
                "Each row is the PSD of one click (65 frequency bins)."
            ),
            data=click_power,
            timestamps=timestamps_shifted,
            unit="no unit",
            resolution=-1.0,
        )

        echolocation_container.add_timeseries(waveform_series)
        echolocation_container.add_timeseries(amplitude_series)
        echolocation_container.add_timeseries(power_series)
        behavior_module.add(echolocation_container)
