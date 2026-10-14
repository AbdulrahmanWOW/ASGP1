"""ASGP MCP gateway: governs tools/call for any MCP client."""

from asgp_gateway.config import GatewayConfig
from asgp_gateway.gateway import ASGPGateway

__all__ = ["ASGPGateway", "GatewayConfig"]
__version__ = "0.1.0"
