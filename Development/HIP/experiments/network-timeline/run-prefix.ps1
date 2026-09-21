$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\network-timeline";$a='D:\DLSSNR-Lab\Magpie-DLSS5-AMD-0.23\DLSS5-AMD';$m="$r\mh-empty-c256-modules"
foreach($height in 900,1080){
 if(Get-Process LOP-Win64-Shipping,SB-Win64-Shipping,OnimushaWotS,re9,Magpie -ErrorAction SilentlyContinue){throw 'Game running'}
 $folder="$d\$height";$w=if($height -eq 900){1600}else{1920};$h=if($height -eq 900){960}else{1152}
 Push-Location $folder
 try{& "$d\prefix.exe" "$a\native-game-tiled-assets" $m "$folder\flags.txt" "$folder\input.f32" "$folder\expected.f32" $w $h > prefix.log;if($LASTEXITCODE){throw 'Prefix failed'};Get-Content prefix.log}finally{Pop-Location}
}
