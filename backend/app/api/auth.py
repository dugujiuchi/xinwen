"""管理端鉴权依赖"""
from fastapi import Header, HTTPException
from app.config import settings


def verify_admin(x_admin_key: str = Header(...)):
    """验证管理员密码。若 ADMIN_ENABLED=false 则跳过验证。"""
    if not settings.admin_enabled:
        return True
    if x_admin_key != settings.admin_password:
        raise HTTPException(status_code=403, detail="管理员密码错误")
    return True
