# 1. 파이썬 3.10 버전(가벼운 버전)을 기반으로 함
FROM python:3.10-slim

# 2. 파이썬 로그가 바로 출력되도록 설정 (모니터링용)
ENV PYTHONUNBUFFERED=1

# 3. 작업 폴더 생성
WORKDIR /app

# 4. 라이브러리 목록 복사 및 설치
COPY requirements.txt /app/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN pip install gunicorn  # 나스(리눅스)용 실행기 설치

# 5. 프로젝트 코드 전체 복사
COPY . /app/

# 6. 정적 파일 모으기 (이미지 만들 때 실행)
RUN python manage.py collectstatic --noinput

# 7. 서버 실행 명령어 (8000번 포트)
# 주의: 'config.wsgi:application' 부분의 config는 
# settings.py가 들어있는 폴더 이름으로 바꿔주세요!
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "SujuOrderSystem.wsgi:application"]