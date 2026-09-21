.LBB48_6:                               ; =>This Inner Loop Header: Depth=1
	s_delay_alu instid0(SALU_CYCLE_1)
	v_add_nc_u32_e32 v37, s13, v36
	v_and_or_b32 v38, s12, 2, v34
	s_lshr_b32 s14, s13, 5
	s_add_co_i32 s13, s13, 16
	s_wait_alu 0xfffe
	s_add_co_i32 s14, s14, s11
	v_and_b32_e32 v45, -4, v37
	v_lshl_or_b32 v37, v38, 7, v35
	s_wait_alu 0xfffe
	s_lshl_b32 s15, s14, 9
	s_add_co_i32 s14, s14, s8
	s_add_co_i32 s12, s12, 2
	s_wait_alu 0xfffe
	s_add_co_i32 s16, s14, s8
	s_wait_kmcnt 0x0
	v_add_co_u32 v43, s18, s6, v37
	s_wait_alu 0xf1ff
	v_add_co_ci_u32_e64 v44, null, s7, 0, s18
	s_lshl_b32 s14, s14, 9
	v_add_co_u32 v37, vcc_lo, v43, s15
	s_wait_alu 0xfffe
	s_lshl_b32 s17, s16, 9
	s_add_co_i32 s16, s16, s8
	s_wait_alu 0xfffd
	v_add_co_ci_u32_e64 v38, null, 0, v44, vcc_lo
	v_add_co_u32 v39, vcc_lo, v43, s14
	s_wait_alu 0xfffe
	s_lshl_b32 s16, s16, 9
	s_wait_alu 0xfffd
	v_add_co_ci_u32_e64 v40, null, 0, v44, vcc_lo
	v_add_co_u32 v41, vcc_lo, v43, s17
	s_wait_alu 0xfffd
	v_add_co_ci_u32_e64 v42, null, 0, v44, vcc_lo
	s_wait_alu 0xfffe
	v_add_co_u32 v43, vcc_lo, v43, s16
	s_wait_alu 0xfffd
	v_add_co_ci_u32_e64 v44, null, 0, v44, vcc_lo
	global_load_b64 v[45:46], v45, s[4:5]
	s_clause 0x3
	global_load_b64 v[37:38], v[37:38], off
	global_load_b64 v[39:40], v[39:40], off
	global_load_b64 v[41:42], v[41:42], off
	global_load_b64 v[43:44], v[43:44], off
	s_cmp_ge_u32 s13, s9
	s_wait_loadcnt 0x3
	v_wmma_f32_16x16x16_fp8_fp8 v[25:32], v[45:46], v[37:38], v[25:32]
	s_wait_loadcnt 0x2
	v_wmma_f32_16x16x16_fp8_fp8 v[17:24], v[45:46], v[39:40], v[17:24]
	s_wait_loadcnt 0x1
	v_wmma_f32_16x16x16_fp8_fp8 v[9:16], v[45:46], v[41:42], v[9:16]
	s_wait_loadcnt 0x0
	v_wmma_f32_16x16x16_fp8_fp8 v[1:8], v[45:46], v[43:44], v[1:8]
	s_cbranch_scc0 .LBB48_6
