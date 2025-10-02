#!/bin/sh
python scripts/mqtt_to_baesapi.py &
python api/app.py &



wait
