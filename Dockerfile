## aws fargate用
# FROM python:3.10.4
# 
# WORKDIR /speech_to_text_back_end
# ADD . /speech_to_text_back_end
# 
# RUN apt-get update 
# RUN apt-get clean
# RUN apt-get -y install ffmpeg
# RUN pip install --upgrade pip
# RUN pip install -r requirements.txt
# 
# ENV TZ Asia/Tokyo
# ENV LANG ja_JP.UTF-8
# ENV LANGUAGE ja_JP:ja
# ENV LC_ALL ja_JP.UTF-8
# 
# ENV PORT 5050
# EXPOSE 5050
# 
# CMD ["gunicorn", "-c","config/gunicorn_setting.py"]


# aws lambda用
FROM python:3.10.4

# pipを更新し、lambdaで実行するためのランタイムをインストール
RUN pip install --upgrade pip
RUN pip install awslambdaric

# ローカルで実行するためのエミュレーターをダウンロードし、実行権限を付与
ADD https://github.com/aws/aws-lambda-runtime-interface-emulator/releases/latest/download/aws-lambda-rie-arm64 /usr/bin/aws-lambda-rie-arm64
RUN chmod 755 /usr/bin/aws-lambda-rie-arm64
# ランタイムを起動するスクリプトをコピーし、実行権限を付与
COPY entry.sh "/entry.sh"
RUN chmod 755 /entry.sh

# whisperが使うffmpegをインストール
RUN apt-get update 
RUN apt-get clean
RUN apt-get -y install ffmpeg

# flaskアプリを丸ごとコピーし、pythonライブラリをインストール
WORKDIR /speech_to_text_back_end
COPY . .
RUN pip install -r requirements.txt

# 起動
ENTRYPOINT [ "/bin/bash", "/entry.sh" ]
CMD [ "main.lambda_handler" ]
