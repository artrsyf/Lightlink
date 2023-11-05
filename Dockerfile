FROM python:3.10-slim

RUN apt-get update && \
    apt-get install -y python3-pip libpq-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

WORKDIR /usr/src/apps/lightlink/

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN pip install --upgrade pip
COPY ./requirements.txt .
RUN pip install -r requirements.txt

RUN apt-get --purge -y autoremove python3-pip && \
    apt-get clean

COPY . /usr/src/apps/lightlink/

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]