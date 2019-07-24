ARG BUILD_FROM
FROM $BUILD_FROM

ENV LANG C.UTF-8

RUN apk add python3 gcc build-base git
RUN python3 -m ensurepip --upgrade
RUN git clone https://github.com/bmartin5692/sucks.git && cd sucks && git checkout D901 && python3 setup.py install
RUN pip3 install paho-mqtt

# Copy data for add-on
COPY vacuum.py /

WORKDIR /data

RUN chmod a+x /vacuum.py

CMD [ "/vacuum.py" ]
