.LBB80_6:                               ; =>This Inner Loop Header: Depth=1
	v_and_or_b32 v37, s12, 2, v131
	s_lshr_b32 s13, s4, 5
	v_add_co_u32 v35, vcc_lo, v33, s4
	s_wait_alu 0xfffe
	s_add_co_i32 s14, s13, s8
	v_lshl_or_b32 v37, v37, 7, v0
	s_add_co_i32 s15, s13, s9
	s_wait_alu 0xfffe
	s_lshl_b32 s14, s14, 9
	s_wait_alu 0xfffd
	v_add_co_ci_u32_e64 v36, null, s5, v34, vcc_lo
	v_add_co_u32 v43, s17, s2, v37
	s_wait_alu 0xf1ff
	v_add_co_ci_u32_e64 v44, null, s3, 0, s17
	s_add_co_i32 s16, s13, s10
	s_lshl_b32 s15, s15, 9
	s_wait_alu 0xfffe
	v_add_co_u32 v37, vcc_lo, v43, s14
	s_add_co_i32 s13, s13, s11
	s_lshl_b32 s16, s16, 9
	s_wait_alu 0xfffd
	v_add_co_ci_u32_e64 v38, null, 0, v44, vcc_lo
	v_add_co_u32 v39, vcc_lo, v43, s15
	s_wait_alu 0xfffe
	s_lshl_b32 s13, s13, 9
	s_wait_alu 0xfffd
	v_add_co_ci_u32_e64 v40, null, 0, v44, vcc_lo
	v_add_co_u32 v41, vcc_lo, v43, s16
	s_wait_alu 0xfffd
	v_add_co_ci_u32_e64 v42, null, 0, v44, vcc_lo
	s_wait_alu 0xfffe
	v_add_co_u32 v43, vcc_lo, v43, s13
	s_wait_alu 0xfffd
	v_add_co_ci_u32_e64 v44, null, 0, v44, vcc_lo
	global_load_b64 v[35:36], v[35:36], off
	s_clause 0x3
	global_load_b64 v[37:38], v[37:38], off
	global_load_b64 v[39:40], v[39:40], off
	global_load_b64 v[41:42], v[41:42], off
	global_load_b64 v[43:44], v[43:44], off
	s_add_nc_u64 s[4:5], s[4:5], 16
	s_add_co_i32 s12, s12, 2
	s_wait_alu 0xfffe
	s_add_co_i32 s13, s4, -16
	s_wait_alu 0xfffe
	s_cmp_lt_u32 s13, 0x3f0
	s_wait_loadcnt 0x3
	v_wmma_f32_16x16x16_fp8_fp8 v[25:32], v[35:36], v[37:38], v[25:32]
	s_wait_loadcnt 0x2
	v_wmma_f32_16x16x16_fp8_fp8 v[17:24], v[35:36], v[39:40], v[17:24]
	s_wait_loadcnt 0x1
	v_wmma_f32_16x16x16_fp8_fp8 v[9:16], v[35:36], v[41:42], v[9:16]
	s_wait_loadcnt 0x0
	v_wmma_f32_16x16x16_fp8_fp8 v[1:8], v[35:36], v[43:44], v[1:8]
	s_cbranch_scc1 .LBB80_6
