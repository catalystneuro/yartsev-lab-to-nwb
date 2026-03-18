# Yartsev Lab — Conversion Notes

## Experiment Overview

Neuropixels recordings in freely flying Egyptian fruit bats during spatial navigation tasks.
Data includes hippocampal single-unit activity, LFP, 3D flight behavior, echolocation clicks,
and head IMU (accelerometer + gyroscope). Associated paper:
"Replay and representation dynamics in the hippocampus of freely flying bats" (Nature, 2025).

Session identifier format: `Dataset_{number}_{bat_id}_{date}` (e.g., `Dataset_3_14543_240419`)

## Data Streams

| Stream | Format | File Pattern | Notes |
|--------|--------|--------------|-------|
| LFP (all channels) | MATLAB v7.3 HDF5 .mat | `LFP_probe{1,2,3}.mat` | int16, ~1250 Hz, 30–200 ch per probe |
| Spike sorting (SU) | MATLAB v5 .mat | `SU_kilosort4_outdir_probe{1,2,3}.mat` | Kilosort4 output; per-unit data in MATLAB tables |
| Behavior (3D position) | MATLAB v5 .mat | `Extracted_Behavior_*.mat` | 120 Hz, smoothed + flight-segmented |
| IMU (accel + gyro) | MATLAB v5 .mat | `IMU_data.mat` | 500 Hz, 3-axis acc + gyro |
| Echolocation clicks | MATLAB v5 .mat | `Detected_Clicks_{date}_Mic1.mat` | Click times + waveforms + power |
| Ripple events | MATLAB v5 .mat | `RPL_probe{1,2,3}.mat` | SWR detections, LFP trace |
| Best probe/channel | MATLAB v5 .mat | `BPC_Dataset_*.mat` | Single [probe, channel] pair |
| Unit merges | MATLAB v5 .mat | `merges_Dataset_*.mat` | Putative duplicate cluster IDs |

## Directory Structure

```
yartsev_demo_data/
├── Demo_Session/
│   ├── SU_kilosort4_outdir_probe{1,2,3}.mat   # Spike sorting
│   ├── LFP_probe{1,2,3}.mat                    # LFP data (HDF5 format)
│   ├── RPL_probe{1,2,3}.mat                    # Sharp-wave ripples
│   ├── Extracted_Behavior_240419.mat            # 3D flight behavior
│   ├── IMU_data.mat                             # Head accelerometer + gyroscope
│   ├── Detected_Clicks_240419_Mic1.mat          # Echolocation clicks
│   ├── BPC_Dataset_3_14543_240419.mat           # Best probe/channel for LFP
│   └── merges_Dataset_3_14543_240419.mat        # Unit merge candidates
├── Helper functions/                            # MATLAB analysis scripts
├── NP_Bat_Demo.m                               # Demo analysis script
├── How to use.pdf
└── Replay-...-nature-2025.pdf                  # Associated paper
```

## Data Parameters (Demo_Session)

- **Session**: Dataset_3, Bat 14543, Date 240419 (April 19, 2024)
- **Session duration**: ~5268 s (~87.8 min), t range: [-12.677, 5255.219] s
- **Behavior**: 120 Hz, 642724 samples, 38 flights, room dims: X[-2.9,2.9]m, Y[-2.6,2.6]m, Z[0,2.3]m
- **LFP probe 1**: 30 channels, 1250 Hz
- **LFP probe 2**: 200 channels, 1250 Hz
- **LFP probe 3**: 154 channels, 1250 Hz
- **Spike sorting probe 1**: 24 good units, 37 MUA
- **Spike sorting probe 2**: 159 good units, 147 MUA
- **Spike sorting probe 3**: 109 good units, 121 MUA
- **Echolocation clicks**: 1444 clicks, t=[98.9, 5030.6] s
- **IMU**: 500 Hz, 3-axis accelerometer + gyroscope
- **Species**: Egyptian fruit bat (Rousettus aegyptiacus)

## Sessions

- Number of subjects: TBD (need full dataset info)
- Number of sessions: TBD
- Session naming convention: `Dataset_{number}_{bat_id}_{date}`

## Existing Resources

- Publication: "Replay and representation dynamics in the hippocampus of freely flying bats", Nature 2025
- DOI: TBD (need to confirm)
- Analysis code: NP_Bat_Demo.m (in demo data)
- Data source: local path `/Users/pauladkisson/Documents/CatalystNeuro/YartsevConv/yartsev_demo_data/`

## Metadata (from paper)

- Species: *Rousettus aegyptiacus* (Egyptian fruit bat)
- All bats: adult males, body weight 151–171 g
- 6 bats total (5 with 3 probes, 1 with 2 probes), 23 sessions (3–4/bat)
- Recording system: SpikeGadgets wireless Neuropixels 1.0 headstage
- Position tracking: 16 Motion Analysis Raptor-12HS cameras, Cortex-64 software, 120 Hz
- Spike sorting: Kilosort4 + Phy visual curation
- LFP band: 0.5–200 Hz; spike band: 600–6000 Hz
- Institution: University of California, Berkeley (Pacific timezone)
- DOI: doi:10.1038/s41586-025-09341-z
- 4 microphones total; only Mic1 in demo data
- t=0 in data ≈ start of behavioral tracking; neural recording starts ~95 s later
- Session start time exact (time-of-day) unknown; using midnight 2024-04-19 as placeholder

## Open Questions

- [ ] Exact per-bat weight and DOB not in processed data files — needs subject records
- [ ] Exact session start times (time-of-day) unknown — using midnight as placeholder
- [ ] Is there a DANDI dandiset already?
- [ ] Are raw Kilosort4 output directories available for future spike sorting inclusion?

## Interface Mapping (Preliminary)

| Stream | Proposed Interface | Status |
|--------|-------------------|--------|
| LFP | CUSTOM: LFPInterface (read HDF5 .mat) | Needs implementation |
| Spike sorting (per-unit) | CUSTOM: BatKilosortInterface | **Blocked** — MCOS tables |
| 3D position | CUSTOM: BatBehaviorInterface | Needs implementation |
| Flight epochs | TimeIntervals | Derivable from bflying + f_smp |
| IMU (accelerometer) | CUSTOM: IMUInterface | Needs implementation |
| Echolocation clicks | CUSTOM: EcholocationInterface | Needs implementation |
| Ripple events | CUSTOM: RippleInterface | Partial — table is MCOS |
