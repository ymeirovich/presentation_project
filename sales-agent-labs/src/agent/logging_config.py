import logging

def setup_logging() -> None:
    """
    Configure global logging for the entire application.
    Reads LOG_LEVEL from environment (.env) or defaults to INFO.
    """
    log_level = "INFO" 

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Reduce noise from overly chatty libraries
    logging.getLogger("google").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
