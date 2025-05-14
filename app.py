import os
import json
import base64
from dotenv import load_dotenv
import datetime
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)
load_dotenv()
# ─── CONFIGURATION ─────────────────────────────────────────────────────────────
CONFIG = {
    "AZURE_DEVOPS_PAT": os.getenv("AZURE_DEVOPS_PAT"),
    "ORGANIZATION": os.getenv("ORGANIZATION"),
    "PROJECT": os.getenv("PROJECT"),
    "REPO": os.getenv("REPO"),
    "API_VERSION": os.getenv("API_VERSION", "7.1"),  # Default value if not set
    "BASE_URL": os.getenv("BASE_URL", "https://dev.azure.com/{ORGANIZATION}/{PROJECT}/_apis/git/repositories/{REPO}")
}

qlik_server = os.getenv("QLIK_SERVER")  # Default Qlik server if not set
api_key = os.getenv("QLIK_API_KEY")

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
             f'--server "{qlik_server}" '
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
            return jsonify({
                "appName": app_name,
                "folderName": folder_name,
                "message": f"App unbuilt and pushed to Azure DevOps successfully in folder: {folder_name}"
            }), 200
        else:
            print("[ERROR] Azure push:", presp.status_code, presp.text)
            return "Push failed", 500

    except Exception as e:
        print("[ERROR] unbuild_app:", e)
        return "Server error", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9008, debug=True)
