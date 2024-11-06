# Machinery sensor class
#   There are three types of sensors:
#       Temperature in °C
#       Vibration in mm/s
#       Pressure in PSI


from threading import Thread, Event
import time
import random
import errors
import keying


class MachinerySensor(threading.Thread):
    SLEEP_INTERVAL = 60

    # Constructor
    def __init__(self, sensor_id, sensor_sn):
        super().__init__()
        self.id = sensor_id
        self.sn = sensor_sn
        self.reading = None
        self.signal = threading.Event()
        self.signal.clear()
        self.cert = None
        self.key = None
        if self.sn == "T79HD20J":
            self.cert = keying.SENSOR_1A2B3C_CERTIFICATE
            self.key = keying.SENSOR_1A2B3C_KEY
        elif self.sn == "H54JU72D":
            self.cert = keying.SENSOR_4D5E6F_CERTIFICATE
            self.key = keying.SENSOR_4D5E6F_KEY
        elif self.sn == "L20YT63C":
            self.cert = keying.SENSOR_7G8H9I_CERTIFICATE
            self.key = keying.SENSOR_7G8H9I_KEY
        else:
            raise errors.GenericError("Unknown sensor")
            
    # Generates a random sensor reading
    def gen_reading(self):
        if self.sn == "T79HD20J":
            return round(random.uniform(20.0, 100.0), 2)
        elif self.sn == "H54JU72D":
            return round(random.uniform(0.0, 20.0), 2)
        elif self.sn == "L20YT63C":
            return round(random.uniform(10.0, 100.0), 2)
        else:
            raise errors.GenericError("Unknown sensor")

    # Function that runs when calling start() on object
    def run(self):
        while True:
            self.reading = self.gen_reading()
            self.signal.set()
            time.sleep(self.SLEEP_INTERVAL)
