"""
ACGS-2 CLI Configuration
Constitutional Hash: cdd01ef066bc6cf2
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class CLIConfig:
    """CLI configuration settings"""

    base_url: str = "http://localhost:8080"
    api_key: Optional[str] = None
    tenant_id: str = "acgs-dev"
    timeout: float = 30.0
    config_file: Optional[Path] = None

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "CLIConfig":
        """Load configuration from file or environment"""
        config = cls()

        # Try to load from specified path
        if config_path:
            config_file = Path(config_path)
        else:
            # Try default locations
            config_dir = Path.home() / ".acgs2"
            config_file = config_dir / "config.json"

        if config_file.exists():
            try:
                with open(config_file, "r") as f:
                    data = json.load(f)
                    for key, value in data.items():
                        if hasattr(config, key):
                            setattr(config, key, value)
                config.config_file = config_file
            except Exception as e:
                # Ignore config file errors, use defaults
                pass

        return config

    def save(self) -> None:
        """Save configuration to file"""
        if not self.config_file:
            config_dir = Path.home() / ".acgs2"
            config_dir.mkdir(exist_ok=True)
            self.config_file = config_dir / "config.json"

        data = {
            "base_url": self.base_url,
            "tenant_id": self.tenant_id,
            "timeout": self.timeout,
        }
        if self.api_key:
            data["api_key"] = self.api_key

        with open(self.config_file, "w") as f:
            json.dump(data, f, indent=2)


# Global configuration instance
_config: Optional[CLIConfig] = None


def get_config() -> CLIConfig:
    """Get global configuration instance"""
    global _config
    if _config is None:
        _config = CLIConfig.load()
    return _config
