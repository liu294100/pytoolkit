import requests
from flask import Blueprint, Response, current_app, jsonify, request

from ..services.epg_service import load_epg_programmes
from ..services.http_service import (
    DEFAULT_HEADERS,
    ensure_http_url,
    fetch_text,
    get_proxy_settings,
    normalize_input_url,
    request_url,
    update_proxy_settings,
)
from ..services.m3u_service import parse_m3u
from ..services.proxy_service import rewrite_m3u8_content
from ..services.source_service import load_sources

api_bp = Blueprint("api", __name__)


def _make_proxy_url(raw_url: str) -> str:
    return f"/api/proxy-stream?url={requests.utils.quote(raw_url, safe='')}"


def _attach_channel_proxy_fields(channels: list[dict]) -> None:
    for channel in channels:
        channel_url = (channel.get("url") or "").strip()
        if channel_url:
            channel["playUrl"] = _make_proxy_url(channel_url)

        logo_url = normalize_input_url(channel.get("logo") or "")
        if logo_url.startswith("http://") or logo_url.startswith("https://"):
            channel["logoUrl"] = _make_proxy_url(logo_url)
        else:
            channel["logoUrl"] = ""


@api_bp.route("/sources", methods=["GET"])
def get_sources():
    data = load_sources(current_app.config["SOURCES_FILE"])
    return jsonify(data)


@api_bp.route("/proxy-settings", methods=["GET"])
def get_proxy_config():
    return jsonify(get_proxy_settings())


@api_bp.route("/proxy-settings", methods=["POST"])
def save_proxy_config():
    data = request.get_json(silent=True) or {}
    try:
        settings = update_proxy_settings(
            enabled=bool(data.get("enabled")),
            host=(data.get("host") or "127.0.0.1").strip(),
            port=data.get("port", 7890),
        )
        return jsonify(settings)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@api_bp.route("/channels", methods=["GET"])
def get_channels():
    source_url = normalize_input_url(request.args.get("source_url", ""))
    source_name = request.args.get("source_name", "").strip() or "自定义源"
    user_agent = request.args.get("user_agent", "").strip() or None

    if not source_url:
        return jsonify({"error": "缺少 source_url 参数"}), 400

    try:
        m3u_text = fetch_text(source_url, current_app.config["REQUEST_TIMEOUT_SECONDS"], user_agent=user_agent)
        channels = parse_m3u(m3u_text, source_name)
        _attach_channel_proxy_fields(channels)
        return jsonify({"channels": channels, "total": len(channels)})
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else "未知"
        if status_code == 404:
            return jsonify({"error": f"源地址 404：{source_url}"}), 502
        if status_code in (401, 403):
            return jsonify({"error": f"上游拒绝访问（{status_code}），可能触发风控或需要浏览器环境"}), 502
        return jsonify({"error": f"远程请求失败: {status_code}"}), 502
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@api_bp.route("/channels-text", methods=["POST"])
def get_channels_by_text():
    data = request.get_json(silent=True) or {}
    m3u_text = (data.get("m3u_text") or "").strip()
    source_name = (data.get("source_name") or "文本导入").strip()
    if not m3u_text:
        return jsonify({"error": "缺少 m3u_text"}), 400

    try:
        channels = parse_m3u(m3u_text, source_name)
        _attach_channel_proxy_fields(channels)
        return jsonify({"channels": channels, "total": len(channels)})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@api_bp.route("/epg", methods=["GET"])
def get_epg():
    epg_url = normalize_input_url(request.args.get("epg_url", ""))
    channel_name = (request.args.get("channel_name") or "").strip()
    tvg_id = (request.args.get("tvg_id") or "").strip()
    if not epg_url:
        return jsonify({"error": "缺少 epg_url 参数"}), 400
    if not channel_name and not tvg_id:
        return jsonify({"error": "缺少 channel_name 或 tvg_id"}), 400

    try:
        programmes = load_epg_programmes(
            epg_url=epg_url,
            channel_name=channel_name,
            tvg_id=tvg_id,
            timeout=current_app.config["REQUEST_TIMEOUT_SECONDS"],
        )
        return jsonify({"programmes": programmes, "total": len(programmes)})
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else "未知"
        return jsonify({"error": f"EPG 请求失败: {status_code}"}), 502
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@api_bp.route("/proxy-text", methods=["GET"])
def proxy_text():
    target_url = normalize_input_url(request.args.get("url", ""))
    if not target_url:
        return jsonify({"error": "缺少 url 参数"}), 400

    try:
        content = fetch_text(target_url, current_app.config["REQUEST_TIMEOUT_SECONDS"])
        return Response(content, content_type="text/plain; charset=utf-8")
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@api_bp.route("/proxy-stream", methods=["GET"])
def proxy_stream():
    target_url = normalize_input_url(request.args.get("url", ""))
    if not target_url:
        return jsonify({"error": "缺少 url 参数"}), 400

    try:
        ensure_http_url(target_url)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    timeout = current_app.config["REQUEST_TIMEOUT_SECONDS"]
    forward_headers = {}
    for header in ["Range", "If-Range", "Accept"]:
        value = request.headers.get(header)
        if value:
            forward_headers[header] = value

    try:
        upstream = request_url(target_url, timeout=(8, timeout), stream=True, extra_headers=forward_headers)
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else "未知"
        return jsonify({"error": f"上游返回状态码: {status_code}"}), 502
    except Exception as exc:
        return jsonify({"error": f"请求上游失败: {exc}"}), 502

    content_type = upstream.headers.get("Content-Type", "")
    is_hls = ".m3u8" in target_url or "application/vnd.apple.mpegurl" in content_type

    if is_hls:
        body = upstream.text
        rewritten = rewrite_m3u8_content(body, target_url)
        return Response(rewritten, status=upstream.status_code, content_type="application/vnd.apple.mpegurl; charset=utf-8")

    passthrough_headers = {}
    for header in ["Content-Type", "Content-Length", "Accept-Ranges", "Content-Range", "Cache-Control", "ETag"]:
        value = upstream.headers.get(header)
        if value:
            passthrough_headers[header] = value

    def generate():
        for chunk in upstream.iter_content(chunk_size=1024 * 64):
            if chunk:
                yield chunk

    return Response(generate(), status=upstream.status_code, headers=passthrough_headers)
