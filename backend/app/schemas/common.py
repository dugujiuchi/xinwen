from typing import Generic, TypeVar, Optional

from pydantic import BaseModel

T = TypeVar("T")


class PaginationParams(BaseModel):
    """分页参数"""
    page: int = 1
    size: int = 20


class ApiResponse(BaseModel, Generic[T]):
    """统一响应格式"""
    code: int = 200
    message: str = "success"
    data: Optional[T] = None


class PaginatedData(BaseModel, Generic[T]):
    """分页数据包装"""
    items: list[T]
    total: int
    page: int
    size: int


class PaginatedResponse(ApiResponse[PaginatedData[T]], Generic[T]):
    """带分页的统一响应"""
    pass
