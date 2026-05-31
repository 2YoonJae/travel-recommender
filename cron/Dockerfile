FROM python:3.11-slim

ENV TZ=Asia/Seoul

# cron 데몬 + 시간대 데이터 설치, 컨테이너 로컬타임을 KST로 고정
RUN apt-get update \
    && apt-get install -y --no-install-recommends cron tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY generate_weather_html.py .

# crontab 등록 (/etc/cron.d drop-in)
COPY weather-cron /etc/cron.d/weather-cron
RUN chmod 0644 /etc/cron.d/weather-cron

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]
