# Remaining runs after the 900 repeat/contention sets: regression-order primer sequence, 1080 repeats, PDL timing ABBA.
$d='D:\DLSSNR-Lab\hip-backend\pdl-race'
& "$d\sequence.ps1" -N 30 -Pdl 1 -Out "$d\seq900"
& "$d\repeat.ps1" -N 50 -Heights 1080 -Configs pdl1 -Out "$d\rep1080"
& "$d\abba.ps1" -Rounds 3
