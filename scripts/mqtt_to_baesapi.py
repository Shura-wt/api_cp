#! /usr/bin/env python3

import paho.mqtt.client as mqtt
from datetime import datetime
import requests
import json, traceback
import logging
import signal
import sys

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("mqtt_to_baesapi")

# TLS files (unused for plain TCP, kept for future TLS enablement)
tls_ca_cert = "/etc/mosquitto/ca_certificates/rootCA.pem"
tls_certfile = "/etc/mosquitto/ca_certificates/mosquitto.crt"
tls_keyfile = "/etc/mosquitto/ca_certificates/mosquitto.key"

# MQTT credentials (do not log secrets)
MOSQUITTO_USER = "gps_tracker"
MOSQUITTO_PWD = "p8$9z5Gn&x"
MQTT_HOST = "90.113.56.213"
MQTT_PORT = 1883  # 8883 for TLS
MQTT_KEEPALIVE = 60

# BAES API credentials/host (do not log secrets)
BAESAPI_SERVER = "localhost"
BAESAPI_USER = "superadmin"
BAESAPI_PWD = "superadmin_password"

ANNOUNCE_TOPIC = "testtopic/connection"
ANNOUNCE_MSG = "connection effectué sript python"  # texte demandé


def on_connect(client, userdata, flags, rc, properties):
    if rc == 0:
        logger.info("Connecté au broker MQTT (rc=%s)", rc)
    else:
        logger.error("Échec de connexion au broker MQTT (rc=%s)", rc)
    try:
        client.publish(ANNOUNCE_TOPIC, ANNOUNCE_MSG, qos=1, retain=False)
        logger.info("Message d'annonce publié sur '%s'", ANNOUNCE_TOPIC)
        client.subscribe("baes/data")
        logger.info("Abonné au topic 'baes/data'")
    except Exception:
        logger.exception("Erreur lors de la publication d'annonce ou de l'abonnement")


def on_disconnect(client, userdata, rc, properties=None):
    if rc != 0:
        logger.warning("Déconnexion inattendue du broker MQTT (rc=%s)", rc)
    else:
        logger.info("Déconnexion du broker MQTT (rc=%s)", rc)


def on_message(client, userdata, message):
    try:
        payload = message.payload.decode('utf-8')
        json_data = json.loads(payload)
        logger.info("Message reçu sur %s: %s", message.topic, payload)

        # Get the error code from the JSON data
        erreur_raw = json_data.get("baes_state", json_data.get("erreur", 6))
        erreur = int(erreur_raw) if isinstance(erreur_raw, (int, float)) or (
            isinstance(erreur_raw, str) and erreur_raw.isdigit()) else 6

        # Get the baes_id from the JSON data
        baes_id_raw = json_data.get("baes_id")
        if baes_id_raw is None:
            raise ValueError("baes_id manquant dans le message")

        # Remove colons and convert hex string to integer
        baes_id = int(baes_id_raw.replace(":", ""), 16)

        # Ensure it's within 64-bit unsigned range
        baes_id &= 0xFFFFFFFFFFFFFFFF

        # Get temperature and vibration from the JSON data if they exist
        temperature = json_data.get("temperature")
        vibration = json_data.get("vibration")

        data = {
            "baes_id": baes_id,
            "erreur": int(erreur)
        }

        # Add temperature and vibration to the data if they exist
        if (temperature is not None) and (temperature != "nan"):
            data["temperature"] = float(temperature)
        if vibration is not None:
            data["vibration"] = vibration

        logger.info("Envoi des données vers BAES API: %s", data)
        result = requests.post(
            f"http://{BAESAPI_SERVER}:5000/erreurs/", json=data, verify=False, timeout=5.0
        )
        logger.info("Réponse BAES API: status=%s body=%s", result.status_code, result.text)
    except Exception:
        logger.exception("Erreur lors du décodage et de l'insertion des données")


def _graceful_shutdown(signum, frame):
    logger.info("Signal %s reçu. Arrêt en cours...", signum)
    try:
        client.loop_stop()
        client.disconnect()
    except Exception:
        logger.exception("Erreur pendant l'arrêt du client MQTT")
    finally:
        sys.exit(0)


# Startup logs
logger.info("Démarrage du service MQTT -> BAES API")
try:
    logger.info(
        "Versions: paho-mqtt=%s, requests=%s", getattr(mqtt, "__version__", "?"), getattr(requests, "__version__", "?")
    )
except Exception:
    # Non bloquant
    pass
logger.info(
    "Configuration: MQTT host=%s port=%s keepalive=%s | BAES API server=%s | Announce topic=%s",
    MQTT_HOST,
    MQTT_PORT,
    MQTT_KEEPALIVE,
    BAESAPI_SERVER,
    ANNOUNCE_TOPIC,
)

# Register signal handlers for graceful shutdown
signal.signal(signal.SIGTERM, _graceful_shutdown)
signal.signal(signal.SIGINT, _graceful_shutdown)

# MQTT client setup
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
# client.tls_set(ca_certs=tls_ca_cert,
#                certfile=tls_certfile,
#                keyfile=tls_keyfile,
#                tls_version=mqtt.ssl.PROTOCOL_TLS)
# client.tls_insecure_set(True)
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message
client.username_pw_set(MOSQUITTO_USER, MOSQUITTO_PWD)

# Connect and start loop
try:
    logger.info("Connexion au broker MQTT %s:%s ...", MQTT_HOST, MQTT_PORT)
    client.connect(MQTT_HOST, MQTT_PORT, MQTT_KEEPALIVE)
    logger.info("Boucle MQTT démarrée")
    client.loop_forever()
except Exception:
    logger.exception("Échec critique: impossible de se connecter ou de démarrer la boucle MQTT")
    sys.exit(1)
