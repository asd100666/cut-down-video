# Task Plan: 流光媒体工作台

## Goal
交付一个 Windows 优先、可直接启动的 PySide6 本地媒体工作台：保留可靠的视频下载能力，增加非破坏性人工剪辑、项目保存、音轨混合、离线导出，以及生成后仍可人工修改的自动剪辑配方。

## Current Phase
Phase 21

## Acceptance Goals
1. 双击启动脚本或运行入口即可打开中文桌面界面。
2. 粘贴播放页、m3u8、mpd 或媒体直链后，可先解析信息再下载。
3. 支持保存目录、清晰度、浏览器 Cookie、Referer、播放列表开关。
4. 下载不阻塞界面；实时展示状态、进度、速度和剩余时间；支持取消。
5. 自动识别 Python 包与 FFmpeg 状态，并提供可执行的安装/修复提示。
6. 设置持久化；日志避免主动输出 Cookie/token；默认阻止重复提交同一活动任务。
7. 提供 requirements、启动脚本、README 与打包配置/脚本。
8. 通过语法、核心逻辑、Qt 离屏启动和受控真实下载链路测试。

## Phases

### Phase 1: Discovery & Product Design
- [x] Capture product requirements and acceptance goals
- [x] Inspect local runtimes and available dependencies
- [x] Generate and record desktop UI design system
- [x] Decide architecture and project structure
- **Status:** complete

### Phase 2: Core Download Engine
- [x] Implement models, settings and dependency checks
- [x] Implement yt-dlp analysis/download workers
- [x] Implement progress, cancellation and error classification
- **Status:** complete

### Phase 3: PySide6 Desktop UI
- [x] Implement main window and reusable widgets
- [x] Connect analysis/download flows without blocking UI
- [x] Add format selection, settings, logs and task state
- **Status:** complete

### Phase 4: Distribution & Documentation
- [x] Add requirements and one-click startup bootstrap
- [x] Add build configuration/script
- [x] Write Chinese README and usage notes
- **Status:** complete

### Phase 5: Testing & Verification
- [x] Run static and unit tests
- [x] Run Qt offscreen smoke test
- [x] Exercise controlled real download chain
- [x] Fix issues and re-run regression suite
- **Status:** complete

### Phase 6: Delivery
- [x] Verify deliverables and acceptance goals
- [x] Record final limitations and operating instructions
- [x] Deliver runnable project
- **Status:** complete

### Phase 7: Light Green Dual-Column Redesign
- [x] Inspect the supplied title-bar reference and current UI code
- [x] Generate a light green desktop utility design system
- [x] Replace scroll layout with a fixed-size two-column window
- [x] Apply accessible light green gradient styling and consistent toolbar/app icons
- [x] Re-run unit, native visual, packaged build and startup tests
- **Status:** complete

### Phase 8: Alignment, Toast & Animated Logo Refinement
- [x] Inspect the three supplied UI references and capture exact deltas
- [x] Make sections 1/2 equal height and align the entire lower left/right regions
- [x] Replace in-card analysis messages with a themed countdown toast overlay
- [x] Replace the logo with a new animated SVG identity and matching window icon
- [x] Remove advanced-option collapsing, simplify labels and add a spaced 2×2 choice grid
- [x] Remove the legal footer description
- [x] Run tests, native visual QA, rebuild and verify the packaged EXE
- **Status:** complete

### Phase 9: Batch Analysis & Download Queue
- [x] Inspect the supplied focus and URL-input references
- [x] Review the current single-item engine/worker/UI architecture
- [x] Replace the URL field with one-address-per-line multiline input and remove paste action
- [x] Add sequential batch analysis with per-item success/failure results
- [x] Add per-item download actions plus top-right successful-items batch download
- [x] Keep per-item and batch action states synchronized during work/cancellation
- [x] Remove checkbox focus borders and preserve the fixed aligned layout
- [x] Run tests, native visual QA, rebuild and verify the packaged EXE
- **Status:** complete

### Phase 10: Left-Side Media Card & Expanded Activity Log
- [x] Re-read the completed batch layout and generate updated UI guidance
- [x] Move section 2 beneath section 1 in the left column
- [x] Keep only download queue and activity log in the right column
- [x] Increase the fixed window height and reserve at least one third of the right body for logs
- [x] Keep oversized download queues bounded with internal vertical scrolling
- [x] Update geometry assertions and complete native visual QA
- [x] Bump the release, rebuild and verify the packaged EXE
- **Status:** complete

### Phase 11: Editable Video Workbench Foundation
- [x] Preserve the completed downloader as the first top-level workbench
- [x] Add a second top-level editing workbench without blocking the UI
- [x] Add project save/open, local media import and non-destructive clip data models
- [x] Add manual clip trim, split, reorder, delete and undo/redo controls
- [x] Add an editable audio-track list and project-level export settings
- [x] Render the current editable plan through FFmpeg and expose progress/errors
- [x] Add an EditPlan boundary that later automatic-highlight recipes can populate
- [x] Add unit/UI tests, native visual QA and update usage documentation
- **Status:** complete

### Phase 12: Editable Long-Video Highlight Recipe
- [x] Detect scene boundaries locally with cancellable FFmpeg analysis
- [x] Build a deterministic target-duration highlight planner with timeline coverage
- [x] Expose source scope, target duration, scene threshold and maximum clip length controls
- [x] Generate the result into the same editable timeline with recipe metadata
- [x] Keep undo/redo, manual trim/reorder/delete and project saving available after generation
- [x] Add planner tests and a real scene-analysis smoke chain
- [x] Re-run full regression, native editor QA and packaged startup verification
- **Status:** complete

### Phase 13: Optional Offline Intelligence Layer
- [x] Add a model registry, writable storage location and missing/corrupt/version status checks
- [x] Add direct HTTPS download with progress, cancellation, `.part` resume and post-download hash recording
- [x] Add a model-management dialog with purpose, size, source, status, install path and per-model actions
- [x] Expose model status from the main header and automatic-highlight dialog
- [x] Add real configuration switches for speech, face/subject and semantic analysis that are gated by installed models
- [x] Add offline ASR timestamps/subtitle artifacts to the EditPlan evidence model
- [x] Add face/subject and visual-quality scores without changing source media
- [x] Add semantic chapter/highlight selection with graceful deterministic fallback
- [x] Keep every generated decision editable and evidence-linked
- [x] Add unit/download/UI tests, native visual QA and packaged verification
- **Status:** complete

### Phase 14: Model Transfer Responsiveness & Verification Stability
- [x] Show live transfer/hash speed, completed bytes, total bytes and remaining time
- [x] Interrupt blocked network reads when cancelling instead of waiting for the socket timeout
- [x] Make download and manual verification worker shutdown deterministic and crash-safe
- [x] Explain that verification reads local files in chunks and compares/records SHA-256 metadata
- [x] Add stalled-network cancellation, speed calculation and repeated verify/cancel UI tests
- [x] Re-run native UI, real model download and packaged startup/runtime verification
- **Status:** complete

### Phase 16: Header Control Height Alignment
- [x] Give the main dependency/model status group one shared outer height
- [x] Give the model-manager summary/directory action group the same shared outer height
- [x] Add native geometry assertions and visually inspect both affected headers
- [x] Re-run regression and rebuild/verify the Windows package
- **Status:** complete

### Phase 17: Native-Style Preview Controls & Preview-First Resizing
- [x] Match dependency badges to the model-button height and remove the brand subtitle
- [x] Move playback controls into an in-video bottom overlay
- [x] Add play/pause, seek, playback speed and full-screen behavior
- [x] Cap the timeline panel and keep its table vertically scrollable
- [x] Prove resized height goes to preview, not timeline
- [x] Run regression, native visual QA and rebuild/verify the Windows package
- **Status:** complete

### Phase 18: One-Click Preview & Player Diagnostics
- [x] Preserve/select newly imported material in the asset library
- [x] Make the asset preview action load and start playback in one click
- [x] Disable asset actions without a valid selection and show a clear fallback prompt
- [x] Surface media loading, ready and decode-error states in the editor status bar
- [x] Add UI and real-player regression coverage
- [x] Rebuild and verify the Windows package
- **Status:** complete

### Phase 19: Always-Visible In-Player Controls
- [x] Replace the fragile `QVideoWidget` child overlay with a controls strip owned by the player container
- [x] Keep playback controls inside the black preview frame in windowed and full-screen modes
- [x] Preserve play/pause, seek, time, speed, volume/mute and full-screen behavior
- [x] Add geometry assertions that prove controls do not descend from the native video surface
- [x] Run real playback and native visual verification with an active video frame
- [x] Rebuild and verify the Windows package
- **Status:** complete

### Phase 20: Professional Multi-Track Editing Workbench
- [x] Replace the fixed player footer with a native-style hover overlay that remains keyboard/touch accessible
- [x] Replace the table-only timeline with visible video, audio and subtitle lanes plus a time ruler/playhead
- [x] Support selecting, reordering, deleting and inserting clips on the video lane
- [x] Add selected-video smart scene splitting and keep every generated clip manually editable
- [x] Add one-click offline speech recognition into an editable subtitle lane
- [x] Add editable clip-to-clip transitions with at least cut, fade and dissolve choices
- [x] Preserve/import external audio as an editable audio lane
- [x] Promote highlight extraction and narration to parameterized recipe dialogs
- [x] Connect available downloaded models and provide explicit model gates/fallbacks
- [x] Extend project persistence, export behavior, tests, documentation and packaged verification
- **Status:** complete

### Phase 21: Real Local-LLM Narration Completion
- [x] Select and provision a packageable Windows GGUF inference runtime
- [x] Make the model manager check/download every runtime artifact needed for narration
- [x] Invoke the verified Qwen GGUF model for editable narration-draft generation
- [x] Keep deterministic draft and SAPI voice generation as explicit offline fallbacks
- [x] Add cancellation, progress, timeout and actionable failure feedback
- [x] Verify real local-LLM generation, manual editing, audio-track insertion and final export
- [x] Extend tests, documentation, versioning and packaged-runtime diagnostics
- [x] Rebuild and verify the final Windows distribution and ZIP
- **Status:** complete

## Future Backlog

### Phase 15: TLS 下载恢复与可最大化自适应工作台
- [x] 复现并追踪 Whisper Small 下载的 TLS EOF 异常路径
- [x] 对可重试网络中断增加有界重试、续传与明确进度提示
- [x] 将固定主窗口改为可最大化/可调整大小，并设置合理最小尺寸
- [x] 让下载页、编辑页和视频预览随窗口可用空间伸缩且不遮挡控件
- [x] 完成编译、自动化测试、原生窗口最大化与缩放验收
- [x] 重建 Windows 发布目录并执行打包后启动检查
- **Status:** complete

### 下载并发与排队（记录于 2026-08-25，暂不实施）
- [ ] 下载进行期间仍可继续提交并解析新的视频地址。
- [ ] 提供“最大并发下载数”设置，用于限制同时下载的任务数量。
- [ ] 超出并发上限的下载任务自动进入等待队列，并在已有任务结束后继续执行。
- **Status:** recorded / not scheduled

## Key Questions
1. Are PySide6, yt-dlp and FFmpeg already available locally?
2. Which UI layout remains clear during both analysis and download states?
3. How should cancellation remain responsive and avoid orphaned subprocesses?
4. How can the app be usable before a packaged EXE is produced?
5. Which real download target can be tested legally and deterministically?

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| Windows-first PySide6 desktop application | Best fit for local FFmpeg, browser cookies and filesystem downloads |
| Separate UI, application service and yt-dlp engine | Keeps business logic testable and leaves room for later Web reuse |
| Treat DRM and access controls as unsupported | Product downloads only content the user is authorized to access |
| Dark, high-contrast single-window task layout | Matches the design-system recommendation while keeping long-running status visible |
| Bundle an `imageio-ffmpeg` fallback | Makes merging work after dependency bootstrap even when FFmpeg is absent from PATH |
| Support one active operation at a time | Clear state model for the first finished desktop release; avoids accidental duplicate downloads |
| Redesign for a fixed desktop canvas with two balanced columns | User explicitly prefers large-screen density and no internal scrolling |
| Supersede the original dark single-column presentation | The new light mint dual-column design is the current product UI; download behavior remains unchanged |
| Use non-layout toast notifications for transient analysis/error feedback | Prevents card heights from changing and keeps 1/2 alignment stable |
| Run batch analysis and downloads sequentially on one worker thread | Keeps yt-dlp/browser-cookie access predictable, preserves cancellation and avoids saturating disk/network |
| Show one persistent result row per submitted URL | Makes success, failure and individual download eligibility explicit; the batch action can then operate only on successful rows |
| Place input, media summary and settings in one left-side workflow column | Keeps configuration context together while dedicating the entire right side to queue execution and diagnostics |
| Allocate 37% of the right-column body to activity logs | Exceeds the requested one-third minimum after accounting for the inter-card gap and improves multi-task troubleshooting |
| Represent every automatic or manual result as an editable `EditProject`/`EditPlan` | Keeps automation reversible and guarantees the user can refine clip boundaries, order, audio and export settings |
| Use normalized per-clip intermediates before final concat/mix | Handles mixed source resolutions/codecs and missing source audio more reliably than a single fragile filter graph |
| Keep editing analysis/export workers independent from download workers | Both workflows remain responsive and can be cancelled without coupling their internal state machines |
| Start automatic editing with a deterministic scene-coverage recipe | It works fully offline now, produces explainable results and establishes the recipe contract before optional speech/face/semantic models are installed |
| Store downloaded models under the writable per-user app-data directory | Packaged applications may be installed read-only; user data survives upgrades and can be checked without modifying the distribution |
| Gate intelligence switches on verified installed-model state | The UI must never imply an AI capability is active when its required local files are missing or incomplete |
| Estimate transfer and hash rates from a short sliding window | Smooths momentary timing noise while keeping bytes, speed and ETA responsive when the task changes phase |
| Close the active HTTP response as part of cancellation | Interrupts a blocked socket read immediately instead of waiting for the read timeout before the worker can finish |
| Run model download and verification as owned `QThread` subclasses | Gives the dialog one deterministic thread lifetime and prevents queued cleanup from destroying a running worker |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| UI design search raised `UnicodeEncodeError` under GBK stdout | 1 | Retry with Python UTF-8 mode (`-X utf8`) rather than repeating the same invocation |
| PySide6, yt-dlp and FFmpeg are absent from the active Python/PATH | 1 | Design a bootstrap launcher that creates a local virtual environment and installs Python dependencies; provide FFmpeg installation guidance and capability checks |
| `py -3.12 -m venv` could not resolve the Astral-managed Python 3.12 runtime | 1 | Use the working `python` 3.11 interpreter and revise bootstrap fallback order to prefer it before launcher-specific versions |
| Qt offscreen render showed Chinese placeholder boxes | 1 | Confirmed offscreen `QFontDatabase` contains zero families; perform native Windows render for visual QA |
| Direct execution of `tests/real_download_smoke.py` could not import `streamlight` | 1 | Add the project root to `sys.path` inside the standalone smoke script, matching its documented invocation |
| Combined hardening patch missed an exact README context line | 1 | Inspected the UTF-8 source and split the change into smaller patches with exact anchors |
| Windows PowerShell 5.1 misparsed the Chinese UTF-8 startup script | 1 | Add a UTF-8 BOM so the legacy parser decodes non-ASCII string literals correctly before execution |
| Windows PowerShell 5.1 likewise misparsed the BOM-less Chinese build script | 1 | Add UTF-8 BOM to `build.ps1` before retrying the actual package build |
| Combined patch attempted delete and add of `styles.py` in one operation | 1 | Split the stylesheet replacement into separate delete and add patches; apply icon changes independently |
| First 1.2.0 rebuild could not replace the existing distribution because the prior packaged EXE still held `base_library.zip` open | 1 | Resolve the exact executable path, stop only that project-local process, then rebuild successfully |
| Catch-up recommendation attempted `git diff --stat`, but this workspace has no Git repository | 1 | Treat the current filesystem and planning files as source of truth; do not repeat Git-only checks |
| Editing-workbench design search raised `UnicodeEncodeError` under GBK stdout | 1 | Re-run the required design search with Python UTF-8 mode (`-X utf8`) |
| Fixed numeric slice for the end of `main_window.py` exceeded its current line count | 1 | Stop using guessed indices and inspect the tail with `Get-Content -Tail` |
| A final Windows regression run found an occasional curl `.part` delete-sharing race after the worker thread ended | 1 | Make the curl worker verify the `.part` handle is renameable before reporting cancellation complete, then stress-test repeated cancellation |
| Real transfer smoke did not cancel after the GitHub curl phase label changed | 1 | Match both standard and fallback download phases and shorten curl progress sampling to 0.1 seconds |
| PowerShell `rg` invocation used Unix-style wildcard path arguments | 1 | Use ripgrep `--glob` filters or explicit Windows paths instead of shell wildcard operands |
| Editor source inspection requested lines beyond the file length | 1 | Clamp requested ranges to the actual line count before formatting output |
| Preview-action test found `QListWidget.clearSelection()` retains `currentItem()` | 1 | Require the current item to also be selected before treating it as an actionable asset |
| Targeted UI test waited on the unsaved-project confirmation dialog during teardown | 1 | Stop only the identified test processes and clear the fixture's dirty flag before closing its window |
| Direct invocation of the GUI-subsystem packaged EXE did not populate PowerShell `$LASTEXITCODE` | 1 | Capture the packaged diagnostic with `subprocess.run` and assert both exit code 0 and the success marker |
| PowerShell redirected-output diagnostic command was rejected by command policy | 1 | Avoid retrying the same shell form; use a read-only Python subprocess capture without temporary output files |
| Professional editor design-system search raised `UnicodeEncodeError` under GBK stdout | 1 | Retry the required design-system search with Python UTF-8 mode (`-X utf8`) before using its recommendations |
| Initial architecture search referenced non-existent `editor_renderer.py` and `model_registry.py` paths | 1 | Use the actual `editor_engine.py` renderer and in-file registry in `model_manager.py` for subsequent inspection |
| Editor model regression still expected schema version 2 after adding transition metadata | 1 | Update the round-trip expectation to schema version 3 while retaining default-field compatibility for older projects |
| Combined editor import/dialog patch used an incorrect anchor after `HighlightDialog` | 1 | Inspect the exact class boundary and apply the worker import and new dialog at stable current anchors |
| Legacy player test expected non-overlapping fixed controls after switching to composited hover overlay | 1 | Assert the overlay stays within the composited canvas and becomes visible on mouse movement instead |
| Existing UI smoke test expected the old `流光下载器` window title | 1 | Update the assertion for the new top-level `流光媒体工作台` shell and add second-workbench coverage |
| Combined progress update used a stale exact anchor for the 1.4.0 test row | 1 | Split the planning update into smaller patches and append new test evidence using current file context |
| Editor preview fixture edited row 2 after duplicating row 0, but insertion shifted the duplicate to row 1 | 1 | Target the newly inserted row 1 and keep row 2 as the supplemental clip |
| Final combined planning patch again depended on a fragile historical test-table anchor | 1 | Update `task_plan.md` and `progress.md` independently and insert new evidence before stable section headers |
| Progress update assumed the test and current-session sections were adjacent | 2 | Locate headings with `rg -n` and patch the test table, Phase 12 block and reboot table at their actual positions |
| Assumed Ultralytics release URLs for a pre-exported `yolov8n.onnx` returned 404 | 1 | Do not ship an unverified URL; use verified Hugging Face/OpenCV model artifacts or a repository asset confirmed by API metadata |
| `llama-cpp-python` has no compatible prebuilt CPython 3.11 Windows wheel on the configured package index | 1 | Do not make the Qwen GGUF runtime a hard dependency; keep deterministic/BGE/CLIP semantic planning available and treat local Qwen generation as a separately provisioned optional runtime |
| Phase 21 diagnostic referenced non-existent `ModelManager.specs` and resolved the wrong CLI model root | 1 | Use `ModelManager.registry`; initialize the Qt app identity or pass the packaged application's model root explicitly in real-model tests |
| Rechecking `llama-cpp-python==0.3.16` on both default and CPU wheel indexes found no compatible Windows binary | 2 | Stop retrying Python extension installation; use the official prebuilt llama.cpp CPU x64 archive as a managed runtime component |
| First Phase 21 targeted run passed 20/24 tests; three assertions still expected six models/one narration dependency, and the later hover test inherited unclosed failed windows | 1 | Update intentional registry expectations to seven models and two narration components, add explicit narration coverage, then rerun the hover test in a clean sequence |
| First curl-fallback cancellation regression left the `.part` handle locked during temporary-directory cleanup | 1 | Reap or kill the terminated curl process and close both pipes before clearing the active-process reference or returning cancellation |
| Runtime smoke tried to print a missing `pywhispercpp.__version__` attribute after all imports succeeded | 1 | Verify package metadata through `importlib.metadata` instead of relying on a module attribute |
| First intelligence regression passed 20/21 tests; the UI test still expected the former six-column timeline | 1 | Update the intentional geometry/schema assertion to seven columns and add evidence-specific coverage |
| Evidence-reason planner test exposed that normalized scene boundaries dropped the new `reason` field | 1 | Preserve `SceneBoundary.reason` while clamping time/score before selection |
| PowerShell HEAD metadata probe exposed that `BaseResponse.ResponseUri` is not available in the current PowerShell web-response type | 1 | Use the successfully returned `Content-Length` only; avoid relying on version-specific response properties |
| Final lifecycle review found cancellation was not checked during SHA-256 hashing and manual verification had no cancel path | 1 | Check cancellation once per 1 MiB hash block and expose cancel for both download+verify and verify-only workers |
| User reports no live model-download speed, cancel appears frozen, and manual verify can terminate the app | 1 | Reproduce blocked reads and repeated verification, then replace flag-only cancellation with active response interruption and harden Qt worker ownership/cleanup |
| First official-hash metadata script fell back to a full model GET because the selected Hugging Face API response omitted LFS metadata, then failed through an unavailable local proxy | 1 | Do not retry the large download; query the repository tree/path metadata endpoints that expose LFS OIDs and hash only small non-LFS files |
| First Phase 14 regression run passed 29/30 tests; the repeated-verification assertion searched the detail label for the phase name | 1 | Assert the phase from `progress_title`, where the UI intentionally displays it, then add a separate mid-verification cancellation test |
| Final `rg` evidence command used Chinese curly quotes inside a PowerShell double-quoted regex and split part of the pattern into a path | 1 | Keep the successful completion check, then rerun evidence lookup with a PowerShell single-quoted regex |
| Partial plan inspection missed the later completed Phase 15 and temporarily reused its phase number for header alignment | 1 | Re-read the current phase list, preserve the existing TLS/adaptive-window work and renumber this UI pass to Phase 16 |
| Real player smoke passed playback/seek/rate/full-screen but Windows kept the temporary MP4 locked during `TemporaryDirectory` cleanup | 1 | Stop playback, clear the `QMediaPlayer` source, process deferred widget deletion and wait briefly before deleting the temporary directory |
| Guessed README line slice extended past the file length while locating the developer-test section | 1 | Stop using a fixed numeric end index and inspect the exact section with `Get-Content -Tail` before patching |
| PowerShell emitted `PropertyNotFoundException` when non-LFS auxiliary files had no `lfs` property | 1 | Treat official SHA-256 as optional per file; require it for all large binary/model artifacts and retain size+recorded-hash checks for small repository text assets |
| 本机 `curl` 探测 Whisper 官方 Hugging Face 地址时返回 `schannel: failed to receive handshake` | 1 | 记录为当前网络/代理 TLS 通道的独立复现；继续核对代理与其他 HTTPS 站点，同时保留应用内有界重试和官方 SHA-256 校验 |
| 读取 Windows Internet Settings 的可选 `AutoConfigURL` 属性时触发 `PropertyNotFoundException` | 1 | 不再假设可选注册表字段存在；使用 Python `urllib.request.getproxies()` 和已验证的代理 TCP 监听结果定位实际代理 |
| Computer Use 的应用目录把同一个 Python 窗口重复列在两个应用项下，首次按列表筛选得到 2 个候选 | 1 | 未执行输入；改用 `list_windows()` 按真实窗口 ID 去重，确认唯一源码窗口后继续 |
| 旧版打包窗口首次通过辅助元素关闭时缺少按钮几何信息 | 1 | 动作未发生；重新获取截图状态后按已验证的标题栏关闭坐标重试一次，窗口正常关闭且未出现未保存提示 |
| 直接执行无控制台打包 EXE 的诊断参数后 PowerShell 未设置 `$LASTEXITCODE` | 1 | 改用隐藏的 `Start-Process -Wait -PassThru` 读取真实 `ExitCode=0`，不再依赖控制台进程变量 |

## Notes
- Re-read this file before major architectural and release decisions.
- Record every material failure and avoid repeating the same unsuccessful attempt.
