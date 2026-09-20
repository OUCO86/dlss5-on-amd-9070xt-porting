"""Generate a comparison-only build: force all blocks and disable temporal reuse."""
from pathlib import Path
import shutil
root=Path(__file__).resolve().parents[2];out=Path('/tmp/dlss5-full-control')
for folder in ['src','scripts']:shutil.copytree(root/folder,out/folder,dirs_exist_ok=True)
headers=out/'Development/HIP';headers.mkdir(parents=True,exist_ok=True)
for p in (root/'Development/HIP').glob('*.h'):shutil.copyfile(p,headers/p.name)
p=headers/'hip_reference_network.h';s=p.read_text()
old='const char*mode_s=std::getenv("DLSS5_VIT_ADAPTIVE");U mode=mode_s?U(std::stoul(mode_s)):0;'
assert old in s;s=s.replace(old,'U mode=0; // Comparison build: never reuse predicted features.',1)
old='H(opt.height){';assert old in s;s=s.replace(old,'H(opt.height){opt.skip_blocks.clear(); // Comparison build: execute every block.\n',1)
p.write_text(s);print(out)
