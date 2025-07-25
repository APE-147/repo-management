"""
命令行界面模块 - 使用 Typer 框架
"""
import sys
import logging
import platform
import subprocess
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich import print

from .core.manager import RepoManager
from .services.config import Config
from .utils.templates import create_launchd_plist

# 创建 Typer 应用
app = typer.Typer(
    name="repo-manager",
    help="GitHub Repository Manager - 自动化GitHub仓库管理系统",
    rich_markup_mode="rich"
)

console = Console()

def setup_cli_logging(verbose: bool = False):
    """设置CLI日志"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

@app.command()
def init(
    config_dir: Optional[str] = typer.Option(None, "--config-dir", "-c", help="自定义配置目录路径"),
    force: bool = typer.Option(False, "--force", "-f", help="强制重新配置")
):
    """初始化系统"""
    config = Config(config_dir)
    
    console.print("=== GitHub Repository Manager 初始化 ===", style="bold blue")
    
    # 运行配置向导
    if not config.validate_config() or force:
        console.print("配置GitHub用户名...", style="yellow")
        # 尝试从环境变量获取
        import os
        github_username = os.getenv("GITHUB_USERNAME", "")
        if not github_username:
            console.print("请设置环境变量 GITHUB_USERNAME 或手动配置")
            console.print("export GITHUB_USERNAME=your-username")
            github_username = typer.prompt("请输入GitHub用户名 (回车跳过)", default="").strip()
        
        if github_username:
            config.github_username = github_username
            config.save_config()
            console.print(f"已设置GitHub用户名: {github_username}", style="green")
        else:
            console.print("未设置GitHub用户名，稍后可通过 'repo-manager config --set github_username=用户名' 设置", style="yellow")
    else:
        console.print("配置已存在且有效", style="green")
    
    # 初始化管理器
    manager = RepoManager(config)
    if manager.initialize():
        console.print("\n✅ 初始化成功!", style="bold green")
        console.print(f"配置目录: {config.config_dir}")
        console.print(f"数据目录: {config.data_dir}")
        console.print(f"repo-index目录: {config.repo_index_dir}")
    else:
        console.print("\n❌ 初始化失败!", style="bold red")
        raise typer.Exit(1)

@app.command()
def scan(
    config_dir: Optional[str] = typer.Option(None, "--config-dir", "-c", help="自定义配置目录路径")
):
    """执行一次完整扫描"""
    config = Config(config_dir)
    manager = RepoManager(config)
    
    if not manager.initialize():
        console.print("❌ 系统未正确初始化，请先运行 'repo-manager init'", style="bold red")
        raise typer.Exit(1)
    
    console.print("开始执行扫描...", style="blue")
    result = manager.scan_once()
    
    console.print("✅ 扫描完成!", style="bold green")
    if result["file_changes"]:
        changes = result["file_changes"]
        console.print(f"文件变动: 新增{len(changes['new_files'])}个, "
                     f"修改{len(changes['modified_files'])}个, "
                     f"删除{len(changes['deleted_files'])}个")
    
    if result["unindexed_repos"]:
        console.print(f"发现未索引仓库: {len(result['unindexed_repos'])}个")

@app.command()
def update(
    config_dir: Optional[str] = typer.Option(None, "--config-dir", "-c", help="自定义配置目录路径")
):
    """仅更新索引"""
    config = Config(config_dir)
    manager = RepoManager(config)
    
    if not manager.initialize():
        console.print("❌ 系统未正确初始化，请先运行 'repo-manager init'", style="bold red")
        raise typer.Exit(1)
    
    console.print("开始更新索引...", style="blue")
    new_repos = manager.update_indices_only()
    
    console.print("✅ 索引更新完成!", style="bold green")
    if new_repos:
        console.print(f"发现并添加了 {len(new_repos)} 个未索引仓库到索引中")

@app.command()
def monitor(
    config_dir: Optional[str] = typer.Option(None, "--config-dir", "-c", help="自定义配置目录路径")
):
    """持续监控模式"""
    config = Config(config_dir)
    manager = RepoManager(config)
    
    if not manager.initialize():
        console.print("❌ 系统未正确初始化，请先运行 'repo-manager init'", style="bold red")
        raise typer.Exit(1)
    
    console.print(f"开始持续监控 (间隔: {config.monitor_interval}秒)", style="blue")
    console.print("按 Ctrl+C 停止监控", style="yellow")
    
    try:
        manager.monitor_continuous()
    except KeyboardInterrupt:
        console.print("\n监控已停止", style="yellow")

@app.command()
def autostart(
    enable: bool = typer.Option(True, "--enable/--disable", help="启用或禁用自动启动"),
    config_dir: Optional[str] = typer.Option(None, "--config-dir", "-c", help="自定义配置目录路径")
):
    """配置系统自动启动 (仅支持macOS)"""
    if platform.system() != "Darwin":
        console.print("❌ 此功能仅支持 macOS", style="bold red")
        raise typer.Exit(1)
    
    config = Config(config_dir)
    
    launchagents_dir = Path.home() / "Library" / "LaunchAgents"
    launchagents_dir.mkdir(exist_ok=True)
    plist_file = launchagents_dir / "com.github.repo-manager.plist"
    
    if enable:
        # 启用自动启动
        plist_content = create_launchd_plist(config)
        plist_file.write_text(plist_content)
        
        console.print(f"✅ 服务配置文件已创建: {plist_file}", style="green")
        
        # 加载服务
        try:
            subprocess.run(['launchctl', 'load', str(plist_file)], check=True)
            console.print("✅ 服务已加载并启动", style="bold green")
            console.print("服务将在系统启动时自动运行", style="green")
        except subprocess.CalledProcessError as e:
            console.print(f"❌ 加载服务失败: {e}", style="bold red")
            raise typer.Exit(1)
    else:
        # 禁用自动启动
        if plist_file.exists():
            try:
                subprocess.run(['launchctl', 'unload', str(plist_file)], check=True)
                plist_file.unlink()
                console.print("✅ 自动启动已禁用", style="green")
            except subprocess.CalledProcessError as e:
                console.print(f"❌ 禁用自动启动失败: {e}", style="bold red")
                raise typer.Exit(1)
        else:
            console.print("❌ 服务配置文件不存在", style="yellow")

@app.command()
def status(
    config_dir: Optional[str] = typer.Option(None, "--config-dir", "-c", help="自定义配置目录路径")
):
    """显示系统状态"""
    config = Config(config_dir)
    manager = RepoManager(config)
    
    status_info = manager.get_status()
    
    # 创建状态表格
    table = Table(title="GitHub Repository Manager 状态")
    table.add_column("配置项", style="cyan")
    table.add_column("值", style="green")
    
    table.add_row("配置目录", status_info['config_dir'])
    table.add_row("数据目录", status_info['data_dir'])
    table.add_row("GitHub用户", status_info['github_username'])
    table.add_row("主监控间隔", f"{status_info['monitor_interval']}秒")
    table.add_row("文件监控间隔", f"{status_info['file_monitor_interval']}秒")
    table.add_row("提交延迟", f"{status_info['commit_delay']}秒")
    table.add_row("GitHub缓存间隔", f"{status_info['github_cache_interval']}秒")
    table.add_row("支持分类", ', '.join(status_info['categories']))
    
    console.print(table)
    
    console.print("\n缓存文件状态:", style="bold")
    for cache_name, exists in status_info['cache_files'].items():
        status_icon = "✅" if exists else "❌"
        console.print(f"  {status_icon} {cache_name}")

@app.command()
def config(
    set_config: Optional[str] = typer.Option(None, "--set", help="设置配置项: key=value"),
    get_config: Optional[str] = typer.Option(None, "--get", help="获取配置项值"),
    list_config: bool = typer.Option(False, "--list", help="列出所有配置"),
    config_dir: Optional[str] = typer.Option(None, "--config-dir", "-c", help="自定义配置目录路径")
):
    """配置管理"""
    config = Config(config_dir)
    
    if set_config:
        # 设置配置值
        try:
            key, value = set_config.split('=', 1)
            
            # 类型转换
            if value.lower() in ('true', 'false'):
                value = value.lower() == 'true'
            elif value.isdigit():
                value = int(value)
            
            config.set(key, value)
            config.save_config()
            console.print(f"✅ 设置 {key} = {value}", style="green")
            
        except ValueError:
            console.print("❌ 格式错误，请使用: key=value", style="bold red")
            raise typer.Exit(1)
    
    elif get_config:
        # 获取配置值
        value = config.get(get_config)
        if value is not None:
            console.print(f"{get_config} = {value}")
        else:
            console.print(f"❌ 配置项 '{get_config}' 不存在", style="bold red")
            raise typer.Exit(1)
    
    elif list_config:
        # 列出所有配置
        table = Table(title="当前配置")
        table.add_column("配置项", style="cyan")
        table.add_column("值", style="green")
        
        for key, value in config._config.items():
            table.add_row(key, str(value))
        
        console.print(table)
    
    else:
        # 运行配置向导
        config.setup_wizard()

@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="详细输出")
):
    """GitHub Repository Manager - 自动化GitHub仓库管理系统"""
    setup_cli_logging(verbose)

if __name__ == "__main__":
    app()