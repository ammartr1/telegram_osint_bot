import aiohttp
import requests
from bs4 import BeautifulSoup
import phonenumbers
from phonenumbers import carrier, geocoder, timezone
import exifread
from PIL import Image
import hashlib
import re
from email_validator import validate_email, EmailNotValidError
from sherlock_project import SherlockDetect
from maigret import maigret

class OSINTEngine:
    
    @staticmethod
    async def instagram_scrape(username):
        try:
            url = f"https://www.instagram.com/{username}/?__a=1&__d=1"
            headers = {"User-Agent": "Mozilla/5.0"}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        user = data.get('graphql', {}).get('user', {})
                        return {
                            "full_name": user.get('full_name'),
                            "bio": user.get('biography'),
                            "followers": user.get('edge_followed_by', {}).get('count'),
                            "following": user.get('edge_follow', {}).get('count'),
                            "is_private": user.get('is_private'),
                            "email": re.search(r'[\w\.-]+@[\w\.-]+\.\w+', user.get('biography', '')),
                            "phone": re.search(r'(\+?\d{10,15})', user.get('biography', ''))
                        }
            return {"error": "private or not found"}
        except:
            return {"error": "failed"}

    @staticmethod
    async def phone_lookup(phone):
        try:
            parsed = phonenumbers.parse(phone, None)
            return {
                "valid": phonenumbers.is_valid_number(parsed),
                "country": geocoder.description_for_number(parsed, "en"),
                "carrier": carrier.name_for_number(parsed, "en"),
                "timezones": timezone.time_zones_for_number(parsed)
            }
        except:
            return {"error": "invalid number"}

    @staticmethod
    async def email_breach_check(email):
        try:
            validate_email(email)
            h = hashlib.sha1(email.encode()).hexdigest().upper()
            url = f"https://api.pwnedpasswords.com/range/{h[:5]}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.text()
                        return {"breached": h[5:] in data, "platforms": ["HaveIBeenPwned check passed"]}
            return {"error": "breach check failed"}
        except EmailNotValidError:
            return {"error": "invalid email"}

    @staticmethod
    async def username_search(username):
        results = await SherlockDetect().check_username(username)
        active = [site for site, data in results.items() if data.get("status", {}).get("status") == "claimed"]
        return {"total_sites": len(active), "active_accounts": active[:20]}

    @staticmethod
    async def ip_geo(ip):
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://ip-api.com/json/{ip}") as resp:
                data = await resp.json()
                return {
                    "country": data.get("country"),
                    "city": data.get("city"),
                    "lat": data.get("lat"),
                    "lon": data.get("lon"),
                    "isp": data.get("isp"),
                    "proxy": data.get("proxy"),
                    "vpn": data.get("vpn")
                }

    @staticmethod
    async def photo_exif(image_bytes):
        try:
            tags = exifread.process_file(image_bytes, details=False)
            return {
                "make": str(tags.get("Image Make", "")),
                "model": str(tags.get("Image Model", "")),
                "datetime": str(tags.get("EXIF DateTimeOriginal", "")),
                "gps_lat": str(tags.get("GPS GPSLatitude", "")),
                "gps_lon": str(tags.get("GPS GPSLongitude", ""))
            }
        except:
            return {"error": "no EXIF data"}

    @staticmethod
    async def reverse_image_search(image_url):
        # Google reverse image simulation (free)
        return {"note": "use Google Images manually", "engines": ["Google", "Yandex", "Bing"]}
