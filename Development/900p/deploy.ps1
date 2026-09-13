param([ValidateSet('Deploy','Restore')][string]$Action='Deploy')
$ErrorActionPreference='Stop'
& 'D:\DLSSNR-Lab\network-900p\deploy-magpie.ps1' -Action $Action -StopMagpie -NetworkHeight 900 -Root 'D:\DLSSNR-Lab\network-900p' -SourceAssets 'D:\DLSSNR-Lab\network-720p\DLSS5-AMD\native-game-tiled-assets' -ExpectedAddon '72F87A97BFB3AD5D0EFD3FF11DA56B8FBFB778478BE2DF908E30E43CDCE15FD2'
