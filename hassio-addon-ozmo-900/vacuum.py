#!/usr/bin/python3
#Controlling Ecovacs Deebot vaccum with sucks

from sucks import *
import paho.mqtt.client as paho
import json
import random
import string


class DeebotMQTTClient:

    def __init__(self, mqtt_config, ecovacs_config):
        self._connected = False

        self._command_topic = mqtt_config["command_topic"]
        self._send_command_topic = mqtt_config["send_command_topic"]
        self._state_topic = mqtt_config["state_topic"]
        self._set_fan_speed_topic = mqtt_config["set_fan_speed_topic"]
        self._attribute_topic = mqtt_config["json_attributes_topic"]
        self._error_topic = mqtt_config["error_topic"]
        self._availability_topic = mqtt_config["availability_topic"]

        random_id = ''.join(random.choice(string.ascii_lowercase) for x in range(6))
        self.mqtt_client = paho.Client("ecovacs-vacuum-" + random_id)
        self.mqtt_client.on_connect = self._on_connect
        self.mqtt_client.on_message = self._on_message

        self._broker_host = mqtt_config["broker_host"]
        self._broker_port = int(mqtt_config["broker_port"])

        if mqtt_config["username"] != "" and mqtt_config["password"] != "":
            self.mqtt_client.username_pw_set(mqtt_config["username"], mqtt_config["password"])

        print("Connecting to broker: ", self._broker_host + ":" + str(self._broker_port))
        self.mqtt_client.connect(self._broker_host, self._broker_port, 60)

        print("Starting the loop... ")
        self.mqtt_client.loop_start()

        while self._connected != True:
            print("waiting to be connected to mqtt broker")
            time.sleep(0.1)

        self._connect_to_deebot(ecovacs_config)

        while True:
            time.sleep(1)


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
        # retain=True, so if HA restarts, it can read the last vacuum status
        self.mqtt_client.publish(topic, json.dumps(message), qos=2, retain=True)

    def _connect_to_deebot(self, config):
        api = EcoVacsAPI(config['device_id'], config['email'], config['password_hash'], config['country'], config['continent'])

        my_vac = api.devices()[0]
        self.vacbot = VacBot(api.uid, api.REALM, api.resource, api.user_access_token, my_vac, config['continent'], monitor=True, verify_ssl=config['verify_ssl'])
        self._subscribe_events()

        self.vacbot.connect_and_wait_until_ready()

    def _subscribe_events(self):
        # Subscribe to the all event emitters
        self.vacbot.batteryEvents.subscribe(self._battery_report)
        self.vacbot.statusEvents.subscribe(self._status_report)
        self.vacbot.lifespanEvents.subscribe(self._lifespan_report)
        self.vacbot.errorEvents.subscribe(self._error_report)

    # Callback function for battery events
    def _battery_report(self, level):
        status_report = {
            "battery_level": int(level * 100),
            "state": self.vacbot.vacuum_status,
            "fan_speed": self.vacbot.fan_speed,
        }
        self.publish(self.get_state_topic(), status_report)
        self.vacbot.run(GetCleanState())
        self.vacbot.run(GetChargeState())

    # Callback function for battery events
    def _status_report(self, status):
        # State has to be one of vacuum states supported by Home Assistant:
        ha_vacuum_supported_statuses = [
            "cleaning", "docked", "paused", "idle", "returning", "error"
        ]

        battery_level = "0"
        if self.vacbot.battery_status != None:
            battery_level = str(float(self.vacbot.battery_status) * 100)

        if status not in ha_vacuum_supported_statuses:
            if status == "charging":
                status = "docked"
            elif status == "auto" or status == "spot_area":
                status = "cleaning"
            elif status == "stop":
                status = "idle"
            elif status == "pause":
                status = "paused"
            else:
                print("Unknow HA status: ", status)

        status_report = {
            "battery_level": int(battery_level),
            "state": str(status),
            "fan_speed": self.vacbot.fan_speed,
        }

        print("Updating status: " + str(status))

        self.publish(self.get_state_topic(), status_report)
        self._publish_availability()

    def _publish_availability(self):
        if self.vacbot.vacuum_status != "offline":
            print("Updating availability: online")
            self.publish(self.get_availability_topic(), "online")
        else:
            print("Updating availability: offline")
            self.publish(self.get_availability_topic(), "offline")

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

        self.publish(self.get_attribute_topic(), attributes_status)
        print("Attributes: " + json.dumps(attributes_status))

    # Callback function for error events
    # THIS NEEDS A LOT OF WORK
    def _error_report(self, error):
        error_str = str(error)
        print("Error: " + error_str)

        self.publish(self.get_error_topic(), error_str)

    def _on_message(self, client, userdata, message):
        payload = message.payload.decode("utf-8").strip()
        print("Message received: ", payload)

        if message.topic == self.get_command_topic():
            if (payload == "turn_on" or payload == "start"):
                print("Clean started...")
                self.vacbot.run(Clean())
            elif(payload == "pause"):
                print("Pause robot")
                self.vacbot.run(Stop())
            elif(payload == "stop"):
                print("Stop robot")
                self.vacbot.run(Stop())
            elif(payload == "return_to_base" or payload == "return_home"):
                print("Return to base")
                self.vacbot.run(Charge())
            elif(payload == "locate"):
                print("Locate robot")
                self.vacbot.run(PlaySound())
            elif(payload == "clean_spot"):
                print("Clean spot")
                self.vacbot.run(Spot())
            elif(payload == "edge"):
                print("Clean edge")
                self.vacbot.run(Edge())

        elif message.topic == self.get_fan_speed_topic():
            self.vacbot.run(Clean(speed=payload))

        elif message.topic == self.get_send_command_topic():
            if payload == "":
                self.vacbot.run(Clean())
            else:
                self.vacbot.run(SpotArea(area=payload))

    def _on_connect(self, client, obj, flags, rc):
        if rc == 0:
            print("Connected to broker")
            self._connected = True
            print("OnConnect: subscribing to ", self.get_command_topic())
            self.mqtt_client.subscribe(self.get_command_topic())
            print("OnConnect: subscribing to ", self.get_fan_speed_topic())
            self.mqtt_client.subscribe(self.get_fan_speed_topic())
            print("OnConnect: subscribing to ", self.get_send_command_topic())
            self.mqtt_client.subscribe(self.get_send_command_topic())
        else:
            print("Connection failed")

    def __del__(self):
        print('Destructor called! Unsubscribing from MQTT topic.')
        self.mqtt_client.disconnect()
        self.mqtt_client.loop_stop()


if __name__ == "__main__":
    options_path = "/data/options.json"
    with open(options_path, encoding='utf-8') as options_file:
        config = json.load(options_file)

    DeebotMQTTClient(config['mqtt'], config['ecovacs'])
