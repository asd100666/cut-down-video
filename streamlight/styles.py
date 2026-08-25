HEADER_ACTION_HEIGHT = 38
HEADER_STATUS_HEIGHT = 34


APP_STYLE = """
QWidget {
    color: #183A2A;
    font-family: "Segoe UI", "Microsoft YaHei UI";
    font-size: 13px;
}

QMainWindow {
    background: #E9F7EF;
}

QWidget#AppRoot {
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 1,
        stop: 0 #F8FDF9,
        stop: 0.48 #ECF9F1,
        stop: 1 #DDF2E7
    );
}

QFrame#HeaderCard {
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #FFFFFF,
        stop: 0.62 #F5FCF8,
        stop: 1 #E4F6EC
    );
    border: 1px solid #C8E3D3;
    border-radius: 15px;
}

QFrame#Card {
    background: #FFFFFF;
    border: 1px solid #CFE5D7;
    border-radius: 13px;
}

QFrame#InfoPanel {
    background: #F7FCF9;
    border: 1px solid #D5EADF;
    border-radius: 10px;
}

QLabel#BrandTitle {
    color: #123C2A;
    font-size: 21px;
    font-weight: 700;
}

QLabel#CardTitle {
    color: #153E2C;
    font-size: 15px;
    font-weight: 650;
}

QLabel#SubsectionTitle {
    color: #295A43;
    font-size: 13px;
    font-weight: 650;
    padding-top: 2px;
}

QLabel#MediaTitle {
    color: #123C2A;
    font-size: 16px;
    font-weight: 650;
}

QLabel#Muted, QLabel#Hint, QLabel#MediaMeta {
    color: #587265;
}

QLabel#StepBadge {
    color: #13704C;
    background: #DDF4E7;
    border: 1px solid #B8DFC9;
    border-radius: 8px;
    font-weight: 700;
}

QLabel#MediaIcon {
    background: #E0F5E9;
    border: 1px solid #B9DFC9;
    border-radius: 10px;
}

QLabel#StatusGood {
    color: #12643F;
    background: #E2F7EB;
    border: 1px solid #B7E2C9;
    border-radius: 9px;
    padding: 0 9px;
}

QLabel#StatusWarn {
    color: #805B12;
    background: #FFF7DE;
    border: 1px solid #ECD79C;
    border-radius: 9px;
    padding: 0 9px;
}

QFrame#Toast {
    background: #F7FCF9;
    border: 1px solid #9FD4B7;
    border-radius: 14px;
}

QFrame#Toast[kind="success"] {
    background: #ECF9F1;
    border-color: #80C9A2;
}

QFrame#Toast[kind="error"] {
    background: #FFF3F5;
    border-color: #E4A6B2;
}

QFrame#Toast[kind="warning"] {
    background: #FFF9E9;
    border-color: #E4CA82;
}

QLabel#ToastIcon {
    background: rgba(255, 255, 255, 170);
    border: 1px solid rgba(138, 191, 161, 150);
    border-radius: 9px;
}

QLabel#ToastTitle {
    color: #153E2C;
    font-size: 14px;
    font-weight: 700;
}

QLabel#ToastMessage {
    color: #587265;
    font-size: 12px;
}

QLabel#ToastCountdown {
    color: #14764E;
    background: #FFFFFF;
    border: 1px solid #B9DFC9;
    border-radius: 19px;
    font-size: 12px;
    font-weight: 700;
}

QLineEdit, QComboBox {
    background: #FBFEFC;
    color: #173A2A;
    border: 1px solid #BED8C9;
    border-radius: 8px;
    min-height: 35px;
    padding: 0 10px;
    selection-background-color: #52BC86;
    selection-color: #FFFFFF;
}

QLineEdit:hover, QComboBox:hover {
    background: #FFFFFF;
    border-color: #77B796;
}

QLineEdit:focus, QComboBox:focus, QPushButton:focus, QToolButton:focus {
    border: 2px solid #219466;
}

QLineEdit:disabled, QComboBox:disabled {
    color: #7E9388;
    background: #EFF5F1;
    border-color: #D6E3DB;
}

QComboBox::drop-down {
    width: 28px;
    border: none;
}

QComboBox QAbstractItemView {
    background: #FFFFFF;
    color: #183A2A;
    border: 1px solid #BFD8CA;
    selection-background-color: #D8F1E3;
    selection-color: #12432E;
    outline: none;
}

QPushButton {
    background: #F2FAF5;
    color: #244B38;
    border: 1px solid #BFDACB;
    border-radius: 8px;
    min-height: 35px;
    padding: 0 13px;
    font-weight: 600;
}

QPushButton:hover {
    background: #E5F5EC;
    border-color: #80B99A;
}

QPushButton:pressed {
    background: #D8EEE2;
}

QPushButton:disabled {
    color: #91A399;
    background: #EEF3F0;
    border-color: #D7E2DB;
}

QPushButton#PrimaryButton {
    color: #FFFFFF;
    background: #218B60;
    border-color: #18764F;
}

QPushButton#PrimaryButton:hover {
    background: #187A53;
    border-color: #116A46;
}

QPushButton#PrimaryButton:pressed {
    background: #126A46;
}

QPushButton#DangerButton {
    color: #9A3345;
    background: #FFF2F4;
    border-color: #E7B8C1;
}

QPushButton#DangerButton:hover {
    background: #FDE6EA;
    border-color: #D493A0;
}

QToolButton {
    background: transparent;
    color: #315B47;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 4px 7px;
}

QToolButton:hover {
    color: #126A46;
    background: #E8F6EE;
    border-color: #C8E4D4;
}

QCheckBox {
    spacing: 7px;
    color: #315646;
    border: none;
    outline: none;
}

QCheckBox:focus {
    border: none;
    outline: none;
}

QProgressBar {
    min-height: 9px;
    max-height: 9px;
    border: none;
    border-radius: 4px;
    background: #DDEBE3;
    color: transparent;
}

QProgressBar::chunk {
    border-radius: 4px;
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #56C88F,stop:1 #16865A);
}

QPlainTextEdit {
    background: #F8FCF9;
    color: #365849;
    border: 1px solid #D2E6DA;
    border-radius: 8px;
    padding: 7px;
    font-family: "Cascadia Mono", "Consolas";
    font-size: 11px;
    selection-background-color: #CDEBD9;
}

QPlainTextEdit#UrlInput {
    background: #FBFEFC;
    color: #173A2A;
    border: 1px solid #BED8C9;
    border-radius: 8px;
    padding: 7px 9px;
    font-family: "Segoe UI", "Microsoft YaHei UI";
    font-size: 13px;
    selection-background-color: #52BC86;
    selection-color: #FFFFFF;
}

QPlainTextEdit#UrlInput:hover {
    background: #FFFFFF;
    border-color: #77B796;
}

QPlainTextEdit#UrlInput:focus {
    border: 2px solid #219466;
}

QListWidget#BatchResults {
    background: transparent;
    border: none;
    outline: none;
    color: #789084;
}

QListWidget#BatchResults::item {
    border: none;
    background: transparent;
}

QFrame#BatchResultRow {
    background: #F8FCF9;
    border: 1px solid #D2E7DA;
    border-radius: 9px;
}

QLabel#ResultTitle {
    color: #173E2C;
    font-size: 13px;
    font-weight: 650;
}

QLabel#ResultMeta {
    color: #637D70;
    font-size: 11px;
}

QLabel#ResultStatus {
    color: #5E7569;
    background: #EDF4F0;
    border: 1px solid #D2E1D8;
    border-radius: 7px;
    padding: 4px 5px;
    font-size: 11px;
    font-weight: 650;
}

QLabel#ResultStatus[kind="success"] {
    color: #12643F;
    background: #E2F7EB;
    border-color: #B7E2C9;
}

QLabel#ResultStatus[kind="working"] {
    color: #176646;
    background: #E8F6EE;
    border-color: #9FD2B6;
}

QLabel#ResultStatus[kind="error"] {
    color: #922F42;
    background: #FFF1F3;
    border-color: #F0C0C9;
}

QLabel#QueueStatus {
    color: #295A43;
    font-weight: 650;
}

QFrame#BatchResultRow QPushButton {
    min-height: 30px;
    padding: 0 10px;
}

QScrollBar:vertical {
    width: 8px;
    background: transparent;
    margin: 2px 0;
}

QScrollBar::handle:vertical {
    min-height: 28px;
    background: #B9DACA;
    border-radius: 4px;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QToolTip {
    color: #173A2A;
    background: #FFFFFF;
    border: 1px solid #BFD8CA;
    padding: 5px;
}

QPushButton#WorkspaceTab {
    min-height: 34px;
    padding: 0 16px;
    color: #416454;
    background: rgba(255, 255, 255, 150);
    border: 1px solid #C9E3D4;
}

QPushButton#WorkspaceTab:checked {
    color: #FFFFFF;
    background: #218B60;
    border-color: #18764F;
}

QPushButton#WorkspaceTab[busy="true"] {
    border: 2px solid #E7B75B;
}

QWidget#EditorWorkbench {
    background: transparent;
}

QFrame#EditorToolbar, QFrame#EditorStatusBar {
    background: rgba(255, 255, 255, 225);
    border: 1px solid #CFE5D7;
    border-radius: 11px;
}

QFrame#EditorPanel {
    background: #FFFFFF;
    border: 1px solid #CFE5D7;
    border-radius: 11px;
}

QLabel#EditorPanelTitle {
    color: #153E2C;
    font-size: 14px;
    font-weight: 700;
}

QLabel#EditorProjectTitle {
    color: #214E39;
    font-weight: 650;
    padding: 0 8px;
}

QLabel#PreviewTime, QLabel#TimelineDuration, QLabel#EditorStatus {
    color: #526F61;
    font-size: 12px;
}

QFrame#VideoSurface {
    background: #101915;
    border: 1px solid #BFD8CA;
    border-radius: 8px;
}

QGraphicsView#VideoPreview {
    background: #050806;
    border: none;
}

QFrame#PlayerControls {
    background: rgba(0, 0, 0, 210);
    border: 1px solid rgba(255, 255, 255, 35);
    border-radius: 7px;
}

QFrame#PlayerControls QPushButton {
    min-height: 30px;
    padding: 0 9px;
    color: #F2FFF7;
    background: rgba(255, 255, 255, 22);
    border: 1px solid rgba(213, 241, 225, 80);
    border-radius: 6px;
}

QFrame#PlayerControls QPushButton:hover {
    background: rgba(88, 190, 136, 105);
    border-color: rgba(207, 245, 224, 170);
}

QFrame#PlayerControls QPushButton:pressed {
    background: rgba(49, 145, 94, 150);
}

QFrame#PlayerControls QLabel#PreviewTime {
    color: #F2FFF7;
    font-family: "Cascadia Mono", "Consolas";
    font-size: 11px;
}

QFrame#PlayerControls QComboBox#PlaybackRate {
    min-height: 30px;
    max-height: 30px;
    min-width: 64px;
    padding: 0 24px 0 8px;
    color: #F2FFF7;
    background: rgba(255, 255, 255, 22);
    border: 1px solid rgba(213, 241, 225, 80);
    border-radius: 6px;
}

QFrame#PlayerControls QSlider::groove:horizontal {
    height: 5px;
    border-radius: 2px;
    background: rgba(221, 242, 230, 100);
}

QFrame#PlayerControls QSlider::sub-page:horizontal {
    border-radius: 2px;
    background: #52C98B;
}

QFrame#PlayerControls QSlider::handle:horizontal {
    width: 14px;
    margin: -5px 0;
    border-radius: 7px;
    background: #F5FFF9;
}

QSlider#PlayerVolume {
    min-width: 58px;
    max-width: 72px;
}

QDialog#VideoFullscreenDialog {
    background: #000000;
}

QListWidget#AssetList, QTableWidget#TimelineTable, QTableWidget#AudioTable, QTableWidget#SubtitleTable {
    background: #F8FCF9;
    alternate-background-color: #F0F8F3;
    color: #244B38;
    border: 1px solid #D2E6DA;
    border-radius: 8px;
    outline: none;
    gridline-color: #DDEBE3;
    selection-background-color: #D8F1E3;
    selection-color: #12432E;
}

QFrame#MultiTrackTimeline {
    background: #102019;
    border: 1px solid #BFD8CA;
    border-radius: 8px;
}

QFrame#TimelineLabels {
    background: #EAF5EE;
    border: none;
    border-right: 1px solid #8DB6A0;
    border-radius: 7px 0 0 7px;
}

QLabel#TimelineLaneLabel {
    color: #244B38;
    font-weight: 700;
    border-bottom: 1px solid #C8DED1;
}

QLabel#TimelineZoomLabel {
    color: #476B59;
    font-size: 10px;
}

QGraphicsView#TimelineGraphicsView {
    background: #102019;
    border: none;
    border-radius: 0 7px 7px 0;
}

QListWidget#AssetList::item {
    min-height: 45px;
    padding: 5px 7px;
    border-bottom: 1px solid #E1EEE6;
}

QListWidget#AssetList::item:selected, QTableWidget::item:selected {
    background: #D8F1E3;
    color: #12432E;
}

QHeaderView::section {
    color: #365B49;
    background: #EAF6EF;
    border: none;
    border-right: 1px solid #D2E6DA;
    border-bottom: 1px solid #C8DFD2;
    padding: 6px;
    font-weight: 650;
}

QSplitter#EditorSplitter::handle {
    background: transparent;
    width: 8px;
}

QSlider::groove:horizontal {
    height: 5px;
    border-radius: 2px;
    background: #D9E9E0;
}

QSlider::sub-page:horizontal {
    border-radius: 2px;
    background: #3BA575;
}

QSlider::handle:horizontal {
    width: 14px;
    margin: -5px 0;
    border-radius: 7px;
    background: #187A53;
}

QSpinBox, QDoubleSpinBox {
    background: #FBFEFC;
    color: #173A2A;
    border: 1px solid #BED8C9;
    border-radius: 7px;
    min-height: 31px;
    padding: 0 7px;
}

QSpinBox:focus, QDoubleSpinBox:focus {
    border: 2px solid #219466;
}

QTabWidget#InspectorTabs::pane {
    border: 1px solid #CFE5D7;
    border-radius: 9px;
    background: #FFFFFF;
    top: -1px;
}

QTabBar::tab {
    min-width: 72px;
    min-height: 32px;
    padding: 0 10px;
    color: #4C6C5D;
    background: #EAF6EF;
    border: 1px solid #CFE5D7;
    border-bottom: none;
    border-top-left-radius: 7px;
    border-top-right-radius: 7px;
}

QTabBar::tab:selected {
    color: #FFFFFF;
    background: #218B60;
    border-color: #18764F;
}

QPushButton#ModelStatusButton {
    min-height: 31px;
    padding: 0 11px;
    color: #805B12;
    background: #FFF7DE;
    border: 1px solid #ECD79C;
    border-radius: 9px;
}

QPushButton#ModelStatusButton[kind="success"] {
    color: #12643F;
    background: #E2F7EB;
    border-color: #B7E2C9;
}

QFrame#IntelligencePanel {
    background: #F4FAF6;
    border: 1px solid #D2E6DA;
    border-radius: 9px;
}

QDialog {
    background: #EFF9F3;
}

QFrame#ModelManagerHeader, QFrame#ModelProgressPanel {
    background: #FFFFFF;
    border: 1px solid #CFE5D7;
    border-radius: 11px;
}

QLabel#ModelManagerTitle {
    color: #123C2A;
    font-size: 19px;
    font-weight: 700;
}

QLabel#ModelSummary {
    color: #805B12;
    background: #FFF7DE;
    border: 1px solid #ECD79C;
    border-radius: 9px;
    padding: 5px 10px;
    font-weight: 650;
}

QLabel#ModelSummary[kind="success"] {
    color: #12643F;
    background: #E2F7EB;
    border-color: #B7E2C9;
}

QLabel#ModelPath {
    color: #365849;
    background: #F8FCF9;
    border: 1px solid #D2E6DA;
    border-radius: 7px;
    padding: 6px 9px;
    font-family: "Cascadia Mono", "Consolas";
    font-size: 11px;
}

QTableWidget#ModelTable {
    background: #FFFFFF;
    color: #244B38;
    border: 1px solid #CFE5D7;
    border-radius: 10px;
    gridline-color: #DDEBE3;
    outline: none;
}

QLabel#ModelState {
    min-width: 62px;
    padding: 5px 7px;
    color: #805B12;
    background: #FFF7DE;
    border: 1px solid #ECD79C;
    border-radius: 8px;
    font-weight: 650;
}

QLabel#ModelState[kind="installed"] {
    color: #12643F;
    background: #E2F7EB;
    border-color: #B7E2C9;
}

QLabel#ModelState[kind="corrupt"] {
    color: #922F42;
    background: #FFF1F3;
    border-color: #F0C0C9;
}

QLabel#ModelState[kind="partial"], QLabel#ModelState[kind="unverified"] {
    color: #176646;
    background: #E8F6EE;
    border-color: #9FD2B6;
}

QLabel#ModelName {
    color: #173E2C;
    font-weight: 650;
}

QLabel#ModelDescription, QLabel#ModelVersion {
    color: #637D70;
    font-size: 11px;
}

QPushButton#LinkButton {
    min-height: 22px;
    padding: 0;
    color: #16764E;
    background: transparent;
    border: none;
    text-align: left;
    font-size: 11px;
}

QPushButton#LinkButton:hover {
    color: #0B5D3D;
    text-decoration: underline;
}

QLabel#ModelProgressTitle {
    color: #214E39;
    font-weight: 650;
}

QPushButton#DangerButton:disabled {
    color: #91A399;
    background: #EEF3F0;
    border-color: #D7E2DB;
}
"""
