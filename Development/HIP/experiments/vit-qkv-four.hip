// Rejected four-output variant. Replace the corresponding kernel in deep_fast.hip; host groups=count/1024.
WAVE void vit_qkv_project_blocked(const float*in,const float*w,float*out,uint tokens){
 uint perpart=(tokens/16)*16,part=bid()/perpart,local=bid()%perpart,first=local/16*16,row=local%16*64;if(part>=3)return;f8 acc[4]{};
 for(uint k=0;k<1024;k+=16){h8 a{};for(uint e=0;e<8;e++)a[e]=(_Float16)in[(first+rc())*1024+k+gr()*8+e];for(uint j=0;j<4;j++){h8 b{};for(uint e=0;e<8;e++)b[e]=(_Float16)w[part*1048576+(row+j*16+rc())*1024+k+gr()*8+e];acc[j]=__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12(a,b,acc[j]);}}
 for(uint j=0;j<4;j++)for(uint e=0;e<8;e++)out[(part*tokens+first+gr()*8+e)*1024+row+j*16+rc()]=acc[j][e];
}
