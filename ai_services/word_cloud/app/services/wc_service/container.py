from dependency_injector import containers, providers

from .word_cloud_service import WordCloudGenerationService


class WordCloudServiceContainer(containers.DeclarativeContainer):

    word_cloud_generator = providers.Dependency()
    data_model = providers.Dependency()
    db_model = providers.Dependency()
    logger = providers.Dependency()
    exception_handler = providers.Dependency()

    word_cloud_generation_service = providers.Singleton(
        WordCloudGenerationService,
        generation_func=word_cloud_generator,
        data_model=data_model,
        db_model=db_model,
        logger=logger,
        exception_handler=exception_handler
    )
