                                        ; =>This Inner Loop Header: Depth=1
	s_wait_alu 0xfffe
	v_and_or_b32 v165, s4, 2, v131
	s_lshr_b32 s12, s5, 5
	v_add_nc_u32_e32 v173, s5, v132
	s_wait_alu 0xfffe
	s_add_co_i32 s13, s12, s8
	s_add_co_i32 s14, s12, s9
	v_lshl_or_b32 v165, v165, 7, v0
	s_wait_alu 0xfffe
	s_lshl_b32 s13, s13, 9
	s_add_co_i32 s15, s12, s10
	s_lshl_b32 s14, s14, 9
	s_add_co_i32 s12, s12, s11
	v_add_co_u32 v171, s16, s2, v165
	s_wait_alu 0xf1ff
	v_add_co_ci_u32_e64 v172, null, s3, 0, s16
	s_wait_alu 0xfffe
	s_lshl_b32 s15, s15, 9
	v_add_co_u32 v165, vcc_lo, v171, s13
	s_wait_alu 0xfffd
	v_add_co_ci_u32_e64 v166, null, 0, v172, vcc_lo
	v_add_co_u32 v167, vcc_lo, v171, s14
	s_lshl_b32 s12, s12, 9
	s_wait_alu 0xfffd
	v_add_co_ci_u32_e64 v168, null, 0, v172, vcc_lo
	s_wait_alu 0xfffe
	v_add_co_u32 v169, vcc_lo, v171, s15
	s_wait_alu 0xfffd
	v_add_co_ci_u32_e64 v170, null, 0, v172, vcc_lo
	v_add_co_u32 v171, vcc_lo, v171, s12
	s_wait_alu 0xfffd
	v_add_co_ci_u32_e64 v172, null, 0, v172, vcc_lo
	global_load_b64 v[173:174], v173, s[0:1]
	s_clause 0x3
	global_load_b64 v[165:166], v[165:166], off
	global_load_b64 v[167:168], v[167:168], off
	global_load_b64 v[169:170], v[169:170], off
	global_load_b64 v[171:172], v[171:172], off
	s_add_co_i32 s12, s5, 16
	s_add_co_i32 s4, s4, 2
	s_cmp_lt_u32 s5, 0xff0
	s_wait_alu 0xfffe
	s_mov_b32 s5, s12
	s_wait_loadcnt 0x3
	v_wmma_f32_16x16x16_fp8_fp8 v[121:128], v[173:174], v[165:166], v[121:128]
	s_wait_loadcnt 0x2
	v_wmma_f32_16x16x16_fp8_fp8 v[113:120], v[173:174], v[167:168], v[113:120]
	s_wait_loadcnt 0x1
	v_wmma_f32_16x16x16_fp8_fp8 v[105:112], v[173:174], v[169:170], v[105:112]
	s_wait_loadcnt 0x0
	v_wmma_f32_16x16x16_fp8_fp8 v[97:104], v[173:174], v[171:172], v[97:104]
	s_cbranch_scc1 .LBB80_12
