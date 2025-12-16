"""
GLM-Labeling CLI 模块

使用 click 实现子命令风格的命令行接口。

Commands:
    run         批量标注图片
    dashboard   启动实时监控 Dashboard
    visualize   生成可视化图片
"""

import click

from .run import run
from .visualize import visualize


@click.group(invoke_without_command=True)
@click.version_option(version="0.2.0", prog_name="glm-label")
@click.pass_context
def cli(ctx):
    """GLM-4.6V 交通场景自动标注系统
    
    \b
    示例:
      glm-label run --prefix D1 --workers 5
      glm-label dashboard --port 8080
      glm-label visualize --prefix D1
    """
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# 注册子命令
cli.add_command(run)
cli.add_command(visualize)

# Dashboard 命令延迟注册（可选依赖）
try:
    from .dashboard_cmd import dashboard
    cli.add_command(dashboard)
except ImportError:
    # Dashboard 依赖未安装，跳过
    pass


def main():
    """CLI 入口点"""
    cli()


if __name__ == "__main__":
    main()
