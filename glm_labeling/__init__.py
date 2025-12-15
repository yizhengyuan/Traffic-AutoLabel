"""
GLM-4.6V 交通场景自动标注系统

核心模块：
- config: 统一配置管理
- utils: 通用工具函数
- detector: 目标检测
- classifier: 交通标志分类
- io: 输入输出处理
"""

__version__ = "0.2.0"
__author__ = "GLM_Labeling Team"

from .config import Config, get_config
from .utils import image as image_utils
from .utils import json_utils
from .utils import logging as log_utils
