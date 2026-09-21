# Step2: C32 post occupancy/LDS tradeoff

prepare.py changes NeedIn16 only for Merge post paths: omit the64×34half input staging array, re-read identical mapped merge input when initializing the residual. Other C32 paths unchanged. Original helper arithmetic includes the sameHrtz boundaries as staging. No format/weight/API changes. Isolated generated module, production untouched.

Build/upload/run as the other C32 probes; baseline post-head-shared-input-modules. Both architectures compile,48 paired frames exact. Compiler actualVGPR158→155; reserved/ForWaves217→169; LDS19712→15360; Occupancy6→8; private0. Normal900/1080 ABBA regresses0.087/0.124ms. Reject. Higher theoretical occupancy is insufficient to offset added reads/logic in this variant; not a universal claim that occupancy never matters.
