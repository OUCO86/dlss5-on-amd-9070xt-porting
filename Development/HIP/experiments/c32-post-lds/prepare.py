from pathlib import Path
import difflib
root=Path(__file__).resolve().parents[4];old=(root/'hip/c32_fused_ffn_attention.hip').read_text()
needle='constexpr bool NeedIn16=Mapped&&!RawMapped;';assert old.count(needle)==1
new=old.replace(needle,'constexpr bool NeedIn16=Mapped&&!RawMapped&&!Merge; // Post merge re-reads its exact input instead of reserving4KiB LDS.')
out=Path('/tmp/c32-post-lds');out.mkdir(exist_ok=True);(out/'c32_fused_ffn_attention.hip').write_text(new)
(root/'Development/HIP/experiments/c32-post-lds/candidate.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/hip/c32_fused_ffn_attention.hip',tofile='b/hip/c32_fused_ffn_attention.hip')))
