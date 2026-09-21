# Read-only frequency observation

prepare.py generates a benchmark with per-frame GetTickCount64 end timestamps and an extended ADL telemetry helper. Build generated telemetry.cpp using /tmp/dlss5-adl headers as documented in Development/HIP/adl-telemetry.md; benchmark uses standard HIP benchmark defines/includes. Remote binaries: clock_observe_telemetry.exe and benchmark_clock_observe.exe under hip-backend.

run.ps1 guards games, samples ADL every200ms while running1000 frozen frames at each tier, Graph/reuse/history off, and stops only its own sampler after the benchmark. No clock/power/voltage setters. Analysis selects adapter0, status0, supported sensors and timestamps spanning frames100–999. Other logical adapters are not independent GPUs. Unsupported counters are not measured zero. Telemetry may be internally averaged/coarse; this is not a controlled frequency sweep.

Sensor IDs per AMD ADL definitions:1GFX clock,2memory clock,8edge temperature,19GFX activity,20memory activity,27hotspot,73board power.3/23/30/35/44/55 unsupported on this run. Read-only driver API is deprecated but currently functional; support flags retained. Results in results/clock-observe-20260921. Existing settings/game files untouched.
