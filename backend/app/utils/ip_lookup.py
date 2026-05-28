"""IP 归属地查询工具 — 基于 ip-api.com 免费接口（无需 API Key，限 45次/分钟）"""
import logging

import httpx

logger = logging.getLogger("ip_lookup")

API_URL = "http://ip-api.com/json/{}?lang=zh-CN"


async def lookup_ip(ip: str) -> dict:
    """查询 IP 归属地，返回 {country, region, city, isp}。查询失败返回空字典。"""
    # 内网 IP 跳过查询
    if ip in ("127.0.0.1", "::1", "localhost") or ip.startswith(
        ("192.168.", "10.", "172.16.", "172.17.", "172.18.", "172.19.",
         "172.20.", "172.21.", "172.22.", "172.23.", "172.24.", "172.25.",
         "172.26.", "172.27.", "172.28.", "172.29.", "172.30.", "172.31."),
    ):
        return {"country": "内网", "region": "", "city": "", "isp": ""}

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(API_URL.format(ip))
            if resp.status_code != 200:
                logger.warning("IP查询失败 status=%d", resp.status_code)
                return {}
            data = resp.json()
            if data.get("status") != "success":
                logger.warning("IP查询失败: %s", data.get("message", ""))
                return {}
            return {
                "country": data.get("country", ""),
                "region": data.get("regionName", ""),
                "city": data.get("city", ""),
                "isp": data.get("isp", ""),
            }
    except Exception as e:
        logger.warning("IP查询异常: %r", e)
        return {}
