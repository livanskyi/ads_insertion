FROM python:3.7-stretch

COPY . /app

WORKDIR /app

RUN pip --no-cache-dir install -r requirements.txt

RUN apt-get update && apt-get --assume-yes install ffmpeg

CMD python app.py