from ...models.data_models import WordCloud
from ...models.db_models import WordCloudDBModel
from .base import BaseAsyncWordCloudService
from typing import Callable
from logging import Logger


class WordCloudGenerationService(BaseAsyncWordCloudService):

    def __init__(self,
                 generation_func: Callable,
                 data_model: WordCloud,
                 db_model: WordCloudDBModel,
                 logger: Logger,
                 exception_handler: Callable):
        self._word_cloud_generator = generation_func
        self._data_model = data_model
        self._db_model = db_model
        self._logger = logger
        self._exception_handler = exception_handler # traceback.print_exc()
    
    
    async def generate(self, text: str, top_k: int, with_weight: bool = True, save_result: bool = True) -> WordCloud:
        try:
            self._logger.info("Generating word cloud...")
            word_cloud_list = self._word_cloud_generator(
                text, topK=top_k, withWeight=with_weight)
            word_cloud = self._data_model.parse_obj(word_cloud_list)
            word_cloud_db_record = self._db_model.parse_obj(word_cloud)
            
            if save_result:
                await word_cloud_db_record.save()
            
            return word_cloud
        except Exception as e:
            self._exception_handler()
            self._logger.error(e)


if __name__ == "__main__":
    import asyncio
    import logging
    from jieba import analyse
    from traceback import print_exc
    from devtools import debug
    
    async def main():
        logging.basicConfig(format="%(asctime)s | %(levelname)s | %(funcName)s | %(message)s",
                            datefmt="%Y-%m-%dT%H:%M:%S%z")
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)
        
        test_text = """
        当地时间20日，希腊卫生部初级保健秘书长马里奥斯·希米斯托克利斯宣布，针对60岁以上人群和医务工作者的第三剂新冠疫苗“加强针”预约平台将于9月30日开放。不过，他强调加强针的疫苗接种并非强制性的。

        希腊国家疫苗接种委员会主席玛丽亚·西奥多里杜则在当天的疫情通报会上指出，第三剂疫苗的接种将在第二剂注射后的6到8个月后进行。她说：“疫苗在预防重症、降低住院率和死亡率方面是有效的。政府的目标是竭尽全力将疫苗接种的人口比例提高到70%，以期建立起免疫墙。科学数据显示，抗体在接种疫苗后的5到6个月内会随着时间的推移而减少，再加上层出不穷的变异新冠病毒，这会给许多人带来风险。”

        西奥多里杜还说，根据现有数据，在重症监护病房接受治疗的新冠肺炎患者中，有59.2%的人年龄在60至79岁之间，48%的新冠死亡病例也处于这一年龄段。关于普通人群是否也需要进行“加强针”的疫苗注射，她表示在做出最终决定之前，仍需要研究相关的数据。
        """
        wc_service = WordCloudGenerationService(
            generation_func=analyse.textrank,
            data_model=WordCloud,
            db_model=WordCloudDBModel,
            logger=logger,
            exception_handler=print_exc
        )
        wc = await wc_service.generate(text=test_text, top_k=20, save_result=False)
        logger.info(wc)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
