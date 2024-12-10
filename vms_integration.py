
from flask import Flask, request, jsonify
import requests
import base64
from datetime import datetime
import configparser

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        process_webhook_data(data)
        return jsonify({'status': 'success'})
    except Exception as e:
        app.logger.error(f"Webhook processing failed: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/analytics-alert', methods=['POST'])
def analytics_alert():
    try:
        data = request.get_json()
        
        # Extract necessary data or provide default values
        ip = data.get("IP", "192.168.1.13")
        channel_no = data.get("ChannelNo", "1")
        datetime_str = data.get("DateTime", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        error_code = data.get("ErrorCode", "multiple_person")
        remarks = data.get("Remarks", "Detailed Description")
        image = data.get("Image", "")  # Expect Base64 image
        image_name = data.get("ImageName", "Image_Name")

        payload = {
            "IP": ip,
            "ChannelNo": channel_no,
            "DateTime": datetime_str,
            "ErrorCode": error_code,
            "Remarks": remarks,
            "Image": image,
            "ImageName": image_name
        }

        # API URL from the config
        config = configparser.ConfigParser()
        config.read('Config.ini')
        api_url = config.get('API', 'analytics_base_url')

        # Make POST request
        response = requests.post(api_url, json=payload, verify=False)  # verify=False to skip SSL certs

        if response.status_code == 200:
            return jsonify({"status": "OK"})
        else:
            return jsonify({"status": "fail", "message": response.text}), response.status_code
    except Exception as e:
        app.logger.error(f"Error in analytics alert: {str(e)}")
        return jsonify({"status": "error", "message": str(e)})

def download_and_encode_image(image_url):
    try:
        response = requests.get(image_url)
        response.raise_for_status()
        image_binary = response.content
        image_base64 = base64.b64encode(image_binary).decode('utf-8')
        return image_base64
    except requests.RequestException as e:
        app.logger.error(f"Failed to download image from {image_url}. Error: {str(e)}")
        return None

def process_webhook_data(data):
    try:
        config = configparser.ConfigParser()
        config.read('Config.ini')
        base_url = config.get('API', 'base_url')

        if isinstance(data, list) and len(data) > 0:
            for data_item in data:
                event_name = "Face_Detected_Event"
                device_id = 2

                matched_card = data_item.get("matched_card") if data_item else None
                camera = data_item.get("camera") if data_item else None

                person_name = matched_card.get("name", "") if matched_card else ""
                snapshot_url = data_item.get("thumbnail", "") if data_item else ""

                snapshot_base64 = download_and_encode_image(snapshot_url) if snapshot_url else None
                camera_name = camera.get("name", "") if camera else ""
                event_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                payload = {
                    "EventName": event_name,
                    "DeviceID": device_id,
                    "SnapshotURL": snapshot_url,
                    "PersonName": person_name,
                    "CameraName": camera_name,
                    "EventTime": event_time,
                    "SnapshotBase64": snapshot_base64
                }

                post_api_url = f"{base_url}?Event={camera_name}"
                response = requests.post(post_api_url, json=payload)

                if snapshot_base64 is None:
                    app.logger.warning("Failed to encode the snapshot to base64.")

                if response.status_code == 200:
                    app.logger.info("Data has been sent successfully.")
                else:
                    app.logger.error(f"Failed to send data. Response status code: {response.status_code} - {response.text}")
        else:
            app.logger.warning("Invalid data format received. Expected a list with at least one item.")
    except Exception as e:
        app.logger.error(f"Error processing webhook data: {str(e)}")

if __name__ == '__main__':
    app.run(port=5000)
