$ErrorActionPreference='Stop'
$r='D:\DLSSNR-Lab\hip-backend';$expected=''
foreach($i in 0..3){
 $m=if($i -in @(1,2)){"$r\c32-register-ex-modules"}else{''}
 & "$r\profile-1080.ps1" -Families none -Tag "regex900-$i" -ExtraFlag DLSS5_NETWORK_HEIGHT=900 -Modules $m -TimingOnly
 $row=Import-Csv "$r\profile1080\regex900-$i-summary.csv"
 if(!$expected){$expected=$row.hash}elseif($expected -ne $row.hash){throw '900 output differs'}
}
