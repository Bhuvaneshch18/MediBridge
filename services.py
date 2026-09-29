import logging
from datetime import datetime, timezone

from extensions import db
from models import Assessment


def create_assessment_record(user_id, disease_name, risk_level="Unknown", probability=0.0):
    """
    Creates a new assessment record.
    """

    try:
        new_assessment = Assessment(
            user_id=user_id,
            disease_name=disease_name,
            risk_level=risk_level,
            risk_score=float(probability) if probability is not None else 0.0,
            status="Completed",
            assessment_date=datetime.now(timezone.utc)
        )

        db.session.add(new_assessment)
        db.session.commit()

        logging.info(
            f"[Assessment Created] User ID: {user_id}, Disease: {disease_name}"
        )

        return True

    except Exception as e:
        db.session.rollback()

        logging.error(
            f"[Assessment Creation Failed] {str(e)}"
        )

        return False
