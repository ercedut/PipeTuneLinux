# Diagnostic JSON Fields

## Top-Level
- `metadata`: runtime metadata.
- `pipewire`: PipeWire and pulse compatibility data.
- `wireplumber`: WirePlumber service and inferred management state.
- `alsa`: ALSA command/file visibility and device lists.
- `bluetooth`: Bluetooth audio card/profile visibility.
- `easyeffects`: EasyEffects install/version visibility.
- `risks`: ordered list of risk findings.
- `recommendations`: ordered list of next-step recommendations.
- `raw_command_status`: normalized command availability/exit summary.

## metadata
- `generated_at` (string, ISO8601 UTC)
- `tool_version` (string)
- `codename` (string)
- `hostname` (string)
- `platform` (string)
- `python_version` (string)

## pipewire
- `services.pipewire` (CommandResult)
- `services.pipewire_pulse` (CommandResult)
- `pactl_get_default_sink` (CommandResult)
- `pactl_get_default_source` (CommandResult)
- `wpctl_inspect_default_sink` (CommandResult)
- `wpctl_inspect_default_source` (CommandResult)
- `pactl_info` (CommandResult)
- `wpctl_status` (CommandResult)
- `pw_dump` (CommandResult)
- `default_sink`:
  - `detected` (bool)
  - `name` (string|null)
  - `source` (`pactl_get_default_sink`|`wpctl_inspect`|`wpctl_status`|`pactl_info`|`unknown`)
  - `explicitly_missing` (bool)
- `default_source`:
  - `detected` (bool)
  - `name` (string|null)
  - `source` (`pactl_get_default_source`|`wpctl_inspect`|`wpctl_status`|`pactl_info`|`unknown`)
  - `explicitly_missing` (bool)
- `pulse_server_name` (string|null)
- `pulse_server_string` (string|null)
- `filter_chain_detected` (bool)

## wireplumber
- `service_status` (CommandResult)
- `wpctl_status` (CommandResult)
- `has_managed_audio_nodes` (bool)

## alsa
- `aplay_list` (CommandResult)
- `arecord_list` (CommandResult)
- `cards_file`:
  - `path` (string)
  - `exists` (bool)
  - `content` (string|null)
  - `error` (string|null)
- `version_file`:
  - `path` (string)
  - `exists` (bool)
  - `content` (string|null)
  - `error` (string|null)
- `ucm2_directory`:
  - `path` (string)
  - `exists` (bool)
- `playback_devices` (string[])
- `capture_devices` (string[])
- `cards` (string[])

## bluetooth
- `pactl_cards` (CommandResult)
- `bluetooth_cards_detected` (bool)
- `bluetooth_card_names` (string[])
- `active_profiles` (string[])
- `profile_hints` (string[])
- `playback_mode` (`not_active`|`hfp_hsp`|`a2dp`|`unknown`)
- `bluetooth_audio_active` (bool)

## easyeffects
- `installed` (bool)
- `binary_path` (string|null)
- `version` (CommandResult|null)

## risks
Array of:
- `severity` (`critical`|`high`|`medium`|`low`|`info`)
- `code` (string)
- `message` (string)

## recommendations
Array of recommendation strings ordered by risk priority.

## raw_command_status
Array of command summary objects:
- `component` (string)
- `name` (string)
- `command` (string)
- `available` (bool)
- `exit_code` (int|null)
- `timed_out` (bool)
- `error` (string|null)

## CommandResult
Shape used in collectors:
- `command` (string)
- `available` (bool)
- `exit_code` (int|null)
- `stdout` (string)
- `stderr` (string)
- `timed_out` (bool)
- `error` (string|null)
