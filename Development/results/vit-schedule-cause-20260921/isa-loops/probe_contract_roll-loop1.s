                                        ; =>This Inner Loop Header: Depth=1
	s_wait_alu 0xfffe
	v_and_or_b32 v69, s12, 2, v131
	s_add_co_i32 s13, s4, 0x400
	v_add_co_u32 v67, vcc_lo, v65, s4
	s_wait_alu 0xfffe
	s_lshr_b32 s13, s13, 5
	v_lshl_or_b32 v69, v69, 7, v0
	s_wait_alu 0xfffe
	s_add_co_i32 s14, s13, s8
	s_add_co_i32 s15, s13, s9
	s_wait_alu 0xfffe
	s_lshl_b32 s14, s14, 9
	s_wait_alu 0xfffd
	v_add_co_ci_u32_e64 v68, null, s5, v66, vcc_lo
	v_add_co_u32 v75, s17, s2, v69
	s_wait_alu 0xf1ff
	v_add_co_ci_u32_e64 v76, null, s3, 0, s17
	s_add_co_i32 s16, s13, s10
	s_lshl_b32 s15, s15, 9
	s_wait_alu 0xfffe
	v_add_co_u32 v69, vcc_lo, v75, s14
	s_add_co_i32 s13, s13, s11
	s_lshl_b32 s16, s16, 9
	s_wait_alu 0xfffd
	v_add_co_ci_u32_e64 v70, null, 0, v76, vcc_lo
	v_add_co_u32 v71, vcc_lo, v75, s15
	s_wait_alu 0xfffe
	s_lshl_b32 s13, s13, 9
	s_wait_alu 0xfffd
	v_add_co_ci_u32_e64 v72, null, 0, v76, vcc_lo
	v_add_co_u32 v73, vcc_lo, v75, s16
	s_wait_alu 0xfffd
	v_add_co_ci_u32_e64 v74, null, 0, v76, vcc_lo
	s_wait_alu 0xfffe
	v_add_co_u32 v75, vcc_lo, v75, s13
	s_wait_alu 0xfffd
	v_add_co_ci_u32_e64 v76, null, 0, v76, vcc_lo
	global_load_b64 v[67:68], v[67:68], off
	s_clause 0x3
	global_load_b64 v[69:70], v[69:70], off
	global_load_b64 v[71:72], v[71:72], off
	global_load_b64 v[73:74], v[73:74], off
	global_load_b64 v[75:76], v[75:76], off
	s_add_nc_u64 s[4:5], s[4:5], 16
	s_add_co_i32 s12, s12, 2
	s_wait_alu 0xfffe
	s_add_co_i32 s13, s4, 0x3f0
	s_wait_alu 0xfffe
	s_cmp_lt_u32 s13, 0x7f0
	s_wait_loadcnt 0x3
	v_wmma_f32_16x16x16_fp8_fp8 v[57:64], v[67:68], v[69:70], v[57:64]
	s_wait_loadcnt 0x2
	v_wmma_f32_16x16x16_fp8_fp8 v[49:56], v[67:68], v[71:72], v[49:56]
	s_wait_loadcnt 0x1
	v_wmma_f32_16x16x16_fp8_fp8 v[41:48], v[67:68], v[73:74], v[41:48]
	s_wait_loadcnt 0x0
	v_wmma_f32_16x16x16_fp8_fp8 v[33:40], v[67:68], v[75:76], v[33:40]
	s_cbranch_scc1 .LBB80_8
