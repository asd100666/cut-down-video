# Progress Log

## Session: 2026-08-24

### Phase 1: Discovery & Product Design
- **Status:** complete
- **Started:** 2026-08-24
- Actions taken:
  - Captured acceptance goals and six implementation phases.
  - Confirmed an empty starting workspace.
  - Selected a layered PySide6 + yt-dlp + FFmpeg architecture direction.
  - Audited local runtimes: Python exists, but runtime packages and FFmpeg are absent.
  - Started the required UI design-system search; first attempt exposed a GBK stdout issue.
  - Re-ran design search in UTF-8 mode and captured dark-theme, accessibility and progress-feedback guidance.
  - Finalized the first-release architecture and dependency bootstrap strategy.
- Files created/modified:
  - `task_plan.md`
  - `findings.md`
  - `progress.md`

### Phase 2: Core Download Engine
- **Status:** complete
- Actions taken:
  - Prepared module boundaries for models, engine, workers, settings and UI.
- Files created/modified:
  - `streamlight/models.py`, `dependencies.py`, `errors.py`, `engine.py`, `workers.py`

### Phase 3: PySide6 Desktop UI
- **Status:** complete
- Actions taken:
  - Implemented the complete single-window Chinese workflow and dark high-contrast theme.
  - Added persistent settings, advanced options, progress/cancel states, logs and dependency badges.
  - Passed a Qt offscreen construction smoke test.
  - Rendered a first screenshot; layout is sound, while the offscreen plugin reported no fonts and displayed Chinese placeholders.
  - Re-rendered through the native Windows platform and confirmed correct Chinese font rendering and overall visual hierarchy.
  - Replaced platform-dependent standard icons with a consistent SVG line-icon helper.
- Files created/modified:
  - `streamlight/main_window.py`
  - `streamlight/styles.py`
  - `streamlight/settings.py`
  - `main.py`

### Phase 4: Distribution & Documentation
- **Status:** complete
- Actions taken:
  - Added dependency manifests and an idempotent double-click bootstrap.
  - Added PyInstaller onedir packaging configuration.
  - Wrote Chinese installation, usage, update, support-boundary and test documentation.
- Files created/modified:
  - `requirements.txt`, `requirements-dev.txt`
  - `启动流光下载器.ps1`, `启动流光下载器.bat`
  - `Streamlight.spec`, `build.ps1`, `README.md`

### Phase 5: Testing & Verification
- **Status:** complete
- Actions taken:
  - Created the local `.venv` with Python 3.11 and installed production dependencies.
  - Passed seven unit/UI construction tests.
  - Passed native Windows visual QA after isolating an offscreen font limitation.
  - Generated a local HLS stream and passed a real yt-dlp analysis/download test, producing a non-empty MP4.
  - Hardened close/cancel behavior so the window waits for the worker rather than destroying a running thread.
  - Passed final native visual QA after the SVG icon replacement.
- Files created/modified:
  - `tests/test_core.py`, `tests/test_ui_smoke.py`, `tests/real_download_smoke.py`
  - `artifacts/ui-preview-final.png`

### Phase 6: Delivery
- **Status:** complete
- Actions taken:
  - Re-read the acceptance plan and confirmed all eight goals are represented in code or documentation.
  - Reviewed the complete non-environment file list and found no unresolved TODO/FIXME markers.
  - Prepared direct launch, source documentation and optional Windows packaging handoff.
  - Built the actual Windows onedir distribution and verified the packaged EXE remains running after startup.
- Files created/modified:
  - `task_plan.md`, `findings.md`, `progress.md`
  - `dist/流光下载器/流光下载器.exe` and packaged runtime files

### Phase 7: Light Green Dual-Column Redesign
- **Status:** complete
- Actions taken:
  - Recovered the completed project context and reopened the plan for the new redesign request.
  - Captured fixed-size, no-scroll, dual-column, light-green-gradient and title-bar icon requirements.
  - Implemented the 1240×760 two-column canvas, light mint design system, application icon and no-scroll log presentation.
  - Passed all seven unit/UI tests and completed the first native visual render.
  - Refined vertical alignment and default-expanded advanced settings; second native render confirms the requested fixed no-scroll composition.
  - Restored explicit native checkbox ticks and passed the final source visual/test regression.
  - Bumped the application to 1.1.0, rebuilt the full Windows distribution and verified the packaged EXE remains running after startup.
- Files created/modified:
  - `streamlight/main_window.py`, `styles.py`, `icons.py`, `__init__.py`
  - `main.py`, `tests/test_ui_smoke.py`
  - `artifacts/ui-light-dual-final.png`
  - `dist/流光下载器/流光下载器.exe` and packaged runtime files
- Files created/modified:
  - `task_plan.md`, `findings.md`, `progress.md`

### Phase 8: Alignment, Toast & Animated Logo Refinement
- **Status:** complete
- Actions taken:
  - Recovered the 1.1.0 project state and captured all requested alignment, toast, logo, option-grid and footer-removal changes.
  - Equalized sections 1/2 at 154 px and verified the entire lower left/right region shares exact top and bottom edges.
  - Replaced all inline transient feedback with a themed countdown toast overlay and retained persistent operational progress in section 4.
  - Added a custom SVG stream/download logo that animates only during active work and also supplies the application/window icon.
  - Removed the advanced collapse control, made the panel permanently visible and reorganized shortened checkbox labels into a spaced 2×2 grid.
  - Removed the footer sentence, rendered and visually inspected the final native UI and toast states.
  - Bumped to 1.2.0, passed compile plus 7/7 tests, rebuilt the Windows distribution and verified the packaged EXE startup.
- Files created/modified:
  - `streamlight/main_window.py`, `styles.py`, `icons.py`, `toast.py`, `__init__.py`
  - `tests/test_ui_smoke.py`
  - `artifacts/ui-v1.2-final.png`, `artifacts/ui-v1.2-toast.png`
  - `task_plan.md`, `findings.md`, `progress.md`

### Phase 9: Batch Analysis & Download Queue
- **Status:** complete
- Actions taken:
  - Recovered the completed 1.2.0 state and inspected the two supplied references as visual evidence only.
  - Generated the required batch-queue design guidance and reviewed the current single-item engine, workers, UI and tests.
  - Chose sequential workers with persistent per-URL result rows, per-row download buttons and a batch-success-only action.
  - Confirmed checkbox focus styling can be fixed independently without removing focus indicators from other controls.
  - Replaced the single-line URL control with a multiline editor where Enter inserts a new address line; removed the paste action.
  - Added ordered URL parsing/deduplication, batch item state, sequential analysis/download workers and cancellation propagation.
  - Added compact success/failure result rows, individual download actions and the top-right open-folder/batch-download actions.
  - Preserved fixed 1240×760 card alignment while using an as-needed scrollbar only for an unbounded result queue.
  - Passed 11/11 automated tests and a real two-item local HLS batch analysis/download test.
  - Completed native visual QA, bumped to 1.3.0, rebuilt the distribution and verified packaged startup.
- Files created/modified:
  - `streamlight/main_window.py`, `models.py`, `engine.py`, `workers.py`, `styles.py`, `__init__.py`
  - `tests/test_core.py`, `test_ui_smoke.py`, `test_batch_workers.py`, `real_download_smoke.py`
  - `README.md`, `artifacts/ui-v1.3-batch.png`
  - `task_plan.md`, `findings.md`, `progress.md`

### Phase 10: Left-Side Media Card & Expanded Activity Log
- **Status:** complete
- Actions taken:
  - Recovered the completed 1.3.0 batch release and reviewed the current layout and geometry tests.
  - Generated the required updated UI guidance and translated the request into a three-card left workflow plus two-card right operations stack.
  - Selected a 1240×860 fixed window and 63:37 right-column height ratio so the activity log exceeds one third of usable height.
  - Moved media information beneath the URL card, leaving queue and logs as the only right-column cards.
  - Added an explicit as-needed vertical scrollbar policy to the bounded queue and verified 20 result rows cannot escape its card.
  - Updated geometry tests for the new 1240×860 canvas, card order, one-third log minimum and queue containment.
  - Passed 12/12 automated tests and native QA with ten mixed results.
  - Bumped to 1.4.0, rebuilt the Windows distribution and verified packaged startup.
- Files created/modified:
  - `streamlight/main_window.py`, `streamlight/__init__.py`
  - `tests/test_ui_smoke.py`
  - `artifacts/ui-v1.4-left-media-log.png`
  - `task_plan.md`, `findings.md`, `progress.md`

## Test Results
| Test | Input | Expected | Actual | Status |
|------|-------|----------|--------|--------|
| Python compile | `compileall` over app and tests | No syntax errors | Passed | ✓ |
| Unit/UI smoke | `unittest discover` | Models, redaction, cancellation, options and window construction pass | 7/7 passed | ✓ |
| Native visual render | Windows Qt platform, 1040×840 | Correct Chinese text and hierarchy | 184 fonts; render correct | ✓ |
| Real HLS download | Generated 2-second local HLS | Analyze and produce non-empty media file | MP4, 28,448 bytes | ✓ |
| Real audio extraction | Same generated HLS, audio preset | Produce non-empty MP3 through FFmpeg fallback | MP3, 19,630 bytes | ✓ |
| Bootstrap diagnostic | `启动流光下载器.ps1 -CheckOnly` under Windows PowerShell 5.1 | Parse UTF-8 Chinese script and validate environment | Passed | ✓ |
| Packaged EXE smoke | Start hidden `dist/流光下载器/流光下载器.exe`, observe for 4 seconds | Application remains running with packaged dependencies | Passed; test process then terminated | ✓ |
| Packaged FFmpeg presence | Inspect onedir distribution | Media processing fallback included | 2 matching packaged files | ✓ |
| Fixed dual-column UI | Native render at 1240×760 | Two columns, no main scroll, no clipped controls | Passed | ✓ |
| Window/application icon | Runtime QIcon plus UI smoke assertion | Non-null icon available to title bar and header | Passed | ✓ |
| Version 1.1.0 packaged EXE | Rebuild and hidden startup observation | New distribution starts with bundled dependencies | Passed | ✓ |
| Version 1.2.0 compile/test regression | `compileall` plus `unittest discover` | New toast/logo/layout code is valid and all checks pass | 7/7 passed | ✓ |
| Version 1.2.0 alignment assertions | Show native-size window and compare card geometries | Sections 1/2 equal; lower regions share top/bottom | Passed | ✓ |
| Version 1.2.0 native visual QA | Render default and visible-toast states at 1240×760 | No clipping, themed overlay, clear 2×2 options | Passed | ✓ |
| Version 1.2.0 packaged EXE | Rebuild and hidden startup observation for 4 seconds | New distribution starts with bundled dependencies | Passed; test process then terminated | ✓ |
| Version 1.3.0 unit/UI/worker regression | `compileall` plus `unittest discover` | URL parsing, batch continuation and action states pass | 11/11 passed | ✓ |
| Real two-item batch HLS chain | Two local playlist URLs | Both analyze and produce distinct non-empty files | 2/2 analyzed and downloaded | ✓ |
| Version 1.3.0 native visual QA | Three mixed result rows, checkbox focused | No focus box; clear rows; exact button order/alignment | Passed | ✓ |
| Version 1.3.0 packaged EXE | Rebuild and hidden startup observation for 4 seconds | New batch-enabled distribution remains running | Passed; test process then terminated | ✓ |
| Version 1.4.0 layout regression | `compileall` plus `unittest discover` | New column order, proportions and queue boundary pass | 12/12 passed | ✓ |
| Oversized queue containment | Populate 20 result rows | Internal vertical scroll; queue stays inside card | Passed | ✓ |
| Version 1.4.0 native visual QA | Ten mixed rows and populated logs | Left 1/2/3; right queue/log; log ≥ one third | Passed | ✓ |
| Version 1.4.0 packaged EXE | Rebuild and hidden startup observation for 4 seconds | Rebalanced distribution remains running | Passed; test process then terminated | ✓ |
| Version 2.1.0 unit/UI regression | `compileall` plus `unittest discover` | Download, editor, history, planner and UI behavior remain valid | 18/18 passed | ✓ |
| Real editor export chain | Mixed source clips plus offset music | Trim, normalize, concatenate and mix offline | 45,826-byte MP4, 1.67 seconds | ✓ |
| Real highlight analysis | Four generated color scenes | Detect scene boundaries and hit target duration | 2 boundaries, 3 clips, 2.40 seconds | ✓ |
| Version 2.1.0 native editor QA | Populated material, timeline and audio data | No clipping; manual and auto controls remain accessible | Passed | ✓ |
| Version 2.1.0 packaged EXE | Hidden startup observation for 4 seconds | Multimedia-enabled workbench remains running | Passed; 256,771,404 bytes | ✓ |
| Version 2.2.0 unit/UI regression | `compileall` plus `unittest discover` | Model lifecycle, evidence schema, cancellable hashing, fallback and all prior workflows remain valid | 26/26 passed | ✓ |
| Real YuNet/MediaPipe/BGE/CLIP inference | Official temporary model downloads plus generated video | Visual evidence and complete text/vision semantic scoring run offline | 2 visual records; 2×512 BGE; semantic 0.903/0.166 | ✓ |
| Real Whisper runtime | Official Tiny GGML plus generated WAV | Native model loads and transcription completes offline on CPU | Passed | ✓ |
| Version 2.2.0 native UI QA | Main editor, model manager and model-gated highlight dialog | Badge, six rows, gates and evidence fields fit without clipping | Passed | ✓ |
| Version 2.2.0 packaged AI runtime | `流光下载器.exe --check-ai-runtimes` | Lazy native modules and DLLs import inside package | Exit 0 | ✓ |
| Version 2.2.0 packaged EXE | Hidden startup observation for 4 seconds | Complete workbench remains running | Passed; 435,678,862 bytes | ✓ |
| Version 2.2.1 model-transfer regression | `compileall` plus `unittest discover` | Speed/ETA, stalled cancellation, official hashes and repeated/cancelled verification remain stable | 31/31 passed | ✓ |
| Real model cancel/resume chain | Official 11,990,159-byte MediaPipe Person model in a temporary directory | Cancel after 1 MiB, retain `.part`, resume and compare official SHA-256 | Passed; cancelled in 2.516 s and resumed ready | ✓ |
| Version 2.2.1 native model UI QA | Idle model manager plus active-transfer state | Verification note wraps; bytes, MB/s, ETA and cancel remain visible | Passed | ✓ |
| Version 2.2.1 packaged AI runtime/startup | Internal runtime self-check plus hidden 4-second GUI observation | Runtime exit 0 and GUI stays alive | Passed; 1,505 files, 435,682,715 bytes | ✓ |
| Version 2.2.3 header-control alignment | Main dependency header and model-manager header at native size | All mixed label/button groups have a 38 px outer height and identical centerline | Passed; 34/34 regression tests | ✓ |
| Version 2.2.3 packaged AI runtime/startup | Internal runtime self-check plus hidden 4-second GUI observation | Runtime exit 0 and GUI stays alive | Passed; 1,505 files, 435,686,466 bytes | ✓ |
| Version 2.3.0 preview-player regression | `compileall` plus full unittest suite | Overlay controls, bounded timeline, resize allocation and full-screen round trip remain stable | 35/35 passed | ✓ |
| Real native preview playback | Generated 3-second H.264/AAC MP4 | Play advances, seek reaches 1.2 s, 1.5× applies and full-screen restores | Passed | ✓ |
| Version 2.3.0 native visual QA | Default, 1600×1000 and full-screen editor states | Controls stay inside video; extra height goes to preview | Passed | ✓ |
| Version 2.3.0 packaged runtime/startup | Packaged runtime self-check plus hidden 4-second GUI observation | Runtime exit 0 and GUI stays alive | Passed; 1,505 files, 435,690,178 bytes | ✓ |

## Error Log
| Timestamp | Error | Attempt | Resolution |
|-----------|-------|---------|------------|
| 2026-08-24 | `UnicodeEncodeError` from UI design search under GBK stdout | 1 | Retry using Python `-X utf8` |
| 2026-08-24 | PySide6/yt-dlp packages and FFmpeg executable not found | 1 | Account for them in bootstrap and dependency UX |
| 2026-08-24 | `py -3.12` reported no matching runtime while creating `.venv` | 1 | Retry with verified active Python 3.11 and adjust bootstrap |
| 2026-08-24 | Qt offscreen screenshot rendered Chinese as boxes | 1 | Font database is empty only under the offscreen platform; re-render using native Windows platform |
| 2026-08-24 | Standalone real-download smoke script could not import `streamlight` | 1 | Insert project root in the script before application imports |
| 2026-08-24 | Multi-file hardening patch failed README context verification | 1 | Re-read exact snippets and apply smaller targeted changes |
| 2026-08-24 | Windows PowerShell 5.1 reported misleading brace parser errors in Chinese startup script | 1 | Add UTF-8 BOM for parser-time encoding detection |
| 2026-08-24 | Windows PowerShell 5.1 misparsed `build.ps1` Chinese strings | 1 | Add UTF-8 BOM before retrying packaging |
| 2026-08-24 | `apply_patch` rejected simultaneous delete/add of `styles.py` | 1 | Split stylesheet replacement into two patch operations |
| 2026-08-24 | First 1.2.0 package rebuild found `dist` locked by the previously started packaged EXE | 1 | Matched the process by its exact project-local executable path, stopped it and rebuilt successfully |
| 2026-08-24 | Catch-up's suggested `git diff --stat` failed because the workspace is not a Git repository | 1 | Continue from the filesystem and persistent planning documents |
| 2026-08-25 | Editing-workbench UI design search failed under GBK stdout | 1 | Retry with `python -X utf8` and keep the failure recorded |
| 2026-08-25 | Guessed `main_window.py` tail range exceeded the file length | 1 | Use `Get-Content -Tail` instead of another guessed numeric slice |
| 2026-08-25 | First regression run had 11/12 passes; the only failure expected the former window title | 1 | Update the UI test for the intentional media-workbench rename and add editor assertions |
| 2026-08-25 | Native preview fixture used the pre-insertion row index after duplicating a clip | 1 | Update the duplicate at its actual inserted row and rerun the renderer |

## Session: 2026-08-25

### Phase 20: Professional Multi-Track Editing Workbench
- **Status:** in progress
- Inspected the supplied native-player reference and translated it into hover/click/focus reveal behavior.
- Recorded the requested professional editor workflow and began auditing current project, worker, model and export boundaries before implementation.
- Completed the required design-system search in UTF-8 and retained video-first hierarchy, high contrast, stable hover transitions and accessible focus guidance.
- Confirmed existing persistent clip/audio/subtitle models and reusable Whisper/narration capability boundaries.
- Audited project persistence and FFmpeg export: planned transition metadata, subtitle editing/muxing and a graphical view over the existing single project state.
- Added the graphical multi-track timeline component and schema-v3 transition/timeline mapping methods; core tests exposed only the intentional schema-version expectation.
- First integrated UI run passed construction and core model coverage; updated the obsolete fixed-footer geometry assertion for the new composited hover overlay.

### Phase 19: Always-Visible In-Player Controls
- **Status:** complete
- Traced the packaged-runtime symptom to `PlayerControls` being a child of the native `QVideoWidget` surface.
- Selected a sibling layout inside the same black player container so active video rendering cannot cover playback controls.
- Compared the 2.3 empty-state visual against the reported active-playback symptom; the defect is rendering-layer visibility, not missing control construction.
- Rebuilt the preview surface as a vertical native-player composition: expanding `QVideoWidget` plus an opaque 48 px sibling control strip inside the same black frame.
- Real H.264/AAC playback passed with visible controls, one-click autoplay, seek, 1.5× rate and full-screen restore; saved an active-playback acceptance image.
- Native default, expanded and full-screen renders confirm the fixed player strip remains inside the preview frame without increasing the bounded timeline.
- Updated the shared media-preview rule for Windows/Qt native-surface stacking and bumped the release to 2.3.2.
- Compilation and the complete automated regression suite pass 36/36.
- Rebuilt the 2.3.2 Windows package; packaged runtime diagnostics exit 0 and the four-second GUI startup observation passes.

### Phase 18: One-Click Preview & Player Diagnostics
- **Status:** complete
- Reproduced the no-response path in source: import refresh clears asset selection, and the preview action loads without playing.
- Selected a pending-seek/autoplay state so playback starts after the backend reports media loaded, while timeline selection remains a non-autoplay seek operation.
- Planned explicit loading/ready/error status feedback and selection-gated asset actions.
- First targeted run passed the existing player-control test but exposed Qt retaining `currentItem()` after selection clearing; tightened asset validity to require a selected current item.
- The rerun reached the unsaved-project confirmation during test teardown; terminated only the two exact test processes and updated the fixture to close non-interactively.
- Targeted UI coverage passes 2/2; the native H.264/AAC player smoke reports `autoplay=true` with normal seek, rate and full-screen behavior.
- Full compilation and automated regression suite pass 36/36.
- Bumped the application to 2.3.1, rebuilt the Windows onedir package, passed packaged runtime diagnostics with exit code 0 and passed the four-second GUI startup observation.

### Phase 11: Editable Video Workbench Foundation
- **Status:** complete
- Actions taken:
  - Recovered the completed 1.4.0 downloader context and confirmed the new manual-editing requirement.
  - Defined the first editing delivery as a complete editable project loop rather than a one-click irreversible renderer.
  - Recorded the application-shell, EditPlan and regression-test direction before code changes.
  - Completed the required editor design-system search in UTF-8 and retained only guidance compatible with the established light-mint desktop UI.
  - Inspected current models, workers, main-window structure, icons, settings and tests to select a self-contained editor module plus stacked application shell.
  - Re-read the active plan before architecture decisions and inspected shutdown/dependency behavior.
  - Chose FFprobe-first/FFmpeg-fallback probing and normalized intermediate rendering so existing offline dependencies can support mixed imported footage.
  - Implemented the editable project model, snapshot history, media probe, cancellable renderer, editor workers and full manual editing workspace.
  - Embedded download/edit pages in a top-level stacked shell and extended the existing SVG/style system without replacing the established light-mint design.
  - Passed Python compilation; the first regression run passed 11/12 tests with only the intentional window-title assertion outstanding.
  - Added editor model/UI regression coverage; compile plus the full suite now passes 17/17.
  - Passed a real offline FFmpeg editor smoke chain with mixed 640×360/854×480 sources, source-audio volume, a silent clip, trimming and an offset external music track; output MP4 was 45,826 bytes and 1.67 seconds.
  - Rendered the first native editor preview; recorded an inspector overlap issue and selected a three-tab inspector correction before delivery.
  - Replaced the stacked inspector with `镜头 / 音轨 / 项目` tabs; the second native render confirms there is no clipping or overlap.
  - Updated the README for the two-workbench workflow and bumped the application package to 2.0.0.
  - Rebuilt the Windows onedir distribution; packaged startup remained alive for four seconds with 34 multimedia matches and one bundled FFmpeg executable.

### Phase 12: Editable Long-Video Highlight Recipe
- **Status:** complete
- Actions taken:
  - Selected a deterministic FFmpeg scene-analysis and target-duration coverage planner as the first automatic recipe.
  - Implemented cancellable FFmpeg scene-boundary analysis, chronological target-duration coverage planning and multi-asset proportional duration allocation.
  - Added an “自动精华” dialog for source scope, target duration, maximum clip length, scene threshold and replace/append behavior.
  - Ensured generated clips use the same editable timeline, history and project format with `long_video_highlight` recipe metadata.
  - Passed 18/18 regressions and a real four-scene smoke test producing three editable clips totaling 2.4 seconds.
  - Completed native visual QA with the automatic-highlight action visible and all manual editing controls unclipped.
  - Updated documentation and bumped the application package to 2.1.0.
  - Rebuilt and launched the final packaged distribution; it remained running with 34 multimedia matches, one bundled FFmpeg executable and a 256,771,404-byte onedir payload.

### Phase 13: Optional Offline Intelligence Layer
- **Status:** complete
- Actions taken:
  - Recovered the verified 2.1.0 baseline and promoted model management from planned to active work.
  - Defined required states and download behavior so intelligence toggles cannot silently run without verified model files.
  - Completed the required model-manager design search and retained live status/action guidance compatible with the established desktop style.
  - Queried authoritative model repositories and verified initial ASR, face and local-instruction model file names/sizes.
  - Inspected current header, settings and highlight-dialog integration points for status and capability gating.
  - Verified downloadable quantized ONNX packages for Chinese text embedding and CLIP visual/text embedding.
  - Rejected three unverified YOLO release URLs after explicit 404 results instead of exposing broken download actions.
  - Verified the OpenCV MediaPipe person detector URL and exact 11,990,159-byte artifact size for the subject-analysis package.
  - Implemented the model registry, missing/partial/unverified/corrupt/installed checks, resumable downloader, SHA-256 manifest recording, model dialog, header badge and capability-gated highlight switches.
  - Passed 21/21 automated tests including a local HTTP Range-resume chain and corruption-state checks.
  - Passed a real YuNet official-source download and generated the first native model-manager preview.
  - Re-ran compilation and the full suite after the status-chip/disabled-button visual correction; 21/21 tests pass.
  - Re-rendered and visually inspected the native model-manager dialog; the corrected status and disabled-action hierarchy is clear and all six models remain scroll-accessible.
  - Added the real offline inference layer: Whisper timestamped subtitle evidence, YuNet/MediaPipe/quality visual evidence, BGE/CLIP semantic-diversity scoring, deterministic fallback warnings and evidence-linked editable clips.
  - Added Windows binary runtime dependencies and PyInstaller collection rules; local imports and 24/24 automated tests pass.
  - Passed a real temporary model/runtime smoke for YuNet, MediaPipe and BGE; visual sampling returned two evidence records and BGE returned 2×512 embeddings.
  - Passed a real pywhispercpp runtime/model smoke with the official Tiny GGML artifact; model load, automatic language detection and transcription completed offline on CPU.
  - Re-rendered the native editor and automatic-highlight dialog; the model badge, evidence column and exact missing-model gates fit without clipping.
  - Passed the complete real BGE+CLIP semantic smoke, including model download, SHA-256 recording, Chinese tokenization, text embedding, frame preprocessing, vision embedding and combined scoring.
  - Made download and SHA-256 verification a single monotonic two-stage progress sequence and kept `.part` cancellation/resume behavior.
  - Updated the bootstrap, documentation and release version to 2.2.0; source runtime diagnostics and 26/26 tests pass.
  - Rebuilt the Windows onedir distribution, passed its internal AI runtime self-check, observed normal GUI startup for four seconds and re-ran real export/highlight regressions.
  - Extended cancellation into 1 MiB SHA-256 verification blocks, added verification-worker cancellation coverage, rebuilt again and re-passed packaged runtime/startup checks.

### Phase 14: Model Transfer Responsiveness & Verification Stability
- **Status:** complete
- Actions taken:
  - Recorded the user-reported missing speed, blocked cancellation and verification-process-exit symptoms.
  - Recovered the complete 2.2.0 model lifecycle and identified the flag-only cancellation/socket-timeout window plus fragile worker cleanup as primary reproduction targets.
  - Reduced network reads to 256 KiB, shortened the socket timeout to eight seconds and made cancellation close the active HTTP response so blocked reads stop promptly while `.part` remains resumable.
  - Added completed bytes, real per-phase totals, a three-second sliding speed window and ETA for both download and local hashing.
  - Replaced moved QObject workers with dialog-owned download/verification `QThread` subclasses and made close/Escape wait for cancellation rather than destroying live threads.
  - Added official source SHA-256 values for every large registry artifact; mismatches are quarantined as `.corrupt` and exposed as repairable file errors.
  - Documented that manual verification only hashes local files in 1 MiB blocks, never uploads or executes them, and remains cancellable.
  - Added stalled-read interruption, speed/ETA, official mismatch, repeated verification and mid-verification cancellation coverage; compilation and all 31 automated tests pass.
  - Ran the real MediaPipe transfer chain: cancelled at 1 MiB in 2.516 seconds, retained `.part`, resumed to 11,990,159 bytes and passed official SHA-256.
  - Rendered and inspected idle/active native model-manager states; bytes, 3.21 MB/s, ETA and cancel fit without clipping.
  - Bumped to 2.2.1, rebuilt the Windows distribution, passed packaged AI runtime diagnostics and observed GUI startup for four seconds.

### Phase 15: TLS 下载恢复与可最大化自适应工作台
- **Status:** complete
- Actions taken:
  - 根据用户截图定位到 Whisper Small 下载的 `SSL: UNEXPECTED_EOF_WHILE_READING`，初步判断为可恢复的传输层提前断流，不是模型推理或格式错误。
  - 确认用户运行的“流光媒体工作台”来自本工程打包目录。
  - 确认主窗口通过 `setFixedSize(1240, 860)` 明确禁用了最大化和调整大小，开始检查下载重试边界与两工作台的伸缩布局。
  - 追踪到模型下载器已有 256 KiB 分块、8 秒读超时、取消关闭连接和 `.part` Range 续传，但所有瞬态 TLS/网络错误都会立即结束任务，提前 EOF 也只报告大小不一致。
  - 确认编辑页核心区域已使用伸缩 Splitter，解除主窗口固定尺寸并补充 Expanding/resize 处理即可让预览和时间线获得新增空间，无需重写工作台结构。
  - 已实现最多 4 次有界退避重试（1/2/4/8 秒）：TLS EOF、超时、连接重置、提前 EOF 和 408/425/429/5xx 会保留 `.part` 后自动 Range 续传；证书校验失败和永久 HTTP 错误仍立即终止。
  - 已将主窗口改为默认 1240×860、最小 1180×760、允许最大化/拖动调整；工作台栈、编辑 Splitter 与视频预览使用 Expanding，浮动提示在 resize 时重新锚定右上角。
  - 新增两项回归：本地服务器连续两次提前断流后第三次自动续传成功；窗口从 1240×860 扩至 1600×1000 后预览宽高和 Toast 横向位置同步增长。
  - Python 编译与模型管理/UI 针对性测试 13/13 通过。
  - 全量自动化测试 33/33 通过。
  - 对 Whisper 官方文件做只读 TLS 探测时，本机 `curl` 也复现 Schannel 握手失败；开始区分 Hugging Face 特定链路与全局 HTTPS/代理问题。
  - Python `urllib` 检测到系统代理 `127.0.0.1:9674`，端口由 Mihomo 监听；Microsoft 与 Hugging Face 经该代理均在 CONNECT 200 后 TLS 握手失败，确认是当前代理/节点链路问题。
  - 使用原生 Windows 窗口完成源码版验收：最大化按钮可点击并切换为还原；下载页两列完整扩展，剪辑页视频预览/时间线随窗口显著增大且无裁切、重叠或主滚动条。
  - 更新 README 并将版本提升到 2.2.2；模型持续失败提示会显示脱敏后的 HTTPS 代理主机/端口。
  - 关闭无任务、无素材的旧版打包窗口后成功重建 `dist/流光下载器`；成品为 1,505 个文件、435,686,024 bytes。
  - 打包 AI runtime 自检 `ExitCode=0`；最终 EXE 已启动并在下载页、剪辑页重复通过最大化与自适应原生验收。
  - Phase 15 complete；最终 2.2.2 打包窗口保持打开，供用户直接测试。

### Phase 16: Header Control Height Alignment
- **Status:** complete
- Actions taken:
  - Inspected the supplied screenshot and traced the mismatch to expanding `QLabel` badges mixed with naturally sized `QPushButton` controls.
  - Added one shared 38 px outer-height metric for both affected header groups and explicitly aligned every control vertically.
  - Added Qt geometry assertions for equal heights and centerlines in the main header and model-manager header; targeted tests pass 2/2.
  - Rendered and inspected native 2.2.3 main/editor and model-manager views; both highlighted groups are aligned with no text/icon compression.
  - Passed Python compilation, all 34 automated tests and the source AI runtime diagnostic.
  - Rebuilt the 2.2.3 Windows onedir package; packaged runtime diagnostics exit 0 and the GUI remains alive through the four-second startup observation.

### Phase 17: Native-Style Preview Controls & Preview-First Resizing
- **Status:** complete
- Actions taken:
  - Inspected both supplied screenshots and mapped the requested header, subtitle, player-control and resize changes to current Qt widgets.
  - Confirmed the existing center column gives 57% of vertical growth to the timeline; selected a bounded timeline plus expanding preview layout.
  - Confirmed `QMediaPlayer` can keep the existing playback backend while adding overlay seek, rate and full-screen controls.
  - Removed the brand subtitle and made the complete dependency/model group use the shorter shared header height.
  - Implemented a video-child overlay with play/pause, seek, elapsed/total time, 0.5×–2.0× speed, volume/mute and full-screen/restore actions.
  - Bounded the timeline to 220–300 px with an internal as-needed vertical scrollbar; all remaining center-column height now belongs to preview.
  - Added targeted geometry, resize, internal-scroll, rate and full-screen round-trip coverage; 3/3 targeted tests pass.
  - Rendered and inspected default, expanded and full-screen native states; corrected an over-wide speed selector to 72 px.
  - Passed compilation, all 35 automated tests and the source AI runtime diagnostic.
  - Passed a real native H.264/AAC player chain covering play, 1.2-second seek, 1.5× rate and full-screen restore.
  - Updated the README and UI rule reference, promoted the release to 2.3.0 and rebuilt the Windows distribution.
  - Packaged AI runtime diagnostics exit 0; the packaged GUI remains alive through the four-second startup observation.

### Phase 20: Professional Multi-Track Editing Workbench
- **Status:** complete
- Actions taken:
  - Replaced the always-visible footer with a composited `QGraphicsVideoItem` player and a mouse/keyboard accessible hover control layer.
  - Added a time ruler, playhead and visible video/audio/subtitle lanes with zoom, clip selection, drag reorder and transition nodes.
  - Added selected-clip smart scene splitting, Whisper subtitle recognition, per-cue subtitle editing and cut/fade/dissolve properties.
  - Added parameterized highlight and narration dialogs; all generated clips, subtitles and SAPI narration audio return to the same editable project.
  - Extended schema 3 persistence, schema 2 migration, timeline subtitle mapping, transition-aware duration and soft-subtitle export.
  - Fixed chained FFmpeg transition timestamps/framerate after a real three-clip export initially collapsed to 0.47 seconds.
  - Fixed Windows SAPI invocation after the first real smoke exposed unreliable PowerShell `-Command` parameter binding.
  - Updated the player runtime smoke from the old non-overlap assertion to hover show/hide and overlay containment checks.
  - Passed compilation and all 38 automated tests.
  - Passed real H.264/AAC player, three-clip dissolve/fade export with video/audio/subtitle streams, scene-highlight and Windows SAPI WAV tests.
  - Rendered and visually inspected default, expanded and fullscreen editor states; preview growth, hover controls and multi-track geometry are unclipped.
  - The first package attempt was blocked by two old packaged processes locking `base_library.zip`; only those two processes under the current `dist` directory were stopped, then the build succeeded.
  - Promoted the release to 3.0.0 and rebuilt 1,505 files totaling 435,728,580 bytes; packaged AI diagnostics exit 0 and the GUI stays alive through the four-second startup observation.

## 5-Question Reboot Check
| Question | Answer |
|----------|--------|
| Where am I? | Phase 21 final packaging and distribution verification |
| Where am I going? | Rebuild and verify the 3.1.0 Windows distribution and ZIP |
| What's the goal? | A runnable local media workbench whose automatic results always remain manually editable |
| What have I learned? | The bundled native Windows runtimes can execute Whisper, YuNet, MediaPipe, BGE and CLIP fully offline after model installation |
| What have I done? | Integrated real Qwen2.5 GGUF generation through managed llama.cpp, editable review, cancellation/fallback and SAPI/export; 43 tests and all source smoke chains pass |

### Phase 21: Real Local-LLM Narration Completion
- **Status:** complete
- Actions taken:
  - Added the official pinned llama.cpp Windows CPU runtime as the seventh managed component, with safe extraction and joint capability gating with Qwen2.5 3B.
  - Added a responsive GitHub `curl` fallback with `.part` resume, live byte progress and cancellation cleanup while retaining the existing HTTPS verifier.
  - Implemented real CPU-only Qwen narration generation from project facts, clean output parsing, timeout, cancellation and deterministic failure fallback.
  - Added parameter selection, model status, model management, human draft review and SAPI confirmation before inserting the editable narration audio track.
  - Updated release documentation, model count, local-model smoke instructions, runtime diagnostics and version to 3.1.0.
  - Passed compileall, source runtime diagnostics, all 43 automated tests and the real local-Qwen/editor-export/player smoke chains.
  - Found and fixed a late Windows curl `.part` delete-sharing race; the final design uses a managed work file, native handle-release probing and atomic `.part` restoration.
  - Passed 20 consecutive curl cancellation runs and a real 11,990,159-byte model cancel/resume/SHA-256 transfer with 131 progress events.
  - Rebuilt the 3.1.0 Windows package: 1,505 files totaling 435,744,094 bytes.
  - Packaged diagnostics exit 0 with `MANAGED_COMPONENTS=7`; the GUI remains alive for four seconds.
  - Rebuilt and inspected `dist/流光下载器.zip` (174,795,478 bytes, 1,514 entries, SHA-256 `afe7cf71d675d8a831a1df6257e57d0ca6b672b34724c9db1b23d3cb32c10edb`).
