from flask import Flask, render_template, request, jsonify
import csv
import math
import os
import threading

app = Flask(__name__)

# Robust paths for files
CSV_PATH = os.path.join(os.path.dirname(__file__), 'gi_tags.csv')
GOVT_REGISTRY_PATH = os.path.join(os.path.dirname(__file__), 'govt_registry.txt')

# Lock to prevent simultaneous writing issues during the demo
file_lock = threading.Lock()

def is_govt_verified(product_name):
    """Simulates checking the Government GI Registry."""
    try:
        with open(GOVT_REGISTRY_PATH, 'r', encoding='utf-8') as f:
            official_names = [line.strip().lower() for line in f.readlines()]
        return product_name.strip().lower() in official_names
    except FileNotFoundError:
        return False

def load_gi_data():
    tags = []
    try:
        with file_lock:
            with open(CSV_PATH, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    tags.append({
                        'id': int(row['id']),
                        'name': row['name'],
                        'lat': float(row['lat']),
                        'lon': float(row['lon']),
                        'story': row['story'],
                        'authentication': row['authentication'],
                        'contact': row['contact'],
                        'verified': row.get('verified', 'false') == 'true'
                    })
    except FileNotFoundError:
        with open(CSV_PATH, 'w', newline='', encoding='utf-8') as f:
            f.write("id,name,lat,lon,story,authentication,contact,verified\n")
        print(f"Created new file: {CSV_PATH}")
    except Exception as e:
        print(f"Silently handled error: {e}")
    return tags

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/add', methods=['POST'])
def add_tag():
    name = request.form.get('name')
    lat = request.form.get('lat')
    lon = request.form.get('lon')
    story = request.form.get('story')
    authentication = request.form.get('authentication')
    contact = request.form.get('contact')

    if not name or not lat or not lon:
        return jsonify({'error': 'Missing required fields'}), 400

    # Check against the "Govt Registry"
    verified_status = is_govt_verified(name)

    try:
        with file_lock:
            with open(CSV_PATH, 'r', encoding='utf-8') as rf:
                reader = csv.reader(rf)
                next_id = sum(1 for row in reader)
            with open(CSV_PATH, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([next_id, name, lat, lon, story, authentication, contact, str(verified_status).lower()])
        return jsonify({'message': 'success', 'verified': verified_status})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/gi_tags')
def get_nearby_tags():
    GI_TAGS = load_gi_data()
    user_lat = request.args.get('lat', type=float)
    user_lon = request.args.get('lon', type=float)
    radius = request.args.get('radius', 5000, type=float)

    if user_lat is None or user_lon is None:
        return jsonify({'error': 'Missing lat/lon'}), 400

    nearby = []
    for tag in GI_TAGS:
        dist = haversine(user_lat, user_lon, tag['lat'], tag['lon'])
        if dist <= radius:
            tag_copy = tag.copy()
            tag_copy['distance'] = round(dist, 2)
            nearby.append(tag_copy)

    return jsonify(nearby)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
