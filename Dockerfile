FROM python:3.6-slim

MAINTAINER me@dwilches.com

USER root

WORKDIR /app

ADD src /app
ADD cfg /etc

RUN pip install --trusted-host pypi.python.org -r requirements.txt

EXPOSE 80

CMD ["python", "-m", "slack_notiphier"]

