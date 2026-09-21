# Expand weight-load scheduling probe

For C128/C256 fused FFN expansion, load four B fragments before issuing their four independent WMMA operations. K accumulation order preserved; no numerical changes. This is same-K load batching, not a claim of achieved cross-iteration software pipelining. prepare.py emits a temporary source/patch; production unchanged. build.ps1 builds both targets and run.ps1 checks48 frame pairs plus900/1080 ABBA against post-head-shared-input-modules.

compare-code.py BASELINE_HSACO CANDIDATE_HSACO compares four active bytein_fb kernel symbol bodies. C256 both variants and C128 mapped are byte-identical; C128 unmapped differs. Net timings show no gain, so candidate not adopted. See results/ffn-expand-prefetch-20260921. Check machine-code changes before measuring similar source-only scheduling proposals.
