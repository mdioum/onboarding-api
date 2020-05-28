FROM ubuntu:18.04

ENV PYTHONWARNINGS="ignore:Unverified HTTPS request" \
    KUBECONFIG=/home/.kube/config \
    MAIL_REQUEST_DESTINATION=""

RUN apt-get update -y && \
    apt-get install -y python3-pip python3-dev

COPY ./requirements.txt /requirements.txt

WORKDIR /

RUN pip3 install -r requirements.txt
RUN rm /usr/lib/python3/dist-packages/pycrypto-2.6.1.egg-info
COPY . /
EXPOSE 8080
ENTRYPOINT [ "python3" ]

CMD [ "app/app.py" ]
