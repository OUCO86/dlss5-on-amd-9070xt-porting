                                        ; =>This Inner Loop Header: Depth=1
	s_wait_alu 0xfffe
	v_and_or_b32 v101, s12, 2, v131
	s_add_co_i32 s13, s4, 0x800
	v_add_co_u32 v99, vcc_lo, v97, s4
	s_wait_alu 0xfffe
	s_lshr_b32 s13, s13, 5
	v_lshl_or_b32 v101, v101, 7, v0
	s_wait_alu 0xfffe
	s_add_co_i32 s14, s13, s8
	s_add_co_i32 s15, s13, s9
	s_wait_alu 0xfffe
	s_lshl_b32 s14, s14, 9
	s_wait_alu 0xfffd
	v_add_co_ci_u32_e64 v100, null, s5, v98, vcc_lo
	v_add_co_u32 v107, s17, s2, v101
	s_wait_alu 0xf1ff
	v_add_co_ci_u32_e64 v108, null, s3, 0, s17
	s_add_co_i32 s16, s13, s10
	s_lshl_b32 s15, s15, 9
	s_wait_alu 0xfffe
	v_add_co_u32 v101, vcc_lo, v107, s14
	s_add_co_i32 s13, s13, s11
	s_lshl_b32 s16, s16, 9
	s_wait_alu 0xfffd
	v_add_co_ci_u32_e64 v102, null, 0, v108, vcc_lo
	v_add_co_u32 v103, vcc_lo, v107, s15
	s_wait_alu 0xfffe
	s_lshl_b32 s13, s13, 9
	s_wait_alu 0xfffd
	v_add_co_ci_u32_e64 v104, null, 0, v108, vcc_lo
	v_add_co_u32 v105, vcc_lo, v107, s16
	s_wait_alu 0xfffd
	v_add_co_ci_u32_e64 v106, null, 0, v108, vcc_lo
	s_wait_alu 0xfffe
	v_add_co_u32 v107, vcc_lo, v107, s13
	s_wait_alu 0xfffd
	v_add_co_ci_u32_e64 v108, null, 0, v108, vcc_lo
	global_load_b64 v[99:100], v[99:100], off
	s_clause 0x3
	global_load_b64 v[101:102], v[101:102], off
	global_load_b64 v[103:104], v[103:104], off
	global_load_b64 v[105:106], v[105:106], off
	global_load_b64 v[107:108], v[107:108], off
	s_add_nc_u64 s[4:5], s[4:5], 16
	s_add_co_i32 s12, s12, 2
	s_wait_alu 0xfffe
	s_add_co_i32 s13, s4, 0x7f0
	s_wait_alu 0xfffe
	s_cmp_lt_u32 s13, 0xbf0
	s_wait_loadcnt 0x3
	v_wmma_f32_16x16x16_fp8_fp8 v[89:96], v[99:100], v[101:102], v[89:96]
	s_wait_loadcnt 0x2
	v_wmma_f32_16x16x16_fp8_fp8 v[81:88], v[99:100], v[103:104], v[81:88]
	s_wait_loadcnt 0x1
	v_wmma_f32_16x16x16_fp8_fp8 v[73:80], v[99:100], v[105:106], v[73:80]
	s_wait_loadcnt 0x0
	v_wmma_f32_16x16x16_fp8_fp8 v[65:72], v[99:100], v[107:108], v[65:72]
	s_cbranch_scc1 .LBB80_10
