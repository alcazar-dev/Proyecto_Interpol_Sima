from flask import Flask, render_template, request, jsonify
from process_wind import process_interpolation
import os

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate_map', methods=['POST'])
def generate_map():
    fecha = request.form['fecha']
    hora = request.form['hora']
    contaminante = request.form['contaminante']
    image_base64 = process_interpolation(fecha, hora, contaminante)
    return jsonify({'image_base64': image_base64})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
