from loguru import logger
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import router
from app.utils.data_loader import DataLoader
from app.usecases.recommendation import RecommendationUsecase
from app.core.config import settings



@asynccontextmanager
async def lifespan(_app: FastAPI):
    """
    Lifespan: загрузка артефактов и инициализация сервиса на старте.
    """
    logger.info("Подготовка сервиса...")
    loader = DataLoader(settings)
    loader.load_all_recommendations()

    service = RecommendationUsecase(loader, settings.s3.recsys)
    service.initialize()

    _app.state.data_loader = loader
    _app.state.recommendation_service = service
    logger.info("Startup complete")
    yield
    logger.info("Shutdown")


app = FastAPI(
    title="Recommendation Service",
    version="1.0.0",
    description="Онлайн-выдача рекомендаций: смешивание ALS, i2i и популярности",
    lifespan=lifespan,
)

app.include_router(router)
