#pragma once
#include <cstdint>
#include <cstring>
#include <stdexcept>
#include <vector>
#include <utility>
namespace hip_reference {
// Lossless encoding only: reject weights requiring quantization or saturation.
inline uint8_t ExactWeightFp8(float value){
 uint32_t bits;std::memcpy(&bits,&value,4);uint32_t a=bits&0x7fffffffu;uint8_t sign=uint8_t((bits>>24)&128u);
 if(!a)return sign;
 if(a>=0x7f800000u)throw std::runtime_error("nonfinite FP8 matrix weight");
 float magnitude;std::memcpy(&magnitude,&a,4);
 if(a<0x3c800000u){float q=magnitude*512.f;if(q<1||q>7||q!=float(uint32_t(q)))throw std::runtime_error("matrix weight not exact FP8 subnormal");return uint8_t(sign|uint8_t(q));}
 int exponent=int(a>>23)-127+7;uint32_t mantissa=(a>>20)&7;
 if(exponent<1||exponent>15||(a&0xfffffu)||(exponent==15&&mantissa==7))throw std::runtime_error("matrix weight not exact finite FP8");
 return uint8_t(sign|(uint8_t(exponent)<<3)|mantissa);
}
// Preserve float-region offsets for scales/bias and separate matrix regions.
// Each matrix becomes row-major FP8 at its original starting byte address.
inline void PackWeightRegions(std::vector<float>&values,const std::vector<std::pair<size_t,size_t>>&regions){
 size_t end=0;for(auto r:regions){if(r.first<end||r.first>values.size()||r.second>values.size()-r.first)throw std::runtime_error("invalid packed matrix region");end=r.first+r.second;}
 auto*bytes=reinterpret_cast<uint8_t*>(values.data());
 for(auto r:regions)for(size_t i=0;i<r.second;i++){
  // Forward packing only overwrites coefficients that have already been read.
  uint8_t encoded=ExactWeightFp8(values[r.first+i]);bytes[r.first*4+i]=encoded;
 }
}
// Reorder packed row-major B into [N/16][K/32][K32][N16], preserving bytes.
inline void TilePackedMatrix(std::vector<float>&v,size_t start,size_t rows,size_t columns){
 if(rows%16||columns%32||start>v.size()||rows*columns>(v.size()-start)*4)throw std::runtime_error("packed tile shape");
 auto*dst=reinterpret_cast<uint8_t*>(v.data()+start);std::vector<uint8_t>src(dst,dst+rows*columns);
 for(size_t n=0;n<rows;n++)for(size_t k=0;k<columns;k++)dst[((n/16)*(columns/32)+k/32)*512+(k%32)*16+n%16]=src[n*columns+k];
}

}
