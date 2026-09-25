// Programmatic-dependent-launch emulation test. A chain of kernels on one stream, all launched with
// hipExtAnyOrderLaunch (no AQL barrier bit), each kernel's groups wait on per-group flags published by the
// previous kernel and then do fixed work. Flags carry an epoch so they never need clearing.
//   stage(k): group g waits flags[k-1][g], flags[k-1][g+1] (a 1-wide halo, like a shifted window), then reads
//   data[k-1][g] and data[k-1][g+1] (written by the producer groups AFTER their work: tests visibility, not just
//   ordering), spins `cycles`, writes data[k][g] = f(inputs), then release-fence + atomic store flags[k][g] = epoch.
// Stage 0 has no producer (waits nothing). Host checks data[K-1] against a CPU model and times the chain
// against the same chain launched with the normal barrier bit.
#define DEV __attribute__((device)) __attribute__((always_inline))
DEV unsigned cyc(){return __builtin_amdgcn_s_getreg((29)|(0<<6)|(19<<11));}
DEV void spin(unsigned cycles){unsigned t0=cyc();while(((cyc()-t0)&0xFFFFFu)<cycles)__builtin_amdgcn_s_sleep(2);}
extern "C" __attribute__((global)) __attribute__((amdgpu_flat_work_group_size(256,256)))
void stage(unsigned cycles,unsigned*flags_in,unsigned*flags_out,unsigned*data_in,unsigned*data_out,unsigned epoch,unsigned groups,unsigned*waits,unsigned stride,unsigned sleep){
 unsigned g=__builtin_amdgcn_workgroup_id_x(),t=__builtin_amdgcn_workitem_id_x();unsigned a=0,b=0,polls=0;
 if(flags_in){
  if(t==0){unsigned g1=g+1<groups?g+1:g;
   while(__hip_atomic_load(flags_in+g*stride,__ATOMIC_RELAXED,__HIP_MEMORY_SCOPE_AGENT)!=epoch||__hip_atomic_load(flags_in+g1*stride,__ATOMIC_RELAXED,__HIP_MEMORY_SCOPE_AGENT)!=epoch){if(sleep>=8)__builtin_amdgcn_s_sleep(8);else if(sleep>=4)__builtin_amdgcn_s_sleep(4);else __builtin_amdgcn_s_sleep(1);polls++;}
   __builtin_amdgcn_fence(__ATOMIC_ACQUIRE,"agent");}
  __builtin_amdgcn_s_barrier();
  __builtin_amdgcn_fence(__ATOMIC_ACQUIRE,"workgroup");
  unsigned g1=g+1<groups?g+1:g;a=data_in[g];b=data_in[g1];
 }
 spin(cycles);
 if(t==0){data_out[g]=a*3u+b+g+epoch;__builtin_amdgcn_fence(__ATOMIC_RELEASE,"agent");__hip_atomic_store(flags_out+g*stride,epoch,__ATOMIC_RELAXED,__HIP_MEMORY_SCOPE_AGENT);if(waits)waits[g]=polls;}
}
