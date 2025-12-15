"""
通用工具模块

包含：
- image: 图像处理工具
- json_utils: JSON 读写工具  
- logging: 日志配置
- retry: 重试装饰器
- labels: 标签处理工具
"""

from .image import (
    image_to_base64_url, 
    image_to_base64,
    get_image_size, 
    crop_region,
    convert_normalized_coords
)
from .json_utils import (
    parse_llm_json, 
    save_annotation, 
    load_annotation,
    to_xanylabeling_format
)
from .retry import retry_with_backoff, retry_api_call
from .labels import (
    get_category,
    normalize_label,
    normalize_vehicle_label,
    get_category_color,
    get_category_emoji
)
from .logging import setup_logger, get_logger, TaskProgress

