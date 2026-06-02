# Measurement Report Fields

This document describes stable machine-readable fields emitted by the v0.4 measurement layer. Field names are intentionally conservative and avoid subjective quality claims.

## Sweep Metadata JSON
Written next to `pipetune measure generate-sweep` WAV output.

- `sample_rate`: integer sample rate in Hz.
- `duration_seconds`: generated duration.
- `start_hz`: sweep start frequency.
- `end_hz`: sweep end frequency.
- `amplitude`: generated peak amplitude.
- `generated_at`: ISO timestamp.
- `pipetune_version`: PipeTune version.
- `warning`: safe playback warning.

## WAV Inspection JSON
Printed by `pipetune measure inspect-wav --json`.

- `path`: inspected WAV path.
- `channel_count`: number of source channels.
- `sample_width_or_format`: decoded sample format, such as `pcm_s16` or `float32`.
- `sample_rate`: sample rate in Hz.
- `duration_seconds`: measured duration.
- `peak_dbfs`: estimated peak level in dBFS.
- `rms_dbfs`: estimated RMS level in dBFS.
- `peak_linear`: peak absolute sample value.
- `rms_linear`: RMS sample value.
- `dc_offset`: estimated DC offset after mono mixdown.
- `clipping_detected`: true when samples are near full scale.
- `silence_detected`: true when signal is silent or too quiet.
- `dominant_frequency_hz`: approximate dominant frequency when detectable.
- `quality_flags`: cautious machine-readable flags.
- `measurement_quality`: `pass`, `warn`, or `fail`.
- `warnings`: human-readable cautions.

## Analysis Report JSON
Written by `pipetune measure analyze-sweep`.

- `sweep_file`: source sweep WAV.
- `recorded_file`: recorded WAV.
- `channel_count`: recorded channel count.
- `sample_width_or_format`: recorded sample format.
- `sample_rate`: sample rate in Hz.
- `duration_seconds`: recorded duration.
- `peak_dbfs`: estimated recorded peak level.
- `rms_dbfs`: estimated recorded RMS level.
- `dc_offset`: estimated recorded DC offset.
- `clipping_detected`: clipping flag.
- `silence_detected`: silence flag.
- `quality_flags`: cautious machine-readable flags.
- `frequency_bins`: approximate response frequency bins.
- `magnitude_db`: approximate magnitude response values.
- `analysis_warning`: primary human-readable warning.
- `warnings`: additional warnings.
- `measurement_quality`: `pass`, `warn`, or `fail`.

## Imported Response Metadata JSON
Written next to `pipetune measure import-rew` normalized CSV output.

- `source_format`: currently `REW`.
- `row_count`: valid imported row count.
- `skipped_row_count`: skipped incomplete or blank row count.
- `detected_frequency_column`: source frequency column name.
- `detected_magnitude_column`: source magnitude column name.
- `min_freq_hz`: minimum imported frequency.
- `max_freq_hz`: maximum imported frequency.
- `imported_at`: ISO timestamp.
- `warnings`: import warnings.

## Response Validation JSON
Printed by `pipetune measure validate-response --json`.

- `input_file`: normalized response CSV path.
- `row_count`: parsed row count.
- `min_freq_hz`: minimum parsed frequency.
- `max_freq_hz`: maximum parsed frequency.
- `sorted_frequency_data`: whether rows were already sorted.
- `duplicate_frequency_count`: duplicate frequency count.
- `unrealistic_magnitude_count`: count of magnitude values outside hard safety bounds.
- `max_adjacent_magnitude_jump_db`: largest adjacent magnitude jump after sorting.
- `quality_flags`: cautious validation flags.
- `warnings`: human-readable warnings.
- `errors`: validation errors.
- `measurement_quality`: `pass`, `warn`, or `fail`.

## Comparison Report JSON
Written by `pipetune measure compare-response`.

- `before_file`: before response CSV.
- `after_file`: after response CSV.
- `grid_point_count`: shared frequency grid point count.
- `min_freq_hz`: shared minimum frequency.
- `max_freq_hz`: shared maximum frequency.
- `frequency_overlap_warning`: warning string or null.
- `average_absolute_difference_db`: average absolute measured difference.
- `max_absolute_difference_db`: maximum absolute measured difference.
- `band_summaries`: summaries for `sub_bass`, `bass`, `low_mid`, `mid`, `upper_mid`, `treble`, and `air`.
- `variance_before`: variance of before magnitudes on the shared grid.
- `variance_after`: variance of after magnitudes on the shared grid.
- `flatter_by_variance`: true only when `variance_after` is lower than `variance_before`.

Legacy aliases `before_variance_db2` and `after_variance_db2` remain for v0.4.0 compatibility.

## Correction Safety Report JSON
Written next to `pipetune measure generate-correction` draft TOML as `.safety.json`.

- `source_file`: normalized response CSV used for the draft.
- `profile_type`: draft profile type.
- `status`: always `draft`.
- `measurement_quality`: input response validation verdict.
- `validation`: embedded response validation report.
- `safety_constraints`: boost, high-pass, preamp, limiter metadata, and broad-band constraints.
- `generated_filter_count`: generated filter count including mandatory high-pass.
- `max_generated_boost_db`: maximum generated boost.
- `warnings`: draft-only and uncalibrated microphone warnings.

