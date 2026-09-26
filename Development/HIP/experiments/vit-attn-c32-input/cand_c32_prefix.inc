   // B1 prefix split: fused_prefix_values ran on the g==0 half only (16 lanes idle) and then shipped values 8..15 with eight
   // bpermutes. Here both halves run the same instruction stream on the same token r: the half-wave selects which Box-Muller
   // pair it evaluates (g==1: a,c -> g0; g==0: b,d -> g1,g2), and g0 is the only value exchanged (one bpermute). Each value's
   // operation sequence is identical to fused_prefix_values, so the features, and everything downstream, are bit-identical.
   h8 a{};
   {const float*rgba=reinterpret_cast<const float*>(in);uint p=win*64+qt*16+r,tile=p/64,x=(tile%(width/8))*8+p%8,y=(tile/(width/8))*8+(p%64)/8,rgbp=y*width+x;
    uint h=production_pcg((x*0x8da6b343u)^(y*0xd8163841u)^(seed*0x9e3779b9u)^0x243f6a88u);
    float u1=production_uniform(g?h*0xcaa5b80du+0x21dd796bu:h*0x2c9277b5u+0xac564b05u),u2=production_uniform(g?h*0x83232c31u+0x3463e0acu:h*0xfa6dc5f9u+0x4712a88eu);
    float rr=__builtin_amdgcn_sqrtf(-2.f*(__builtin_amdgcn_logf(u1)*.6931471805599453f)),tt=(6.283185482025146f*u2)*.15915494309189535f;
    float gc=Hrtz(rr*__builtin_amdgcn_cosf(tt)),gs=Hrtz(rr*__builtin_amdgcn_sinf(tt));
    float g0=__builtin_bit_cast(float,__builtin_amdgcn_ds_bpermute((r+16)*4,__builtin_bit_cast(int,gc)));
    float red=Hrtz(Hrtz(Hrtz(rgba[rgbp*4])-.5f)*.125f),green=Hrtz(Hrtz(Hrtz(rgba[rgbp*4+1])-.5f)*.125f),blue=Hrtz(Hrtz(Hrtz(rgba[rgbp*4+2])-.5f)*.125f);
    float hr=red,hg=green,hb=blue;
    if(temporal){uint q=(y*width+x)*4;hr=Hrtz(Hrtz(Hrtz(history[q])-.5f)*.125f);hg=Hrtz(Hrtz(Hrtz(history[q+1])-.5f)*.125f);hb=Hrtz(Hrtz(Hrtz(history[q+2])-.5f)*.125f);}
    const float lo[8]={gc,gs,hg,hb,g0,1,.0078125f,1},hi[8]={red,green,1,1,blue,hr,1,0};
    for(uint e=0;e<8;e++)a[e]=(_Float16)(g?hi[e]:lo[e]);}
