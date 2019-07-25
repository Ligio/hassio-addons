#!/usr/bin/python3
#Controlling Ecovacs Deebot vaccum with sucks

from sucks import *
import paho.mqtt.client as paho
import json


class DeebotMQTTClient:

    def __init__(self, mqtt_config, vacbot):
        self.vacbot = vacbot
        self.command_topic = mqtt_config["command_topic"]
        self.client = paho.Client(mqtt_config["client_id"])
        self.client.on_message = self._on_message
        self.client.on_connect = self._on_connect

        print("connecting to broker ", mqtt_config["broker_host"] + ":" + str(mqtt_config["broker_port"]))
        if mqtt_config["username"] != "" and mqtt_config["password"] != "":
            self.client.username_pw_set(mqtt_config["username"], mqtt_config["password"])
        self.client.connect(mqtt_config["broker_host"], port=mqtt_config["broker_port"]) 

    def wait_for_requests(self):
        print("Starting the loop... ")
        self.client.loop_forever()

    def _on_connect(self, client, obj, flags, rc):
        if rc == 0:
            print("Connected to broker")
            self._connected = True  
            print("OnConnect: subscribing to ", self.command_topic)
            self.client.subscribe(self.command_topic)
        else:
            print("Connection failed")

    def _on_message(self, client, userdata, message):
        payload = message.payload.decode("utf-8").strip()
        
        if message.topic == self.command_topic:
            if (payload == "turn_on" or payload == "start"):
                print("Clean started...")
                self.vacbot.run(Clean())
            elif(payload == "return_to_base" or payload == "return_home"):
                print("Return to base")
                self.vacbot.run(Charge())
            elif(payload == "locate"):
                print("Locate robot")
                self.vacbot.run(PlaySound())
            elif(payload == "stop"):
                print("Stop robot")
                self.vacbot.run(Stop())

    def __del__(self): 
        print('Destructor called! Unsubscribing from MQTT topic.')
        self.client.disconnect()
        self.client.loop_stop()


def connect_and_subscribe_to_mqtt_broker(mqtt_config, vacbot):
    DeebotMQTTClient(mqtt_config, vacbot).wait_for_requests()

def connect_to_deebot(config):
    api = EcoVacsAPI(config['device_id'], config['email'], config['password_hash'], config['country'], config['continent'])

    my_vac = api.devices()[0]
    vacbot = VacBot(api.uid, api.REALM, api.resource, api.user_access_token, my_vac, config['continent'])
    vacbot.connect_and_wait_until_ready()

    return vacbot

if __name__ == "__main__":
    options_path = "/data/options.json"
    config = {}
    with open(options_path, encoding='utf-8') as options_file:
        config = json.load(options_file)

    vacbot = connect_to_deebot(config['ecovacs'])
    connect_and_subscribe_to_mqtt_broker(config['mqtt'], vacbot)
    
