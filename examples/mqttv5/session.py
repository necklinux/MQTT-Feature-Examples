import utils

import paho.mqtt.client as mqtt
from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.properties import Properties

from utils import print_in_progress, print_success, print_fail, highlight

HOST = "broker.emqx.io"
PORT = 1883

SUCCESS = "\033[1;32;40m\u2714\033[0m "
FAIL = "\033[1;31;40m\u2718\033[0m "
INPROGRESS= "\033[1;34;40m\u2026\033[0m "

def publish(client, topic, payload):
    print_in_progress("Publishing to %s:\n\
    Payload = %s" % (highlight(topic), highlight(payload)))
    client.publish(topic, payload)

def connect(client, callback, clean_start = True, session_expiry_interval = 0):
    properties = Properties(PacketTypes.CONNECT)
    properties.SessionExpiryInterval = session_expiry_interval
    client.connect(host = HOST, port = PORT, clean_start = clean_start, properties = properties)
    print_in_progress("Connecting to %s with Clean Start = %s, Session Expiry Interval = %s" %
        (highlight(HOST), highlight(clean_start), highlight(session_expiry_interval)))
    client.loop_start()

    response = callback.wait_connected()
    if response["reasonCode"] != 0:
        print_fail("Connect to %s failed due to %s" %
                   (highlight(HOST), highlight(response["reasonCode"])))
        exit()

    # Get session present and assigned client id from the response
    assigned_client_id = None
    add_on = ""
    if hasattr(response["properties"], 'AssignedClientIdentifier'):
        assigned_client_id = response["properties"].AssignedClientIdentifier
        add_on = ", Assigned Client Identifier = %s" % highlight(assigned_client_id)

    print_success("Connected. Session Present = %s" % highlight(response["flags"]['session present']) + add_on)
    return assigned_client_id

def subscribe(client, callback, topic):
    client.subscribe(topic, qos = 2)
    print_in_progress("Subscribing to %s" % highlight(topic))
    
    response = callback.wait_subscribed()
    if response["reasonCodes"][0].getId(response["reasonCodes"][0].getName()) > 2:
        print_fail("Subscribe to %s failed due to %s" %
                   (highlight(topic), highlight(response["reasonCodes"][0])))
        exit()

    print_success("Subscribed to %s" % highlight(topic))

def disconnect(client, callback, session_expiry_interval = None):
    if session_expiry_interval is None:
        properties = None
    else:
        properties = Properties(PacketTypes.DISCONNECT)
        properties.SessionExpiryInterval = 0

    client.disconnect(properties = properties)
    callback.wait_disconnected()
    client.loop_stop()
    callback.clear()

    if properties is None:
        print_success("Disconnected\n")
    else:
        print_success("Disconnected and update session expiry interval to %s\n" % highlight(properties.SessionExpiryInterval))

if __name__=="__main__":
    callback = utils.Callbacks()
    #Migrate version 1 to version 2
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1,"", protocol = mqtt.MQTTv5)
    callback.register(client)

    assigned_client_id = connect(client, callback, clean_start = True, session_expiry_interval = 300)
    topic = assigned_client_id + "/test"
    subscribe(client, callback, topic)

    disconnect(client, callback)

    # Resume the session using the Client ID returned by the server
    #Migrate version 1 to version 2
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1,assigned_client_id, protocol = mqtt.MQTTv5)
    callback.register(client)
    connect(client, callback, clean_start = False, session_expiry_interval = 300)

    publish(client, topic, "Hello World")

    messages = callback.wait_messages(1, 2)
    msg = messages[0]["message"]
    print_success("Received from %s\n\
    Payload = %s" % (highlight(msg.topic), highlight(msg.payload.decode("utf-8"))))

    # Update session expiry interval when disconnecting
    disconnect(client, callback, session_expiry_interval = 0)

    #Migrate version 1 to version 2
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1,assigned_client_id, protocol = mqtt.MQTTv5)
    callback.register(client)
    # Session Present will be 0
    connect(client, callback, clean_start = False, session_expiry_interval = 0)
    disconnect(client, callback)
