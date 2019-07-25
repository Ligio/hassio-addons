#!/usr/bin/python3
#Controlling Ecovacs Deebot vaccum with sucks

from sucks import *
#from sucks.sucks import *
import paho.mqtt.client as paho
import json


class DeebotMQTTClient:

    def __init__(self, mqtt_config):
        self._command_topic = mqtt_config["command_topic"]
        self._send_command_topic = mqtt_config["send_command_topic"]
        self._state_topic = mqtt_config["state_topic"]
        self._set_fan_speed_topic = mqtt_config["set_fan_speed_topic"]
        self._attribute_topic = mqtt_config["json_attributes_topic"]
        self._error_topic = mqtt_config["error_topic"]
        self._availability_topic = mqtt_config["availability_topic"]

        self.mqtt_client = paho.Client(mqtt_config["client_id"])
        self.mqtt_client.on_connect = self._on_connect

        print("connecting to broker ", mqtt_config["broker_host"] + ":" + str(mqtt_config["broker_port"]))
        if mqtt_config["username"] != "" and mqtt_config["password"] != "":
            self.mqtt_client.username_pw_set(mqtt_config["username"], mqtt_config["password"])

        self.mqtt_client.connect(mqtt_config["broker_host"], port=int(mqtt_config["broker_port"]))

    def get_command_topic(self):
        return self._command_topic

    def get_send_command_topic(self):
        return self._send_command_topic

    def get_state_topic(self):
        return self._state_topic

    def get_attribute_topic(self):
        return self._attribute_topic

    def get_error_topic(self):
        return self._error_topic

    def get_fan_speed_topic(self):
        return self._set_fan_speed_topic

    def get_availability_topic(self):
        return self._availability_topic

    def publish(self, topic, message):
        self.mqtt_client.publish(topic, json.dumps(message))

    def loop_forever(self):
        self.mqtt_client.loop_forever()

    def _on_connect(self, client, obj, flags, rc):
        if rc == 0:
            print("Connected to broker")
            self._connected = True  
            print("OnConnect: subscribing to ", self._command_topic)
            self.mqtt_client.subscribe(self._command_topic)
        else:
            print("Connection failed")

    def __del__(self): 
        print('Destructor called! Unsubscribing from MQTT topic.')
        self.mqtt_client.disconnect()
        self.mqtt_client.loop_stop()


class DeebotVacuum:

    def __init__(self, config, mqtt_client):
        self.mqtt_client = mqtt_client
        self.vacbot = self._connect_to_deebot(config)
        self._subscribe_events()
        self.mqtt_client.on_message = self._mqtt_on_message_callback

    def wait_for_requests(self):
        print("Ready to receive requests...")
        self.mqtt_client.loop_forever()

    def _mqtt_on_message_callback(self, client, userdata, message):
        payload = message.payload.decode("utf-8").strip()

        if message.topic == self.mqtt_client.get_command_topic():
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
            elif(payload == "clean_spot"):
                print("Clean spot")
                self.vacbot.run(Spot())

    def _connect_to_deebot(self, config):
        api = EcoVacsAPI(config['device_id'], config['email'], config['password_hash'], config['country'], config['continent'])

        my_vac = api.devices()[0]
        vacbot = VacBot(api.uid, api.REALM, api.resource, api.user_access_token, my_vac, config['continent'])
        vacbot.connect_and_wait_until_ready()

        return vacbot

    def _subscribe_events(self):
        # Subscribe to the all event emitters
        self.vacbot.batteryEvents.subscribe(self._battery_report)
        self.vacbot.statusEvents.subscribe(self._status_report)
        self.vacbot.lifespanEvents.subscribe(self._lifespan_report)
        self.vacbot.errorEvents.subscribe(self._error_report)

        # For the first run, try to get & report all statuses
        self.vacbot.request_all_statuses()

    # Callback function for battery events
    def _battery_report(self, level):
        print("Updating battery level: " + str(level * 100))

        status_report = {
            "battery_level": int(level * 100),
            "state": self.vacbot.vacuum_status,
            "fan_speed": self.vacbot.fan_speed,
        }
        self.mqtt_client.publish(self.mqtt_client.get_state_topic(), status_report)

    # Callback function for battery events
    def _status_report(self, status):
        print("Updating status: " + str(status))

        battery_level = "0"
        if self.vacbot.battery_status != None:
            battery_level = str(float(self.vacbot.battery_status) * 100)

        status_report = {
            "battery_level": int(battery_level),
            "state": str(status),
            "fan_speed": self.vacbot.fan_speed,
        }
        self.mqtt_client.publish(self.mqtt_client.get_state_topic(), status_report)

    # Callback function for lifespan (components) events
    def _lifespan_report(self, lifespan):
        lifespan_type = lifespan['type']
        changed_value = str(int(100 * lifespan['lifespan']))

        attributes_status = {
            "clean_status": self.vacbot.clean_status,
            "charge_status": self.vacbot.charge_status
        }

        for component_type in self.vacbot.components.keys():
            if component_type == lifespan_type:
                attributes_status[component_type] = changed_value
            else:
                attributes_status[component_type] = str(int(self.vacbot.components[component_type] * 100))

        self.mqtt_client.publish(self.mqtt_client.get_attribute_topic(), attributes_status)
        print("Attributes: " + json.dumps(attributes_status))

    # Callback function for error events
    # THIS NEEDS A LOT OF WORK
    def _error_report(self, error):
        error_str = str(error)
        print("Error: " + error_str)

        self.mqtt_client.publish(self.mqtt_client.get_error_topic(), error_str)

    # Library generated summary status. Smart merge of clean and battery status
    # I think that when returning it should override "stop" values. Will follow on that.
    def _save_full_vacuum_report(self):
        status_report = {
            "battery_level": int(float(self.vacbot.battery_status) * 100),
            "state": self.vacbot.vacuum_status,
            "fan_speed": self.vacbot.fan_speed,
        }

        self.mqtt_client.publish(self.mqtt_client.get_state_topic(), status_report)

        attributes_status = {
            "clean_status": self.vacbot.clean_status,
            "charge_status": self.vacbot.charge_status
        }

        for component_type in self.vacbot.components.keys():
            attributes_status[component_type] = self.vacbot.components[component_type]

        self.mqtt_client.publish(self.mqtt_client.get_attributes_topic(), attributes_status)

    def __del__(self):
        print('Destructor called for Vacuum!')
        del self.mqtt_client

if __name__ == "__main__":
    options_path = "/data/options.json"
    with open(options_path, encoding='utf-8') as options_file:
        config = json.load(options_file)

    mqtt_client = DeebotMQTTClient(config['mqtt'])
    DeebotVacuum(config['ecovacs'], mqtt_client)\
        .wait_for_requests()
