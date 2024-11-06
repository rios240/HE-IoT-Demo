# Machinery sensor class
#   There are three types of sensors:
#       Temperature in °C
#       Vibration in mm/s
#       Pressure in PSI

import threading
import time
import random
import errors

class MachinerySensor(threading.Thread):
    SLEEP_INTERVAL = 60

    def __init__(self, sensor_id, sensor_sn):
        self.sensor_id = sensor_id
        self.sensor_sn = sensor_sn
        self.latest_number = None
        self.signal = threading.Event()
        self.lock = threading.Lock()

    def gen_number(self):
        if self.sensor_sn == "T79HD20J":
            return round(random.uniform(20.0, 100.0), 2)
        elif self.sensor_sn == "H54JU72D":
            return round(random.uniform(0.0, 20.0), 2)
        elif self.sensor_sn == "L20YT63C":
            return round(random.uniform(10.0, 100.0), 2)
        else:
            raise errors.GenericError("Unknown sensor")

    def run(self):
        while True:
            number = self.gen_number()

            with self.lock:
                self.latest_number = number

            self.signal.set()
            time.sleep(self.SLEEP_INTERVAL)
