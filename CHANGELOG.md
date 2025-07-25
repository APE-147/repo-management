# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-12-07

### Added
- Complete project restructure based on Python CLI framework
- Modern CLI interface using Typer framework with rich console output
- Modular architecture with core/, services/, utils/, plugins/ directories
- New `autostart` command for macOS system service configuration
- Cross-platform installation script (install.sh)
- Configuration management through `pyproject.toml` instead of `setup.py`
- Data directory relocated to `~/Developer/Code/Script_data/repo_manager/`
- Enhanced error handling and user experience

### Changed
- Migrated from argparse to Typer for better CLI experience
- Restructured codebase into logical modules:
  - `core/`: Main business logic (manager, file_monitor, github_detector, etc.)
  - `services/`: Configuration and database management
  - `utils/`: Helper functions and templates
  - `plugins/`: Future extensibility framework
- Updated dependencies to include typer[all] and rich
- Improved logging and status reporting

### Technical Improvements
- Better separation of concerns
- More maintainable code structure
- Enhanced type hints and documentation
- Streamlined installation process