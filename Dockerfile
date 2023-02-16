FROM python:3.10.4

WORKDIR /speech_to_text_back_end
ADD . /speech_to_text_back_end

RUN apt-get update 
RUN apt-get clean;
RUN apt-get -y install ffmpeg
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

ENV TZ Asia/Tokyo
ENV LANG ja_JP.UTF-8
ENV LANGUAGE ja_JP:ja
ENV LC_ALL ja_JP.UTF-8

ENV PORT 5050
EXPOSE 5050

CMD ["gunicorn", "-c","config/gunicorn_setting.py"]
# CMD ["flask", "run"]