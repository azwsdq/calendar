import requests
from webpush import WebPush, WebPushSubscription
from pathlib import Path

wp = WebPush(
    private_key=Path("./private_key.pem"),
    public_key=Path("./public_key.pem"), 
    subscriber="mailto:jon37047@gmail.com"
)

# example subscription info
subscription = WebPushSubscription.model_validate({
    "endpoint": "https://fcm.googleapis.com/fcm/send/...",
    "keys": {
        "auth": "...",
        "p256dh": "..."
    }
})

message = wp.get(message='Hello, world!', subscription=subscription)

requests.post(subscription.endpoint, data=message.encrypted, headers=message.headers)
