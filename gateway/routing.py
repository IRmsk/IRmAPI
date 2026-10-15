"""模型名 -> Provider 的路由规则。"""
from __future__ import annotations

from gateway.config import Config


class RoutingError(Exception):
    pass


def resolve_provider_key(model: str, config: Config) -> str:
    """根据模型名解析出应使用的 provider key。

    规则（按优先级）：
      1. ark-* / doubao-ark-*              -> doubao_ark（豆包官方方舟）
      2. doubao-web* / doubao-free* / web-* -> doubao_web（需 ALLOW_WEB_PROVIDERS=1）
      3. doubao*                           -> doubao_ark（官方优先）否则 doubao_web（需开 web）
      4. deepseek-*                        -> 官方 API Key 优先；网页版需 ALLOW_WEB_PROVIDERS=1
      5. qwen-*                            -> qwen_api（官方优先）；网页版需 ALLOW_WEB_PROVIDERS=1
      6. kimi-* / glm-* / moonshot-* / compat-* -> openai_compat（通用兼容上游）
      7. 其它未知模型                      -> 默认 doubao_ark（官方），不默认走网页版
    """
    m = model.lower()
    web_ok = config.allow_web_providers

    # 方舟官方通道
    if m.startswith("ark-") or m.startswith("doubao-ark"):
        if not config.ark_enabled:
            raise RoutingError("模型路由到 doubao_ark，但未配置 ARK_API_KEY")
        return "doubao_ark"

    # 豆包网页版（免 Key）通道——需显式开启
    if m.startswith("doubao-web") or m.startswith("doubao-free") or m.startswith("web-"):
        if not web_ok:
            raise RoutingError(
                "网页版 provider 默认关闭。设 ALLOW_WEB_PROVIDERS=1 可启用（逆向网页版免 Key，违反平台 ToS）。"
            )
        if not config.doubao_web_enabled:
            raise RoutingError(
                "模型路由到 doubao_web，但未配置凭据：请设置 DOUBAO_COOKIE_1（完整 Cookie）"
                "或 DOUBAO_SESSIONIDS"
            )
        return "doubao_web"

    # 普通 doubao 模型：官方 API 优先，网页版兜底（需开启）
    if "doubao" in m:
        if config.ark_enabled:
            return "doubao_ark"
        if web_ok and config.doubao_web_enabled:
            return "doubao_web"
        if config.doubao_web_enabled:
            raise RoutingError(
                "未配置 ARK_API_KEY，网页版 provider 默认关闭。设 ALLOW_WEB_PROVIDERS=1 可启用。"
            )
        raise RoutingError("未配置任何豆包凭据（ARK_API_KEY 或 DOUBAO_SESSIONIDS）")

    # DeepSeek：官方 API Key 优先；只有网页版凭据时需开启 web
    if m.startswith("deepseek-"):
        if config.deepseek_api_key:
            return "deepseek_web"  # provider 内部会走官方 API 分支
        if web_ok and config.deepseek_enabled:
            return "deepseek_web"
        if config.deepseek_enabled:
            raise RoutingError(
                "DeepSeek 网页版 provider 默认关闭。设 ALLOW_WEB_PROVIDERS=1 可启用，"
                "或配置 DEEPSEEK_API_KEY 走官方 API。"
            )
        raise RoutingError(
            "模型路由到 deepseek，但未配置凭据：DEEPSEEK_API_KEY（官方）或"
            "DEEPSEEK_COOKIE_1 / DEEPSEEK_TOKEN（网页版，需 ALLOW_WEB_PROVIDERS=1）"
        )

    # 通义千问：官方 API 优先；网页版需开启
    if m.startswith("qwen-"):
        if config.qwen_api_key:
            return "qwen_api"
        if web_ok and config.qwen_cookies:
            return "qwen_web"
        if config.qwen_cookies:
            raise RoutingError(
                "通义千问网页版 provider 默认关闭。设 ALLOW_WEB_PROVIDERS=1 可启用，"
                "或配置 QWEN_API_KEY 走官方 API。"
            )
        raise RoutingError(
            "模型路由到 qwen，但未配置凭据：QWEN_API_KEY（官方）或"
            "QWEN_COOKIE_1（网页版，需 ALLOW_WEB_PROVIDERS=1）"
        )

    # 通用 OpenAI 兼容上游（Kimi / GLM / Moonshot / compat-* 等）
    if (
        m.startswith("compat-")
        or m.startswith("kimi-")
        or m.startswith("glm-")
        or m.startswith("moonshot-")
    ):
        if not config.compat_enabled:
            raise RoutingError(
                "模型路由到 openai_compat，但未配置 COMPAT_BASE_URL / COMPAT_API_KEY"
            )
        return "openai_compat"

    # 未知模型名兜底：优先官方方舟，不默认走网页版
    if config.ark_enabled:
        return "doubao_ark"
    if web_ok and config.doubao_web_enabled:
        return "doubao_web"
    raise RoutingError(
        "没有可用的模型通道。请配置 ARK_API_KEY（官方），或设 ALLOW_WEB_PROVIDERS=1 并配置网页版凭据。"
    )
