from flask import Flask, render_template, request, jsonify, send_file
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
import csv
import math
import os
import tempfile

app = Flask(__name__)

# Constants
EARTH_RADIUS = 6371  # Earth's radius in kilometers

def mercator_projection(lat, lon):
    """Convert (latitude, longitude) to (x, y) using Mercator Projection"""
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)

    x = EARTH_RADIUS * lon_rad
    y = EARTH_RADIUS * math.log(math.tan(math.pi / 4 + lat_rad / 2))

    return x, y

def get_coordinates_from_location(location_name):
    """Get latitude and longitude from location name using geocoding"""
    geolocator = Nominatim(user_agent="geo_coordinate_converter")
    try:
        location = geolocator.geocode(location_name)
        if location:
            return location.latitude, location.longitude
        return None
    except (GeocoderTimedOut, GeocoderUnavailable):
        return None

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/batch_convert', methods=['POST'])
def batch_convert():
    if 'file' not in request.files:
        return jsonify({'error': 'No file selected'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and file.filename.endswith('.csv'):
        # Save to temp file
        temp_dir = tempfile.gettempdir()
        input_path = os.path.join(temp_dir, file.filename)
        file.save(input_path)
        
        coordinates = []
        with open(input_path, newline='') as csvfile:
            reader = csv.reader(csvfile)
            next(reader)  # Skip header
            for row in reader:
                if len(row) >= 2:
                    try:
                        lat = float(row[0])
                        lon = float(row[1])
                        coordinates.append((lat, lon))
                    except ValueError:
                        continue
        
        cartesian_coords = []
        for lat, lon in coordinates:
            x, y = mercator_projection(lat, lon)
            x_rounded = int(round(x))
            y_rounded = int(round(y))
            cartesian_coords.append((x_rounded, y_rounded))
        
        output_filename = 'converted_coordinates.csv'
        output_path = os.path.join(temp_dir, output_filename)
        
        with open(output_path, mode='w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["x", "y"])
            for x, y in cartesian_coords:
                writer.writerow([x, y])
        
        return jsonify({
            'status': f'Converted {len(cartesian_coords)} coordinates',
            'download_url': f'/download/{output_filename}'
        })
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/download/<filename>')
def download(filename):
    temp_dir = tempfile.gettempdir()
    path = os.path.join(temp_dir, filename)
    return send_file(path, as_attachment=True)

@app.route('/convert_coordinates', methods=['POST'])
def convert_coordinates():
    data = request.json
    lat = data.get('latitude')
    lon = data.get('longitude')
    location = data.get('location')
    
    if location:
        result = get_coordinates_from_location(location)
        if not result:
            return jsonify({'error': 'Location not found'}), 400
        lat, lon = result
    
    try:
        lat = float(lat)
        lon = float(lon)
        
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            return jsonify({'error': 'Invalid coordinate range'}), 400
        
        x, y = mercator_projection(lat, lon)
        return jsonify({
            'original_coords': f"{lat}, {lon}",
            'x': int(round(x)),
            'y': int(round(y)),
            'latitude': lat,
            'longitude': lon
        })
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid coordinates'}), 400

if __name__ == '__main__':
    app.run(debug=True)