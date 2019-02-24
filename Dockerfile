# To build and upload the image to Amazon ECS follow these steps:
#
# 1. Declare the following environment variables:
#    - PHABRICATOR_URL: http://example.com
#    - PHABRICATOR_TOKEN: api-xxxxxxx
#    - PHABRICATOR_WEBHOOK_MAC: xxxxxx
#    - SLACK_TOKEN: xoxa-xxxxxx
#
# 2. In the folder where `Dockerfile` lives:
#    $ aws ecr create-repository --repository-name
#    $ `aws ecr get-login --region us-west-2 --no-include-email`
#    $ cat Dockerfile | envsubst | docker build -t slack-notiphier-app . -f -
#    $ docker tag slack-notiphier-app:latest AWS_ACCOUNT_ID.dkr.ecr.us-west-2.amazonaws.com/slack-notiphier
#    $ docker push AWS_ACCOUNT_ID.dkr.ecr.us-west-2.amazonaws.com/slack-notiphier
#
# 3. If troubleshooting the container is needed:
#    $ docker run -it slack-notiphier-app bash
#

FROM python:3.6-slim

LABEL maintainer="me@dwilches.com"

USER root

WORKDIR /app

ADD src /app

RUN pip install --trusted-host pypi.python.org -r requirements.txt

EXPOSE 5000

RUN echo '\n\
_flask_debug: true \n\
log_level: DEBUG \n\
phabricator_url: ${PHABRICATOR_URL} \n\
phabricator_token: ${PHABRICATOR_TOKEN} \n\
phabricator_webhook_hmac: ${PHABRICATOR_WEBHOOK_MAC} \n\
slack_token: ${SLACK_TOKEN} \n\
\n\
channels: \n\
  __default__: "#general" \n\
  __debug__: "#slack-notiphier-debug" \n\
' > /etc/slack-notiphier.cfg

CMD ["python", "-m", "slack_notiphier"]

