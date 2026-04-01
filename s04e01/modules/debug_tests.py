import os
import requests

OKO_URL = os.environ.get("OKO_URL", "https://oko.ag3nts.org").rstrip("/")
LOGIN = os.environ.get("LOGIN")
PASSWORD = os.environ.get("PASSWORD")
AI_DEVS_SECRET = os.environ.get("AI_DEVS_SECRET")

print("LOGIN:", LOGIN)
print("PASSWORD:", PASSWORD)
print("SECRET:", AI_DEVS_SECRET)
print("LOGIN URL:", f"{OKO_URL}/")

headers = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/146.0.0.0 Mobile Safari/537.36",
    "Referer": f"{OKO_URL}/",
    "Origin": OKO_URL,
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
              "image/avif,image/webp,image/apng,*/*;q=0.8,"
              "application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
    "Upgrade-Insecure-Requests": "1",
}

data = {
    "action": "login",
    "login": LOGIN,
    "password": PASSWORD,
    "access_key": AI_DEVS_SECRET,
}

print("HEADERS:")
for k, v in headers.items():
    print(f"  {k}: {v}")

print("DATA:", data)

s = requests.Session()
resp = s.post(f"{OKO_URL}/", data=data, headers=headers, allow_redirects=False)

print("status:", resp.status_code)
print("location:", resp.headers.get("Location"))
print("set-cookie:", resp.headers.get("Set-Cookie"))
print("login-form in body:", "login-form" in resp.text)
print("response url:", resp.url)
print("response snippet:", resp.text[:500])
print("session cookies:", s.cookies.get_dict())