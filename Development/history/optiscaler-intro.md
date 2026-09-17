# OptiScaler 是什麼

寫於 2026-09-18，依據：官方倉庫 github.com/optiscaler/OptiScaler（0.9.4，2026-07-18 發布）的 README、wiki、OptiScaler.ini 原文，以及 09-17 夜在 9070 XT 機器上實裝黑神話的過程。沒查證的地方都標了「未驗證」。

## 一句話

OptiScaler 是一個放在遊戲目錄裡的「放大器替換層」：遊戲以為自己在調 DLSS / XeSS / FSR2 / FSR3，其實調到了 OptiScaler，OptiScaler 再把這一幀交給你選的放大器（FSR 4、FSR 3.1、XeSS、DLSS）去算，順便還能塞進遊戲原本沒有的幀生成。

它的價值全在**輸入**：遊戲給放大器的那一整套東西——低分辨率的抖動彩色幀、深度、運動矢量、曝光、反應遮罩——都經它的手。拿到這套輸入，換哪個放大器都是一句配置的事。

## 為什麼 A 卡玩家都在用它

- RX 9070 / 9070 XT 的 FSR 4 只有少數遊戲原生支持。OptiScaler 讓任何有 DLSS 或 FSR2/3 選項的遊戲都能跑 FSR 4，這是它 2025 年爆紅的原因。
- 沒有幀生成的遊戲可以加 FSR-FG 或 XeSS-FG（它管這叫 OptiFG）；有 DLSS-FG 的遊戲可以借 Nukem 的 dlssg-to-fsr3 轉成 FSR3 插幀。
- 原生 FSR 3.1 遊戲可以「熱切換」到 OptiScaler 的放大器（ini 裡 EnableHotSwapping）。

## 它怎麼做到的

三種方式截遊戲的放大器調用（都在 ini 的 `[Inputs]` 段）：

| 遊戲用的是 | OptiScaler 截的東西 | ini 開關 |
|---|---|---|
| DLSS | nvngx.dll 的 NGX 調用；N 卡以外需要「假冒」一張 N 卡讓遊戲露出 DLSS 選項（fakenvapi + Dxgi spoofing） | EnableDlssInputs |
| XeSS | libxess.dll | EnableXeSSInputs |
| FSR 3.1 / FSR 4（ffx_api） | amd_fidelityfx_dx12.dll 的 ffxCreateContext / ffxDispatch | EnableFfxInputs / UseFfxInputs |
| FSR 2 / FSR 3.0（靜態鏈進遊戲 exe 的） | 用特徵碼在內存裡找到函數再掛鉤 | EnableFsr2Inputs / EnableFsr3Inputs / Fsr3Pattern |

輸出端（`[Upscalers]` 段 `Dx12Upscaler=`）：`ffx`（FSR 2.3 / 3.1 / 4.x，走它自帶的 amd_fidelityfx_dx12.dll + amd_fidelityfx_upscaler_dx12.dll）、`xess`、`dlss`、`fsr21`、`fsr22`。RDNA4 上默認自動選 FSR 4。

它自己是個 DLL，靠改名成遊戲會加載的系統 DLL 名字進入進程：`dxgi.dll`（最常用）、`winmm.dll`、`d3d12.dll`、`version.dll`、`dbghelp.dll` 等。裝進去後遊戲一啟動它就在了，Insert 鍵開菜單（`[Menu] ShortcutKey` 可改）。

## 包裡有什麼（0.9.4，55 MB 的 7z）

```
OptiScaler.dll                              主體，要改名
OptiScaler.ini                              1500 行帶註釋的配置，每一項默認 auto
setup_windows.bat / setup_linux.sh          幫你改名、選文件名、處理舊版本
amd_fidelityfx_dx12.dll                     FSR 4 這套（ffx_api 2.3.0 + upscaler 4.1.1 + framegeneration 4.0.1）
amd_fidelityfx_upscaler_dx12.dll
amd_fidelityfx_framegeneration_dx12.dll
amd_fidelityfx_vk.dll
libxess.dll / libxess_dx11.dll / libxess_fg.dll / libxell.dll   XeSS 輸出與 XeSS 插幀
fakenvapi.dll + fakenvapi.ini               假 nvapi：讓 A 卡遊戲露出 DLSS 選項、Reflex 轉 Anti-Lag
dlssg_to_fsr3_amd_is_better.dll             Nukem 的 DLSS-FG → FSR3-FG
D3D12_Optiscaler\D3D12Core.dll              新版 DX12 運行時（FSR 4 需要）
Licenses\                                   FidelityFX、XeSS、DirectX 的許可
```
OptiScaler 本身是 GPL-3。包裡不含任何 NVIDIA 的東西；要 DLSS 輸出得自己放 nvngx_dlss.dll。

## 怎麼裝（官方流程）

1. 全部解壓到遊戲 **真正的 exe** 所在目錄（UE 遊戲是 `xxx\Binaries\Win64`，不是啟動器旁邊）。
2. 跑 `setup_windows.bat`，選一個文件名（默認 dxgi.dll）。目錄裡已經有別的 mod 佔了 dxgi.dll 就選 winmm.dll。
3. 進遊戲，畫面設置裡選 DLSS（A 卡要開 spoofing 才看得到）或 FSR/XeSS，按 Insert 看 OptiScaler 菜單，確認輸入被截到、輸出是你要的放大器。
4. 逐遊戲的坑看 wiki：wiki 有 200 多頁，每個熱門遊戲一頁（黑神話那頁寫著「spoofing 會讓貼圖發藍，改用 OptiPatcher 解鎖 DLSS 輸入」「原生 FSR FG 在 OptiScaler 下會不順」）。

## 和別的 mod 疊加

它有專門一頁講這個：
- **ReShade**：把 ReShade 改名 `ReShade64.dll`，ini 裡 `LoadReshade=true`，OptiScaler 起來後自己加載 ReShade。ReShade 的 addon（.addon64）照常放在同目錄。
- **Special K**、ASI 插件：`plugins` 子目錄或 `LoadSpecialK=true`。
- 另一種是 Ultimate ASI Loader，把大家都改成 .asi 由它統一加載。

## 和 DLSS 5 神經渲染的關係

OptiScaler 本體不認識 DLSS 5。社區的做法是拿它當「輸入整理器」：
- N 卡：Dagherbou 的 OptiScaler fork 把 nvngx_dlssnr.dll 當一個 pass 插在放大之後，不用 ReShade（VideoCardz 2026-09 報道）。
- A 卡：danielblnc 的 DLSS-NR-on-AMD 是一個 version.dll 代理，Detours 鉤 amd_fidelityfx_dx12.dll 的 ffxCreateContext / ffxDispatch，在 FSR 跑完後接神經網絡；和 OptiScaler 拼在一起 = OptiScaler 把任何遊戲變成「FSR 4 遊戲」，他鉤那個 FSR 4。Vodkaman23 的包就是 Dagherbou 的 dxgi.dll 加三份同一個 danielblnc DLL（三遍）。

咱們的 dlss5-amd.addon64 鉤的是同一個位置（amd_fidelityfx_dx12.dll / loader 的 ffxDispatch），所以拼法一樣：OptiScaler 當 dxgi.dll、`Dx12Upscaler=ffx`、`LoadReshade=true`、咱們的 ReShade 改名 ReShade64.dll，addon 和 DLSS5-AMD 文件夾照放。09-17 夜在黑神話上試了一次沒通，但沒通的原因是咱們插件自己的三條劍星專用假設（見 DevHistory 09-18 00:20），以及後來發現的遊戲本身 62 秒黑屏退出（停掉咱們插件也一樣），不是 OptiScaler 的問題。

## 什麼時候需要它、什麼時候不需要

- 遊戲自帶 FSR 3.1 / FSR 4 的 ffx_api DLL 或 XeSS：咱們的插件可以直接鉤，不需要 OptiScaler（劍星、浪人崛起、RE Requiem 屬於這類；但這條在劍星之外還沒真正驗證通過）。
- 遊戲只有 DLSS，或者 FSR 是靜態鏈進 exe 的（黑神話）：需要 OptiScaler 先把它變成 ffx_api 調用。
- 只想在 A 卡上用 FSR 4 / 加插幀、不碰 DLSS 5：OptiScaler 單獨就夠了，這是它的本職。

## 未驗證 / 存疑

- OptiScaler 在 RDNA4 上輸出 FSR 4 時，是否一定經過 amd_fidelityfx_dx12.dll 的 ffxDispatch（09-17 黑神話那次進程裡只加載了 loader + upscaler DLL，沒有 amd_fidelityfx_dx12.dll）。這決定咱們的鉤子能不能截到它的輸出。
- 黑神話 wiki 說 FSR3 輸入可用，但 09-17 沒讓它截到（它自己的日誌當時沒開）。
- 反作弊遊戲一律不行，這點所有這類 mod 都一樣。
