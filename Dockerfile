FROM python:3.6

WORKDIR /app

RUN apt-get -y update && apt-get -y install libav-tools

COPY requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir

ENV PYTHONPATH /app
ENV PYTHONUNBUFFERED 1
ENV DEEZLOAD_DEBUG 0
ENV DEEZLOAD_UI web
ENV DEEZLOAD_HOME /output
# update youtube_dl before starting server
ENV UPYT 1

COPY . ./


EXPOSE 8000
VOLUME /output

CMD [ "./run.sh" ]
