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
// Lossless binary16 encoding; reject any weight that would require rounding.
inline uint16_t ExactWeightHalf(float v){uint32_t b;std::memcpy(&b,&v,4);uint32_t a=b&0x7fffffffu;uint16_t sign=uint16_t((b>>16)&0x8000u);if(!a)return sign;if(a>=0x7f800000u)throw std::runtime_error("nonfinite half weight");int e=int(a>>23)-127;if(e>15)throw std::runtime_error("half weight overflow");if(e>=-14){if(a&8191u)throw std::runtime_error("weight not exact half");return uint16_t(sign|((e+15)<<10)|((a>>13)&1023u));}float x=v<0?-v:v,q=x*16777216.f;if(q<1||q>1023||q!=float(uint32_t(q)))throw std::runtime_error("weight not exact half subnormal");return uint16_t(sign|uint16_t(q));}
inline void PackHalfMatrix(std::vector<float>&v,size_t count){if(count>v.size())throw std::runtime_error("half matrix shape");auto*bytes=reinterpret_cast<uint8_t*>(v.data());for(size_t i=0;i<count;i++){uint16_t h=ExactWeightHalf(v[i]);std::memcpy(bytes+i*2,&h,2);}}
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
// Exact structural precondition for the grouped MH contraction fast path.
inline void ValidateGroupedMhContract(const std::vector<float>&v,unsigned c){
 if((c!=64&&c!=128&&c!=256)||v.size()<size_t(8)*c*c)throw std::runtime_error("grouped contract shape");
 for(unsigned row=0;row<c;row++)for(unsigned k=0;k<4*c;k++)if(k/128!=row/32&&v[size_t(4)*c*c+size_t(row)*4*c+k]!=0.f)throw std::runtime_error("nonzero outside grouped contraction");
}
// Reorder packed row-major B into [N/16][K/32][K32][N16], preserving bytes.
// Fragment-native tiles (vit_expand_blocked_fp8_frag_*): same 512-byte (16 rows x 32 k) tiles as TilePackedMatrix, but
// inside a tile the bytes are ordered [k/16 within tile][lane half gr][row%16][8 consecutive k], so the WMMA B operand of
// lane (row%16, gr) at K16 step j is one 8-byte load at ((j*2+gr)*16+row%16)*8. Pure permutation of the same bytes.
inline void FragmentPackedMatrix(std::vector<float>&v,size_t start,size_t rows,size_t columns){
 if(rows%16||columns%32||start>v.size()||rows*columns>(v.size()-start)*4)throw std::runtime_error("packed fragment shape");
 auto*dst=reinterpret_cast<uint8_t*>(v.data()+start);std::vector<uint8_t>src(dst,dst+rows*columns);
 for(size_t n=0;n<rows;n++)for(size_t k=0;k<columns;k++)dst[((n/16)*(columns/32)+k/32)*512+(((k%32)/16*2+(k%16)/8)*16+n%16)*8+k%8]=src[n*columns+k];
}
inline void TilePackedMatrix(std::vector<float>&v,size_t start,size_t rows,size_t columns){
 if(rows%16||columns%32||start>v.size()||rows*columns>(v.size()-start)*4)throw std::runtime_error("packed tile shape");
 auto*dst=reinterpret_cast<uint8_t*>(v.data()+start);std::vector<uint8_t>src(dst,dst+rows*columns);
 for(size_t n=0;n<rows;n++)for(size_t k=0;k<columns;k++)dst[((n/16)*(columns/32)+k/32)*512+(k%32)*16+n%16]=src[n*columns+k];
}

}
