"""
重试装饰器

提供带指数退避的重试机制，用于 API 调用。
"""

import time
import functools
from typing import Tuple, Type, Callable, Any
import logging


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    logger_name: str = "glm_labeling"
) -> Callable:
    """
    带指数退避的重试装饰器
    
    Args:
        max_retries: 最大重试次数
        initial_delay: 初始延迟（秒）
        backoff_factor: 延迟增长因子
        exceptions: 需要捕获的异常类型
        logger_name: 日志记录器名称
        
    Returns:
        装饰器函数
        
    Usage:
        @retry_with_backoff(max_retries=3)
        def call_api():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            logger = logging.getLogger(logger_name)
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries} failed: {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        logger.error(
                            f"All {max_retries} attempts failed. Last error: {e}"
                        )
            
            raise last_exception
        
        return wrapper
    return decorator


def retry_api_call(
    func: Callable,
    max_retries: int = 3,
    delay: float = 2.0,
    backoff_factor: float = 2.0,
    on_retry: Callable = None
) -> Any:
    """
    函数式重试调用（非装饰器版本）

    支持指数退避和 429 限流处理。

    Args:
        func: 要执行的函数（无参数 lambda 或 partial）
        max_retries: 最大重试次数
        delay: 初始重试间隔（秒）
        backoff_factor: 退避因子（默认 2.0，指数退避）
        on_retry: 重试时的回调函数 (attempt, error) -> None

    Returns:
        函数执行结果

    Usage:
        result = retry_api_call(
            lambda: client.chat.completions.create(...),
            max_retries=3
        )
    """
    last_exception = None
    current_delay = delay

    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            last_exception = e

            if attempt < max_retries - 1:
                # 检查是否为 429 限流错误
                wait_time = current_delay
                if _is_rate_limit_error(e):
                    # 从响应头获取重试时间，或使用更长的默认等待
                    wait_time = _get_retry_after(e) or (current_delay * 2)

                if on_retry:
                    on_retry(attempt + 1, e)

                time.sleep(wait_time)
                current_delay *= backoff_factor  # 指数退避

    raise last_exception


def _is_rate_limit_error(e: Exception) -> bool:
    """检查是否为 API 限流错误 (429)"""
    error_str = str(e).lower()
    # 检查常见的限流错误标识
    if '429' in error_str or 'rate limit' in error_str or 'too many requests' in error_str:
        return True
    # 检查异常属性
    if hasattr(e, 'status_code') and e.status_code == 429:
        return True
    if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
        if e.response.status_code == 429:
            return True
    return False


def _get_retry_after(e: Exception) -> float | None:
    """从异常中提取 Retry-After 头的值"""
    try:
        if hasattr(e, 'response') and hasattr(e.response, 'headers'):
            retry_after = e.response.headers.get('Retry-After')
            if retry_after:
                return float(retry_after)
    except (ValueError, TypeError):
        pass
    return None
