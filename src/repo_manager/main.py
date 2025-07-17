#!/usr/bin/env python3
"""
Repository Manager Main Entry Point
"""

import sys
import os
import argparse
import logging
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from repo_manager.cli import main as cli_main
from repo_manager.core.manager import RepoManager

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Repository Manager')
    parser.add_argument('command', choices=['daemon', 'scan', 'sync', 'status'], 
                       help='Command to run')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--config-dir', help='Configuration directory')
    
    args = parser.parse_args()
    
    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if args.command == 'daemon':
        # Run as daemon
        repo_manager = RepoManager(config_dir=args.config_dir)
        repo_manager.start_daemon()
    elif args.command == 'scan':
        # Run one-time scan
        repo_manager = RepoManager(config_dir=args.config_dir)
        repo_manager.scan_repositories()
    elif args.command == 'sync':
        # Sync with GitHub
        repo_manager = RepoManager(config_dir=args.config_dir)
        repo_manager.sync_github()
    elif args.command == 'status':
        # Show status
        repo_manager = RepoManager(config_dir=args.config_dir)
        repo_manager.show_status()
    else:
        # Use CLI
        cli_main()

if __name__ == '__main__':
    main()