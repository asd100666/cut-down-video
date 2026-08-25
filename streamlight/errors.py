from __future__ import annotations

import re


class UserCancelled(Exception):
    """用户主动取消当前任务。"""


_SECRET_QUERY_RE = re.compile(
    r"(?i)(token|sig|signature|auth|authorization|key|policy|expires)=([^&\s]+)"
)
_COOKIE_RE = re.compile(r"(?i)(cookie\s*:\s*)[^\r\n]+")


def redact_secrets(message: str) -> str:
    value = _SECRET_QUERY_RE.sub(lambda match: f"{match.group(1)}=<已隐藏>", str(message))
    return _COOKIE_RE.sub(r"\1<已隐藏>", value)


def friendly_error(error: BaseException) -> tuple[str, str]:
    raw = redact_secrets(str(error)).strip()
    lower = raw.lower()

    if "unsupported url" in lower or "no suitable extractor" in lower:
        return "暂不支持这个页面", "可尝试更新 yt-dlp，或粘贴浏览器开发者工具中合法获取的 m3u8/mpd 地址。"
    if any(word in lower for word in ("sign in", "login", "cookies", "authentication")):
        return "页面需要登录状态", "在高级选项中选择你已登录该网站的浏览器，然后重新分析。"
    if "403" in lower or "forbidden" in lower:
        return "服务器拒绝访问（403）", "检查浏览器 Cookie、Referer 和链接是否过期；临时媒体地址通常需要重新获取。"
    if "drm" in lower:
        return "媒体可能受 DRM 保护", "本工具不绕过 DRM 或网站访问控制，请改用站点提供的离线功能。"
    if "ffmpeg" in lower:
        return "FFmpeg 处理失败", "检查依赖状态，或安装完整版 FFmpeg 后重新启动应用。"
    if any(word in lower for word in ("timed out", "timeout", "connection", "network")):
        return "网络连接失败", "检查网络连接后重试；程序已为媒体分片配置自动重试。"
    if "requested format is not available" in lower:
        return "所选清晰度不可用", "改用“最佳画质”或降低分辨率后重试。"

    detail = raw or error.__class__.__name__
    if len(detail) > 360:
        detail = detail[:357] + "..."
    return "任务执行失败", detail

