import keys
import json, jwt, base64, datetime, re, http.client, ssl, gzip, asyncio, gc, sys, os, time, threading, queue
from io import BytesIO
from protobuf_decoder.protobuf_decoder import Parser
from CDX import *
from datetime import datetime, timedelta
from google.protobuf.timestamp_pb2 import Timestamp
from rich.console import Console
from rich.panel import Panel
from rich.align import Align
from cfonts import render, say
import urllib3
import hashlib
import hmac
import string
import random
import uuid
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from google_play_scraper import app as play_store_app

from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs

RCD = 0.1
RDT = 0.1
console = Console()
lock = threading.Lock()
ab = 0
bs = threading.Semaphore(5000)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
lrt = time.time()

ReS = 600


# ============================================================
#  AUTO UPDATE SYSTEM (NO HARDCODED FALLBACK)
# ============================================================
def AuToUpDaTE():
    """
    Play Store theke latest version niye, ggwhitehawk API theke OB ber kore.
    Returns: (server_url, ob_version, client_version)
    """
    try:
        data = play_store_app('com.dts.freefireth', lang="en", country='US')
        store_version = data.get("version")

        if not store_version:
            print("[!] Play Store version not found")
            return None, None, None

        api_url = f"https://version.ggwhitehawk.com/live/ver.php?version={store_version}&lang=fr&device=android&channel=android"
        r = requests.get(api_url, timeout=15)
        json_data = r.json()

        server_url = json_data.get('server_url')
        ob_version = json_data.get('latest_release_version')
        remote_version = json_data.get('remote_version')

        return server_url, ob_version, remote_version

    except Exception as e:
        print(f"[!] Auto-update failed: {e}")
        return None, None, None


# ============================================================
#  GLOBAL VERSION STATE
# ============================================================
obve = None
_current_version = None
version_ready = threading.Event()


def fetch_until_success():
    global obve, _current_version
    attempt = 0
    while True:
        attempt += 1
        url, ob, remote = AuToUpDaTE()
        if ob and remote:
            obve = ob
            _current_version = remote
            version_ready.set()
            console.print(f"[green]✅ Auto-update: Client Version = {remote}, OB = {ob}[/green]")
            return True
        console.print(f"[yellow]⚠️ Version fetch failed (attempt {attempt}), retrying in 5s...[/yellow]")
        time.sleep(5)


def version_refresher():
    global obve, _current_version
    while True:
        time.sleep(1800)
        try:
            url, ob, remote = AuToUpDaTE()
            if ob and remote:
                with lock:
                    if obve != ob or _current_version != remote:
                        console.print(f"[yellow]🔄 Auto-updated: {obve} → {ob} | {_current_version} → {remote}[/yellow]")
                        obve = ob
                        _current_version = remote
        except Exception:
            pass


# ============================================================
#  INITIAL VERSION FETCH
# ============================================================
fetch_until_success()

rf = False

RAF = {
    "BD": "BD.txt"
}

online_count = 0
total_accounts = 0
active_accounts = []
html_server_running = False
restart_lock = threading.Lock()


# ============================================================
#  ghost_packet (sync version)
# ============================================================
def ghost_packet(player_id, nm, secret_code, key, iv):
    fields = {
        1: 61,
        2: {
            1: int(player_id),
            2: {
                1: int(player_id),
                2: 1159,
                3: f"[b][c][{ArA_CoLor()}]{nm}",
                5: 12,
                6: 9999999,
                7: 1,
                8: {
                    2: 1,
                    3: 1,
                },
                9: 3,
            },
            3: secret_code,
        },
    }

    try:
        proto_data = CrEaTe_ProTo(fields)
        if hasattr(proto_data, '__await__'):
            loop = asyncio.new_event_loop()
            proto_data = loop.run_until_complete(proto_data)
            loop.close()
    except Exception:
        proto_data = _build_ghost_proto(fields)

    try:
        packet = GeneRaTePk(proto_data.hex(), "0515", key, iv)
        if hasattr(packet, '__await__'):
            loop = asyncio.new_event_loop()
            packet = loop.run_until_complete(packet)
            loop.close()
        return packet
    except Exception:
        return _build_ghost_packet(proto_data, key, iv)


def _build_ghost_proto(fields):
    def encode_varint(n):
        out = []
        while True:
            b = n & 0x7F
            n >>= 7
            if n:
                b |= 0x80
            out.append(b)
            if not n:
                break
        return bytes(out)

    def encode_field(k, v):
        if isinstance(v, int):
            return encode_varint((k << 3) | 0) + encode_varint(v)
        if isinstance(v, str):
            v = v.encode()
        if isinstance(v, bytes):
            return encode_varint((k << 3) | 2) + encode_varint(len(v)) + v
        if isinstance(v, dict):
            inner = b"".join(encode_field(kk, vv) for kk, vv in v.items())
            return encode_varint((k << 3) | 2) + encode_varint(len(inner)) + inner
        return b""

    return b"".join(encode_field(k, v) for k, v in fields.items())


def _build_ghost_packet(proto_bytes, key, iv):
    try:
        hex_payload = EnC_PacKeT(proto_bytes.hex(), key, iv)
        if isinstance(hex_payload, str):
            return bytes.fromhex("0515" + hex_payload)
        return b""
    except Exception:
        return b""


def ev(num):
    if num < 0:
        raise ValueError("Number must be non-negative")
    out = []
    while True:
        b = num & 0x7F
        num >>= 7
        if num:
            b |= 0x80
        out.append(b)
        if not num:
            break
    return bytes(out)


def cf(num, val):
    if isinstance(val, int):
        return ev((num << 3) | 0) + ev(val)
    if isinstance(val, (str, bytes)):
        v = val.encode() if isinstance(val, str) else val
        return ev((num << 3) | 2) + ev(len(v)) + v
    if isinstance(val, dict):
        nested = cp(val)
        return ev((num << 3) | 2) + ev(len(nested)) + nested
    return b""


def cp(fields):
    return b"".join(cf(k, v) for k, v in fields.items())


def ea(plain_text):
    plain_text = bytes.fromhex(plain_text)
    key = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
    iv = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])
    cipher = AES.new(key, AES.MODE_CBC, iv)
    cipher_text = cipher.encrypt(pad(plain_text, AES.block_size))
    return cipher_text.hex()


def ERML(open_id, access_token, version=None):
    if version is None:
        version = _current_version

    if not version:
        version_ready.wait(timeout=60)
        version = _current_version

    if not version:
        print("[!] Version not ready, skipping ERML")
        return None

    timestamp = str(datetime.now())[:-7]
    unique_id = str(uuid.uuid4())

    payload_fields = {
        3: timestamp,
        4: 'free fire',
        7: version,
        8: 'Android OS 11 / API-30 (RP1A.200720.011/230921V810)',
        9: 'Handheld',
        10: 'MT6769V/CU',
        11: 'WIFI',
        12: 750,
        13: 1708,
        14: '480',
        15: 'INFINIX MOBILITY LIMITED Infinix X6812',
        16: 4096,
        17: 'Mali-G52 MC2',
        18: 'OpenGL ES 3.2 v1.r26p0-01eac0.f143e3f9482527bbad36b3ec27f93e59',
        19: f'Google|{unique_id}',
        20: "2019120828",
        21: 'en',
        22: open_id,
        23: '4',
        24: 'Handheld',
        25: 'Infinix X6812',
        29: access_token,
        30: 3,
        62: 64000,
        63: random.randint(15000, 35000),
        70: 2,
        73: 2,
        76: 1,
        77: 'WIFI',
        78: 2,
        79: 1,
        83: '2019120828',
        85: 0,
        86: 'OpenGLES2',
        87: 16383,
        88: 4,
        90: '00000',
        91: 'WIFI',
        92: random.randint(3000, 7000),
        93: 'android',
        94: 'FwQVTgUPX1UaUllDDwcWCRBpWAUOUgsvA1snWlBaO1kFYg==',
        97: 1,
        99: '4',
        100: '4',
    }

    proto_bytes = cp(payload_fields)
    encrypted = ea(proto_bytes.hex())
    return bytes.fromhex(encrypted)


def pr(parsed_results):
    result_dict = {}
    for result in parsed_results:
        field_data = {}
        field_data["wire_type"] = result.wire_type
        if result.wire_type == "varint":
            field_data["data"] = result.data
        if result.wire_type == "string":
            field_data["data"] = result.data
        if result.wire_type == "bytes":
            field_data["data"] = result.data
        elif result.wire_type == "length_delimited":
            field_data["data"] = pr(result.data.results)
        result_dict[result.field] = field_data
    return result_dict


def gar(input_text):
    try:
        parsed_results = Parser().parse(input_text)
        parsed_results_objects = parsed_results
        parsed_results_dict = pr(parsed_results_objects)
        json_data = json.dumps(parsed_results_dict)
        return json_data
    except Exception as e:
        return None


def GRA(uid, password, mt=2):
    url = "https://100067.connect.garena.com/api/v2/oauth/guest/token:grant"
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Content-Type": "application/json; charset=utf-8",
        "Host": "100067.connect.garena.com",
        "User-Agent": "GarenaMSDK/4.0.33 (iPhone11,8;ios - 17.0.2;en-MA;MA;app v1.126.1 2019120772)",
        "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8"
    }
    data = {
        "client_id": "100067",
        "client_secret": "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3",
        "client_type": 1,
        "password": password,
        "response_type": "token",
        "uid": int(uid),
        "source": 1
    }
    session = requests.Session()
    for attempt in range(1, mt + 1):
        try:
            response = session.post(url, headers=headers, json=data, timeout=5)
            if response.status_code != 200:
                if attempt < mt:
                    time.sleep(0.5)
                    continue
                return None, None
            response_data = response.json()
            if "data" in response_data:
                open_id = response_data["data"].get("open_id")
                access_token = response_data["data"].get("access_token")
            else:
                open_id = response_data.get("open_id")
                access_token = response_data.get("access_token")
            if open_id and access_token:
                return open_id, access_token
            if attempt < mt:
                time.sleep(0.5)
        except:
            if attempt < mt:
                time.sleep(0.5)
    return None, None


def ML(payload):
    rel = obve
    if not rel:
        version_ready.wait(timeout=60)
        rel = obve
    if not rel:
        print("[!] OB version not ready, skipping ML")
        return None

    try:
        headers = {
            'X-Unity-Version': '2022.3.47f1',
            'ReleaseVersion': rel,
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-GA': 'v1 1',
            'User-Agent': 'UnityPlayer/2022.3.47f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)',
            'Host': 'loginbp.ggpolarbear.com',
            'Connection': 'Keep-Alive',
            'Accept-Encoding': 'gzip'
        }
        url = "https://loginbp.ggpolarbear.com/MajorLogin"
        response = requests.post(url, data=payload, headers=headers, timeout=10, verify=False)
        raw_data = response.content
        if response.headers.get('Content-Encoding') == 'gzip':
            with gzip.GzipFile(fileobj=BytesIO(raw_data)) as f:
                raw_data = f.read()
        if response.status_code == 200:
            return raw_data.hex()
        return None
    except Exception as e:
        return None


class FC:
    def __init__(self, uid, password, region):
        self.uid = uid
        self.password = password
        self.region = region
        self.bot_uid = "Unknown"
        self.saved_data = None
        self.running = True
        self.target_found = False
        self.login_success = False
        self.ghost_sent = False
        self.message_sent = False

    def gki(self, serialized_data):
        my_message = keys.MyMessage()
        my_message.ParseFromString(serialized_data)
        timestamp = my_message.field21
        key = my_message.field22
        iv = my_message.field23
        timestamp_obj = Timestamp()
        timestamp_obj.FromNanoseconds(timestamp)
        timestamp_seconds = timestamp_obj.seconds
        timestamp_nanos = timestamp_obj.nanos
        combined_timestamp = timestamp_seconds * 1_000_000_000 + timestamp_nanos
        return combined_timestamp, key, iv

    def glp(self, jwt_token, encrypted_payload):
        rel = obve
        if not rel:
            version_ready.wait(timeout=60)
            rel = obve
        if not rel:
            print("[!] OB version not ready, skipping glp")
            return None, None, None, None

        url = f'https://clientbp.ggpolarbear.com/GetLoginData'
        headers = {
            'Expect': '100-continue',
            'Authorization': f'Bearer {jwt_token}',
            'X-Unity-Version': '2022.3.47f1',
            'X-GA': 'v1 1',
            'ReleaseVersion': rel,
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'UnityPlayer/2022.3.47f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)',
            'Host': 'clientbp.ggpolarbear.com',
            'Connection': 'close',
            'Accept-Encoding': 'gzip, deflate, br',
        }
        try:
            response = requests.post(url, headers=headers, data=encrypted_payload, timeout=10, verify=False)
            content = response.content
            data = json.loads(DeCode_PackEt(content.hex()))
            address = data['32']['data']
            address2 = data['14']['data']
            ip = address[:len(address) - 6]
            ip2 = address2[:len(address2) - 6]
            port = address[len(address) - 5:]
            port2 = address2[len(address2) - 5:]
            return ip, port, ip2, port2
        except Exception as e:
            return None, None, None, None

    def gt(self, uid, password):
        try:
            if not uid or not password:
                return None
            open_id, access_token = GRA(uid, password)
            if not access_token or not open_id:
                return None
            encrypted_payload = ERML(open_id, access_token)
            if not encrypted_payload:
                return None
            response = ML(encrypted_payload)
            if not response:
                return None
            decoded = DeCode_PackEt(response)
            decoded_data = json.loads(decoded)
            bot_uid = decoded_data['1']['data']
            jwt_token = decoded_data['8']['data']

            # ✅ JWT expiry check
            try:
                decoded_jwt = jwt.decode(jwt_token, options={"verify_signature": False})
                exp = decoded_jwt.get('exp')
                if exp and exp < time.time() + 30:
                    # Token expired or about to expire in 30s
                    return None
            except Exception:
                pass

            combined_timestamp, key, iv = self.gki(bytes.fromhex(response))
            ip, port, ip2, port2 = self.glp(jwt_token, encrypted_payload)
            if not ip or not ip2:
                return None
            return jwt_token, key, iv, combined_timestamp, ip, port, ip2, port2, bot_uid
        except Exception as e:
            return None

    def gft(self, uid, password):
        result = self.gt(uid, password)
        if result is None:
            return None
        token, key, iv, timestamp, ip, port, ip2, port2, bot_uid = result
        try:
            decoded_jwt = jwt.decode(token, options={"verify_signature": False})
            account_uid = decoded_jwt.get('account_id')
            encoded_account = hex(account_uid)[2:]
            hex_value = DecodE_HeX(timestamp)
            jwt_hex = token.encode().hex()
            length = len(encoded_account)
            padding_map = {7: '000000000', 8: '00000000', 9: '0000000', 10: '000000'}
            padding = padding_map.get(length, '00000000')
            packet_length = len(EnC_PacKeT(jwt_hex, key, iv)) // 2
            length_hex = hex(packet_length)[2:]
            header = f'0115{padding}{encoded_account}{hex_value}00000{length_hex}'
            final_token = header + EnC_PacKeT(jwt_hex, key, iv)
            return {
                'token': token,
                'auth': final_token,
                'ip': ip,
                'port': port,
                'ip2': ip2,
                'port2': port2,
                'key': key,
                'iv': iv,
                'bot_uid': bot_uid
            }
        except Exception as e:
            return None

    def cleanup(self):
        pass

    def start(self):
        global ab, rf, lrt, online_count, active_accounts

        with bs:
            with lock:
                ab += 1

            while not rf:
                try:
                    self.saved_data = self.gft(self.uid, self.password)
                    if not self.saved_data:
                        with lock:
                            console.print(f"[red]{self.uid} [{self.region}] AuTh fAiLeD - Retrying...[/red]")
                        time.sleep(3)
                        continue

                    auth = self.saved_data['auth']
                    ip = self.saved_data['ip']
                    port = self.saved_data['port']
                    ip2 = self.saved_data['ip2']
                    port2 = self.saved_data['port2']
                    key = self.saved_data['key']
                    iv = self.saved_data['iv']
                    self.bot_uid = self.saved_data['bot_uid']

                    with lock:
                        console.print(f"[green]SuCc Bot: {self.bot_uid} [{self.region}][/green]")
                        self.login_success = True
                        if not any(a['uid'] == self.uid for a in active_accounts):
                            online_count += 1
                            active_accounts.append({
                                'uid': self.uid,
                                'bot_uid': self.bot_uid,
                                'region': self.region,
                                'time': datetime.now().strftime('%H:%M:%S')
                            })

                    # ============================================================
                    #  AUTO SQUAD CREATE LOOP (No Global Join / No Detect)
                    # ============================================================
                    while self.running and not rf:
                        sock = None
                        sock2 = None
                        try:
                            # ---------- Connect to login server ----------
                            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            sock.settimeout(5.0)
                            sock.connect((ip, int(port)))
                            sock.send(bytes.fromhex(auth))
                            time.sleep(0.05)

                            # ---------- Connect to game server ----------
                            sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            sock2.settimeout(5.0)
                            sock2.connect((ip2, int(port2)))
                            sock2.send(bytes.fromhex(auth))
                            time.sleep(0.05)

                            # ---------- STEP 1: Open Squad (Auto Create) ----------
                            open_sq_packet = asyncio.run(OpEnSq(key, iv, self.region, _current_version))
                            sock2.send(open_sq_packet)
                            time.sleep(0.3)

                            with lock:
                                console.print(f"[cyan][{self.bot_uid}] [{self.region}] Squad Created ✅[/cyan]")

                            # ---------- STEP 2: Set Squad Size (cHSq22) ----------
                            try:
                                sq_size_packet = asyncio.run(cHSq22(4, self.bot_uid, key, iv, self.region))
                                sock2.send(sq_size_packet)
                                time.sleep(0.3)
                                with lock:
                                    console.print(f"[cyan][{self.bot_uid}] [{self.region}] Squad Size Set ✅[/cyan]")
                            except Exception as e:
                                with lock:
                                    console.print(f"[yellow][{self.bot_uid}] Squad size error: {e}[/yellow]")

                            # ---------- STEP 3: Send World Recruit Packet ----------
                            try:
                                recruit_packet = asyncio.run(
                                    MAHIR_World_Recruit_Packet(self.bot_uid, key, iv)
                                )
                                if recruit_packet:
                                    sock2.send(recruit_packet)
                                    time.sleep(0.3)
                                    with lock:
                                        console.print(f"[cyan][{self.bot_uid}] [{self.region}] World Recruit Sent 📢[/cyan]")
                            except Exception as e:
                                with lock:
                                    console.print(f"[yellow][{self.bot_uid}] Recruit error: {e}[/yellow]")

                            # ---------- STEP 4: Wait 15 seconds ----------
                            with lock:
                                console.print(f"[yellow][{self.bot_uid}] [{self.region}] Waiting 15s before cHSq...[/yellow]")

                            wait_start = time.time()
                            while time.time() - wait_start < 15:
                                if rf or not self.running:
                                    break
                                time.sleep(0.5)

                            # ---------- STEP 5: cHSq (Squad Settings before leave) ----------
                            try:
                                chsq_packet = asyncio.run(
                                    cHSq(4, self.bot_uid, key, iv, self.region)
                                )
                                sock2.send(chsq_packet)
                                time.sleep(2)
                                with lock:
                                    console.print(f"[cyan][{self.bot_uid}] [{self.region}] cHSq Sent ✅[/cyan]")
                            except Exception as e:
                                with lock:
                                    console.print(f"[yellow][{self.bot_uid}] cHSq error: {e}[/yellow]")

                            # ---------- STEP 6: Leave Squad ----------
                            try:
                                leave_packet = asyncio.run(
                                    leave_squad_packet(key, iv, self.region, self.bot_uid)
                                )
                                sock2.send(leave_packet)
                                time.sleep(0.3)
                                with lock:
                                    console.print(f"[magenta][{self.bot_uid}] [{self.region}] Left Squad 🚪[/magenta]")
                            except Exception as e:
                                with lock:
                                    console.print(f"[yellow][{self.bot_uid}] Leave error: {e}[/yellow]")

                            # ---------- STEP 7: Cooldown before next cycle ----------
                            for _ in range(20):  # 2 seconds
                                if rf or not self.running:
                                    break
                                time.sleep(0.1)

                            with lock:
                                console.print(f"[green][{self.bot_uid}] [{self.region}] Cycle Complete 🔄 Restarting...[/green]")

                        except Exception as e:
                            with lock:
                                console.print(f"[red][{self.bot_uid}] Cycle error: {e}[/red]")
                            time.sleep(2)
                        finally:
                            if sock:
                                try:
                                    sock.close()
                                except:
                                    pass
                            if sock2:
                                try:
                                    sock2.close()
                                except:
                                    pass

                        # Small delay before reconnect
                        for _ in range(10):
                            if rf:
                                break
                            time.sleep(0.1)

                    if rf:
                        break

                except Exception as e:
                    with lock:
                        console.print(f"[red]{self.uid} Error: {e} - Retrying in 3s[/red]")
                    time.sleep(3)
                    continue

            with lock:
                try:
                    ab -= 1
                    active_accounts[:] = [a for a in active_accounts if a['uid'] != self.uid]
                    if online_count > 0:
                        online_count -= 1
                except:
                    pass


def laf(file_path):
    accounts = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    parts = line.split(':')
                    if len(parts) >= 2:
                        uid = parts[0].strip()
                        password = ':'.join(parts[1:]).strip()
                        if uid and password:
                            accounts.append((uid, password))
    except:
        pass
    return accounts


def laa():
    all_accounts = []
    for region, file_path in RAF.items():
        accounts = laf(file_path)
        for uid, password in accounts:
            all_accounts.append((uid, password, region))
    random.shuffle(all_accounts)
    return all_accounts


def rb(uid, password, region):
    try:
        client = FC(uid, password, region)
        client.start()
    except Exception:
        pass


# ============ HTML SERVER ============
class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()

            global online_count, active_accounts, total_accounts

            try:
                with open('BD.txt', 'r', encoding='utf-8') as f:
                    bd_content = f.read()
            except:
                bd_content = ""

            accounts_html = ""
            for acc in active_accounts[-100:]:
                accounts_html += f"""
                <tr>
                    <td>{acc['bot_uid']}</td>
                    <td>{acc['uid']}</td>
                    <td>{acc['region']}</td>
                    <td>{acc['time']}</td>
                    <td style="color: #00ff00;">● ONLINE</td>
                </tr>
                """

            cur_ver = _current_version or "loading..."
            cur_rel = obve or "loading..."

            html = f"""
            <!DOCTYPE html>
            <html lang="bn">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>MAHIR BOT DASHBOARD</title>
                <style>
                    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        background: linear-gradient(135deg, #0a0a2e 0%, #1a1a4e 50%, #0a0a2e 100%);
                        color: #fff;
                        min-height: 100vh;
                        padding: 20px;
                    }}
                    .container {{ max-width: 1200px; margin: 0 auto; }}
                    .header {{
                        text-align: center;
                        padding: 30px;
                        background: linear-gradient(90deg, #ff0000, #ff6600, #ff0000);
                        border-radius: 15px;
                        margin-bottom: 30px;
                        box-shadow: 0 0 30px rgba(255, 0, 0, 0.5);
                    }}
                    .header h1 {{
                        font-size: 2.5em;
                        text-shadow: 0 0 20px #fff, 0 0 40px #ff6600;
                        letter-spacing: 3px;
                    }}
                    .header p {{ margin-top: 10px; font-size: 1.1em; opacity: 0.9; }}
                    .stats {{
                        display: grid;
                        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                        gap: 20px;
                        margin-bottom: 30px;
                    }}
                    .stat-card {{
                        background: rgba(255, 255, 255, 0.05);
                        border: 2px solid #ff6600;
                        border-radius: 15px;
                        padding: 25px;
                        text-align: center;
                        backdrop-filter: blur(10px);
                        transition: all 0.3s;
                    }}
                    .stat-card:hover {{
                        transform: translateY(-5px);
                        box-shadow: 0 0 30px rgba(255, 102, 0, 0.6);
                    }}
                    .stat-card h2 {{
                        font-size: 3em;
                        color: #00ff00;
                        text-shadow: 0 0 20px #00ff00;
                    }}
                    .stat-card p {{
                        margin-top: 10px;
                        font-size: 1.2em;
                        color: #ffcc00;
                    }}
                    .section {{
                        background: rgba(255, 255, 255, 0.05);
                        border: 2px solid #00ccff;
                        border-radius: 15px;
                        padding: 25px;
                        margin-bottom: 30px;
                        backdrop-filter: blur(10px);
                    }}
                    .section h2 {{
                        color: #00ccff;
                        margin-bottom: 20px;
                        text-shadow: 0 0 10px #00ccff;
                        font-size: 1.5em;
                    }}
                    table {{
                        width: 100%;
                        border-collapse: collapse;
                        margin-top: 15px;
                    }}
                    th, td {{
                        padding: 12px;
                        text-align: left;
                        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                    }}
                    th {{
                        background: rgba(255, 102, 0, 0.3);
                        color: #ffcc00;
                        font-weight: bold;
                    }}
                    tr:hover {{ background: rgba(255, 255, 255, 0.05); }}
                    textarea {{
                        width: 100%;
                        height: 300px;
                        background: rgba(0, 0, 0, 0.5);
                        color: #00ff00;
                        border: 2px solid #00ccff;
                        border-radius: 10px;
                        padding: 15px;
                        font-family: 'Courier New', monospace;
                        font-size: 14px;
                        resize: vertical;
                    }}
                    textarea:focus {{
                        outline: none;
                        box-shadow: 0 0 20px rgba(0, 204, 255, 0.5);
                    }}
                    .btn {{
                        display: inline-block;
                        padding: 12px 30px;
                        background: linear-gradient(90deg, #ff0000, #ff6600);
                        color: #fff;
                        border: none;
                        border-radius: 10px;
                        font-size: 1.1em;
                        font-weight: bold;
                        cursor: pointer;
                        margin-top: 15px;
                        transition: all 0.3s;
                        text-shadow: 0 0 10px #fff;
                    }}
                    .btn:hover {{
                        transform: scale(1.05);
                        box-shadow: 0 0 30px rgba(255, 102, 0, 0.8);
                    }}
                    .btn-green {{
                        background: linear-gradient(90deg, #00cc00, #00ff00);
                        color: #000;
                    }}
                    .btn-blue {{
                        background: linear-gradient(90deg, #0066ff, #00ccff);
                        color: #fff;
                    }}
                    .footer {{
                        text-align: center;
                        padding: 20px;
                        color: #888;
                        font-size: 0.9em;
                    }}
                    .refresh-note {{
                        text-align: center;
                        color: #ffcc00;
                        margin-top: 10px;
                        font-size: 0.9em;
                    }}
                    .empty-warning {{
                        text-align: center;
                        padding: 40px;
                        color: #ffcc00;
                        font-size: 1.2em;
                    }}
                </style>
                <script>
                    setTimeout(function(){{ location.reload(); }}, 10000);
                </script>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🔥 MAHIR BOT DASHBOARD 🔥</h1>
                        <p>⚡ REAL-TIME MONITORING SYSTEM ⚡</p>
                    </div>

                    <div class="stats">
                        <div class="stat-card">
                            <h2>{online_count}</h2>
                            <p>🟢 ONLINE ACCOUNTS</p>
                        </div>
                        <div class="stat-card">
                            <h2>{total_accounts}</h2>
                            <p>📊 TOTAL ACCOUNTS</p>
                        </div>
                        <div class="stat-card">
                            <h2>{ab}</h2>
                            <p>⚙️ ACTIVE THREADS</p>
                        </div>
                        <div class="stat-card">
                            <h2 style="font-size: 1.4em; color: #00ccff;">{cur_ver}</h2>
                            <p>📦 VERSION ({cur_rel})</p>
                        </div>
                    </div>

                    <div class="section">
                        <h2>📋 Active Accounts (Last 100)</h2>
                        <table>
                            <thead>
                                <tr>
                                    <th>BOT UID</th>
                                    <th>UID</th>
                                    <th>REGION</th>
                                    <th>TIME</th>
                                    <th>STATUS</th>
                                </tr>
                            </thead>
                            <tbody>
                                {accounts_html if accounts_html else '<tr><td colspan="5" class="empty-warning">⚠️ No active accounts yet. Add accounts to BD.txt below.</td></tr>'}
                            </tbody>
                        </table>
                        <div class="refresh-note">🔄 Auto-refresh every 10 seconds</div>
                    </div>

                    <div class="section">
                        <h2>📝 Edit BD.txt</h2>
                        <form method="POST" action="/update">
                            <textarea name="bd_content" placeholder="uid:password&#10;uid:password&#10;...">{bd_content}</textarea>
                            <br>
                            <button type="submit" class="btn btn-green">💾 SAVE & START ACCOUNTS</button>
                        </form>
                    </div>

                    <div class="footer">
                        <p>© 2024 MAHIR BOT | Premium Auto System</p>
                        <p>Owner: MAHIR | Contact: @MAHIR0208</p>
                    </div>
                </div>
            </body>
            </html>
            """
            self.wfile.write(html.encode('utf-8'))

        elif self.path == '/api/stats':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            stats = {
                'online': online_count,
                'total': total_accounts,
                'threads': ab,
                'version': _current_version or "loading...",
                'release': obve or "loading...",
                'accounts': active_accounts[-100:]
            }
            self.wfile.write(json.dumps(stats).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')

    def do_POST(self):
        if self.path == '/update':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            params = parse_qs(post_data)

            if 'bd_content' in params:
                new_content = params['bd_content'][0]
                try:
                    with open('BD.txt', 'w', encoding='utf-8') as f:
                        f.write(new_content)

                    threading.Thread(target=restart_all_accounts, daemon=True).start()

                    self.send_response(302)
                    self.send_header('Location', '/')
                    self.end_headers()
                except Exception as e:
                    self.send_response(500)
                    self.end_headers()
                    self.wfile.write(f"Error: {str(e)}".encode('utf-8'))
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'No content provided')
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')

    def log_message(self, format, *args):
        pass


def restart_all_accounts():
    global rf, online_count, active_accounts, total_accounts, ab

    with restart_lock:
        console.print("\n[bold yellow]🔄 Restarting all accounts...[/bold yellow]")

        rf = True
        time.sleep(4)

        with lock:
            online_count = 0
            active_accounts = []
            ab = 0

        all_accounts = laa()
        total_accounts = len(all_accounts)

        rf = False
        time.sleep(1)

        if not all_accounts:
            console.print("[bold red]⚠️ No accounts found! Waiting for new upload...[/bold red]")
            return

        console.print(f"[bold cyan]📥 Loaded {total_accounts} accounts[/bold cyan]")

        for uid, password, region in all_accounts:
            thread = threading.Thread(target=rb, args=(uid, password, region), daemon=True)
            thread.start()
            time.sleep(0.05)


def ss():
    global rf, lrt, total_accounts, html_server_running, ab, online_count, active_accounts

    try:
        print(render('GLoBaL', colors=['white', 'magenta'], align='center'))
        print(render('MAHIR BOT', colors=['white', 'red'], align='center'))
    except:
        pass

    console.print(f"[bold green]📦 Version: {_current_version} ({obve})[/bold green]")

    if not html_server_running:
        try:
            server = HTTPServer(('0.0.0.0', 8080), DashboardHandler)
            html_server_running = True
            server_thread = threading.Thread(target=server.serve_forever, daemon=True)
            server_thread.start()
            console.print(f"[bold green]✅ Dashboard:[/bold green] [bold cyan]http://localhost:8080[/bold cyan]")
        except Exception as e:
            console.print(f"[bold red]❌ Dashboard failed: {e}[/bold red]")

    first_run = True

    while True:
        try:
            all_accounts = laa()
            total_accounts = len(all_accounts)

            if not all_accounts:
                if first_run:
                    console.print("\n[bold red]⚠️ No Acc FouND![/bold red]")
                    console.print("[bold yellow]💡 Dashboard এ BD.txt upload করুন: http://localhost:8080[/bold yellow]\n")
                    first_run = False
                else:
                    console.print("[yellow]⏳ Waiting for accounts in BD.txt...[/yellow]")

                time.sleep(10)
                continue

            first_run = False
            console.print(f"\n[bold cyan]✅ ALL Acc : {total_accounts}[/bold cyan]\n")

            for uid, password, region in all_accounts:
                thread = threading.Thread(target=rb, args=(uid, password, region), daemon=True)
                thread.start()
                time.sleep(0.05)

            while True:
                time.sleep(10)

                if ab == 0 and not rf:
                    console.print("[yellow]🔄 All threads stopped. Reloading accounts...[/yellow]")
                    break

        except Exception as e:
            console.print(f"[red]SS Error: {e}[/red]")
            time.sleep(5)
            continue


def restart_program():
    global ReS
    while True:
        time.sleep(ReS)
        console.print(f"\n[bold yellow]⏰ Auto-restart after {ReS//60} minutes...[/bold yellow]")
        try:
            restart_all_accounts()
        except Exception as e:
            console.print(f"[red]Restart error: {e}[/red]")


# ============ MAIN ============
if __name__ == "__main__":
    try:
        version_thread = threading.Thread(target=version_refresher, daemon=True)
        version_thread.start()

        restart_thread = threading.Thread(target=restart_program, daemon=True)
        restart_thread.start()

        ss()
    except KeyboardInterrupt:
        console.print("\n [bold red]Program Stopped by User![/bold red] \n")
        os._exit(0)
    except Exception as e:
        console.print(f"\n Error: {e} \n")