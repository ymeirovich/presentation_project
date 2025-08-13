import logging
import os

def setup_logging() -> None:
    """
    Global logging config.
    LOG_LEVEL controls app logs; HTTP_DEBUG=1 enables verbose HTTP logs for GOOGLE API.
    """
    log_level=os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    #Quiet noise libs by default
    logging.getLogger("google").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    #Optional: flip on wire-level HTTP logs when debugging
    if os.getenv("HTTP_DEBUG") == "1":
        # googleapiclient uses httplib2; these loggers surface request/response info
        logging.getLogger("googleapiclient.discovery").setLevel(logging.DEBUG)
        logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.DEBUG)
        logging.getLogger("googleapiclient.http").setLevel(logging.DEBUG)
        logging.getLogger("httplib2").setLevel(logging.DEBUG)

        
# def setup_logging() -> None:
#     """
#     Configure global logging for the entire application.
#     Reads LOG_LEVEL from environment (.env) or defaults to INFO.
#     """
#     log_level = "INFO" 

#     logging.basicConfig(
#         level=log_level,
#         format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
#         datefmt="%Y-%m-%d %H:%M:%S",
#     )

#     # Reduce noise from overly chatty libraries
#     logging.getLogger("google").setLevel(logging.WARNING)
#     logging.getLogger("urllib3").setLevel(logging.WARNING)
