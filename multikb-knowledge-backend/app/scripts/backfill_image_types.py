"""
Backfill image_type for existing DocumentImage records.
"""

from app.config.database import SessionLocal
from app.services.image_service import ImageService
from app.core.logging import logger


def main():
    db = SessionLocal()
    try:
        service = ImageService(db)
        updated = service.backfill_missing_image_types()
        logger.info(f"完成回填，更新记录数: {updated}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
