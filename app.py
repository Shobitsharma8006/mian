import os
import json
import base64
import datetime
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# ─── CONFIGURATION ─────────────────────────────────────────────────────────────
CONFIG = {
    "AZURE_DEVOPS_PAT": "D5nB4HR81sJDpwDglNmd7qgpVlKxmFRNVRB1odqN9yzpYbJ3n6K6JQQJ99BEACAAAAAB0o46AAASAZDO35Wy",
    "ORGANIZATION": "amrit0258",
    "PROJECT": "Switchblade",
    "REPO": "Unbuilt_Apps",
    "API_VERSION": "7.1",
    "BASE_URL": "https://dev.azure.com/{ORGANIZATION}/{PROJECT}/_apis/git/repositories/{REPO}"
}

qlik_server = "https://nhbmsqcubd4gp2k.in.qlikcloud.com"
api_key = "eyJhbGciOiJFUzM4NCIsImtpZCI6IjNhOWRhNzE5LTUxM2MtNGJiZC1hYTc0LTMxOGNiYTJhZjhhZSIsInR5cCI6IkpXVCJ9.eyJzdWJUeXBlIjoidXNlciIsInRlbmFudElkIjoiUG5aZlNFOW5LUlJleXFhZl96R3M5VEtacUVJRkVzd0MiLCJqdGkiOiIzYTlkYTcxOS01MTNjLTRiYmQtYWE3NC0zMThjYmEyYWY4YWUiLCJhdWQiOiJxbGlrLmFwaSIsImlzcyI6InFsaWsuYXBpL2FwaS1rZXlzIiwic3ViIjoiNjc5NzA3ZTNmZGM0ZTE3MjBmZTM1NzAyIn0.-D9r96Q3M1hFnpKoC_0f9S8dLyS3OGOvfdIA4GdMqph68sjJqihLChNQLCxoBiwJGLViR1WUiihP1lQm128VrZTcT7K0GgZPBv6AhQGxixR-XN3n83-MyrN6fEPe8SJ9"

# ─── AUTH HEADERS ──────────────────────────────────────────────────────────────
PAT_ENCODED = base64.b64encode(f":{CONFIG['AZURE_DEVOPS_PAT']}".encode()).decode("ascii")
AZURE_HEADERS = {
    "Authorization": f"Basic {PAT_ENCODED}",
    "Content-Type": "application/json"
}
QLIK_HEADERS = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}


@app.route("/getApps", methods=["GET"])
def get_apps():
    try:
        resp = requests.get(f"{qlik_server}/api/v1/apps", headers=QLIK_HEADERS)
        resp.raise_for_status()
        apps = [
            {"id": a["attributes"]["id"], "name": a["attributes"]["name"]}
            for a in resp.json().get("data", [])
        ]
        return jsonify(apps)
    except Exception as e:
        print("[ERROR] get_apps:", e)
        return "Failed to fetch apps", 500


@app.route("/unbuildApp", methods=["POST"])
def unbuild_app():
    try:
        data = request.get_json()
        app_id = data.get("appId")
        app_name = data.get("appName")

        if not app_id or not app_name:
            return "Missing appId or appName", 400

        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c if c.isalnum() or c in (' ', '_', '-') else '_' for c in app_name).strip().replace(" ", "_")
        folder_name = f"{safe_name}_{ts}"
        output_root = "unbuild_output"
        output_folder = os.path.join(output_root, folder_name)
        os.makedirs(output_folder, exist_ok=True)

        cmd = (
            f'qlik app unbuild --app "{app_id}" '
            f'--dir "{output_folder}" '
            f'--headers Authorization="Bearer {api_key}" --verbose'
        )
        print("→ Running:", cmd)
        os.system(cmd)

        if not any(os.scandir(output_folder)):
            return "No files found after unbuild", 400

        repo_url = CONFIG["BASE_URL"].format(**CONFIG)
        ref_url = f"{repo_url}/refs?filter=heads/main&api-version={CONFIG['API_VERSION']}"
        commit_id = requests.get(ref_url, headers=AZURE_HEADERS).json()["value"][0]["objectId"]

        changes = []
        for root, _, files in os.walk(output_folder):
            for fn in files:
                fpath = os.path.join(root, fn)
                with open(fpath, "rb") as fh:
                    b64 = base64.b64encode(fh.read()).decode()
                rel = os.path.relpath(fpath, output_folder).replace("\\", "/")
                changes.append({
                    "changeType": "add",
                    "item": {"path": f"/{folder_name}/{rel}"},
                    "newContent": {"content": b64, "contentType": "base64encoded"}
                })

        if not changes:
            return "No files to commit", 400

        push_url = f"{repo_url}/pushes?api-version={CONFIG['API_VERSION']}"
        push_body = {
            "refUpdates": [{"name": "refs/heads/main", "oldObjectId": commit_id}],
            "commits": [{
                "comment": f"Unbuilt app {app_id} → {folder_name}",
                "changes": changes
            }]
        }

        presp = requests.post(push_url, headers=AZURE_HEADERS, json=push_body)
        if presp.status_code == 201:
            return "Success", 200
        else:
            print("[ERROR] Azure push:", presp.status_code, presp.text)
            return "Push failed", 500

    except Exception as e:
        print("[ERROR] unbuild_app:", e)
        return "Server error", 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 9008)), debug=True)

