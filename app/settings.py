"""
Settings module for quiz application.

Uses centralized configuration and cross-platform network detection.
"""
from app.config import config
from app.lib.network import NetworkInterface
from app.lib.logger import get_logger
from app.lib.validators import NetworkValidator

logger = get_logger("settings")

# Get configuration values
# Note: Port validation happens lazily when port is accessed via get_port()
# to allow config changes to be reflected
BUFFER_SIZE = config.get("network.buffer_size", 4096)
TIMEOUT = config.get("network.timeout", 30)

def get_port():
    """
    Get and validate port number.
    Validates port when accessed to allow for config changes.
    
    Returns:
        Valid port number (defaults to 4040 if invalid)
    """
    port = config.get("network.port", 4040)
    is_valid, error = NetworkValidator.validate_port(port)
    if not is_valid:
        logger.warning(f"Invalid port {port}: {error}. Using default 4040.")
        port = 4040
        config.set("network.port", port)
    return port

# Initialize port (validated on first access)
PORT = get_port()

# Network interface detection (backward compatible functions)
def getHOTSPOT():
    """
    Get hotspot IP address for admin server.
    
    Returns:
        IP address string or None if not found
    
    Raises:
        OSError: If hotspot cannot be detected
    """
    try:
        ip = NetworkInterface.get_local_ip()
        if ip:
            logger.info(f"Hotspot IP detected: {ip}")
            return ip
        else:
            logger.error("Could not detect hotspot IP address")
            raise OSError("TURN ON HOTSPOT FIRST - Could not detect network interface")
    except Exception as e:
        logger.error(f"Error detecting hotspot IP: {e}", exc_info=True)
        raise OSError("TURN ON HOTSPOT FIRST") from e

def getWIFI():
    """
    Get WiFi IP address for participant client.
    
    Returns:
        IP address string or None if not found
    
    Raises:
        OSError: If WiFi cannot be detected
    """
    try:
        ip = NetworkInterface.get_local_ip()
        if ip:
            logger.info(f"WiFi IP detected: {ip}")
            return ip
        else:
            logger.error("Could not detect WiFi IP address")
            raise OSError("SYSTEM does not have Wi-Fi support - Could not detect network interface")
    except Exception as e:
        logger.error(f"Error detecting WiFi IP: {e}", exc_info=True)
        raise OSError("SYSTEM does not have Wi-Fi support") from e

# Default address (localhost for testing)
# Use get_port() to ensure port is validated
host = "localhost"
port = get_port()
addr = (host, port)

if __name__ == "__main__":
    try:
        wifi_ip = getWIFI()
        hotspot_ip = getHOTSPOT()
        print(f"WiFi IP: {wifi_ip}, Hotspot IP: {hotspot_ip}, Port: {PORT}")
    except Exception as e:
        print(f"Error: {e}")