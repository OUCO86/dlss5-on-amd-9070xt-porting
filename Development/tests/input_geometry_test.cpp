// Run from the repository root:
// g++ -std=c++17 -O2 Development/tests/input_geometry_test.cpp -o /tmp/input_geometry_test && /tmp/input_geometry_test
#include "../../src/native_input_geometry.h"
#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <utility>

static void require(bool ok, const char* message) {
 if (!ok) { std::cerr << "FAIL: " << message << '\n'; std::exit(1); }
}

static void roundtrip(double pixel, unsigned source, unsigned base, unsigned fit) {
 // Pixel-centre transforms used by decoder and encoder, before edge clamping.
 const double network = base + (pixel + .5) * fit / source - .5;
 const double restored = (network + .5 - base) * source / fit - .5;
 require(std::abs(restored - pixel) < 1e-9, "pixel-centre inverse mapping");
 require(network >= base && network <= base + fit - 1, "decoded sample stays inside viewport");
}

static void check(unsigned w, unsigned h) {
 const auto g = NativeInputGeometry::Make(w,h);
 require(g.width == w && g.height == h, "external extent preserved");
 require(g.fit_width >= w && g.fit_height >= h, "accepted inputs never downsampled");
 require(g.x + g.fit_width <= 1920 && g.y + g.fit_height <= 1080, "viewport contained");
 require(g.fit_width == 1920 || g.fit_height == 1080, "one fitted dimension reaches boundary");
 require(1920 - g.fit_width - g.x >= g.x && 1920 - g.fit_width - 2*g.x <= 1, "horizontal padding balanced");
 require(1080 - g.fit_height - g.y >= g.y && 1080 - g.fit_height - 2*g.y <= 1, "vertical padding balanced");
 const double scale = std::min(1920.0/w, 1080.0/h);
 require(std::abs(g.fit_width - w*scale) <= .50000001 && std::abs(g.fit_height - h*scale) <= .50000001, "aspect rounding limited to half pixel");
 require(g.Adapted() == (w != 1920 || h != 1080), "exact1080 bypass");
 for (unsigned bpp : {4u,8u}) {
  const auto pitch = g.RowPitch(bpp);
  require(pitch % 256 == 0 && pitch >= w*bpp && pitch-w*bpp < 256, "256-byte minimal row pitch");
  const auto last_end = (uint64_t(h)-1)*pitch + uint64_t(w)*bpp;
  require(last_end <= uint64_t(pitch)*h, "last raw pixel within allocation");
 }
 for (double p : {0.0, (w-1)*.5, double(w-1)}) roundtrip(p,w,g.x,g.fit_width);
 for (double p : {0.0, (h-1)*.5, double(h-1)}) roundtrip(p,h,g.y,g.fit_height);
}

static void expected(unsigned w,unsigned h,unsigned x,unsigned y,unsigned fw,unsigned fh) {
 const auto g=NativeInputGeometry::Make(w,h);
 require(g.x==x && g.y==y && g.fit_width==fw && g.fit_height==fh,"known viewport");
 check(w,h);
}

int main() {
 expected(1920,1080,0,0,1920,1080);
 expected(1914,1063,0,7,1920,1066);
 expected(1280,720,0,0,1920,1080);
 expected(1600,900,0,0,1920,1080);
 expected(1440,1080,240,0,1440,1080);
 expected(720,1080,600,0,720,1080);
 expected(1,1,420,0,1080,1080);
 expected(1,1080,959,0,1,1080);
 expected(1920,1,0,539,1920,1);
 require(NativeInputGeometry::Make(1914,1063).RowPitch(4)==7680,"1914 RGBA8 pitch");
 require(NativeInputGeometry::Make(1914,1063).RowPitch(8)==15360,"1914 RGBA16 pitch");
 for (const auto size : {std::pair<unsigned,unsigned>{0,1080},{1920,0},{1921,1080},{1920,1081},{3840,2160},{1080,1920}}) {
  require(!NativeInputGeometry::Supported(size.first,size.second),"unsupported size rejected");
  bool threw=false;
  try { NativeInputGeometry::Make(size.first,size.second); } catch (const std::runtime_error&) { threw=true; }
  require(threw,"Make rejects unsupported size");
 }
 require(!NativeInputGeometry::Supported(std::numeric_limits<uint64_t>::max(),1080),"64-bit width rejected without truncation");
 // Exhaust all accepted sizes: catches odd padding and rounding boundaries.
 for (unsigned h=1;h<=1080;++h) for (unsigned w=1;w<=1920;++w) check(w,h);
 std::cout << "PASS: 2,073,600 accepted sizes; fixed viewport cases, padding, inverse mapping, pitch and rejection checks\n";
}
