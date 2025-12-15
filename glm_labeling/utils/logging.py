"""
日志配置模块

提供统一的日志配置，替代散落各处的 print() 语句。
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str = "glm_labeling",
    level: str = "INFO",
    log_file: Optional[Path] = None,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    配置并返回 logger
    
    Args:
        name: logger 名称
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR)
        log_file: 日志文件路径（可选）
        format_string: 自定义格式字符串
        
    Returns:
        配置好的 Logger 实例
    """
    logger = logging.getLogger(name)
    
    # 避免重复添加 handler
    if logger.handlers:
        return logger
    
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # 默认格式
    if format_string is None:
        format_string = "%(asctime)s | %(levelname)-8s | %(message)s"
    
    formatter = logging.Formatter(format_string, datefmt="%Y-%m-%d %H:%M:%S")
    
    # 控制台输出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件输出（可选）
    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = "glm_labeling") -> logging.Logger:
    """
    获取 logger（如果不存在则创建默认配置）
    
    Args:
        name: logger 名称
        
    Returns:
        Logger 实例
    """
    logger = logging.getLogger(name)
    
    # 如果没有 handler，使用默认配置
    if not logger.handlers:
        return setup_logger(name)
    
    return logger


class TaskProgress:
    """
    任务进度跟踪器
    
    用于显示批量处理进度，替代散落的 print 语句
    """
    
    def __init__(self, total: int, task_name: str = "Processing"):
        self.total = total
        self.current = 0
        self.task_name = task_name
        self.logger = get_logger()
        self.success_count = 0
        self.error_count = 0
    
    def start(self):
        """开始任务"""
        self.logger.info("=" * 60)
        self.logger.info(f"🚀 {self.task_name} - Total: {self.total} items")
        self.logger.info("=" * 60)
    
    def update(self, item_name: str, success: bool = True, message: str = ""):
        """更新进度"""
        self.current += 1
        
        if success:
            self.success_count += 1
            emoji = "✅"
        else:
            self.error_count += 1
            emoji = "❌"
        
        progress = f"[{self.current}/{self.total}]"
        log_msg = f"{emoji} {progress} {item_name}"
        if message:
            log_msg += f" - {message}"
        
        if success:
            self.logger.info(log_msg)
        else:
            self.logger.warning(log_msg)
    
    def finish(self, extra_stats: Optional[dict] = None):
        """完成任务"""
        self.logger.info("=" * 60)
        self.logger.info(f"📊 {self.task_name} Complete")
        self.logger.info(f"   ✅ Success: {self.success_count}")
        self.logger.info(f"   ❌ Errors: {self.error_count}")
        
        if extra_stats:
            for key, value in extra_stats.items():
                self.logger.info(f"   📈 {key}: {value}")
        
        self.logger.info("=" * 60)
