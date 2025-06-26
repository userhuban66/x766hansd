# app.py (Silme Fonksiyonu Eklenmiş Tam Kod)
from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from itsdangerous import URLSafeTimedSerializer
import json
import os
from datetime import datetime

app = Flask(__name__)
# BU SECRET_KEY'İ KESİNLİKLE KİMSE İLE PAYLAŞMA!
app.config['SECRET_KEY'] = 'my-super-secret-and-long-key-for-signing'

LICENSE_FILE = "licenses.json"
ADMIN_PASSWORD = "admin123"

s = URLSafeTimedSerializer(app.config['SECRET_KEY'])

# ------------------ Yardımcı Fonksiyonlar ------------------
def load_data():
    if not os.path.exists(LICENSE_FILE):
        initial_data = { "licenses": {}, "settings": { "restrict_to_registered": False } }
        with open(LICENSE_FILE, 'w') as f: json.dump(initial_data, f, indent=4)
    with open(LICENSE_FILE, 'r') as f: return json.load(f)

def save_data(data):
    with open(LICENSE_FILE, 'w') as f: json.dump(data, f, indent=4)

def is_license_active(entry):
    if not entry.get("aktif"): return False
    try:
        return datetime.strptime(entry.get("bitis"), "%Y-%m-%d") >= datetime.today()
    except:
        return False

# ------------------ Web Arayüzü (Panel, Giriş vb.) ------------------
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('panel'))
    return render_template('login.html')

@app.route('/panel')
def panel():
    if not session.get('logged_in'): return redirect(url_for('login'))
    data = load_data()
    return render_template('panel.html', licenses=data.get("licenses", {}), settings=data.get("settings", {}))

@app.route('/update', methods=['POST'])
def update():
    if not session.get('logged_in'): return redirect(url_for('login'))
    hwid = request.form.get('hwid')
    data = load_data()
    data["licenses"][hwid] = {
        "aktif": True if request.form.get('aktif') == 'on' else False,
        "uye_tipi": request.form.get('uye_tipi'),
        "bitis": request.form.get('bitis')
    }
    save_data(data)
    return redirect(url_for('panel'))

@app.route('/toggle_restriction', methods=['POST'])
def toggle_restriction():
    if not session.get('logged_in'): return redirect(url_for('login'))
    data = load_data()
    data["settings"]["restrict_to_registered"] = not data["settings"].get("restrict_to_registered", False)
    save_data(data)
    return redirect(url_for('panel'))

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

# ------------------ Lisans API ------------------
@app.route('/api/lisans')
def api_lisans():
    hwid = request.args.get("hwid")
    if not hwid: return jsonify({"status": "error", "message": "HWID gerekli."}), 400
    data = load_data()
    licenses = data.get("licenses", {})
    entry = licenses.get(hwid)
    if not entry and data.get("settings", {}).get("restrict_to_registered"):
        return jsonify({"status": "rejected", "message": "Yeni kullanıcı kaydı kapalı."})
    if not entry:
        licenses[hwid] = {"aktif": False, "uye_tipi": "deneme", "bitis": "2000-01-01"}
        save_data(data)
        return jsonify({"status": "inactive", "message": "Lisans aktif değil."})
    if is_license_active(entry):
        license_data = {'hwid': hwid, 'bitis': entry['bitis']}
        license_key = s.dumps(license_data, salt=hwid) 
        return jsonify({"status": "ok", "key": license_key})
    else:
        return jsonify({"status": "inactive", "message": "Lisans aktif değil veya süresi dolmuş."})

# ------------------ YENİ: HWID SİLME API ------------------
@app.route('/delete/<string:hwid>', methods=['DELETE'])
def delete_hwid(hwid):
    if not session.get('logged_in'):
        return jsonify({"success": False, "message": "Yetkisiz erişim"}), 401
    
    data = load_data()
    if hwid in data['licenses']:
        del data['licenses'][hwid]
        save_data(data)
        return jsonify({"success": True, "message": f"{hwid} başarıyla silindi."})
    else:
        return jsonify({"success": False, "message": "HWID bulunamadı."}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)