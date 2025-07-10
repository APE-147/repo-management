"""
命令行界面模块
"""
import sys
import argparse
import logging
from pathlib import Path
from .core import RepoManager
from .config import Config

def setup_cli_logging(verbose: bool = False):
    """设置CLI日志"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

def cmd_init(args):
    """初始化系统"""
    config = Config(args.config_dir)
    
    print("=== GitHub Repository Manager 初始化 ===")
    
    # 运行配置向导
    if not config.validate_config() or args.force:
        print("配置GitHub用户名...")
        # 尝试从环境变量获取
        import os
        github_username = os.getenv("GITHUB_USERNAME", "")
        if not github_username:
            print("请设置环境变量 GITHUB_USERNAME 或手动配置")
            print("export GITHUB_USERNAME=your-username")
            github_username = input("请输入GitHub用户名 (回车跳过): ").strip()
        
        if github_username:
            config.github_username = github_username
            config.save_config()
            print(f"已设置GitHub用户名: {github_username}")
        else:
            print("未设置GitHub用户名，稍后可通过 'repo-manager config --set github_username=用户名' 设置")
    else:
        print("配置已存在且有效")
    
    # 初始化管理器
    manager = RepoManager(config)
    if manager.initialize():
        print("\n✅ 初始化成功!")
        print(f"配置目录: {config.config_dir}")
        print(f"数据目录: {config.data_dir}")
        print(f"repo-index目录: {config.repo_index_dir}")
    else:
        print("\n❌ 初始化失败!")
        sys.exit(1)

def cmd_scan(args):
    """执行一次扫描"""
    config = Config(args.config_dir)
    manager = RepoManager(config)
    
    if not manager.initialize():
        print("❌ 系统未正确初始化，请先运行 'repo-manager init'")
        sys.exit(1)
    
    print("开始执行扫描...")
    result = manager.scan_once()
    
    print("✅ 扫描完成!")
    if result["file_changes"]:
        changes = result["file_changes"]
        print(f"文件变动: 新增{len(changes['new_files'])}个, "
              f"修改{len(changes['modified_files'])}个, "
              f"删除{len(changes['deleted_files'])}个")
    
    if result["unindexed_repos"]:
        print(f"发现未索引仓库: {len(result['unindexed_repos'])}个")

def cmd_update(args):
    """仅更新索引"""
    config = Config(args.config_dir)
    manager = RepoManager(config)
    
    if not manager.initialize():
        print("❌ 系统未正确初始化，请先运行 'repo-manager init'")
        sys.exit(1)
    
    print("开始更新索引...")
    new_repos = manager.update_indices_only()
    
    print("✅ 索引更新完成!")
    if new_repos:
        print(f"发现并添加了 {len(new_repos)} 个未索引仓库到索引中")

def cmd_monitor(args):
    """持续监控模式"""
    config = Config(args.config_dir)
    manager = RepoManager(config)
    
    if not manager.initialize():
        print("❌ 系统未正确初始化，请先运行 'repo-manager init'")
        sys.exit(1)
    
    print(f"开始持续监控 (间隔: {config.monitor_interval}秒)")
    print("按 Ctrl+C 停止监控")
    
    try:
        manager.monitor_continuous()
    except KeyboardInterrupt:
        print("\n监控已停止")

def cmd_status(args):
    """显示系统状态"""
    config = Config(args.config_dir)
    manager = RepoManager(config)
    
    status = manager.get_status()
    
    print("=== GitHub Repository Manager 状态 ===")
    print(f"配置目录: {status['config_dir']}")
    print(f"数据目录: {status['data_dir']}")
    print(f"GitHub用户: {status['github_username']}")
    print(f"监控间隔: {status['monitor_interval']}秒")
    print(f"支持分类: {', '.join(status['categories'])}")
    
    print("\n缓存文件状态:")
    for cache_name, exists in status['cache_files'].items():
        status_icon = "✅" if exists else "❌"
        print(f"  {status_icon} {cache_name}")

def cmd_config(args):
    """配置管理"""
    config = Config(args.config_dir)
    
    if args.set:
        # 设置配置值
        try:
            key, value = args.set.split('=', 1)
            
            # 类型转换
            if value.lower() in ('true', 'false'):
                value = value.lower() == 'true'
            elif value.isdigit():
                value = int(value)
            
            config.set(key, value)
            config.save_config()
            print(f"✅ 设置 {key} = {value}")
            
        except ValueError:
            print("❌ 格式错误，请使用: key=value")
            sys.exit(1)
    
    elif args.get:
        # 获取配置值
        value = config.get(args.get)
        if value is not None:
            print(f"{args.get} = {value}")
        else:
            print(f"❌ 配置项 '{args.get}' 不存在")
            sys.exit(1)
    
    elif args.list:
        # 列出所有配置
        print("=== 当前配置 ===")
        for key, value in config._config.items():
            print(f"{key} = {value}")
    
    else:
        # 运行配置向导
        config.setup_wizard()

def cmd_install_service(args):
    """安装系统服务 (macOS)"""
    import platform
    
    if platform.system() != "Darwin":
        print("❌ 此功能仅支持 macOS")
        sys.exit(1)
    
    config = Config(args.config_dir)
    
    # 创建plist文件
    from .templates import create_launchd_plist
    plist_content = create_launchd_plist(config)
    
    # 写入LaunchAgents目录
    launchagents_dir = Path.home() / "Library" / "LaunchAgents"
    launchagents_dir.mkdir(exist_ok=True)
    
    plist_file = launchagents_dir / "com.github.repo-manager.plist"
    plist_file.write_text(plist_content)
    
    print(f"✅ 服务配置文件已创建: {plist_file}")
    
    # 加载服务
    import subprocess
    try:
        subprocess.run(['launchctl', 'load', str(plist_file)], check=True)
        print("✅ 服务已加载并启动")
        print("服务将在系统启动时自动运行")
    except subprocess.CalledProcessError as e:
        print(f"❌ 加载服务失败: {e}")
        sys.exit(1)

def cmd_uninstall_service(args):
    """卸载系统服务 (macOS)"""
    import platform
    
    if platform.system() != "Darwin":
        print("❌ 此功能仅支持 macOS")
        sys.exit(1)
    
    launchagents_dir = Path.home() / "Library" / "LaunchAgents"
    plist_file = launchagents_dir / "com.github.repo-manager.plist"
    
    if plist_file.exists():
        # 卸载服务
        import subprocess
        try:
            subprocess.run(['launchctl', 'unload', str(plist_file)], check=True)
            plist_file.unlink()
            print("✅ 服务已卸载")
        except subprocess.CalledProcessError as e:
            print(f"❌ 卸载服务失败: {e}")
            sys.exit(1)
    else:
        print("❌ 服务配置文件不存在")

def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="GitHub Repository Manager - 自动化GitHub仓库管理系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  repo-manager init                    # 初始化系统
  repo-manager scan                    # 执行一次扫描
  repo-manager monitor                 # 持续监控模式
  repo-manager update                  # 更新索引
  repo-manager status                  # 查看状态
  repo-manager config --set github_username=myuser
  repo-manager install-service        # 安装开机自启动服务 (macOS)
        """
    )
    
    parser.add_argument(
        '--config-dir', '-c',
        help='自定义配置目录路径 (默认: ~/.repo-manager)',
        default=None
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='详细输出'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # init 命令
    init_parser = subparsers.add_parser('init', help='初始化系统')
    init_parser.add_argument('--force', '-f', action='store_true', help='强制重新配置')
    init_parser.set_defaults(func=cmd_init)
    
    # scan 命令
    scan_parser = subparsers.add_parser('scan', help='执行一次完整扫描')
    scan_parser.set_defaults(func=cmd_scan)
    
    # update 命令
    update_parser = subparsers.add_parser('update', help='仅更新索引')
    update_parser.set_defaults(func=cmd_update)
    
    # monitor 命令
    monitor_parser = subparsers.add_parser('monitor', help='持续监控模式')
    monitor_parser.set_defaults(func=cmd_monitor)
    
    # status 命令
    status_parser = subparsers.add_parser('status', help='显示系统状态')
    status_parser.set_defaults(func=cmd_status)
    
    # config 命令
    config_parser = subparsers.add_parser('config', help='配置管理')
    config_group = config_parser.add_mutually_exclusive_group()
    config_group.add_argument('--set', help='设置配置项: key=value')
    config_group.add_argument('--get', help='获取配置项值')
    config_group.add_argument('--list', action='store_true', help='列出所有配置')
    config_parser.set_defaults(func=cmd_config)
    
    # install-service 命令
    install_service_parser = subparsers.add_parser('install-service', help='安装开机自启动服务 (macOS)')
    install_service_parser.set_defaults(func=cmd_install_service)
    
    # uninstall-service 命令
    uninstall_service_parser = subparsers.add_parser('uninstall-service', help='卸载开机自启动服务 (macOS)')
    uninstall_service_parser.set_defaults(func=cmd_uninstall_service)
    
    # 解析参数
    args = parser.parse_args()
    
    # 设置日志
    setup_cli_logging(args.verbose)
    
    # 如果没有指定命令，默认执行monitor
    if not args.command:
        args.command = 'monitor'
        args.func = cmd_monitor
    
    # 执行命令
    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\n操作已取消")
        sys.exit(1)
    except Exception as e:
        if args.verbose:
            import traceback
            traceback.print_exc()
        else:
            print(f"❌ 错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()