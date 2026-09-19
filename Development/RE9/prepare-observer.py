from pathlib import Path
import shutil,difflib
root=Path('/tmp/re9-observer-build')
for d in ['src','Development/HIP','Development/RE9','scripts']:
 (root/d).mkdir(parents=True,exist_ok=True)
 for p in Path(d).glob('*'):
  if p.is_file() and (p.suffix in ['.h','.cpp'] or p.name=='build-addon.sh'):shutil.copy2(p,root/d/p.name)
p=Path('src/native_submission_order_probe.cpp');old=p.read_text();s=old.replace('#include "native_pre_upscale.h"','#include "native_pre_upscale.h"\n#ifdef NATIVE_RE9_OBSERVE_ONLY\n#include "../Development/RE9/re9_ffx_tail_trace.h"\n#endif')
needle=' unsigned n=++frames;log("ffx_begin",got==sizeof(list)?list:nullptr,nullptr,n);'
assert needle in s
s=s.replace(needle,needle+'''
#ifdef NATIVE_RE9_OBSERVE_ONLY
 // Record the original FFX work normally; only arm observation after it returns.
 auto result=original(context,h);ID3D12GraphicsCommandList*native=nullptr;
 if(list&&SUCCEEDED(static_cast<IUnknown*>(list)->QueryInterface(UnwrappedObject,reinterpret_cast<void**>(&native)))&&native){Re9FfxTrace::Arm(native,n,h);native->Release();}
 return result;
#endif
''')
for f,kind in [('compute','dispatch'),('draw','draw'),('draw_indexed','draw_indexed')]:
 pos=s.index('static bool '+f+'(');start=s.index('{',pos)+1
 s=s[:start]+'\n#ifdef NATIVE_RE9_OBSERVE_ONLY\n Re9FfxTrace::Work(reinterpret_cast<void*>(c->get_native()),"'+kind+'");\n#endif\n'+s[start:]
pos=s.index('static void close_list(');start=s.index('{',pos)+1;s=s[:start]+'\n#ifdef NATIVE_RE9_OBSERVE_ONLY\n Re9FfxTrace::Close(reinterpret_cast<void*>(c->get_native()));\n#endif\n'+s[start:]
# Use a distinct local variable to keep the unreachable normal path compilable.
s=s.replace('auto result=original(context,h);ID3D12GraphicsCommandList*native=nullptr;','auto trace_result=original(context,h);ID3D12GraphicsCommandList*native=nullptr;').replace(' return result;\n#endif\n\n#ifdef NATIVE_ORDER_NEURAL',' return trace_result;\n#endif\n\n#ifdef NATIVE_ORDER_NEURAL')
# Ensure the diagnostic return is the trace result (normal hook also has a result later).
a=s.index('// Record the original FFX work normally;');b=s.index('#endif',a);s=s[:a]+s[a:b].replace('return result;','return trace_result;')+s[b:]
s=s.replace('auto s=MH_Initialize();if(s!=MH_OK&&s!=MH_ERROR_ALREADY_INITIALIZED)return 3;', 'auto s=MH_Initialize();if(s!=MH_OK&&s!=MH_ERROR_ALREADY_INITIALIZED)return 3;\n#ifdef NATIVE_RE9_OBSERVE_ONLY\n Re9FfxTrace::InstallNgx();\n#endif')
# This RE9 installation dispatches the upscaler provider directly, bypassing the loader.
old_lookup='module=GetModuleHandleW(L"amd_fidelityfx_dx12.dll");if(!module)module=GetModuleHandleW(L"amd_fidelityfx_loader_dx12.dll");'
assert old_lookup in s
s=s.replace(old_lookup,'module=GetModuleHandleW(L"amd_fidelityfx_upscaler_dx12.dll");')
anchor=' if(!h||(h->type&0x00ffffffu)!=0x00010001u)return original(context,h);'
assert anchor in s
s=s.replace(anchor,'''#ifdef NATIVE_RE9_OBSERVE_ONLY
 {static std::atomic<unsigned>seen{};if(seen.fetch_add(1)<8){Header value{};SIZE_T n=0;ReadProcessMemory(GetCurrentProcess(),h,&value,sizeof value,&n);if(FILE*f=_wfopen(NativeLabPath(L"logs\\\\re9-ffx-tail.txt").c_str(),L"ab")){fprintf(f,"provider_dispatch type=%llx readable=%zu\\n",(unsigned long long)value.type,size_t(n));fclose(f);}}}
#endif
'''+anchor)
s=s.replace('"DLSS5 AMD single-frame verification"','"RE9 FFX ordering observer"')
Path('Development/RE9/observe-ffx-tail.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='a/'+str(p),tofile='b/'+str(p))))
(root/p).write_text('#define NATIVE_RE9_OBSERVE_ONLY 1\n'+s)
