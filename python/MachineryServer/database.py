# Database models used by SQLAlchemy

from flask_sqlalchemy import SQLAlchemy
import server

# absolute path to database (MODIFY THE PATH AS PER YOUR INSTALLATION)
DB_PATH_ABS = "/home/student/HE-IoT-Demo/python/MachineryServer/machinery.sqlite"

server.server.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///"+DB_PATH_ABS
server.server.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# SQLAlchemy database object
db = SQLAlchemy(server.server)


# Table sensor in machinery.sqlite
#  Tracks properties of a sensor resource
class Sensor(db.Model):
    id = db.Column(db.Text, primary_key=True)                   # id of sensor
    serial_no = db.Column(db.Text, primary_key=True)            # serial no. of sensor
    description = db.Column(db.Text, nullable=True)             # sensor description
    utc_assigned_at = db.Column(db.Integer, nullable=False)     # sensor assigned to user unix timestamp
    utc_modified_at = db.Column(db.Integer, nullable=False)     # sensor description modified unix timestamp

