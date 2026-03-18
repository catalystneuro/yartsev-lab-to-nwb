# yartsev-lab-to-nwb

NWB conversion scripts for the [Yartsev Lab](https://mcb.berkeley.edu/labs/yartsev/)
(Forli, Fan, Qi & Yartsev, Nature 2025), using
[NeuroConv](https://github.com/catalystneuro/neuroconv).

Associated paper: **"Replay and representation dynamics in the hippocampus of freely flying bats"**
DOI: [10.1038/s41586-025-09341-z](https://doi.org/10.1038/s41586-025-09341-z)

## Data description

Wireless Neuropixels 1.0 recordings from dorsal hippocampus (CA1/CA3) of freely flying
Egyptian fruit bats (*Rousettus aegyptiacus*) during rewarded aerial foraging. Includes:

- LFP from up to 3 Neuropixels 1.0 probes (~1250 Hz)
- 3D flight position and velocity (120 Hz, Motion Analysis)
- Head IMU — accelerometer and gyroscope (~500 Hz)
- Echolocation click detection (from room microphone, 96 kHz)

**Note:** Per-unit spike times and sharp-wave ripple event tables are stored in MATLAB
table objects (MCOS format) that Python cannot read from MATLAB v5 .mat files.
Re-saving those files as MATLAB v7.3 format and re-running the conversion would
enable including spike trains.

## Installation

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[forli2025]"
```

## Usage

### Single session

```python
from yartsev_lab_to_nwb.forli2025.convert_session import session_to_nwb

session_to_nwb(
    data_dir_path="/path/to/Demo_Session",
    output_dir_path="/path/to/output",
    stub_test=False,
)
```

### Stub test (fast, writes only first ~100 samples per stream)

```python
session_to_nwb(
    data_dir_path="/path/to/Demo_Session",
    output_dir_path="/path/to/output",
    stub_test=True,
)
```

### All sessions

```python
from yartsev_lab_to_nwb.forli2025.convert_all_sessions import dataset_to_nwb

dataset_to_nwb(
    data_dir_path="/path/to/dataset_root",
    output_dir_path="/path/to/output",
    num_workers=4,
)
```

### CLI

```bash
python -m yartsev_lab_to_nwb.forli2025.convert_session \
    --data-dir /path/to/Demo_Session \
    --output-dir /path/to/output \
    --stub-test
```
