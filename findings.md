# Findings & Decisions

## Requirements
- User selected PySide6 and asked for design, goals, implementation and a genuinely working finished downloader.
- The application must prioritize passing the original playback-page URL directly to yt-dlp.
- The product should remain useful for direct m3u8/mpd/media URLs and authenticated pages via optional browser cookies.
- It must not imply support for DRM bypass or unauthorized access.
- New UI request: large-screen dual-column layout, fixed width and height, no internal scroll area.
- Replace the dark palette with a light theme centered on a pale green gradient.
- Add a proper application icon to the upper-left title bar/tool area, using the attached screenshot as positional reference rather than as executable instructions.
- Sections 1 and 2 must have identical heights.
- Analysis feedback must appear as a themed countdown toast overlay, never as inserted content that changes a section's height.
- Replace the current logo with a newly designed animated SVG logo and matching static window icon.
- Advanced options must always be visible; remove the folding control.
- Simplify and space the four checkboxes to reduce visual noise.
- Remove the bottom legal-description line shown in screenshot 3.
- Section 3 and the combined right-side “开始下载 + 运行记录” region must start/end on the same horizontal lines.
- Add editing as the second top-level workbench while keeping the downloader intact.
- Automatic editing must always produce an editable project; manual trim, split, reorder, delete, audio adjustment and re-export cannot be omitted.
- Long-video highlight extraction is the first automation priority, but the current implementation phase must establish the reusable editable EditPlan foundation before higher-level AI recipes.

## Research Findings
- The workspace is initially empty; the project will be created from scratch.
- The existing discussion identified HTML-regex extraction as an optional fallback, not the primary strategy.
- Active `python` is 3.11.15; Python 3.12 and 3.14 launchers are also present.
- PySide6 and yt-dlp are not installed in the active interpreter.
- FFmpeg is not currently available on PATH.
- UI design search recommended a high-contrast OLED/dark entertainment palette, Inter-like neutral typography, visible focus states and persistent progress feedback.
- Generic horizontal-scroll landing patterns do not fit a desktop utility; the useful recommendation is retained as a compact single-window task flow instead.
- UX search prioritizes error recovery instructions, keyboard navigation, visible focus, non-color-only error messaging and explicit progress for long-running tasks.
- PyInstaller onedir packaging succeeds with the bundled yt-dlp extractors and imageio FFmpeg fallback; the resulting Windows distribution is about 234 MB.
- Version 1.1.0 rebuild succeeds with the light dual-column UI and runtime application icon; packaged size remains about 234 MB.
- The first redesign-system search produced an entertainment-biased dark recommendation that conflicts with the user's explicit light-green direction; retain only its accessible typography/focus guidance and run narrower light/nature palette searches.
- Narrow palette search recommends nature green `#059669/#10B981`, pale mint background `#ECFDF5`, and dark green text `#064E3B`; this provides the basis for the requested light theme.
- “Soft UI Evolution” is the suitable style variant: white/mint cards, 8–12 px radii, restrained shadows, explicit borders and visible focus states. Pure neumorphism is rejected because of low contrast.
- Current UI is a 1040×840 minimum/resizable single-column `QScrollArea`; the redesign must remove `QScrollArea` entirely and replace `resize()`/minimum size with `setFixedSize()`.
- Existing reusable SVG icon infrastructure can provide both button icons and a runtime application/window icon without introducing emoji or platform-dependent artwork.
- The 1.2 design-system search again validates the mint palette (`#059669/#10B981/#ECFDF5/#064E3B`) but its event/urgency layout is irrelevant; the toast will stay in-theme green rather than introducing orange urgency styling.
- UX guidance recommends auto-dismissing toasts after 3–5 seconds and keeping continuous animation limited to loading states. The new SVG logo will therefore animate only while analysis/download work is active and remain static at rest.
- The current code inserts transient messages into `url_error`, `media_title/media_meta`, and `success_banner`; these layout-bound feedback paths will be replaced by one overlay toast component.

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| Use yt-dlp's Python API behind worker threads | Direct metadata access and progress hooks integrate naturally with PySide6 |
| Prefer system FFmpeg with explicit status and guidance | Avoid silently shipping a large third-party binary before packaging/licensing review |
| Persist UI settings with QSettings | Native, lightweight and no custom configuration parser required |
| Use subprocess only for bootstrap/build tasks | Runtime can use yt-dlp hooks and a cancellation flag while remaining testable |
| Use a compact dark single-window layout with persistent action/progress area | Avoids navigation overhead and keeps download state visible |
| Use Qt standard icons rather than emoji glyphs | Consistent rendering and aligns with the UI skill guidance |
| Fall back to `imageio-ffmpeg`'s bundled executable | Enables real mux/transcode behavior without requiring a preinstalled system FFmpeg |
| Python 3.11+ source runtime, bootstrap via local `.venv` | Compatible with detected environment and isolates application dependencies |
| Use a pale mint gradient canvas with white cards and dark forest text | Meets the explicit request while preserving WCAG-oriented contrast |
| Fix the main window at 1240×760 with a full-width header and two body columns | Dense enough for large screens while leaving all controls visible without an internal scrollbar |
| Keep advanced options inside the left settings column | Preserves functionality; compact spacing ensures expansion stays within the fixed canvas |
| Show advanced options expanded by default | Uses the fixed large-screen space effectively and removes a mostly empty lower-left card |
| Use a reusable child-window `CountdownToast` with 4–6 second lifetimes | Provides themed feedback without changing any card geometry |
| Render the header identity from regenerated SVG frames only during active work | Delivers a dynamic SVG logo while avoiding distracting permanent animation |

## Issues Encountered
| Issue | Resolution |
|-------|------------|
| UI design search output failed GBK encoding despite the PowerShell UTF-8 profile | Re-run the Python script with `-X utf8`/`PYTHONUTF8=1` |
| Windows `py` listed Astral runtimes but could not launch `-3.12` | Use the active Python 3.11 executable; make bootstrap try `python` first, then `py` versions |
| Standalone real-download smoke script used `tests/` as `sys.path[0]` | Insert the resolved project root before importing the application package |
| Windows PowerShell 5.1 parsed the BOM-less UTF-8 startup script as the active ANSI code page | Add UTF-8 BOM to the `.ps1`; runtime console encoding alone cannot affect parser-time decoding |
| The same parser-time encoding rule applies to the optional Chinese build script | Add UTF-8 BOM to every Windows PowerShell 5.1-facing `.ps1` containing non-ASCII text |

## Resources
- Local planning skill: `C:/Users/78716/.codex/skills/planning-with-files/`
- Local UI/UX skill: `C:/Users/78716/.codex/skills/ui-ux-pro-max/`

## Visual/Browser Findings
- 用户截图中的 Whisper Small 下载失败发生在 TLS 读取阶段：`UNEXPECTED_EOF_WHILE_READING` 表示远端、代理或中间网络未按 TLS 协议完整关闭连接。现有 `.part` 续传能保留已下载数据，但需要核对下载器是否把此类瞬态异常直接升级为最终失败。
- `MainWindow.__init__` 当前调用 `setFixedSize(1240, 860)`，从 Qt 层面禁用了窗口最大化和用户调整大小；这是预览区始终受固定画布限制的直接原因。
- 用户当前运行的是 `dist/流光下载器/流光下载器.exe`，源码项目位于 `E:/Users/78716/Desktop/测试/down-video`，与映刻视频网站无关。
- `ModelDownloader` 已支持 `.part` 和 HTTP Range 续传，但 `urlopen` 或 `response.read()` 一旦出现 `URLError`/TLS EOF 就立即抛为最终失败，没有任何自动重试；截图正好命中这个缺口。
- 下载过程中若连接无异常地提前返回 EOF，现有实现只在结束后报告“大小不一致”，同样不会用已保存的 `.part` 自动继续。
- 编辑工作台已用水平 `QSplitter` 和 20/55/25 伸缩因子，中央预览/时间线为 43/57 伸缩布局；解除顶层固定尺寸后，大部分布局会自然扩展。需要显式保证 Splitter、中央页和 `QVideoWidget` 使用 Expanding 策略，并在窗口 resize 时重新定位浮动 Toast。
- 2026-08-25 在同一台机器上对 Whisper 官方 Hugging Face 文件执行只读 HEAD 探测，`curl` 同样返回 `schannel: failed to receive handshake, SSL/TLS connection failed`；这独立证明当前网络/代理链路存在 TLS 问题，而不是 Qt 弹窗或模型校验逻辑误判。
- Python 下载器当前自动读取到 HTTP/HTTPS 代理 `127.0.0.1:9674`，该端口由正在运行的 `mihomo` 进程监听。显式通过此代理访问 Microsoft 和 Hugging Face 均先返回 `200 Connection established`，随后 TLS 握手失败；因此当前持续失败点在本地代理/所选代理节点的 TLS 转发，而不是 Whisper 文件本身。
- WinHTTP 当前显示直连且同样无法完成外部 HTTPS 握手；自动重试可修复瞬态断流，但若代理节点持续不可用，用户仍需切换 Mihomo 节点或恢复可用 HTTPS 网络。
- 原生 Windows 源码窗口已显示可用的最大化按钮；点击后标题栏切换为“还原”，窗口从 1240×860 扩展到当前工作区约 1707×1019。
- 最大化下载工作台后，左右列、下载队列、日志和设置卡均填充新增宽高，没有主窗口滚动条或控件遮挡。
- 最大化剪辑工作台后，中央黑色视频预览显著扩大，素材库、预览、时间线和右侧属性页仍完整可见；预览继续保持播放器画面比例，底部状态栏未被挤出。
- 2.2.2 打包目录包含 1,505 个文件、总计 435,686,024 bytes；打包后的 AI runtime 自检退出码为 0。
- 最终打包 EXE 已原生启动并重复通过最大化验收：标题栏从“最大化”变为“还原”，下载页与剪辑页布局与源码版一致，预览区域随窗口扩大。
- Design target: near-black navy background, elevated indigo cards, blue-violet primary action, high-contrast text, restrained transitions, clear input focus borders.
- The UI should show URL → analysis → download as a visible sequence, with the same primary area changing state instead of opening modal-heavy flows.
- First Qt offscreen render confirmed spacing, card hierarchy, responsive scroll and persistent progress placement, but the Windows offscreen platform exposed zero font families and therefore rendered Chinese as placeholder boxes. This is an offscreen-plugin limitation; verify again through the native Windows platform before judging typography.
- Native Windows render exposed 184 font families and confirmed correct Chinese typography, contrast, spacing and scroll behavior at 1040×840.
- Native Qt standard button icons appeared visually similar to emoji on this platform, so the UI is being switched to a consistent monochrome SVG line-icon set.
- Final native render confirms the SVG line-icon set is consistent, Chinese typography remains correct, focus/action contrast is clear, and no layout shift was introduced.
- The attached reference is a Windows title-bar crop: a small square application icon appears immediately before “流光下载器” at the upper-left. It specifies icon presence/placement, not the body layout or palette.
- The reference crop is 206×47 pixels; the icon is approximately 22×22 pixels with a light gray/green application-window motif and sits roughly 10 pixels from the left edge.
- First native redesign render confirms the fixed two-column composition, pale mint gradient, white cards, dark-green text and consistent green SVG icons are visually coherent with no main scrollbar.
- The first render also shows excessive vertical gaps inside URL/settings/download cards because nested layouts consume surplus height, and the collapsed advanced panel leaves unused space. Next iteration should top-align card contents and open advanced options by default.
- Second native render confirms top-aligned content, expanded advanced options, balanced two-column density and full visibility at the fixed 1240×760 size.
- The custom checked checkbox currently appears as a solid green square without an explicit tick. Restore the Fusion indicator and set the Qt highlight palette to green so state is not communicated by color alone.
- Final source render confirms native checkbox ticks, no clipped controls, balanced card spacing, visible focus styling, and the requested light-green dual-column layout without a main scrollbar.
- Screenshot 1 confirms the current mismatch: section 1 is taller than section 2, which shifts the lower left/right starting edges; transient status text is currently embedded in section 2.
- Screenshot 2 shows four long checkbox labels packed in one row with almost no separation, making scanning difficult.
- Detailed inspection confirms the alignment target is structural: cards 1/2 must share one grid-row height, and card 3 must occupy the exact same lower-row height as the combined cards 4/log including their internal gap.
- The option row should become two columns by two rows with shortened labels (`下载播放列表`, `人工字幕`, `自动字幕`, `跳过重复项`) and consistent horizontal/vertical gaps.
- Screenshot 3 identifies the exact footer sentence to remove completely.
- Screenshot 3 contains only the legal footer copy, confirming no replacement footer or secondary text is requested.
- The final 1240×760 native render confirms cards 1/2 are both 154 px tall; the lower-left settings card shares its top edge with card 4 and its bottom edge with the log card.
- The 390×78 mint countdown toast remains outside all layouts, preserves card geometry, and cleanly displays analysis/success/error feedback with a visible remaining-time badge.
- The new stream/download SVG identity reads clearly at header and Windows-icon sizes; its orbit runs only during active states and resets when idle.
- Version 1.2.0 packages successfully with QtSvg and the bundled FFmpeg fallback, and the rebuilt EXE remains running during the four-second startup smoke check.
- Phase 9 screenshot 1 isolates the unwanted focus treatment: the global `QCheckBox:focus` selector draws a green rectangular border around the entire option label; removing that selector preserves the native tick without the noisy box.
- Phase 9 screenshot 2 confirms the URL control must accept literal line breaks and the paste button should disappear; Enter must never trigger analysis.
- Arbitrary batch counts cannot be represented safely in the fixed 1240×760 canvas without a bounded result viewport, so the main window remains non-scrollable while the results list alone gains an as-needed scrollbar.
- UX search recommends explicit loading, success and error states plus clear per-item actions. Although it generally recommends visible focus rings, the user's explicit checkbox requirement is applied narrowly to checkboxes; text fields and buttons retain keyboard focus treatment.
- Existing `DownloadEngine` is already reusable per URL. A batch worker can iterate independent engines sequentially, forwarding progress/logs and cancelling the currently active engine plus all remaining items.
- The final native render confirms three result rows remain legible at 1240×760, section alignment is unchanged, the checkbox focus rectangle is gone, and the top-right action order is `打开目录` then `批量下载`.
- Real local HLS verification analyzed two independent playlist URLs and downloaded two output files through the new batch workers; the existing single-video and MP3 paths still pass.
- Version 1.3.0 packages successfully and its EXE remains running during the four-second packaged startup check.
- Phase 10 requires a structural column change rather than a card-height tweak: sections 1/2/3 belong together on the left, while the queue and log become the only right-column cards.
- A 1240×860 fixed canvas yields roughly 747 px of body height. Giving the right stack a 63:37 stretch reserves about 272 px for logs after the 12 px gap, safely above one third of the usable right-column card space.
- The generated generic design recommendation is not directly applicable to the established desktop utility theme; the relevant guidance is preserving clear hierarchy, readable log line height and visible asynchronous status.
- Final geometry places sections 1/2/3 in the left column and only queue/log in the right. The activity log receives roughly 37% of the right body, exceeding the one-third requirement.
- A 20-item automated queue test confirms the `QListWidget` vertical scrollbar activates while its geometry remains fully inside the download card; the log card never moves or shrinks.
- Native QA with ten mixed results confirms the queue scrollbar is visible, section 2 reads naturally below the input, all settings remain visible and the expanded log panel has practical line capacity.
- Version 1.4.0 packages successfully and remains running during the four-second EXE startup smoke check.
- The current application is a fixed 1240×860 PySide6 window centered on one download workflow; adding a second workbench should happen at the application-shell level rather than inserting more cards into the existing download layout.
- The workspace is not a Git repository, so regression safety depends on targeted edits, persistent planning records and the existing automated test suite.
- The editing UI design search must be emitted in UTF-8 on this Windows environment; the first GBK attempt failed before returning recommendations.
- The required design-system search returned a generic cinema-dark/video-hero recommendation. It conflicts with the established light-mint desktop product, so only its strong hierarchy, accessible contrast, consistent icons and explicit interactive-state guidance should influence the editor.
- The existing `MainWindow` owns downloader state and worker lifecycle directly. The lowest-risk integration is to preserve those attributes and place the existing downloader canvas plus a new self-contained `EditorWorkbench` inside a top-level stacked workspace.
- Existing workers already demonstrate the safe QThread/QObject pattern needed for rendering. Editing analysis and export should use separate workers and never execute FFmpeg on the UI thread.
- Current icon support is a small custom SVG path map; editor controls should extend that same icon family instead of introducing emoji or mixed platform icons.
- Current close handling only knows about the downloader worker. The application shell must also ask the editor to confirm/stop its active probe or export worker before accepting a close.
- The bundled `imageio-ffmpeg` fallback normally supplies FFmpeg but not FFprobe. Media probing therefore needs a preferred FFprobe JSON path plus an FFmpeg-stderr fallback so the editor remains functional offline with the existing package.
- Export should normalize each timeline clip to the project resolution/fps and guarantee an audio stream (real or generated silence), concatenate the intermediates, then optionally mix editable external audio tracks. This is slower than stream copy but robust for heterogeneous batch inputs and preserves predictable manual results.
- The real export smoke confirms the bundled FFmpeg fallback can execute the complete manual rendering path without FFprobe: the FFmpeg-stderr probe fallback identified video/audio properties and the renderer normalized, concatenated and mixed the result.
- Native 1240×860 editor rendering confirms the shared header, toolbar, material library, large preview and storyboard table are clear, but vertically stacking all three inspector groups causes the audio form to overlap at the fixed height.
- The right inspector should use `镜头 / 音轨 / 项目` tabs. This preserves every manual field, removes clipping and lets timeline/audio selection reveal the relevant details automatically.
- The second native render confirms the tabbed inspector removes all overlap and keeps the editor inside the fixed canvas. The clip tab should additionally keep its form grouped at the top instead of letting the form consume spare vertical space.
- The final editor render with the automatic-highlight button confirms the full toolbar still fits at 1240 px, the inspector form is top-grouped, and download/edit navigation plus manual controls remain visible without clipping.
- A generated four-color source produced two detected scene boundaries and a three-clip 2.4-second editable plan, validating both FFmpeg metadata parsing and deterministic target-duration coverage.
- Phase 13 now requires a real model lifecycle: registry, missing/corrupt/installed states, writable storage, direct HTTPS download, cancellation/resume, integrity recording and UI-gated capability switches.
- The model-manager design search recommends prominent download actions and live status indicators. Its generic dark app-store palette conflicts with the established light-mint desktop product; retain the live-status hierarchy and explicit actions while continuing the existing palette and SVG icon system.
- Authoritative repository metadata confirms `ggerganov/whisper.cpp` provides multilingual `ggml-small.bin` at 487,601,967 bytes, and `Qwen/Qwen2.5-3B-Instruct-GGUF` provides `qwen2.5-3b-instruct-q4_k_m.gguf` at 2,104,932,768 bytes.
- The OpenCV Zoo YuNet face detector URL responds successfully with a 232,589-byte ONNX file; the MediaPipe person, BGE and CLIP artifacts were subsequently verified and committed to the registry.
- Existing header dependency badges are plain labels; the model summary should become a clickable badge/button beside FFmpeg. `HighlightDialog` currently hard-codes all intelligence flags to false, making it the correct place to replace placeholders with verified, model-gated checkboxes.
- The final offline inference runtime is declared explicitly: pywhispercpp for GGML ASR, OpenCV/ONNX Runtime for vision, and Tokenizers/ONNX Runtime for BGE/CLIP.
- `Xenova/bge-small-zh-v1.5` exposes a verified 24,010,842-byte quantized ONNX model plus tokenizer/config files, suitable for Chinese text embeddings.
- `Xenova/clip-vit-base-patch32` exposes verified quantized ONNX artifacts and tokenizer/preprocessor files; the combined vision/text package is 149.95 MiB with separate 89,117,001-byte vision and 64,504,507-byte text models plus metadata.
- The guessed Ultralytics `yolov8n.onnx` release URLs at v8.3.0, v8.2.0 and v0.0.0 all return 404. They must not enter the registry; subject detection will use a separately verified artifact.
- OpenCV Zoo exposes a verified MediaPipe person detector at `person_detection_mediapipe_2023mar.onnx`; the raw URL resolves successfully to an 11,990,159-byte file. This covers the person/primary-subject part of the face/subject capability alongside YuNet.
- The registry ships six independently downloadable packages: Whisper small ASR, YuNet face, MediaPipe person, BGE-small Chinese text embedding, quantized CLIP vision/text embedding, and an experimental Qwen2.5 3B Q4_K_M narration model that does not gate current semantic editing.
- A real official-source YuNet download completed at exactly 232,589 bytes and reached the verified `installed` state, confirming redirects, streaming download, size validation and SHA-256 manifest recording.
- Native model-dialog QA shows the six-model table, storage path, live summary, source links and task panel fit clearly. Status labels should be compact centered chips, and disabled destructive actions need an explicit grey override because the danger selector otherwise looks active.
- The corrected native model-dialog render confirms compact centered status chips and explicitly grey disabled delete/verify actions. All six rows remain reachable through the bounded internal scrollbar at the 1600×1024 preview size.
- Windows CPython 3.11 has compatible binary wheels for `pywhispercpp 1.5.1`, `onnxruntime 1.29.0`, `opencv-python-headless 4.12.0.88` and `tokenizers 0.22.1`; these can run Whisper GGML and ONNX models fully offline after installation.
- `llama-cpp-python` has no compatible binary wheel on the configured Windows package index. Qwen GGUF must not block the other semantic analyzers; an app-bundled llama.cpp executable can be added later if local generative narration is enabled.
- Real temporary-directory inference passed with downloaded YuNet, MediaPipe person detection and BGE-small models: two video samples produced visual evidence, and two Chinese strings produced normalized 512-dimensional embeddings.
- A real `pywhispercpp` smoke using the official 77,691,713-byte Tiny GGML model loaded and transcribed a generated WAV completely offline on CPU. The production path uses the registry's multilingual Small model and the same API.
- Native editor QA confirms the `本地模型 0/6` header badge fits at 1240px and the new timeline evidence column plus inspector fields remain unclipped. The automatic-highlight dialog clearly disables missing capabilities and reports the exact missing-model counts (speech 1, face/subject 2, semantic 2).
- The complete real semantic chain passed after downloading and verifying both BGE and CLIP in a temporary directory. Two frames produced semantic scores 0.903 and 0.166, confirming tokenizer, BGE ONNX, CLIP image preprocessing, vision ONNX and diversity scoring are compatible with the registry artifacts.
- The final 2.2.0 onedir package is 435,678,862 bytes (415.5 MiB, 1,505 files). Its built-in AI runtime self-check exits 0, and the normal GUI remains alive through the four-second packaged startup observation.
- Phase 14 diagnosis starts from three concrete weaknesses in the 2.2.0 lifecycle: progress signals contain no timing/throughput data; `ModelDownloader.cancel()` only sets an event while `urllib.response.read()` may remain blocked up to the 30-second timeout; and the model dialog owns/deletes worker-thread QObjects through several queued callbacks without an explicit terminal state guard.
- Official source SHA-256 values are available for every large model artifact through Hugging Face/OpenCV LFS metadata: Whisper `1be3…987b`, YuNet `8f23…2fa4`, MediaPipe person `47fd…701f`, BGE ONNX `15b7…9bcc`, CLIP text `73ba…5c3a`, CLIP vision `583f…9299`, and Qwen `626b…c62d`. These can turn manual verification into a real source-integrity comparison without downloading the large files again.
- A 3-second sliding-window meter cleanly resets between the download and hash phases, so each phase reports its own completed bytes, total bytes, throughput and ETA instead of treating download+verification as a doubled total.
- Closing the live `urllib` response during cancellation interrupts the stalled-read test within 1.5 seconds; 256 KiB network chunks provide noticeably more frequent progress than the former 1 MiB reads, while the 8-second connection/read timeout remains a fallback.
- Replacing moved worker QObjects with dialog-owned `QThread` subclasses makes repeated verification and verification cancellation deterministic: the dialog retains the thread until `finished`, waits for termination, then releases it.
- Manual verification does not load or run the model. It reads local files in 1 MiB blocks, checks cancellation between blocks, calculates SHA-256, compares official digests when registered, records auxiliary-file digests, and quarantines mismatches as `.corrupt`; no model content leaves the machine.
- The real MediaPipe transfer smoke cancelled at 1,048,576 bytes in 2.516 seconds, retained `.part`, resumed to 11,990,159 bytes, and completed the registered official SHA-256 comparison.
- Native 2.2.1 model-manager QA confirms the longer verification explanation wraps without clipping and the active row displays `512 KB / 11.43 MB · 3.21 MB/s · 剩余 3秒` beside the cancel action.
- The final 2.2.1 onedir package contains 1,505 files totaling 435,682,715 bytes; its AI runtime self-check exits 0 and the GUI remains alive for the four-second startup observation.
- The reported header mismatch came from mixing vertically expanding `QLabel` badges with naturally sized `QPushButton` controls in the same `QHBoxLayout`; matching padding alone cannot guarantee matching outer geometry.
- A shared 38 px outer height plus explicit vertical centering makes the main `yt-dlp / FFmpeg / 本地模型` group and the model-manager `已安装 / 打开模型目录` group geometrically identical without compressing their text or icons.
- Native 2.2.3 renders confirm both affected groups have aligned borders and centerlines at the default window size; the existing resizable/maximizable Phase 15 layout remains intact.
- The new screenshot clarifies that dependency labels should match the model button's shorter visual height, so the shared header metric needs separate values for the dependency/model group and the taller model-manager action group.
- The editor center column currently assigns 43% of vertical space to preview and 57% to timeline; this directly contradicts preview-first maximized behavior because every extra pixel is biased toward the timeline.
- `QMediaPlayer` already provides play/pause, position seeking and playback-rate APIs. The missing work is an in-video control surface, speed selector, full-screen host and a seek guard so position updates do not fight user dragging.
- `QTableWidget` already supports internal scrolling. Giving the timeline panel a bounded height and `ScrollBarAsNeeded` lets all extra editor height flow to the preview without losing access to clips.
- Native default-size rendering confirms the brand subtitle is gone, all three dependency/model controls share the shorter header height, and the overlay no longer consumes a separate row below the video.
- At 1600×1000 the timeline remains capped at 300 px while the preview absorbs the added vertical space; the player overlay remains anchored to the video bottom rather than the panel bottom.
- Full-screen rendering confirms the same play/seek/time/rate/volume/full-screen control surface survives reparenting into the borderless full-screen host and exposes an explicit `退出全屏` action.
- The first native overlay render showed the playback-rate combo using unnecessary preferred width; constraining it to 72 px leaves more room for the seek track at every window size.
- A real native `QMediaPlayer` smoke with a generated three-second H.264/AAC file reached 250+ ms during playback, sought to 1,200 ms, applied 1.5× rate and completed the full-screen round trip without resetting the source.
- Windows Media Foundation retains the active MP4 handle until the player source is cleared; stopping plus `setSource(QUrl())` releases it cleanly for temporary-file deletion.
- The final 2.3.0 onedir package contains 1,505 files totaling 435,690,178 bytes; packaged AI runtime diagnostics exit 0 and the GUI stays alive through the four-second startup observation.
# Phase 18 Preview Interaction Findings (2026-08-25)

- The asset preview button currently calls `setSource()` and `setPosition()` only; it never starts playback.
- `_refresh_all()` rebuilds the asset list without restoring or assigning selection, including immediately after a successful import.
- Asset preview/timeline action buttons do not currently reflect whether the asset list has a valid selection.
- `QMediaPlayer.mediaStatusChanged` and `errorOccurred` are not connected, so loading and decode failures are silent.
- Timeline selection should continue loading at the clip in-point without forced autoplay; the explicit asset-library “预览” action is the one-click autoplay affordance.
- A pending seek/autoplay flag tied to `LoadedMedia`/`BufferedMedia` avoids racing `setPosition()` and `play()` against asynchronous backend loading.
- A real H.264/AAC fixture confirmed one-click autoplay, seeking, 1.5× playback and full-screen restore on the native multimedia backend.
- Version 2.3.1 packages successfully with 1,505 files totaling 435,692,522 bytes; the packaged AI/runtime diagnostic exits 0 and a hidden GUI startup remains alive for four seconds.
# Phase 19 Player Control Visibility Findings (2026-08-25)

- PySide6 `QVideoWidget` provides a rendering surface, not browser-style built-in playback controls.
- The current custom `PlayerControls` frame is parented directly to `QVideoWidget`; on some Windows multimedia backends the native/hardware video surface can paint above child widgets once frames are rendered.
- Calling `raise_()` during resize is therefore not a reliable cross-backend guarantee even though empty-state screenshots and geometry tests pass.
- The robust layout is one black `VideoSurface` player container with `QVideoWidget` and the controls strip as sibling children; the strip remains visually inside the player while no longer competing with the native video surface's child stacking.
- The existing 2.3 screenshot confirms the bar is visible before active frame rendering, which explains why geometry-only/offscreen checks passed while the user's real playback path still loses it.
- Regression coverage must inspect the parent relationship and non-overlapping sibling geometry during active playback, not only the empty player layout.
- The real H.264/AAC active-playback run now reports `controls_visible=true`; the captured player shows Pause, a moving 00:00.280 / 00:03.000 timeline, 1.0×, volume and full-screen controls in the fixed bottom strip.
- Native video pixels may appear black in a window-ID screenshot because the hardware surface is captured separately, but the moving player position and visible sibling controls prove the active backend path was exercised.
- Default and full-screen native renders show the strip flush to the bottom of the black player frame; all controls remain unclipped and full-screen retains the same control set.
- Version 2.3.2 packages successfully with 1,505 files totaling 435,692,268 bytes; packaged runtime diagnostics exit 0 and the hidden GUI remains alive for four seconds.

### Phase 20 findings
- `QGraphicsVideoItem` inside a `QGraphicsView` allows a real QWidget control layer to sit above decoded video frames; the hover layer can therefore fade without the native video surface covering it.
- Consecutive FFmpeg `xfade` operations require each segment to be normalized with `settb`, `setpts` and an explicit constant `fps`. Without that normalization a three-clip transition chain produced either a 0.47-second output or a `1/0` frame-rate error.
- Timeline subtitle instances must merge the same cue when adjacent split clips overlap during a transition; otherwise identical soft-subtitle packets are emitted at the same time.
- PowerShell `-Command` argument binding was unreliable for the SAPI script. Passing paths/rate in task-specific environment variables and using UTF-16LE `-EncodedCommand` works with Chinese text and paths.
- Qwen GGUF remains an installed-model research option, but this build does not falsely claim an unavailable GGUF inference runtime. Narration drafts use editable subtitle/clip facts and Windows SAPI creates the offline voice track.
- Version 3.0.0 packages as 1,505 files totaling 435,728,580 bytes; packaged AI runtime diagnostics exit 0 and GUI startup remains alive for four seconds.

### Phase 21 findings
- The remaining functional gap is real GGUF text generation: the Qwen2.5 3B Q4_K_M model is registered and a full-size model file exists under the application's local model directory, but no GGUF runtime is currently installed or bundled.
- `llama_cpp`, `ctransformers` and `onnxruntime_genai` are absent from the current virtual environment. The configured Python package index lists `llama-cpp-python` through 0.3.35, so current wheel availability must be rechecked before falling back to a separately managed llama.cpp executable.
- A diagnostic command incorrectly referenced `ModelManager.specs`; the actual public registry is `ModelManager.registry`. CLI construction before setting the Qt application identity also resolves a different `QStandardPaths` root than the packaged application, so real-model smoke tests must explicitly use the installed application model directory or initialize the same Qt identity.
- The refreshed binary-wheel check confirms no compatible `llama-cpp-python` wheel is available for this CPython 3.11 Windows environment, including the project's documented CPU wheel index.
- Official `ggml-org/llama.cpp` release `b10622` provides `llama-b10622-bin-win-cpu-x64.zip` (18,067,843 bytes) with SHA-256 `0f016b001d00a0cc25b955a5ae5eb3ce57a0b16adaa9142f8a3c3269e83fce0a`.
- The downloaded archive hash matches the GitHub release digest. It contains `llama-cli.exe`, its implementation DLL, CPU-specific `ggml` DLLs, `llama.dll`, `llama-common.dll` and OpenMP runtime, so safe extraction of the complete archive is required rather than copying one executable.
- GitHub's new stable `v0.3.0` release currently contains only a nightly tag pointer; the actual Windows artifacts are attached to numbered prereleases. Pinning `b10622` gives a reproducible runtime instead of following a moving latest URL.
- `llama-completion.exe` with an explicit Qwen ChatML prompt and `--no-conversation --no-display-prompt --log-verbosity 1` returns only generated text on stdout; `llama-cli.exe` always includes its banner, prompt and interactive status in stdout and is therefore unsuitable for clean application parsing.
- Real Qwen2.5 3B Q4_K_M CPU generation completed in about four seconds on this machine and produced a fact-grounded Chinese narration paragraph.
- The managed-runtime design now passes safe extraction, generation-output cleanup, narration-fact construction, seven-item model-manager UI and the existing hover-player tests (19/19 targeted tests).
- The application downloader successfully installed the pinned llama.cpp archive through its cancellable system-`curl` fallback, verified the official SHA-256, and atomically prepared the runtime directory.
- Real end-to-end Qwen generation now uses `llama-completion.exe` on CPU, completes in roughly 4–5 seconds on this machine, supports process termination on cancel, and returns clean Chinese text after ChatML marker removal.
- Narration generation is fact-grounded from editable subtitles, clip names, timeline positions and selection evidence; Qwen failure produces an explicit warning and a deterministic editable draft instead of blocking the workflow.
- The narration recipe dialog gates Qwen on both required model entries, defaults to local generation only when both are verified, and uses the themed primary confirmation button.
- Version 3.1.0 source verification passes compileall, 43/43 unit tests, real Qwen generation/cancellation/editing/SAPI/export, real transition/subtitle/audio export and real player playback controls.
- A final Windows stress run exposed an antivirus/delete-sharing race when curl wrote directly to `.part`; curl now writes to a managed work file, waits for a native Windows delete-capable handle, then atomically restores `.part`. Twenty consecutive cancellation runs and a real 11,990,159-byte cancel/resume/SHA-256 transfer pass.
- The final 3.1.0 package contains 1,505 files totaling 435,744,094 bytes. Its runtime diagnostic reports 7 managed components and external llama.cpp readiness, the GUI stays alive for four seconds, and the rebuilt ZIP SHA-256 is `afe7cf71d675d8a831a1df6257e57d0ca6b672b34724c9db1b23d3cb32c10edb`.
# Phase 20 Professional Editor Findings (2026-08-25)

- The supplied player reference uses a translucent black overlay: primary play/time at upper-left, volume/full-screen/menu at upper-right, and a full-width seek bar along the bottom.
- The requested behavior is hover reveal rather than a permanently visible footer; keyboard focus and playback-state changes still need a non-hover reveal path so essential controls are accessible.
- The user explicitly wants a Jianying-style nonlinear editing workflow: video, audio and subtitle tracks; manual clip movement/deletion/insertion; transitions; selected-clip smart splitting; one-click ASR subtitles; parameterized highlight and narration recipes.
- UI/UX search confirmed that primary operations cannot rely exclusively on hover; controls should also appear on click/focus and remain usable from keyboard.
- The design-system search recommends a video-first hierarchy, high-contrast controls, 150–300 ms transitions and visible keyboard focus; its dark-player recommendation can be scoped to preview/timeline while retaining the app's established light-mint shell.
- The project model already persists `clips`, `audio_tracks` and `subtitle_cues`; this is a useful foundation for presenting true lanes rather than inventing a second state model.
- Offline Whisper transcription is already implemented inside `OfflineIntelligenceAnalyzer`, and a narration model capability already exists in the model registry; the missing work is user-facing orchestration, editing UI and export integration.
- `TimelineClip` currently has no transition metadata; `SubtitleCue` is persisted but has no direct editor, and the exporter currently concatenates normalized segments without transitions or subtitle muxing.
- `AudioTrack.start_time` already provides timeline placement for external audio; the new UI can visualize this lane without changing its data meaning.
- The current export pipeline's normalized per-clip intermediates are a suitable boundary for optional FFmpeg `xfade`/`acrossfade`, followed by external audio mixing and subtitle muxing.
- The existing `LongVideoHighlightWorker` owns scene/highlight orchestration, while a dedicated selected-clip scene-split worker and a dedicated speech-recognition worker can reuse lower-level analyzers without blocking the GUI.
- Qwen narration is registered as a downloadable GGUF model, but no GGUF inference runtime or TTS voice runtime is currently bundled; narration must expose this honestly and provide an editable offline fallback instead of pretending the model is active.
