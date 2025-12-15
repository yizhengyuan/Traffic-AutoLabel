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
    on_retry: Callable = None
) -> Any:
    """
    函数式重试调用（非装饰器版本）
    
    Args:
        func: 要执行的函数（无参数 lambda 或 partial）
        max_retries: 最大重试次数
        delay: 重试间隔
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
    
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            last_exception = e
            
            if attempt < max_retries - 1:
                if on_retry:
                    on_retry(attempt + 1, e)
                time.sleep(delay * (attempt + 1))  # 简单线性退避
    
    raise last_exception
