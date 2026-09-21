# Adopt C256 zero-padding shortcut; retain C64 as an experiment

The comparison baseline is147421f, already containing the adopted C128 shortcut. Main now applies the same workgroup-uniform, exact-zero vertical-padding guard to C128 and C256. C64 is unchanged in production. This is a one-line compile-time predicate extension: no input precision, weights, quality switches, host ABI or configuration changes.

## Isolated and whole-network results

Each isolated run uses the real first mapped byte-input kernel,2000warmup/10000measured calls in ABBA. The C256 target uses fragment-packed weights. Full rawFP32 output is compared first/final for every slot:8comparisons per variant, allbitdiff0.

| Candidate | Isolated baseline→candidate μs | Gain |
|---|---:|---:|
|C64 only|130.35250→126.52445|2.94%|
|C256 only|68.62430→65.44610|4.63%|

Ordinary full-network timing freezes inputs, disables adaptive reuse, and uses host wall/sync without a profiler:

| Candidate / control |900P saved ms|1080P saved ms|
|---|---:|---:|
|C64,160frames/slot, discard32|0.020512|−0.004113|
|C64,1000frames/slot, discard200|not repeated|−0.018243|
|C256,160frames/slot, discard32|0.071676|0.051031|
|C256,1000frames/slot, discard200|0.047050|0.088984|

Final C256 baselines13.270240/18.789034ms become13.223190/18.700050ms. These are incremental gains over C128-improved main, not measurements against the installed game or an old release. Batches drift, and these tiny milliseconds are not a fixed game-FPS promise. C64 did not demonstrate a whole-network1080 benefit in either short or longer control, despite its hot isolated target improving; it is therefore not adopted. The precise per-call/scheduling reason remains unmeasured. No combined C64+C256 candidate was built/tested after that gate failed.

## Correctness and resources

C64 passes48paired900/1080 static/moving RGB frames. Adopted C256 passes96pairs including720motion,900temporal history, f32input and f32feature paths. Every full-frame hash matches, and the isolated rawFP32 checks also match. Both variants compile for gfx1200 and gfx1201; runtime testing is gfx1201 only. The original C128 shortcut's predicate proof/checks still apply: channel width changes output size/thread count, not the geometric test. The later attention computation is unchanged.

| Targeted mapped kernel | Actual VGPR old→new | LDS bytes | Compiler Occupancy old→new | Scratch |
|---|---:|---:|---:|---:|
|C64 byte-in/feature-byte|97→93|5440|12→16|0|
|C256 fragment byte-in/feature-byte|101→102|21568|12→12|0|

Compiler resource comments are not actual dynamic occupancy and do not explain C64's whole-network result. The source change was applied only after controls passed; production source exactly matches the validated C256 generated source after removing its three production build defines. No game installation or release ZIP was changed.

Evidence: c64/ and c256/ summaries, raw per-frameCSV, flags, frame/artifact hashes and kernel logs; isa.json. Tools: Development/HIP/experiments/mh-empty-tile, pinned to147421f for reproducibility. The C64 patch remains research only. Future work should inspect remaining padding consumers or individual C64 call shapes before broadening this shortcut; the current result is not permission to skip padded attention queries without proving their consumers are unused.
