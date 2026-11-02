import time, base64, hashlib, hmac, urllib.parse, requests

api_key = "47TGymi96D/03m60TQxccN4qJ0mIyBg+AhraZRBxqWS6eNldAgRCf14S"
api_secret = "xIVDf6LW8D6tAqOmGN24lsLoFpK7nAaJa7X6podFhD1/+jzOAOfgRXTGKEqfy5Ct2fDxGfXvhwz4jo+kFpt6Rw=="

def kraken_request(url_path, data):
    nonce = str(int(time.time() * 1000))
    data["nonce"] = nonce
    postdata = urllib.parse.urlencode(data)
    encoded = (nonce + postdata).encode()
    message = url_path.encode() + hashlib.sha256(encoded).digest()
    mac = hmac.new(base64.b64decode(api_secret), message, hashlib.sha512)
    sig = base64.b64encode(mac.digest()).decode()
    return requests.post(
        "https://api.kraken.com" + url_path,
        headers={"API-Key": api_key, "API-Sign": sig},
        data=data
    ).json()

print(kraken_request("/0/private/Balance", {}))
print(kraken_request("/0/private/GetApiKeyInfo", {}))

