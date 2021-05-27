FROM centos/python-38-centos7

EXPOSE 8000
USER 0
WORKDIR /opt
RUN mkdir spider
COPY ./app /opt/spider
COPY ./requirements.txt /opt/spider
RUN pip install pip -U
RUN pip install -r ./spider/requirements.txt

CMD uvicorn spider.app.server:app --host 0.0.0.0