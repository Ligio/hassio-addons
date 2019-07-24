FROM homeassistant/armv7-base-ubuntu

ENV LANG C.UTF-8

# Copy data for add-on
COPY light_sensor.py /

RUN apt-get update
RUN apt-get install -y python3 python3-smbus

WORKDIR /data

RUN chmod a+x /light_sensor.py

CMD [ "/light_sensor.py" ]
