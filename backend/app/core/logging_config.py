import logging
import sys

# --- Centralized Logging Configuration ---

# Create a logger instance
logger = logging.getLogger("okada_agent")
logger.setLevel(logging.DEBUG)  # Set the lowest level to capture all messages

# Create a handler to output to the console
handler = logging.StreamHandler(sys.stdout)

# Create a formatter to define the log message format
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)'
)

# Set the formatter for the handler
handler.setFormatter(formatter)

# Add the handler to the logger
# Avoid adding handlers multiple times if this module is imported elsewhere
if not logger.handlers:
    logger.addHandler(handler)

# --- Example Usage (for direct execution) ---
if __name__ == "__main__":
    logger.debug("This is a debug message.")
    logger.info("This is an info message.")
    logger.warning("This is a warning message.")
    logger.error("This is an error message.")
    logger.critical("This is a critical message.")
