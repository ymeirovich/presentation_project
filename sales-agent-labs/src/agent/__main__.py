import logging
from .config import settings

def configure_logging():
    #Simple, readable logs for dev; swap to JSON later if you want
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

def main():
    configure_logging()
    log= logging.getLogger("agent")

    log.info("SalesAgent Labs - Day 1 sanity check")
    log.info("Loaded settings: GOOGLE_PROJECT_ID=%s IMAGE_API_KEY=%s LOG_LEVEL=%s",
            settings.GOOGLE_PROJECT_ID,
            "***" if settings.IMAGE_API_KEY else None,
            settings.LOG_LEVEL)
    
    print("Environment is wired. You're ready for Day 2.")

if __name__ == "__main__":
    main()