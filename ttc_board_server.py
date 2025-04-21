# ttc_board_server.py
from flask import Flask, jsonify, render_template
import requests
import datetime
import os
import xml.etree.ElementTree as ET

app = Flask(__name__, template_folder="templates")

STOP_IDS = ["15462", "6604"]
NEXTBUS_URL_TEMPLATE = "https://webservices.nextbus.com/service/publicXMLFeed?command=predictions&a=ttc&stopId={stop_id}"

@app.route("/api/departures")
def get_departures():
    departures_by_stop = {"15462": [], "6604": []}
    now = datetime.datetime.now()

    for stop_id in STOP_IDS:
        url = NEXTBUS_URL_TEMPLATE.format(stop_id=stop_id)
        try:
            response = requests.get(url)
            root = ET.fromstring(response.content)

            for preds in root.findall("predictions"):
                stop_title = preds.attrib.get("stopTitle", stop_id)
                route_title = preds.attrib.get("routeTitle", "Unknown")

                for direction in preds.findall("direction"):
                    for p in direction.findall("prediction"):
                        minutes = int(p.attrib.get("minutes", "-1"))
                        epoch_time = int(p.attrib.get("epochTime", "0"))
                        dep_time = datetime.datetime.fromtimestamp(epoch_time / 1000)

                        departures_by_stop[stop_id].append({
                            "stop_id": stop_id,
                            "stop_name": stop_title,
                            "route": route_title,
                            "departure_time": dep_time.strftime("%H:%M"),
                            "minutes": minutes
                        })
        except Exception as e:
            print(f"Error fetching predictions for stop {stop_id}: {e}")

    for stop_list in departures_by_stop.values():
        stop_list.sort(key=lambda x: x["minutes"])

    return jsonify(departures_by_stop)

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
    <title>TTC Board</title>
    <meta http-equiv=\"refresh\" content=\"60\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
    <style>
        html, body {
            margin: 0;
            padding: 0;
            height: 100%;
            font-family: Verdana, sans-serif;
            background-color: #000;
            color: #fff;
        }
        body {
            display: flex;
            flex-direction: column;
        }
        .header {
            background-color: #cc0000;
            padding: 1em 2em;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-shrink: 0;
        }
        .header-left {
            display: flex;
            align-items: center;
        }
        .header-left img {
            height: 2.2em;
            margin-right: 1em;
        }
        .header-left .title {
            font-size: 2em;
            font-weight: bold;
        }
        .header-left .subtitle {
            font-size: 1em;
        }
        .clock {
            font-size: 2em;
            font-weight: bold;
        }
        .content {
            flex: 1;
            display: flex;
            flex-direction: column;
            justify-content: center;
            padding: 1em;
        }
        .stop-section {
            margin-bottom: 3em;
        }
        .stop-title {
            font-size: 2.5em;
            font-weight: bold;
            margin-bottom: 1em;
        }
        .departure-row {
            display: flex;
            gap: 1em;
        }
        .departure-box {
            flex: 1;
            background-color: #222;
            border-radius: 1em;
            padding: 1em;
            text-align: center;
            min-width: 5em;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            height: 7em;
        }
        .departure-box.empty {
            background-color: transparent;
        }
        .departure-box .large {
            font-size: 3.5em;
            font-weight: bold;
        }
        .departure-box .small {
            font-size: 1.8em;
            margin-top: 0.5em;
        }
        .soon {
            background-color: #cc0000 !important;
        }
        .moderate {
            background-color: #003300 !important;
        }
    </style>
</head>
<body>
    <div class=\"header\">
        <div class=\"header-left\">
            <img src=\"https://upload.wikimedia.org/wikipedia/commons/e/e3/Logo_of_the_Toronto_Transit_Commission.svg\" alt=\"TTC Logo\">
            <div>
                <div class=\"title\">Next Departures</div>
                <div class=\"subtitle\" id=\"last-updated\">Updated just now</div>
            </div>
        </div>
        <div class=\"clock\" id=\"current-time\"></div>
    </div>
    <div class=\"content\" id=\"content\"></div>

    <script>
        let lastUpdated = Date.now();

        function updateTimestamp() {
            const subtitle = document.getElementById("last-updated");
            const diff = Math.floor((Date.now() - lastUpdated) / 60000);
            subtitle.textContent = diff === 0 ? "Updated just now" : "Updated " + diff + " minute" + (diff > 1 ? "s" : "") + " ago";
        }

        function updateClock() {
            const clock = document.getElementById("current-time");
            const now = new Date();
            const hours = now.getHours().toString().padStart(2, '0');
            const minutes = now.getMinutes().toString().padStart(2, '0');
            const seconds = now.getSeconds().toString().padStart(2, '0');
            clock.textContent = `${hours}:${minutes}:${seconds}`;
        }

        async function loadDepartures() {
            const res = await fetch("/api/departures");
            const data = await res.json();
            const content = document.getElementById("content");
            content.innerHTML = "";

            const stopConfigs = {
                "15462": "504A King - To Dundas West Station",
                "6604": "121 Esplanade-River - To Union Station"
            };

            for (const stopId of ["15462", "6604"]) {
                const stopDiv = document.createElement("div");
                stopDiv.className = "stop-section";
                const title = document.createElement("div");
                title.className = "stop-title";
                title.textContent = stopConfigs[stopId];

                const departures = data[stopId].slice(0, 3);
                const row = document.createElement("div");
                row.className = "departure-row";

                for (let i = 0; i < 3; i++) {
                    let box = document.createElement("div");
                    if (departures[i]) {
                        const dep = departures[i];
                        const cls = dep.minutes < 5 ? "soon" : dep.minutes <= 10 ? "moderate" : "";
                        box.className = `departure-box ${cls}`;
                        box.innerHTML = `<div class='large'>${dep.minutes} min</div><div class='small'>${dep.departure_time}</div>`;
                    } else {
                        box.className = "departure-box empty";
                    }
                    row.appendChild(box);
                }

                stopDiv.appendChild(title);
                stopDiv.appendChild(row);
                content.appendChild(stopDiv);
            }

            lastUpdated = Date.now();
            updateTimestamp();
        }

        loadDepartures();
        updateClock();
        setInterval(loadDepartures, 60000);
        setInterval(updateTimestamp, 10000);
        setInterval(updateClock, 1000);
    </script>
</body>
</html>
""")

    app.run(host="0.0.0.0", port=5050, debug=True)
