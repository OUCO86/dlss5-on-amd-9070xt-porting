from pathlib import Path
here=Path(__file__).resolve().parent;root=here.parents[3];out=Path('/tmp/network-fixed-shapes')
s=(root/'Development/HIP/experiments/vit-schedule-cause/runner.cpp.in').read_text()
s=s.replace(' if(!net.C32ProbeDone())throw std::runtime_error("target not reached");',' ')
x=(root/'src/native_hip_network.h').read_text();a=x.index('hip_reference::Options o;');b=x.index('  const wchar_t*modules=',a)
opts=x[a:b].replace('o.width=g.processing_width;o.height=g.processing_height;o.post_shift=post_shift','o.width=W;o.height=H;o.post_shift=3').replace('o.assets=Utf8(directory)','o.assets=argv[1]')
(out/'raw-check.cpp').write_text(s.replace('/* OPTIONS */',opts).replace('PASS ViT schedule controls','PASS selected module raw output'))
