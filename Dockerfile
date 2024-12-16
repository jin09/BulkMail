FROM python:3.8-alpine

RUN apk update && apk add --no-cache gcc libc-dev make

WORKDIR /server

COPY . /server/

RUN pip install --no-cache-dir -r requirements.txt

RUN pytest -v --cov

EXPOSE 8000

CMD ["fastapi", "run", "--workers", "2", "app/main.py"]