from app.services.screening import ScreeningService


def process_screening(job_description: str, resumes: dict[str, str]) -> list[dict]:
    """Background-job entrypoint compatible with Celery/Dramatiq adapters."""
    return ScreeningService().screen_texts(job_description, resumes)
