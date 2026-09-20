# Selected AttExp migration to main — 2026-09-20

User selected exact streaming attention, adaptive reuse R3, and R3 identical-input extension/fused image-anchor commit. These are integrated into canonical HIP source/host used by normal builds, not copied as experimental source generators. Other AttExp experiments were not brought in. main already contained initial KV-pair commit084f8df from before branch creation; d29211a reverts that experiment, which remains in AttExp history.

Adaptation: default adaptive mode remains0; hip-game/hip-magpie presets explicitly set0. Gain may still be loaded from an override file, but absent/empty override now computes the16 channel-scale products from existing contract/projection assets using double intermediate and finalfloat. No new asset required. R3's thresholds/cache lifecycle/F8 behavior preserved. Root build scripts compile changed deep_fast source normally for gfx1200/gfx1201.

Validation:
- Normal HIP addon build scripts/build-addon.sh passes. DLL SHA256 7a315550a49eb74ad75dd99658be55719d1dc6e356dd1f00a639474c09ef6216 (/tmp/main-r3.addon64).
- Standard hip/build-modules.ps1, -Only deep_fast-packed, both targets pass. gfx1200 SHA7eee02c1a53594387e187bdb74b1113b5fcbd7b756119e7517fc69c6ea928374; gfx1201 SHA9fdd8a0207a3097d5df7c6bf9ae9298a905e9039c5944030d072c9f9a96eb231.
- Actual9070XT replay compares frozen R3 host/modules+external gain with main host/modules+automatic gain.900/1080 × static/horizontal motion/small occlusion × full/adaptive ×12frames with temporal history:144 paired RGB frame hashes match, all outputs finite. proof.json records all12 combinations. No elapsed times from these diagnostic runs claimed as performance.
- Direct GPU gate tests400/640:16 checks pass including equality extension, padding/signed-zero changes, forced/full controls, saturation/NaN handling and fused image-anchor commit.

Source reports on AttExp remain authoritative for prior speed measurements: exact stream1.64%/4.18% whole-network at900/1080; R3 vs exact stream frozen9.04%/11.25%, history motion4.93%/6.27%. These different-baseline percentages are not additive, and adaptive is approximate on changed inputs. Current test confirms migration equivalence, not new speed measurements or general gameplay quality.

Only this matched addon+module pair is valid; older addon cannot safely load the new gated-module ABI. Nothing installed to actual games, packaged or published. Existing Stellar Blade R3 stays in place. AttExp retains full experiment history. main defaults retain full calculation, optional adaptive reuse is enabled explicitly per VIT-REUSE.md.
