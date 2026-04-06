"""
高性能缓存管理器
支持内存缓存(TTLCache)和Redis缓存
"""
import hashlib
import json
import pickle
from functools import wraps
from typing import Any, Optional, Callable
from datetime import datetime, timedelta

try:
    from cachetools import TTLCache
    CACHETOOLS_AVAILABLE = True
except ImportError:
    CACHETOOLS_AVAILABLE = False
    print("[WARN] cachetools 未安装")

# 内存缓存实例
_memory_caches = {}


def get_memory_cache(name: str, maxsize: int = 100, ttl: int = 3600) -> Any:
    """获取或创建内存缓存实例"""
    if not CACHETOOLS_AVAILABLE:
        return None

    if name not in _memory_caches:
        _memory_caches[name] = TTLCache(maxsize=maxsize, ttl=ttl)
    return _memory_caches[name]


def cached(cache_name: str, maxsize: int = 100, ttl: int = 3600,
           key_func: Optional[Callable] = None):
    """
    缓存装饰器

    Args:
        cache_name: 缓存名称
        maxsize: 最大缓存条目数
        ttl: 缓存过期时间（秒）
        key_func: 自定义缓存key生成函数
    """
    def decorator(func: Callable) -> Callable:
        cache = get_memory_cache(cache_name, maxsize, ttl)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            if cache is None:
                return await func(*args, **kwargs)

            # 生成缓存key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = _generate_cache_key(func.__name__, args, kwargs)

            # 尝试从缓存获取
            if cache_key in cache:
                print(f"[CACHE HIT] {func.__name__}: {cache_key[:32]}...")
                return cache[cache_key]

            # 执行函数
            result = await func(*args, **kwargs)

            # 存入缓存
            cache[cache_key] = result
            print(f"[CACHE SET] {func.__name__}: {cache_key[:32]}... (size: {len(cache)})")

            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            if cache is None:
                return func(*args, **kwargs)

            # 生成缓存key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = _generate_cache_key(func.__name__, args, kwargs)

            # 尝试从缓存获取
            if cache_key in cache:
                print(f"[CACHE HIT] {func.__name__}: {cache_key[:32]}...")
                return cache[cache_key]

            # 执行函数
            result = func(*args, **kwargs)

            # 存入缓存
            cache[cache_key] = result
            print(f"[CACHE SET] {func.__name__}: {cache_key[:32]}... (size: {len(cache)})")

            return result

        # 根据被装饰函数类型返回相应的wrapper
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def _generate_cache_key(func_name: str, args: tuple, kwargs: dict) -> str:
    """生成缓存key"""
    # 过滤掉非可序列化的参数（如数据库连接）
    serializable_args = []
    for arg in args:
        try:
            json.dumps(arg)
            serializable_args.append(arg)
        except (TypeError, ValueError):
            # 对于非序列化对象，使用其字符串表示
            serializable_args.append(str(type(arg)))

    key_data = {
        "func": func_name,
        "args": serializable_args,
        "kwargs": kwargs
    }

    key_str = json.dumps(key_data, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(key_str.encode()).hexdigest()


def clear_cache(cache_name: Optional[str] = None):
    """清除缓存"""
    global _memory_caches

    if cache_name:
        if cache_name in _memory_caches:
            _memory_caches[cache_name].clear()
            print(f"[CACHE] Cleared {cache_name}")
    else:
        for name, cache in _memory_caches.items():
            cache.clear()
            print(f"[CACHE] Cleared {name}")


def get_cache_stats() -> dict:
    """获取缓存统计信息"""
    stats = {}
    for name, cache in _memory_caches.items():
        stats[name] = {
            "size": len(cache),
            "maxsize": cache.maxsize,
            "currsize": cache.currsize if hasattr(cache, 'currsize') else len(cache),
            "hit_rate": getattr(cache, 'hit_rate', 'N/A')
        }
    return stats


# 特定用途的缓存实例
def get_llm_cache():
    """获取LLM结果缓存"""
    return get_memory_cache("llm_results", maxsize=200, ttl=86400)  # 24小时


def get_shap_cache():
    """获取SHAP分析缓存"""
    return get_memory_cache("shap_results", maxsize=200, ttl=86400)


def get_detection_cache():
    """获取检测结果缓存"""
    return get_memory_cache("detection_results", maxsize=500, ttl=3600)  # 1小时


def get_api_cache():
    """获取API响应缓存"""
    return get_memory_cache("api_responses", maxsize=1000, ttl=300)  # 5分钟
