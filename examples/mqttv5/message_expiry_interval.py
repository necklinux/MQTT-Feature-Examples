import time
import utils

import paho.mqtt.client as mqtt
from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.properties import Properties

HOST = "broker.emqx.io"
PORT = 1883

def publish(client, topic, payload, properties):
    print("[Publish] Topic: %s, Payload: %s" % (topic, payload))
    client.publish(topic, payload, properties = properties)

a_callback = utils.Callbacks()
b_callback = utils.Callbacks()

# a_client as publisher
a_clientid = utils.random_clientid()
#Migrate version 1 to version 2
a_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1,a_clientid.encode("utf-8"), protocol = mqtt.MQTTv5)
a_callback.register(a_client)

# b_client as subsriber
b_clientid = utils.random_clientid()
connect_properties = Properties(PacketTypes.CONNECT)
connect_properties.SessionExpiryInterval = 300
#Migrate version 1 to version 2
b_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1,b_clientid.encode("utf-8"), protocol = mqtt.MQTTv5)
b_callback.register(b_client)

a_client.connect(host = HOST, port = PORT, clean_start = True)
a_client.loop_start()
response = a_callback.wait_connected()

b_client.connect(host = HOST, port = PORT, clean_start = True, properties = connect_properties)
b_client.loop_start()
response = b_callback.wait_connected()

topic = b_clientid + "/demo"
b_client.subscribe(topic, qos = 2)
response = b_callback.wait_subscribed()
b_client.disconnect()
b_callback.wait_disconnected()
b_client.loop_stop()
b_callback.clear()

# Publish messages with the expiry interval after the subscriber goes offline
publish_properties = Properties(PacketTypes.PUBLISH)
publish_properties.MessageExpiryInterval = 5
publish(a_client, topic, "Expiry Interval is 5 seconds", publish_properties)

publish_properties.MessageExpiryInterval = 60
publish(a_client, topic, "Expiry Interval is 60 seconds", publish_properties)

# The subscriber waits 6 seconds before reconnecting
time.sleep(6)
#Migrate version 1 to version 2
b_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1,b_clientid.encode("utf-8"), protocol = mqtt.MQTTv5)
b_callback.register(b_client)

connect_properties = Properties(PacketTypes.CONNECT)
connect_properties.SessionExpiryInterval = 0
b_client.connect(host = HOST, port = PORT, clean_start = False, properties = connect_properties)
b_client.loop_start()
response = b_callback.wait_connected()

messages = b_callback.wait_messages(2, 1)

if len(messages) == 1:
    msg = messages[0]["message"]
    print("[Received] Topic: %s, Payload: %s, Remaining expiry interval: %d" %
          (msg.topic, msg.payload.decode("utf-8"), msg.properties.MessageExpiryInterval))
else:
    print("Unexpected result")

# Disconnect
a_client.disconnect()
a_callback.wait_disconnected()
a_client.loop_stop()

b_client.disconnect()
b_callback.wait_disconnected()
b_client.loop_stop()
