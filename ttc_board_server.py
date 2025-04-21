# ttc_board_server.py
from flask import Flask, jsonify, render_template
from google.transit import gtfs_realtime_pb2
import requests
import datetime
import os

app = Flask(__name__, template_folder="templates")

STOP_IDS = ["15462", "6604"]  # List of TTC stop IDs
GTFS_RT_URL = "https://bustime.ttc.ca/gtfsrt/trips"

@app.route("/api/departures")
def get_departures():
    feed = gtfs_realtime_pb2.FeedMessage()
    response = requests.get(GTFS_RT_URL)
    feed.ParseFromString(response.content)

    departures = []
    now = datetime.datetime.now()

    for entity in feed.entity:
        if entity.HasField("trip_update"):
            for stop_time_update in entity.trip_update.stop_time_update:
                if stop_time_update.stop_id in STOP_IDS:
                    if stop_time_update.HasField("departure"):
                        dep_time = datetime.datetime.fromtimestamp(stop_time_update.departure.time)
                        minutes = int((dep_time - now).total_seconds() / 60)
                        if minutes >= 0:
                            departures.append({
                                "route": entity.trip_update.trip.route_id,
                                "stop_id": stop_time_update.stop_id,
                                "departure_time": dep_time.strftime("%H:%M"),
                                "minutes": minutes
                            })

    departures.sort(key=lambda x: x["minutes"])
    return jsonify(departures)

@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    os.makedirs("templates", exist_ok=True)
    with open("templates/index.html", "w") as f:
        f.write("""
<!DOCTYPE html>
<html>
<head>
    <title>TTC Departure Board</title>
    <meta http-equiv="refresh" content="60">
    <style>
        body { font-family: sans-serif; background: #111; color: #fff; text-align: center; padding-top: 2em; }
        h1 { font-size: 2em; }
        table { margin: 2em auto; border-collapse: collapse; width: 90%; }
        th, td { padding: 1em; border-bottom: 1px solid #444; }
        th { background: #222; }
        tr:nth-child(even) { background: #1a1a1a; }
    </style>
</head>
<body>
    <h1>Next TTC Departures</h1>
    <table>
        <thead>
            <tr><th>Stop</th><th>Route</th><th>Departure Time</th><th>In</th></tr>
        </thead>
        <tbody id="departures"></tbody>
    </table>

    <script>
        async function loadDepartures() {
            const res = await fetch("/api/departures");
            const data = await res.json();
            const tbody = document.getElementById("departures");
            tbody.innerHTML = "";
            data.forEach(dep => {
                const row = `<tr><td>${dep.stop_id}</td><td>${dep.route}</td><td>${dep.departure_time}</td><td>${dep.minutes} min</td></tr>`;
                tbody.innerHTML += row;
            });
        }

        loadDepartures();
        setInterval(loadDepartures, 60000);
    </script>
</body>
</html>
""")

    app.run(host="0.0.0.0", port=5000, debug=True)