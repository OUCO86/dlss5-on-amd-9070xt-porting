// Fixed-duration kernel for stream/launch experiments. First version spun on __builtin_readsteadycounter (s_sendmsg_rtn
// REALTIME): that message is slow and serialised GPU-wide (a 200us request finished after 2 loop iterations and the
// kernel's wall time scaled with the number of waves), so it measured message contention, not overlap. This version
// waits on the per-wave 20-bit SHADER_CYCLES counter (s_getreg, local, wraps at 2^20) and sleeps between polls so the
// waves hold slots without loading the ALUs: overlap of two launches then shows up directly as shorter wall time.
// `cycles` must stay below 2^19. Thread 0 of each group writes its poll count.
extern "C" __attribute__((global)) __attribute__((amdgpu_flat_work_group_size(256,256))) void spin(unsigned cycles,unsigned*out){
 unsigned t0=__builtin_amdgcn_s_getreg((29)|(0<<6)|(19<<11)) /* HW_REG_SHADER_CYCLES id 29, offset 0, size 20 */;unsigned n=0;
 while(((__builtin_amdgcn_s_getreg((29)|(0<<6)|(19<<11))-t0)&0xFFFFFu)<cycles){__builtin_amdgcn_s_sleep(2);n++;}
 if(__builtin_amdgcn_workitem_id_x()==0)out[__builtin_amdgcn_workgroup_id_x()]=n;
}
