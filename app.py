from flask import Flask, render_template, request, jsonify
import csv
import math
import os
import threading

app = Flask(__name__)

CSV_PATH = os.path.join(os.path.dirname(__file__), 'gi_tags.csv')
file_lock = threading.Lock()

# --- BULLETPROOF VERIFICATION ---
# Hardcoded list to bypass any file encoding issues entirely.
OFFICIAL_GI_TAGS = {
    "banarasi saree", "bagh print", "kanchipuram silk", "pochampally ikat",
    "darjeeling tea", "mysore silk", "kolhapuri chappal", "nagpur orange",
    "alphonso mango", "basmati rice", "madhubani painting", "pattachitra",
    "kalamkari", "channapatna toys", "mysore sandalwood", "bidriware",
    "warli painting", "phulkari", "bandhani", "kutch embroidery",
    "pashmina", "kashmiri saffron", "kangra tea", "muga silk",
    "assam tea", "sikkim large cardamom", "naga mircha", "manipur black rice",
    "odisha rasagola", "banglar rasogolla", "joynagar moa", "sitalpati",
    "aranmula mirror", "alleppey coir", "thanjavur painting", "madurai sungudi",
    "nilgiri tea", "coorg green cardamom", "mysore agarbathi", "hyderabad haleem",
    "hyderabadi pearls", "tirupati laddu", "guntur sannam chilli", "araku coffee",
    "uppada jamdani saree", "gadwal saree", "cheriyal paintings", "nirmal toys"
}

def is_govt_verified(product_name):
    """Checks against the hardcoded verified list."""
    try:
        return product_name.strip().lower() in OFFICIAL_GI_TAGS
    except Exception:
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

    verified_status = is_govt_verified(name)

    try:
        with file_lock:
            with open(CSV_PATH, 'r', encoding='utf-8') as rf:
                reader = csv.reader(rf)
                next_id = sum(1 for row in reader)
            with open(CSV_PATH, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([next_id, name, lat, lon, story, authentication, contact, str(verified_status).lower()])
        
        return jsonify({'message': 'success', 'verified': verified_status, 'new_id': next_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/delete/<int:tag_id>', methods=['DELETE'])
def delete_tag(tag_id):
    try:
        with file_lock:
            with open(CSV_PATH, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                fieldnames = reader.fieldnames
            new_rows = [row for row in rows if int(row['id']) != tag_id]
            with open(CSV_PATH, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(new_rows)
        return jsonify({'message': 'success'})
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
