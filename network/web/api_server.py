from flask import Flask, jsonify, request, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

device_id = 0

# Load configuration, and Create the SQLAlchemy object
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///api.db'
db = SQLAlchemy(app)

# This is the database model object
class Device(db.Model):
    __tablename__ = 'devices'
    id = db.Column(db.Integer, primary_key=True)
    hostname = db.Column(db.String(120), index=True)
    loopback = db.Column(db.String(40))
    mgmt_ip = db.Column(db.String(40))
    role = db.Column(db.String(40))
    vendor = db.Column(db.String(40))
    os = db.Column(db.String(40))
    self_url = db.Column(db.String(120))
    

    def __init__(self, hostname, loopback, mgmt_ip, role, vendor, os):
        self.hostname = hostname
        self.loopback = loopback
        self.mgmt_ip = mgmt_ip
        self.role = role
        self.vendor = vendor
        self.os = os
        
    
    def get_url(self):
        return url_for('interface', id=self.id, _external=True)

    def __repr__(self):
        return '<Device %r>' % self.hostname
    
    # format to send as dict for GET DB
    def to_dict(self):
        return {
            'id': self.id,
            'hostname': self.hostname,
            'loopback': self.loopback,
            'mgmt_ip': self.mgmt_ip,
            'role': self.role,
            'vendor': self.vendor,
            'os': self.os,
            'self_url': self.self_url
            }


@app.route('/devices/', methods=['GET'])
def get_devices():

    try:

        last_device = Device.query.order_by(Device.id.desc()).first()

        if not last_device.id:
            device_json = {"device": "http://172.16.1.123:5000/devices/", "message":"Not exist data record"}
            return jsonify(device_json)
        
        if last_device:
            last_id = last_device.id

        device_urls = [f"http://172.16.1.123:5000/devices/{i}" for i in range(1, last_id + 1)]
        device_json = {"device": device_urls}
        return jsonify(device_json)

    except Exception as e:
        print("Error no existe ID en la base de datos: ", str(e))
        return jsonify({"error": "Error al solicitar informacion de devices, no existe ID registrado"}), 400
    
@app.route('/db/', methods=['GET'])
def get_db():
    devices = Device.query.all()
    device_list = [device.to_dict() for device in devices]
    return jsonify(device_list)

@app.route('/devices/', methods=['POST'])
def post_devices():
    # Obtener los datos del nuevo equipo desde la solicitud JSON
    new_device = request.get_json()

    # Verificar que se hayan proporcionado datos válidos
    if not new_device:
        return jsonify({"error": "Datos invalidos"}), 400
    
    # Crear un nuevo objeto Device y agregarlo a la base de datos
    device = Device(
        hostname=new_device['hostname'],
        loopback=new_device['loopback'],
        mgmt_ip=new_device['mgmt_ip'],
        role=new_device['role'],
        vendor=new_device['vendor'],
        os=new_device['os']
    )

    try:
        # insert device to db
        db.session.add(device)
        db.session.commit()
        # get all info from db
        devices = Device.query.all()
        devices_list = [device.to_dict() for device in devices]
        # captured last device id
        device_id = devices_list [-1]["id"]
        print("Device ID: ", device_id)
        # update parameter id into instance device
        device.id = device_id
        print(device)
        # Generate a URL for the 'get_device' route with id=x
        device_url = device.get_url()
        print(device_url)

        # Get the existing device from the database
        existing_device = Device.query.get(device_id)
        existing_device.self_url = device_url
        db.session.commit()
        # Devolver una respuesta con los datos del nuevo equipo y el código de respuesta 201 (Created)
        return jsonify({"message": "Equipo registrado con éxito", "device": new_device}), 201, {'Location': device_url}
        # http POST http://172.30.157.251:5000/devices 'hostname'='iosv-1' 'loopback'='192.168.0.1' 'mgmt_ip'='172.16.1.225' 'role'='spine' 'vendor'='Cisco' 'os'='14.6'
    except Exception as e:
        db.session.rollback()
        print("Error al registrar el dispositivo:", str(e))
        return jsonify({"error": "Error al registrar el dispositivo"}), 500
    

@app.route('/devices/<int:id>', methods=['GET'])
def interface(id):
    devices = Device.query.all()
    device_list = [device.to_dict() for device in devices]

    return jsonify(device_list[id - 1])


@app.route('/devices/<int:id>', methods=['PUT'])
def update_device(id):

    # Get the existing device from the database
    existing_device = Device.query.get(id)

    if not existing_device:
        return jsonify({"error": "Device not found"}), 404

    # Obtener los datos del nuevo equipo desde la solicitud JSON
    updated_data = request.get_json()

        # Update the fields of the existing device
    existing_device.hostname = updated_data.get('hostname', existing_device.hostname)
    existing_device.loopback = updated_data.get('loopback', existing_device.loopback)
    existing_device.mgmt_ip = updated_data.get('mgmt_ip', existing_device.mgmt_ip)
    existing_device.role = updated_data.get('role', existing_device.role)
    existing_device.vendor = updated_data.get('vendor', existing_device.vendor)
    existing_device.os = updated_data.get('os', existing_device.os)
    existing_device.self_url = updated_data.get('self_url', existing_device.self_url)

    try:
        db.session.commit()
        return jsonify({"message": "Device updated successfully", "device": existing_device.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Error updating device", "details": str(e)}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Crea las tablas en la base de datos si no existen
    app.run(host='0.0.0.0', debug=True)
    