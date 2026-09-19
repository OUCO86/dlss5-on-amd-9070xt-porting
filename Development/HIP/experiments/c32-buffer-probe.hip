typedef unsigned uint;
extern "C" __attribute__((global)) void probe(const unsigned short*in,unsigned short*readout,unsigned short*storeout,uint*fout,uint n,uint cfg){
 uint i=__builtin_amdgcn_workgroup_id_x()*256+__builtin_amdgcn_workitem_id_x();if(i>=n)return;
 auto r=__builtin_amdgcn_make_buffer_rsrc(const_cast<unsigned short*>(in),0,0x7fffffff,cfg);
 auto w=__builtin_amdgcn_make_buffer_rsrc(storeout,0,0x7fffffff,cfg);
 unsigned short b=__builtin_amdgcn_raw_buffer_load_b16(r,i*2,0,0);readout[i]=b;
 __builtin_amdgcn_raw_buffer_store_b16(in[i],w,i*2,0,0);
 fout[2*i]=__builtin_bit_cast(uint,float(__builtin_bit_cast(_Float16,b)));
 fout[2*i+1]=__builtin_bit_cast(uint,float(reinterpret_cast<const _Float16*>(in)[i]));
}
