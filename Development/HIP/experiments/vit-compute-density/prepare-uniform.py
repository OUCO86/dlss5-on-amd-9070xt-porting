from pathlib import Path
here=Path(__file__).resolve().parent
script=(here/'prepare-seeded.py').read_text()
script=script.replace('seed[e]=float(repeat*8+e+1)*.0625f','seed[e]=repeat==1?.5f:repeat==2?1.f:repeat==3?2.f:repeat==4?4.f:repeat==5?-.5f:repeat==6?-1.f:-2.f').replace("(out/'seeded.hip')","(out/'uniform.hip')")
exec(compile(script,str(here/'prepare-seeded.py'),'exec'),{'__file__':str(here/'prepare-seeded.py')})
