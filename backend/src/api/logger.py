import logging
from pythonjsonlogger.json import JsonFormatter

def setup_logging():
    """Configures structured JSON logging for production."""
    logger = logging.getLogger()

    # Clear existing handlers
    while logger.hasHandlers():
        logger.removeHandler(logger.handlers[0])

    handler = logging.StreamHandler()

    # We want standard timestamp, severity level, logger name, and the actual message.
    # The python-json-logger automatically appends any `extra={"event": ...}` kwargs.
    formatter = JsonFormatter(
        '%(asctime)s %(levelname)s %(name)s %(message)s',
        datefmt='%Y-%m-%dT%H:%M:%SZ'
    )

    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    # Supress noisy third parties
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
