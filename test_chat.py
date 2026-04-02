import requests

while True:
    msg = input("You: ")

    res = requests.post(
        "http://127.0.0.1:5000/chat",
        json={"message": msg}
    )

    print("Assistant:", res.json()["reply"])
    print("Mistakes:", res.json()["mistakes"])


