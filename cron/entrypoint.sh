#!/bin/sh
set -e

touch /var/log/cron.log

# 컨테이너 시작 시 1회 즉시 생성 (HTML이 바로 존재하도록)
echo "[entrypoint] 초기 weather.html 생성..."
python /app/generate_weather_html.py || echo "[entrypoint] 초기 생성 실패(다음 cron에서 재시도)"

# cron 데몬 시작 후 로그를 포그라운드로 흘려 컨테이너 유지
echo "[entrypoint] cron 데몬 시작"
cron
exec tail -f /var/log/cron.log
