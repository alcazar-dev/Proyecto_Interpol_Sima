from flask import Flask, render_template, request, jsonify, Response
from process_wind import process_interpolation, generate_daily_gif

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate_map', methods=['POST'])
def generate_map():
    fecha = request.form['fecha']
    hora = request.form['hora']
    contaminante = request.form['contaminante']
    result = process_interpolation(fecha, hora, contaminante)
    
    if "error" in result:
        return jsonify({"error": result["error"]})
    return jsonify({"image_base64": result["image_base64"]})


@app.route('/generate_gif', methods=['POST'])
def generate_gif():
    fecha = request.form['fecha']
    contaminante = request.form['contaminante']
    gif_path, error = generate_daily_gif(fecha, contaminante)

    if error:
        return jsonify({'error': error})

    return jsonify({'gif_path': gif_path})



if __name__ == '__main__':
    app.run(debug=True)


