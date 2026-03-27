import csv
import json
import os
from datetime import datetime

from flask import Flask, jsonify

app = Flask(__name__)

DATA_FILE = "data.json"
USERS_FILE = "users.csv"


# ---------------------------
# DEFAULT STRUCTURE
# ---------------------------
def default_data():
    return {
        "timestamp": "",
        "last_updated": "",
        "total_participants": 0,
        "total_activated": 0,
        "total_arrived": 0,
        "currently_active": 0,
        "undo_arrivals": 0,
        "total_events": 0,
        "last_5_arrived": [],
        "arrived_ids": [],  # 🔥 NEW
        "system_status": "running",
    }


# ---------------------------
# SAFE JSON LOAD/SAVE
# ---------------------------
def load_json(file):
    if not os.path.exists(file):
        return default_data()
    try:
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default_data()


def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ---------------------------
# ENSURE STRUCTURE
# ---------------------------
def ensure_structure(data):
    defaults = default_data()

    for key, value in defaults.items():
        if key not in data or data[key] is None:
            data[key] = value

    if not isinstance(data["last_5_arrived"], list):
        data["last_5_arrived"] = []

    if not isinstance(data["arrived_ids"], list):
        data["arrived_ids"] = []

    return data


# ---------------------------
# LOAD USERS
# ---------------------------
def load_users():
    users = []
    if not os.path.exists(USERS_FILE):
        return users

    try:
        with open(USERS_FILE, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                try:
                    users.append({"id": int(row["id"]), "name": row["name"]})
                except:
                    continue
    except:
        pass

    return users


# ---------------------------
# ROUTE: ARRIVED
# ---------------------------
@app.route("/arrived/<int:user_id>", methods=["GET"])
def arrived(user_id):
    data = ensure_structure(load_json(DATA_FILE))
    users = load_users()

    data["total_participants"] = len(users)

    user = next((u for u in users if u["id"] == user_id), None)
    if not user:
        return jsonify({"error": "User not found"}), 404

    # 🚫 PREVENT DOUBLE ARRIVAL
    if user_id in data["arrived_ids"]:
        return jsonify({"status": "already_arrived", "user": user["name"]}), 400

    now = datetime.now()

    arrival_entry = {
        "id": user["id"],
        "name": user["name"],
        "timestamp": now.isoformat(),
        "formatted_time": now.strftime("%H:%M:%S"),
    }

    # Track arrival
    data["arrived_ids"].append(user_id)

    data["last_5_arrived"].append(arrival_entry)
    data["last_5_arrived"] = data["last_5_arrived"][-5:]

    data["total_arrived"] = len(data["arrived_ids"])
    data["total_events"] = int(data.get("total_events", 0)) + 1

    data["timestamp"] = now.isoformat()
    data["last_updated"] = now.strftime("%Y-%m-%d %H:%M:%S")

    save_json(DATA_FILE, data)

    return jsonify(
        {
            "status": "success",
            "user": user["name"],
            "time": arrival_entry["formatted_time"],
        }
    )


# ---------------------------
# ROUTE: RESET
# ---------------------------
@app.route("/reset", methods=["GET"])
def reset():
    data = ensure_structure(load_json(DATA_FILE))

    data["arrived_ids"] = []
    data["last_5_arrived"] = []
    data["total_arrived"] = 0
    data["currently_active"] = 0
    data["undo_arrivals"] += 1

    now = datetime.now()
    data["timestamp"] = now.isoformat()
    data["last_updated"] = now.strftime("%Y-%m-%d %H:%M:%S")

    save_json(DATA_FILE, data)

    return jsonify({"status": "reset_complete"})


# ---------------------------
# ROUTE: GET AVAILABLE USERS
# ---------------------------
@app.route("/getavailable", methods=["GET"])
def get_available():
    data = ensure_structure(load_json(DATA_FILE))
    users = load_users()

    arrived_set = set(data["arrived_ids"])

    available = [
        {"id": u["id"], "name": u["name"]} for u in users if u["id"] not in arrived_set
    ]

    return jsonify({"available_count": len(available), "users": available})


# ---------------------------
# ROUTE: HOME
# ---------------------------
@app.route("/")
def home():
    data = ensure_structure(load_json(DATA_FILE))
    users = load_users()

    data["total_participants"] = len(users)

    save_json(DATA_FILE, data)

    return jsonify(data)


@app.route("/checkalive", methods=["GET"])
def check_alive():
    return "OKBABOU", 200


@app.route("/viewarrived", methods=["GET"])
def view_arrived():
    data = ensure_structure(load_json(DATA_FILE))
    users = load_users()

    arrived_set = set(data["arrived_ids"])

    arrived_users = [
        {"id": u["id"], "name": u["name"]} for u in users if u["id"] in arrived_set
    ]

    return jsonify(
        {
            "available_count": len(arrived_users),  # same key name as requested
            "users": arrived_users,
        }
    )


@app.route("/arrivedName/<string:name>", methods=["GET"])
def arrived_name(name):
    data = ensure_structure(load_json(DATA_FILE))
    users = load_users()

    data["total_participants"] = len(users)

    # Find user by exact name (case-sensitive)
    user = next((u for u in users if u["name"] == name), None)
    if not user:
        return jsonify({"error": "User not found"}), 404

    # Prevent double arrival
    if user["id"] in data["arrived_ids"]:
        return jsonify({"status": "already_arrived", "user": user["name"]}), 400

    now = datetime.now()
    arrival_entry = {
        "id": user["id"],
        "name": user["name"],
        "timestamp": now.isoformat(),
        "formatted_time": now.strftime("%H:%M:%S"),
    }

    # Track arrival
    data["arrived_ids"].append(user["id"])
    data["last_5_arrived"].append(arrival_entry)
    data["last_5_arrived"] = data["last_5_arrived"][-5:]

    data["total_arrived"] = len(data["arrived_ids"])
    data["total_events"] = int(data.get("total_events", 0)) + 1

    data["timestamp"] = now.isoformat()
    data["last_updated"] = now.strftime("%Y-%m-%d %H:%M:%S")

    save_json(DATA_FILE, data)

    return jsonify(
        {
            "status": "success",
            "user": user["name"],
            "time": arrival_entry["formatted_time"],
        }
    )


# ---------------------------
# INIT
# ---------------------------
if not os.path.exists(DATA_FILE):
    save_json(DATA_FILE, default_data())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
