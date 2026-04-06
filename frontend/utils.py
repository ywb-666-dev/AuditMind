"""
前端工具函数 - 缓存和性能优化
"""
import streamlit as st
import requests
from datetime import datetime, timedelta
import hashlib
import json

# API基础URL
API_BASE_URL = "http://localhost:8000/api"


class APICache:
    """API响应缓存管理器"""

    def __init__(self):
        self._init_cache()

    def _init_cache(self):
        """初始化缓存存储"""
        if 'api_cache' not in st.session_state:
            st.session_state.api_cache = {}
        if 'api_cache_timestamp' not in st.session_state:
            st.session_state.api_cache_timestamp = {}

    def get(self, key: str, ttl: int = 300) -> any:
        """
        获取缓存数据

        Args:
            key: 缓存key
            ttl: 过期时间（秒），默认5分钟

        Returns:
            缓存数据或None
        """
        self._init_cache()

        if key not in st.session_state.api_cache:
            return None

        timestamp = st.session_state.api_cache_timestamp.get(key, 0)
        if datetime.now().timestamp() - timestamp > ttl:
            # 缓存过期，清除
            del st.session_state.api_cache[key]
            del st.session_state.api_cache_timestamp[key]
            return None

        return st.session_state.api_cache[key]

    def set(self, key: str, value: any):
        """设置缓存数据"""
        self._init_cache()
        st.session_state.api_cache[key] = value
        st.session_state.api_cache_timestamp[key] = datetime.now().timestamp()

    def clear(self, pattern: str = None):
        """清除缓存"""
        self._init_cache()
        if pattern:
            keys_to_remove = [k for k in st.session_state.api_cache if pattern in k]
            for k in keys_to_remove:
                del st.session_state.api_cache[k]
                if k in st.session_state.api_cache_timestamp:
                    del st.session_state.api_cache_timestamp[k]
        else:
            st.session_state.api_cache.clear()
            st.session_state.api_cache_timestamp.clear()


# 全局缓存实例
api_cache = APICache()


def cached_api_request(endpoint: str, method: str = "GET", data: dict = None,
                       headers: dict = None, timeout: int = 30,
                       cache_ttl: int = 300, force_refresh: bool = False):
    """
    带缓存的API请求

    Args:
        endpoint: API端点
        method: HTTP方法
        data: 请求数据
        headers: 请求头
        timeout: 超时时间
        cache_ttl: 缓存过期时间（秒）
        force_refresh: 是否强制刷新缓存

    Returns:
        API响应数据
    """
    # 只有GET请求使用缓存
    if method != "GET":
        return _make_raw_request(endpoint, method, data, headers, timeout)

    # 生成缓存key
    cache_key = _generate_cache_key(endpoint, method, data, headers)

    # 尝试从缓存获取
    if not force_refresh:
        cached = api_cache.get(cache_key, ttl=cache_ttl)
        if cached is not None:
            print(f"[CACHE HIT] {endpoint}")
            return cached

    # 执行请求
    result = _make_raw_request(endpoint, method, data, headers, timeout)

    # 缓存结果
    if result is not None:
        api_cache.set(cache_key, result)
        print(f"[CACHE SET] {endpoint}")

    return result


def _make_raw_request(endpoint: str, method: str, data: dict,
                      headers: dict, timeout: int) -> any:
    """执行原始API请求"""
    url = f"{API_BASE_URL}{endpoint}"

    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=timeout)
        elif method == "POST":
            response = requests.post(url, json=data, headers=headers, timeout=timeout)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, timeout=timeout)
        else:
            return None

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            # 认证失败，清除缓存
            api_cache.clear()
            return None
        else:
            return None
    except Exception as e:
        print(f"[API ERROR] {endpoint}: {e}")
        return None


def _generate_cache_key(endpoint: str, method: str, data: dict, headers: dict) -> str:
    """生成缓存key"""
    key_data = {
        "endpoint": endpoint,
        "method": method,
        "data": data,
        "auth": headers.get("Authorization") if headers else None
    }
    key_str = json.dumps(key_data, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(key_str.encode()).hexdigest()


def clear_api_cache(pattern: str = None):
    """清除API缓存"""
    api_cache.clear(pattern)


# 性能监控装饰器
def performance_timer(func):
    """函数执行时间计时器"""
    import time
    import functools

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        print(f"[PERF] {func.__name__} took {elapsed:.3f}s")
        return result

    return wrapper


# 批量数据加载优化
def batch_load_data(items: list, batch_size: int = 10):
    """
    分批加载数据，避免一次加载过多导致卡顿

    Args:
        items: 数据列表
        batch_size: 每批大小

    Yields:
        每批数据
    """
    for i in range(0, len(items), batch_size):
        yield items[i:i + batch_size]


# 延迟加载组件
class LazyLoader:
    """延迟加载组件"""

    def __init__(self, loader_func, *args, **kwargs):
        self.loader_func = loader_func
        self.args = args
        self.kwargs = kwargs
        self._data = None
        self._loaded = False

    @property
    def data(self):
        if not self._loaded:
            self._data = self.loader_func(*self.args, **self.kwargs)
            self._loaded = True
        return self._data

    def refresh(self):
        """刷新数据"""
        self._data = self.loader_func(*self.args, **self.kwargs)
        self._loaded = True
        return self._data
