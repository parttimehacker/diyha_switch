#!/usr/bin/python3
""" DIYHA switch
    Receives MQTT messages from MQTT broker or motion sensor to turn on/off switch.
"""

# The MIT License (MIT)
#
# Copyright (c) 2019 parttimehacker@gmail.com
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import argparse
import logging.config
import time
import paho.mqtt.client as mqtt

from pkg_classes.switchcontroller import SwitchController
from pkg_classes.topicmodel import TopicModel
from pkg_classes.whocontroller import WhoController
from pkg_classes.testmodel import TestModel

# Constants for GPIO pins

SWITCH_GPIO = 17
MOTION_GPIO = 27

# Start logging and enable imported classes to log appropriately.

logging.config.fileConfig(fname="/usr/local/diyha_switch/logging.ini",
                          disable_existing_loggers=False)
LOGGER = logging.getLogger("diyha_switch")
LOGGER.info('Application started')

# Location provided by MQTT broker at runtime and managed by this class.

TOPIC = TopicModel() # Location MQTT topic

# Set up diy/system/who message handler from MQTT broker and wait for client.

WHO = WhoController()

# set up alarm GPIO controller

SWITCH = SwitchController(SWITCH_GPIO) # Alarm or light controller

# process diy/system/test development messages

TEST = TestModel(SWITCH)

# Process MQTT messages using a dispatch table algorithm.

def system_message(msg):
    """ Log and process system messages. """
    LOGGER.info(msg.topic+" "+msg.payload.decode('utf-8'))
    if msg.topic == 'diy/system/fire':
        if msg.payload == b'ON':
            SIREN.sound_alarm(True)
        else:
            SIREN.sound_alarm(False)
    elif msg.topic == 'diy/system/panic':
        if msg.payload == b'ON':
            SIREN.sound_alarm(True)
        else:
            SIREN.sound_alarm(False)
    elif msg.topic == 'diy/system/test':
        TEST.on_message(msg.payload)
    elif msg.topic == TOPIC.get_setup():
        topic = msg.payload.decode('utf-8') + "/alive"
        TOPIC.set(topic)
    elif msg.topic == 'diy/system/who':
        if msg.payload == b'ON':
            WHO.turn_on()
        else:
            WHO.turn_off()

#pylint: disable=unused-argument

def topic_message(msg):
    """ Set the sensors location topic. Used to publish measurements. """
    LOGGER.info(msg.topic+" "+msg.payload.decode('utf-8'))
    topic = msg.payload.decode('utf-8') + "/motion"
    TOPIC.set(topic)


#  A dictionary dispatch table is used to parse and execute MQTT messages.

TOPIC_DISPATCH_DICTIONARY = {
    "diy/system/fire":
        {"method":system_message},
    "diy/system/panic":
        {"method":system_message},
    "diy/system/test":
        {"method": system_message},
    "diy/system/who":
        {"method":system_message},
    TOPIC.get_setup():
        {"method":topic_message}
    }


def on_message(client, userdata, msg):
    """ dispatch to the appropriate MQTT topic handler """
    #pylint: disable=unused-argument
    TOPIC_DISPATCH_DICTIONARY[msg.topic]["method"](msg)


def on_connect(client, userdata, flags, rc_msg):
    """ Subscribing in on_connect() means that if we lose the connection and
        reconnect then subscriptions will be renewed.
    """
    #pylint: disable=unused-argument
    client.subscribe("diy/system/fire", 1)
    client.subscribe("diy/system/panic", 1)
    client.subscribe("diy/system/test", 1)
    client.subscribe("diy/system/who", 1)
    client.subscribe(TOPIC.get_setup(), 1)


def on_disconnect(client, userdata, rc_msg):
    """ Subscribing on_disconnect() tilt """
    #pylint: disable=unused-argument
    client.connected_flag = False
    client.disconnect_flag = True


if __name__ == '__main__':

    # Setup MQTT handlers then wait for timed events or messages

    CLIENT = mqtt.Client()
    CLIENT.on_connect = on_connect
    CLIENT.on_disconnect = on_disconnect
    CLIENT.on_message = on_message

    # initilze the Who client for publishing.

    WHO.set_client(CLIENT)

    # command line argument contains Mosquitto MQTT broker IP address.

    PARSER = argparse.ArgumentParser('sensor.py parser')
    PARSER.add_argument('--mqtt', help='MQTT server IP address')
    ARGS = PARSER.parse_args()

    BROKER_IP = ARGS.mqtt
    print(BROKER_IP)

    CLIENT.connect(BROKER_IP, 1883, 60)
    CLIENT.loop_start()

    # Message broker will send the location and set waiting to false.

    while TOPIC.waiting_for_location:
        time.sleep(5.0)

    # Loop forever waiting for and handling MQTT messages.

    while True:
        time.sleep(5.0)
