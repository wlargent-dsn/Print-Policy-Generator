"""
Configuration loader for Automatic Print GPO Generator.
Loads and validates settings from config.yaml.
"""

import os
import yaml
from typing import Dict, List, Optional


class Config:
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self._load_config()

    def _load_config(self):
        """Load and validate configuration from YAML file."""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        if config is None:
            raise ValueError("Configuration file is empty or invalid YAML")

        # Validate required sections
        required_sections = ['site_mappings', 'print_servers', 'gpo_xml_path', 'logging']
        for section in required_sections:
            if section not in config:
                raise ValueError(f"Missing required configuration section: {section}")

        # Load site mappings
        self.site_mappings: Dict[str, str] = config['site_mappings']
        if not isinstance(self.site_mappings, dict):
            raise ValueError("site_mappings must be a dictionary")

        # Load print servers
        self.print_servers: List[str] = config['print_servers']
        if not isinstance(self.print_servers, list) or not self.print_servers:
            raise ValueError("print_servers must be a non-empty list")

        # Load GPO XML path
        self.gpo_xml_path: str = config['gpo_xml_path']
        if not isinstance(self.gpo_xml_path, str) or not self.gpo_xml_path.strip():
            raise ValueError("gpo_xml_path must be a non-empty string")

        # Load logging config
        logging_config = config['logging']
        self.log_directory: str = logging_config.get('directory', 'logs')
        self.log_rotation_days: int = logging_config.get('rotation_days', 30)
        if not isinstance(self.log_rotation_days, int) or self.log_rotation_days <= 0:
            raise ValueError("rotation_days must be a positive integer")

        # Load SMTP config (optional)
        if 'smtp' in config and config['smtp'] is not None:
            smtp_config = config['smtp']
            self.smtp_server: str = smtp_config['server']
            self.smtp_port: int = smtp_config['port']
            self.smtp_from_email: str = smtp_config['from_email']
            self.smtp_to_email: str = smtp_config['to_email']

            # Validate SMTP settings
            if not all(isinstance(x, str) for x in [self.smtp_server, self.smtp_from_email, self.smtp_to_email]):
                raise ValueError("SMTP server, from_email, and to_email must be strings")
            if not isinstance(self.smtp_port, int) or not (1 <= self.smtp_port <= 65535):
                raise ValueError("SMTP port must be an integer between 1 and 65535")
        else:
            self.smtp_server = None
            self.smtp_port = None
            self.smtp_from_email = None
            self.smtp_to_email = None

        # Load printer overrides (optional)
        self.printer_overrides: Dict[str, str] = config.get('printer_overrides') or {}
        if not isinstance(self.printer_overrides, dict):
            raise ValueError("printer_overrides must be a dictionary")

    def get_site_for_printer(self, printer_name: str) -> Optional[str]:
        """Determine ADDS site for a printer based on name prefix or override."""
        # Check overrides first
        if printer_name in self.printer_overrides:
            return self.printer_overrides[printer_name]

        # Check prefix mappings
        for site, prefix in self.site_mappings.items():
            if printer_name.startswith(prefix):
                return site

        return None  # No matching site found