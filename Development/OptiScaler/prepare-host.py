from pathlib import Path
import subprocess,shutil,difflib,json
root=Path(__file__).resolve().parents[2];here=Path(__file__).resolve().parent
host=Path('/tmp/re9-upstream-bridge-review');rev='8f71f73bfc836a37936e7cee6701750ad4e8bfec'
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=host,text=True).strip()==rev
prefix='OptiScaler-DLSSNR-PreSR-Multipass-main/OptiScaler/'
def original(name):return subprocess.check_output(['git','show',rev+':'+prefix+name],cwd=host,text=True)
def write(name,s):
 old=original(name);(host/prefix/name).write_text(s)
 (here/(Path(name).name+'.patch')).write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='a/'+prefix+name,tofile='b/'+prefix+name,n=2)))

# --- LmxxfNrApi.h: ABI v2 ---
name='dlssnr/backend/lmxxf_runtime/LmxxfNrApi.h';s=original(name).replace('#define LMXXF_NR_ABI_VERSION 1u','#define LMXXF_NR_ABI_VERSION 2u')
write(name,s)

# --- LmxxfNrRuntime.cpp ---
name='dlssnr/backend/lmxxf_runtime/LmxxfNrRuntime.cpp';s=original(name)
s=s.replace('(info->struct_size != sizeof(LmxxfNrFrameInfo) && info->struct_size != legacySize)', '(info->struct_size != sizeof(LmxxfNrFrameInfo))')
s=s.replace('JoinPath(dll, L"shaders"),','JoinPath(dll, L"DLSS5-AMD\\native-game-tiled-assets"),\n        JoinPath(dll, L"..\\DLSS5-AMD\\native-game-tiled-assets"),\n        JoinPath(dll, L"shaders"),')
s=s.replace('session->bridge->EnqueueAfterProducer(j->seed, false);','session->bridge->EnqueueAfterProducer(session->queue, j->seed, false);')
s=s.replace('1.f, j->transfer_strength, j->color_strength, j->debug_view);','1.f, NativeCodecParameters{j->transfer_strength, j->color_strength, NativeCodecDebugView(j->debug_view)});')
s=s.replace('    uint32_t state = LMXXF_NR_JOB_NONE;', '    uint32_t state = LMXXF_NR_JOB_NONE;\n    bool hipQueued = false, outputsRecorded = false;')
s=s.replace('        j->state = LMXXF_NR_JOB_NR_COMPLETE;', '        j->hipQueued = true;\n        j->state = LMXXF_NR_JOB_NR_COMPLETE;')
s=s.replace('        j->state = LMXXF_NR_JOB_CONSUMER_COMPLETE;', '        j->outputsRecorded = true;\n        j->state = LMXXF_NR_JOB_CONSUMER_COMPLETE;')
s=s.replace('        if (j)\n            j->state = LMXXF_NR_JOB_RETIRED;', '        if (!j || !j->hipQueued || !j->outputsRecorded)\n            return Fail(LMXXF_NR_INVALID_ARGUMENT, "Retire: producer/HIP/consumer incomplete");\n        session->bridge->NotifyOutputSubmitted(session->queue);\n        j->state = LMXXF_NR_JOB_RETIRED;')
s=s.replace('        if (FAILED(DrainGpu()))','        if ((bridge && !bridge->WaitForSubmittedWork()) || FAILED(DrainGpu()))')
s=s.replace('        NativeResolveNetworkGeometry(info->color_width, info->color_height);','        _wputenv_s(L"DLSS5_CODEC_SRGB", L"0");\n        NativeResolveNetworkGeometry(info->color_width, info->color_height);')
s=s.replace('session->bridge->Create(session->queue, opt, {});', 'session->bridge->Create(session->queue, opt, {});\n            session->bridge->PrepareStagedKernels();')

# Reject unsupported render inputs before changing network globals or allocating HIP.
start=s.index('        if (!session->hipPrepared)\n', s.index('int32_t PrepareFrame('))
end=s.index('        auto *color =', start)
s=s[:start]+s[end:]
start=s.index('        auto *color =', s.index('int32_t PrepareFrame('))
end=s.index('        const bool geoChanged', start)
validation=s[start:end]
s=s[:start]+s[end:]
validation += r'''        {
            static const bool fitLarge = [&] {
                unsigned v = 0;
                if (const char *e = std::getenv("DLSS5_FIT_LARGE")) return e[0] == '1' && !e[1];
                std::wstring dir = session->assetsDir;
                for (int up = 0; up < 4 && !dir.empty(); up++)
                {
                    const std::wstring flags = JoinPath(dir, L"native-game-flags.txt");
                    if (FILE *f = _wfopen(flags.c_str(), L"rb")) { char line[256]; while (fgets(line, sizeof line, f)) sscanf(line, "DLSS5_FIT_LARGE=%u", &v); fclose(f); break; }
                    const size_t cut = dir.find_last_of(L"\\/"); if (cut == std::wstring::npos) break; dir.resize(cut);
                }
                return v == 1;
            }();
            if (fitLarge)
                NativeFitLargeInputOverride() = true;
        }
        if (!NativeInputGeometry::Supported(cdesc.Width, ch, NativeFitLargeInput()))
        {
            char message[192] {};
            std::snprintf(message, sizeof message,
                          "PrepareFrame: render input %llux%u exceeds supported limit 1920x1080 (DLSS5_FIT_LARGE=0); original SR",
                          static_cast<unsigned long long>(cdesc.Width), ch);
            return Fail(LMXXF_NR_INVALID_ARGUMENT, message);
        }
        if (cw != info->color_width || ch != info->color_height)
            return Fail(LMXXF_NR_INVALID_ARGUMENT, "PrepareFrame: render input metadata/texture size mismatch; original SR");
        if (cdesc.Dimension != D3D12_RESOURCE_DIMENSION_TEXTURE2D || cdesc.DepthOrArraySize != 1 ||
            cdesc.MipLevels != 1 || cdesc.SampleDesc.Count != 1 ||
            (cdesc.Flags & D3D12_RESOURCE_FLAG_DENY_SHADER_RESOURCE) ||
            !(NativeIsGameColor(cfmt) || cfmt == DXGI_FORMAT_R9G9B9E5_SHAREDEXP))
            return Fail(LMXXF_NR_INVALID_ARGUMENT, "PrepareFrame: unsupported render input texture; original SR");
        if (session->initializationBlocked)
            return Fail(LMXXF_NR_FAILED, "PrepareFrame: failed initialization could not drain safely; original SR");
        if (session->job.state != LMXXF_NR_JOB_NONE && session->job.state != LMXXF_NR_JOB_RETIRED)
            return Fail(LMXXF_NR_INVALID_ARGUMENT, "PrepareFrame: previous frame not retired; original SR");

'''
s=s.replace('        // Match upstream auto tier:', validation+'        // Match upstream auto tier:',1)
s=s.replace('    bool hipPrepared = false;', '    bool hipPrepared = false;\n    bool initializationBlocked = false;')

# Bring lazy bridge creation into the same transaction as the codec chain.
start=s.index('            if (!session->bridge)', s.index('int32_t PrepareFrame('))
end=s.index('            NativeGameCodec *enc',start)
bridge=s[start:end]
s=s[:start]+s[end:]
s=s.replace('                enc = new NativeGameCodec();', bridge+'                enc = new NativeGameCodec();',1)
s=s.replace('                delete enc;\n                throw;', r'''                delete enc;
                if (!session->bridge || session->bridge->WaitForSubmittedWork())
                {
                    session->TeardownCodecChain();
                    session->job = {};
                }
                else
                    session->initializationBlocked = true;
                throw;''',1)
write(name,s)

# --- LmxxfProductionOptions.h ---
name='dlssnr/backend/lmxxf_runtime/LmxxfProductionOptions.h';s=original(name).replace('    return o;','    o.mh_feature_byte=o.mh_proj_diag_fb=o.mh_byte_stream=o.decoder_byte=o.mh_ffn_frag256=true;\n    return o;');write(name,s)

# --- LmxxfBackend.cpp ---
name='dlssnr/backend/LmxxfBackend.cpp';s=original(name)
s=s.replace('    const auto nextToDll = directory / L"lmxxf-modules";','    for(const auto& base : {directory, directory.parent_path()}){\n        const auto bundled=base / L"DLSS5-AMD" / L"native-game-tiled-assets" / L"HIP";\n        if(std::filesystem::exists(bundled / L"SHA256SUMS"))return bundled;\n    }\n    const auto nextToDll = directory / L"lmxxf-modules";')
s=s.replace('    LmxxfCut::ClearPendingEnqueue();\n    pendingJob = nullptr;','    if(pendingJob){SetStatus("lmxxf: prior job not yet submitted; original SR");return nullptr;}\n    LmxxfCut::ClearPendingEnqueue();\n    pendingJob = nullptr;',1)
s=s.replace('void LmxxfBackend::Submitted(ID3D12CommandQueue *, UINT, ID3D12CommandList *const *)\n{','void LmxxfBackend::Submitted(ID3D12CommandQueue *submittedQueue, UINT, ID3D12CommandList *const *)\n{\n    if(DlssNr::Submission::InsideLogicalExecute() || submittedQueue != queue || LmxxfCut::Pending().job)return;')
s=s.replace('        api->table.Retire(session, pendingJob);','        const auto rc=api->table.Retire(session, pendingJob);\n        if(rc != LMXXF_NR_OK){SetStatus("lmxxf: consumer retirement failed");return;}')
s=s.replace('const bool rebindish = frameRc == LMXXF_NR_UNAVAILABLE || (err[0] && (std::strstr(err, "rebind") || std::strstr(err, "geometry")));', 'const bool rebindish = frameRc != LMXXF_NR_INVALID_ARGUMENT && (frameRc == LMXXF_NR_UNAVAILABLE || (err[0] && (std::strstr(err, "rebind") || std::strstr(err, "geometry"))));')
write(name,s)

# --- AmdBridge.cpp ---
name='dlssnr/amd/AmdBridge.cpp';s=original(name).replace('    return std::filesystem::exists(Directory() / L"dlssnr_amd_pass1.dll", ec);','    if(DlssNr::Backend::RequestedKind()==DlssNr::Backend::Kind::Lmxxf)\n        return std::filesystem::exists(Directory() / L"LmxxfNrRuntime.dll", ec);\n    return std::filesystem::exists(Directory() / L"dlssnr_amd_pass1.dll", ec);');write(name,s)

# --- ResourceStateBook.h ---
name='dlssnr/submission/ResourceStateBook.h';s=original(name)
s=s.replace('                if (reasonOut)\n                    *reasonOut = "aliasing_barrier";\n                return false;','                if (openSplitBarrier || bar.Flags != D3D12_RESOURCE_BARRIER_FLAG_NONE)\n                {\n                    if (reasonOut) *reasonOut = "aliasing_during_split_transition";\n                    return false;\n                }\n                continue;',1)
s=s.replace('        if (sawAliasing)\n        {\n            if (reasonOut)\n                *reasonOut = "aliasing_barrier";\n            return false;\n        }\n','')
write(name,s)

# Copy core headers/shaders
for folder,patterns in [('src',('*.h',)),('Development/HIP',('*.h',)),('shaders',('*.hlsl','*.hlsli'))]:
 target=host/'third_party/lmxxf'/folder;target.mkdir(parents=True,exist_ok=True)
 for pattern in patterns:
  for p in (root/folder).glob(pattern):shutil.copyfile(p,target/p.name)
shutil.copyfile(root/'LICENSE',host/'third_party/lmxxf/LICENSE')
(here/'upstream.json').write_text(json.dumps({'repository':'https://github.com/TheAutomatic/dlss-5-amd-project','branch':'release/1.9.0','commit':rev,'core_base':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'host_license':'GPL-3.0 (retained upstream)','core_license':'MIT'},indent=2)+'\n')
for patch in here.glob('lmxxf_*.cpp.patch'):
    subprocess.run(['patch','-p1','-d',str(host)],stdin=open(patch),check=True)

print('prepared external host',rev)
