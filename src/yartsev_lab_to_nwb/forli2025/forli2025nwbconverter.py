"""NWBConverter for Yartsev lab freely flying bat hippocampus recordings.

Forli, Fan, Qi & Yartsev, Nature 2025: "Replay and representation dynamics
in the hippocampus of freely flying bats."

Data included:
- LFP from up to 3 Neuropixels 1.0 probes (dorsal CA1/CA3)
- 3D flight behavior (position, velocity, flight epochs)
- Head IMU (accelerometer + gyroscope)
- Echolocation click events

Data NOT included (MATLAB table objects unreadable by Python):
- Per-unit spike times (good_units / mua_units in SU_kilosort4_outdir_probe*.mat)
- Sharp-wave ripple event table (RPL_probe*.mat table field)
"""

from neuroconv import NWBConverter

from .behavior_interface import BatBehaviorInterface
from .echolocation_interface import BatEcholocationInterface
from .imu_interface import BatIMUInterface
from .lfp_interface import BatLFPInterface


class Forli2025NWBConverter(NWBConverter):
    """Primary conversion class for Yartsev lab bat hippocampus data."""

    data_interface_classes = dict(
        LFPProbe1=BatLFPInterface,
        LFPProbe2=BatLFPInterface,
        LFPProbe3=BatLFPInterface,
        Behavior=BatBehaviorInterface,
        IMU=BatIMUInterface,
        Echolocation=BatEcholocationInterface,
    )
