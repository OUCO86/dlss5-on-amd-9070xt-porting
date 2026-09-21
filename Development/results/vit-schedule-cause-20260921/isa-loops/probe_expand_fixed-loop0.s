.LBB76_6:                               ; =>This Inner Loop Header: Depth=1
	s_wait_alu 0xfffe
	v_add_nc_u32_e32 v67, s2, v36
	s_clause 0xe
	global_load_b64 v[37:38], v[33:34], off offset:-768
	global_load_b64 v[39:40], v[33:34], off offset:-512
	global_load_b64 v[41:42], v[33:34], off offset:-256
	global_load_b64 v[43:44], v[33:34], off offset:-49920
	global_load_b64 v[45:46], v[33:34], off offset:-49664
	global_load_b64 v[47:48], v[33:34], off offset:-49408
	global_load_b64 v[49:50], v[33:34], off offset:-49152
	global_load_b64 v[51:52], v[33:34], off offset:-33536
	global_load_b64 v[53:54], v[33:34], off offset:-33280
	global_load_b64 v[55:56], v[33:34], off offset:-33024
	global_load_b64 v[57:58], v[33:34], off offset:-32768
	global_load_b64 v[59:60], v[33:34], off offset:-17152
	global_load_b64 v[61:62], v[33:34], off offset:-16896
	global_load_b64 v[63:64], v[33:34], off offset:-16640
	global_load_b64 v[65:66], v[33:34], off offset:-16384
	s_add_co_i32 s2, s2, 64
	s_wait_alu 0xfffe
	s_cmp_gt_u32 s2, 0x3ef
	v_add_nc_u32_e32 v68, 16, v67
	v_add_nc_u32_e32 v69, 32, v67
	v_add_nc_u32_e32 v71, 48, v67
	v_add_nc_u32_e32 v75, 64, v67
	s_clause 0x2
	global_load_b64 v[67:68], v68, s[4:5]
	global_load_b64 v[69:70], v69, s[4:5]
	global_load_b64 v[71:72], v71, s[4:5]
	global_load_b64 v[73:74], v[33:34], off
	global_load_b64 v[75:76], v75, s[4:5]
	v_add_co_u32 v33, vcc_lo, 0x400, v33
	s_wait_alu 0xfffd
	v_add_co_ci_u32_e64 v34, null, 0, v34, vcc_lo
	s_wait_loadcnt 0x4
	v_wmma_f32_16x16x16_fp8_fp8 v[25:32], v[67:68], v[43:44], v[25:32]
	v_wmma_f32_16x16x16_fp8_fp8 v[17:24], v[67:68], v[51:52], v[17:24]
	v_wmma_f32_16x16x16_fp8_fp8 v[9:16], v[67:68], v[59:60], v[9:16]
	v_wmma_f32_16x16x16_fp8_fp8 v[1:8], v[67:68], v[37:38], v[1:8]
	s_wait_loadcnt 0x3
	v_wmma_f32_16x16x16_fp8_fp8 v[25:32], v[69:70], v[45:46], v[25:32]
	v_wmma_f32_16x16x16_fp8_fp8 v[17:24], v[69:70], v[53:54], v[17:24]
	v_wmma_f32_16x16x16_fp8_fp8 v[9:16], v[69:70], v[61:62], v[9:16]
	v_wmma_f32_16x16x16_fp8_fp8 v[1:8], v[69:70], v[39:40], v[1:8]
	s_wait_loadcnt 0x2
	v_wmma_f32_16x16x16_fp8_fp8 v[25:32], v[71:72], v[47:48], v[25:32]
	v_wmma_f32_16x16x16_fp8_fp8 v[17:24], v[71:72], v[55:56], v[17:24]
	v_wmma_f32_16x16x16_fp8_fp8 v[9:16], v[71:72], v[63:64], v[9:16]
	v_wmma_f32_16x16x16_fp8_fp8 v[1:8], v[71:72], v[41:42], v[1:8]
	s_wait_loadcnt 0x0
	v_wmma_f32_16x16x16_fp8_fp8 v[25:32], v[75:76], v[49:50], v[25:32]
	v_wmma_f32_16x16x16_fp8_fp8 v[17:24], v[75:76], v[57:58], v[17:24]
	v_wmma_f32_16x16x16_fp8_fp8 v[9:16], v[75:76], v[65:66], v[9:16]
	v_wmma_f32_16x16x16_fp8_fp8 v[1:8], v[75:76], v[73:74], v[1:8]
	s_cbranch_scc0 .LBB76_6
