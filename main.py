import os, sys, time, json, ssl, socket, threading, asyncio, random, uuid, re
from datetime import datetime
import requests
import urllib3
from threading import Thread
import threading
from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for
from functools import wraps
from Pb2 import MajoRLoGinrEq_pb2, xKEys
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from google.protobuf.timestamp_pb2 import Timestamp
from google_play_scraper import app as play_store_info
import aiohttp
from xC4 import *

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ADMIN_PASSWORD = "MAHIR"
SECRET_KEY = "mahir_group_secret_2024"

app = Flask(__name__)
app.secret_key = SECRET_KEY

connected_clients = {}
connected_clients_lock = threading.Lock()

# গ্লোবাল কনফিগ
AUTO_INTERVAL = 10              # গ্রুপ সাইকেল ১০ সেকেন্ড
RESTART_INTERVAL = 5 * 60       # সব account restart প্রতি ৫ মিনিট
RECONNECT_CHECK_INTERVAL = 5    # dead client check প্রতি ৫ সেকেন্ড
HELP_COOLDOWN = 30              # /help এর cooldown (sec)

auto_running = True
help_cooldown = {}              # { uid: last_time }
help_cooldown_lock = threading.Lock()

C = "\033[96m"; G = "\033[92m"; Y = "\033[93m"; R = "\033[91m"; RS = "\033[0m"; BOLD = "\033[1m"

# ==================== HELP MESSAGE ====================
HELP_MESSAGE = """╔══════════════════════════╗
   🎯 MAHIR GROUP BOT 🎯
╚══════════════════════════╝

👋 হ্যালো! আমি MAHIR GROUP BOT।
এই গ্রুপে আপনাকে স্বাগতম ✨

📌 গ্রুপ নিয়মাবলী:
 ├─ 🚫 স্প্যাম করবেন না
 ├─ 🤝 সবাইকে সম্মান করুন
 ├─ 📛 গালাগালি নিষিদ্ধ
 └─ 🎮 শুধু গেম রিলেটেড কথা

💡 কমান্ড:
 ├─ /help  → এই মেসেজ
 ├─ /info  → বট ইনফো
 └─ /rules → গ্রুপ রুলস

🔥 MAHIR GROUP ─ Always Active 24/7 🔥"""

INFO_MESSAGE = """🤖 MAHIR GROUP BOT INFO
━━━━━━━━━━━━━━━━━━━━
▸ Name   : MAHIR BOT
▸ Version: v4.0
▸ Status : 🟢 Online 24/7
▸ Owner  : MAHIR GROUP
━━━━━━━━━━━━━━━━━━━━
💬 Type /help for commands"""

RULES_MESSAGE = """📜 MAHIR GROUP RULES
━━━━━━━━━━━━━━━━━━━━
1️⃣ স্প্যাম করা যাবে না
2️⃣ গালাগালি সম্পূর্ণ নিষিদ্ধ
3️⃣ সবাইকে সম্মান করুন
4️⃣ অ্যাডভার্টাইজমেন্ট নিষিদ্ধ
5️⃣ গেম রিলেটেড টপিক চলবে
6️⃣ অ্যাডমিনের সিদ্ধান্ত চূড়ান্ত
━━━━━━━━━━━━━━━━━━━━
⚠️ নিয়ম ভাঙলে kick/ban 🚫"""

# ==================== LIVE UPDATE ====================
def AuToUpDaTE():
    try:
        data = play_store_info('com.dts.freefireth', lang="fr", country='CA')
        store_version = data.get("version")
        if not store_version: sys.exit(1)
        api_url = f"https://version.ggwhitehawk.com/live/ver.php?version={store_version}&lang=fr&device=android&channel=android"
        r = requests.get(api_url, timeout=15)
        if r.status_code != 200: sys.exit(1)
        j = r.json()
        return j.get('server_url'), j.get('latest_release_version'), j.get('remote_version'), store_version
    except Exception as e:
        print(f"{R}❌ Update failure: {e}{RS}"); sys.exit(1)

try:
    temp_url, temp_ob, temp_remote, temp_store = AuToUpDaTE()
    DYNAMIC_SERVER_URL = temp_url.rstrip('/')
    CURRENT_OB = temp_ob
    FREEFIRE_VERSION_NAME = temp_remote
    STORE_VERSION = temp_store
    print(f"{G}✅ LIVE: OB={CURRENT_OB} | Remote={FREEFIRE_VERSION_NAME}{RS}")
except Exception as e:
    print(f"{R}❌ {e}{RS}"); sys.exit(1)

# ==================== ACCOUNTS ====================
def load_accounts(filename="accs.txt"):
    accounts = []
    try:
        if not os.path.exists(filename):
            with open(filename, "w") as f: f.write("# UID:PASSWORD\n")
            return []
        with open(filename, "r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if line and not line.startswith("#"):
                    if ":" in line:
                        parts = line.split(":")
                        uid, pwd = parts[0].strip(), parts[1].strip()
                    else:
                        uid, pwd = line.strip(), ""
                    if uid.isdigit():
                        accounts.append({'id': uid, 'password': pwd})
        print(f"{G}📦 Loaded: {len(accounts)} accounts{RS}")
    except Exception as e:
        print(f"{R}❌ Load error: {e}{RS}")
    return accounts

ACCOUNTS = load_accounts("accs.txt")

# গ্লোবাল অ্যাকাউন্ট রেজিস্ট্রি
account_objects = {}   # uid -> FF_CLient instance
account_lock = threading.Lock()

# ==================== PACKET BUILDERS ====================

def MAHIR_World_Recruit_Packet(target_id, key, iv):
    try:
        fields = {
            1: 66,
            2: {
                1: int(target_id),
                5: {},
                9: "",
                10: 1
            }
        }
        proto_data = CrEaTe_ProTo(fields)
        if proto_data is None:
            return None
        proto_hex = proto_data.hex() if hasattr(proto_data, 'hex') else bytes(proto_data).hex()
        final_packet = GeneRaTePk(proto_hex, '0515', key, iv)
        if final_packet is None:
            return None
        if isinstance(final_packet, str):
            return bytes.fromhex(final_packet)
        if isinstance(final_packet, (bytes, bytearray)):
            return bytes(final_packet)
        return None
    except Exception as e:
        print(f"❌ World Recruit Error: {e}")
        return None


def cHSq22(bot_uid, K, V, region):
    try:
        fields = {
            1: 17,
            2: {
                1: int(bot_uid),
                2: 1,
                3: 3,
                4: 1,
                5: "\x1a",
                8: 1
            }
        }
        if region.lower() == "ind": packet_type = '0514'
        elif region.lower() == "bd": packet_type = "0519"
        else: packet_type = "0515"
        proto_data = CrEaTe_ProTo(fields)
        if proto_data is None:
            return None
        proto_hex = proto_data.hex() if hasattr(proto_data, 'hex') else bytes(proto_data).hex()
        pkt = GeneRaTePk(proto_hex, packet_type, K, V)
        if pkt is None:
            return None
        if isinstance(pkt, str):
            return bytes.fromhex(pkt)
        if isinstance(pkt, (bytes, bytearray)):
            return bytes(pkt)
        return None
    except Exception as e:
        print(f"❌ cHSq22 Error: {e}")
        return None


def OpEnSq(K, V, region, version):
    try:
        fields = {
            1: 1,
            2: {
                2: "\u0001",
                3: 43,
                4: 1,
                5: "en",
                8: [{"1": "IDC2", "2": 171, "3": "BD"}],
                9: 1,
                10: "rYUW\u0017\t\u0007NR\u000f\u0005\u0004\\W\u0002\u000fV\u0004TPQ\u0003\u000f\u0005\u0004]\u0005\u000b\u0000\u0002W\u0005\r\nVY\u0004\u0007\u0007\u0007\u0017\u0001\bNQ\fS\u0005\u000e\u0006\f\u0005\rT\u0002\r\u0000TS\u0007U\u0004X\u0006RY\u0005\u0003\u0003SW\u0000\u000eQ\u0000^\u0014\u0003\u0004JXS\u000f\u0000g{gqfePblEZJp{_xU\bmQW\f\u0007\u000f\u0015\u0007H\\U^CHXh@Ax`\u000f~\rPN~Nz\\\u001fr_ckPU\u000b\u0015\u0005\u0003Ekfp\u007fcY\u0001nWV\u0002\u0005azE~N\u0007HTg\u0007w}@\u0002{\t\u0013\u0001NeNP]DUf|]ugINs{\u0001\\rAgB_\u0004fA]\u0004\r\u001a\u0000HpOv\\\u0005|gS\u0019\\A\u007fWW\u0003\u007fTqFGi\u0004Qr\u0019dW\u0004\u0011\rD\u0002yeZ]A\u0016a\u0007Ungeg\u0007E\\P\u001b\u000b\u0004\u0005dd\ff\r\u000f\u0017\t\u000fNRyZd\u0012tZ\fe\u0007AGv\u007fw]{P\u001c\u007f\u000ff\u0005ZJK\u0004\u0005\u0014\u0001Jgq\u001frymsB\u0001\u000fd`\u001bj~[}\u0004SDZ|IxKB\u0000\n\u0011\u0002J^`tjYN\u0007WQdE[PQ\u0002_{VP`S\t\u007f\u001dP\n\u000f\u000f\u0015\u0004\u0004L{V\u0003@yP[rgJ{Hpk\u0001\u000bw\u0001Agt_\u0003HxPc\u000b\u0017\u0005E`y\ngWoy\u0006S{A\u001b``Y\u0002Xzw}dDWOKsg\t\u0013\u000eNf\u000e\\`\u0005AwJc\u0003BM\u0001^\u0000R\u0002Qoh]tbS~`G\r\u001a\u0004HibAQ\u000f^XNt~kDUWaeaNqcLQ]Py[G\u0004",
                11: 1,
                13: 1,
                14: {
                    1: "08FAA33B035B3F16020859055555000200030001000000004AFA7572105C674946762514220104186fa2e8770e748c3f6a68ed75000000ff18470f0bcacfa16d",
                    2: 681,
                    3: {
                        14: {
                            11: "1106064f50055401030f03020403060155070d01540e060e020607540706030354530f041003064d715c46434b1f061f031e1205034a1c40677c5f554775755f504e677446185b584901534144685b67620f",
                            0: 72
                        }
                    },
                    4: "x\\\\R",
                    6: 13,
                    7: {2: 80},
                    8: version,
                    9: 2,
                    10: 1,
                    11: "03626253513677542b504e4635416456324b796f566c576a326567507844414c33507138513031762b66536c626a587648434e3348414e376c472b72474637794165676e72436b553671626b694538706f534e5a582b2f7a44675a547475465650542b384d69565a507151312b444b53576f786f6d592f7156394f76755254482b7154486a78486f664169734267564970454d454e6b4c326a4763445a4a5176416d687947356b7669564e544d71515745754b32324d384e4931424d437445395532415156694b667948314574412b32644536464b53773132554155596363372b7753652b66676c393742756544446a58496d6e35666d45444a51535948326644484c5650676755472f51794b776e77545151324a505265352f72314830616d374264424f556b712f523246734d635475516d47364c684a547a4379345774444245795268305754366f68532f785a48736a4c7a4366506378372f386a534133352b67787642657450397a4f6f463639344945386e6e77336b507344357a6e6337593649776b4142435761776f6d572b6948594f5939686d647632706975584168416d6d6a74496f5945444c6e506e5738616f7153304f74486b732f5a3953543252447345507a3343655438774e6874756d57634b4438585445376649386c305173726a772f4a57514f76394b50307257644538593375422f2b495836757675452b487a6a4853466c75726f33515432536567595758535854714674495a61454d476c51314b7639666c59525539465047366c30663045314f7a2b2b36324339644b664c4d39315a782f6f625938726a6e682b77524a3962636e544e41715466486f72354b714d3d"
                },
                19: 329,
                21: "374f5219",
                24: {1: 21},
                27: "a_6534489873065906362"
            }
        }
        proto_bytes = CrEaTe_ProTo(fields)
        if proto_bytes is None:
            return None
        proto_hex = proto_bytes.hex() if hasattr(proto_bytes, 'hex') else bytes(proto_bytes).hex()
        packet = GeneRaTePk(proto_hex, '0515', K, V)
        if packet is None:
            return None
        if isinstance(packet, str):
            return bytes.fromhex(packet)
        if isinstance(packet, (bytes, bytearray)):
            return bytes(packet)
        return None
    except Exception as e:
        print(f"❌ OpEnSq Error: {e}")
        return None


def LeAvEsQ(K, V, region="BD"):
    try:
        fields = {
            1: 2,
            2: {
                1: 1
            }
        }
        if region.lower() == "ind": packet_type = '0514'
        elif region.lower() == "bd": packet_type = "0519"
        else: packet_type = "0515"
        proto_data = CrEaTe_ProTo(fields)
        if proto_data is None:
            return None
        proto_hex = proto_data.hex() if hasattr(proto_data, 'hex') else bytes(proto_data).hex()
        pkt = GeneRaTePk(proto_hex, packet_type, K, V)
        if pkt is None:
            return None
        if isinstance(pkt, str):
            return bytes.fromhex(pkt)
        if isinstance(pkt, (bytes, bytearray)):
            return bytes(pkt)
        return None
    except Exception as e:
        print(f"❌ LeAvEsQ Error: {e}")
        return None


# ==================== TERMINAL LOG HELPERS ====================
def log_recv(client_id, raw_bytes):
    try:
        if not raw_bytes:
            return
        hex_str = raw_bytes.hex()
        ptype = hex_str[:4] if len(hex_str) >= 4 else "????"
        preview = hex_str[:60] + ("..." if len(hex_str) > 60 else "")
        print(f"{C}[RECV {client_id}]{RS} type={ptype} len={len(raw_bytes)} data={preview}")
    except Exception as e:
        print(f"{R}[RECV parse error] {e}{RS}")


def log_send(client_id, label, raw_bytes):
    if raw_bytes is None:
        print(f"{R}[SEND {client_id}] {label} FAILED (None){RS}")
        return
    hex_str = raw_bytes.hex()
    ptype = hex_str[:4] if len(hex_str) >= 4 else "????"
    preview = hex_str[:60] + ("..." if len(hex_str) > 60 else "")
    print(f"{G}[SEND {client_id}]{RS} {label} type={ptype} len={len(raw_bytes)} data={preview}")


# ==================== GROUP CREATE / EXIT LOGIC ====================
def exit_group_on_client(client, region="BD"):
    try:
        if not hasattr(client, 'CliEnts2') or not client.key:
            return False, "no socket"
        pkt = LeAvEsQ(client.key, client.iv, region)
        if pkt:
            client.CliEnts2.send(pkt)
            log_send(client.id, "LEAVE_SQUAD", pkt)
            return True, "sent"
        return False, "LeAvEsQ failed"
    except Exception as e:
        return False, str(e)


def create_group_on_client(client, region="BD"):
    try:
        if not hasattr(client, 'CliEnts2') or not client.key:
            return False, "no socket"

        pkt_open = OpEnSq(client.key, client.iv, region, FREEFIRE_VERSION_NAME)
        if pkt_open:
            client.CliEnts2.send(pkt_open)
            log_send(client.id, "OPEN_SQUAD", pkt_open)
            time.sleep(0.15)
        else:
            return False, "OpEnSq failed"

        pkt_size = cHSq22(int(client.id), client.key, client.iv, region)
        if pkt_size:
            client.CliEnts2.send(pkt_size)
            log_send(client.id, "SQUAD_SIZE", pkt_size)
            time.sleep(0.15)
        else:
            return False, "cHSq22 failed"

        pkt_recruit = MAHIR_World_Recruit_Packet(int(client.id), client.key, client.iv)
        if pkt_recruit:
            client.CliEnts2.send(pkt_recruit)
            log_send(client.id, "WORLD_RECRUIT", pkt_recruit)
            time.sleep(0.1)
        else:
            return False, "World Recruit failed"

        return True, "sent"
    except Exception as e:
        return False, str(e)


def create_group_with_all_accounts():
    print(f"\n{C}{'='*60}{RS}")
    print(f"{G}👥 CREATING GROUP ON ALL CONNECTED ACCOUNTS{RS}")
    print(f"{C}{'='*60}{RS}")
    with connected_clients_lock:
        clients = list(connected_clients.values())
    if not clients:
        print(f"{R}❌ No clients connected!{RS}")
        return 0, 0
    print(f"{G}📊 Total clients: {len(clients)}{RS}")
    success = 0
    for client in clients:
        ok, msg = create_group_on_client(client)
        if ok:
            success += 1
            print(f"{G}✅ Group created: {client.id}{RS}")
        else:
            print(f"{R}❌ {client.id}: {msg}{RS}")
        time.sleep(0.2)
    print(f"\n{G}✅ GROUP CREATE: {success}/{len(clients)} successful{RS}\n")
    return success, len(clients)


# ==================== AUTO LOOP (10s) ====================
def auto_group_cycle_loop():
    global auto_running
    print(f"{Y}⏰ Auto Group Cycle started (every {AUTO_INTERVAL}s: EXIT → RECREATE){RS}")

    while auto_running:
        try:
            with connected_clients_lock:
                clients = list(connected_clients.values())
            if not clients:
                time.sleep(3)
                continue

            print(f"\n{C}{'━'*60}{RS}")
            print(f"{Y}[{datetime.now().strftime('%H:%M:%S')}] 🔄 AUTO CYCLE START ({len(clients)} clients){RS}")

            print(f"{Y}➡️  STEP 1: Leaving old group...{RS}")
            exit_ok = 0
            for client in clients:
                ok, msg = exit_group_on_client(client)
                if ok: exit_ok += 1
                time.sleep(0.05)
            print(f"{G}   ✅ Exit done: {exit_ok}/{len(clients)}{RS}")

            time.sleep(0.5)

            print(f"{Y}➡️  STEP 2: Creating new group...{RS}")
            success = 0
            for client in clients:
                ok, msg = create_group_on_client(client)
                if ok:
                    success += 1
                else:
                    print(f"{R}   ❌ {client.id}: {msg}{RS}")
                time.sleep(0.1)
            print(f"{G}   ✅ Group recreated: {success}/{len(clients)}{RS}")

            print(f"{Y}➡️  STEP 3: Extra World Recruit...{RS}")
            recruit_ok = 0
            for client in clients:
                try:
                    if not hasattr(client, 'CliEnts2') or not client.key:
                        continue
                    pkt = MAHIR_World_Recruit_Packet(int(client.id), client.key, client.iv)
                    if pkt:
                        client.CliEnts2.send(pkt)
                        log_send(client.id, "WORLD_RECRUIT", pkt)
                        recruit_ok += 1
                    time.sleep(0.05)
                except Exception:
                    pass
            print(f"{G}   ✅ Recruit sent: {recruit_ok}/{len(clients)}{RS}")
            print(f"{C}{'━'*60}{RS}\n")

            time.sleep(AUTO_INTERVAL)

        except Exception as e:
            print(f"{R}❌ Auto cycle error: {e}{RS}")
            time.sleep(5)


# ==================== AUTO RESTART (EVERY 5 MIN) ====================
def auto_restart_all_loop():
    print(f"{Y}🔁 Auto Restart Loop started (every {RESTART_INTERVAL}s = 5 min){RS}")
    while True:
        try:
            time.sleep(RESTART_INTERVAL)

            print(f"\n{C}{'='*60}{RS}")
            print(f"{Y}[{datetime.now().strftime('%H:%M:%S')}] 🔁 AUTO RESTART ALL ACCOUNTS{RS}")
            print(f"{C}{'='*60}{RS}")

            with account_lock:
                uids = list(account_objects.keys())

            if not uids:
                print(f"{Y}   (no accounts to restart){RS}")
                continue

            for uid in uids:
                try:
                    with account_lock:
                        obj = account_objects.get(uid)
                    if obj:
                        obj.stop()
                except Exception as e:
                    print(f"{R}   ❌ stop {uid}: {e}{RS}")

            with connected_clients_lock:
                connected_clients.clear()
            with account_lock:
                account_objects.clear()

            print(f"{G}   ✅ Stopped {len(uids)} accounts. Reconnecting...{RS}")
            time.sleep(2)

            for acc in ACCOUNTS:
                t = threading.Thread(target=start_account, args=(acc,), daemon=True)
                t.start()
                time.sleep(0.5)

            print(f"{G}   ✅ Restart triggered for {len(ACCOUNTS)} accounts{RS}\n")

        except Exception as e:
            print(f"{R}❌ Auto restart error: {e}{RS}")
            time.sleep(10)


# ==================== AUTO RECONNECT DEAD CLIENTS ====================
def auto_reconnect_dead_loop():
    print(f"{Y}🩺 Auto Reconnect Dead Loop started (every {RECONNECT_CHECK_INTERVAL}s){RS}")
    while True:
        try:
            time.sleep(RECONNECT_CHECK_INTERVAL)

            with account_lock:
                current_uids = set(account_objects.keys())

            with connected_clients_lock:
                connected_uids = set(connected_clients.keys())

            all_uids = set(str(a['id']) for a in ACCOUNTS)
            dead_uids = all_uids - connected_uids

            for uid in list(current_uids):
                obj = account_objects.get(uid)
                if obj is None:
                    dead_uids.add(uid)
                    continue
                if not getattr(obj, 'running', False):
                    dead_uids.add(uid)
                    continue
                sock2 = getattr(obj, 'CliEnts2', None)
                if sock2 is None:
                    dead_uids.add(uid)
                    continue
                try:
                    sock2.setblocking(False)
                    try:
                        peek = sock2.recv(1, socket.MSG_PEEK)
                        if peek == b'':
                            dead_uids.add(uid)
                    except BlockingIOError:
                        pass
                    except (ConnectionResetError, OSError):
                        dead_uids.add(uid)
                    finally:
                        try: sock2.setblocking(True)
                        except: pass
                except Exception:
                    dead_uids.add(uid)

            if not dead_uids:
                continue

            print(f"{Y}🩺 Reconnect check: {len(dead_uids)} dead → restarting{RS}")

            for uid in dead_uids:
                with account_lock:
                    old = account_objects.pop(uid, None)
                if old:
                    try: old.stop()
                    except: pass

                with connected_clients_lock:
                    connected_clients.pop(uid, None)

                acc = next((a for a in ACCOUNTS if str(a['id']) == str(uid)), None)
                if acc:
                    print(f"{G}   ♻️ Reconnecting {uid}...{RS}")
                    t = threading.Thread(target=start_account, args=(acc,), daemon=True)
                    t.start()

        except Exception as e:
            print(f"{R}❌ Reconnect loop error: {e}{RS}")
            time.sleep(5)


# ==================== CHAT / HELP / EXTRA ACTIONS ====================
def send_squad_chat_on_client(client, message, chat_type=1, squad_id="0"):
    try:
        if not hasattr(client, 'CliEnts2') or not client.key:
            return False, "no socket"
        pkt = ChaT_sQ(str(message), int(chat_type), int(client.id), str(squad_id), client.key, client.iv)
        if pkt:
            client.CliEnts2.send(pkt)
            log_send(client.id, "SQUAD_CHAT", pkt)
            return True, "sent"
        return False, "ChaT_sQ failed"
    except Exception as e:
        return False, str(e)


def send_global_chat_on_client(client, message):
    try:
        if not hasattr(client, 'CliEnts2') or not client.key:
            return False, "no socket"
        pkt = GLobaL(str(message), client.key, client.iv)
        if pkt:
            client.CliEnts2.send(pkt)
            log_send(client.id, "GLOBAL_CHAT", pkt)
            return True, "sent"
        return False, "GLobaL failed"
    except Exception as e:
        return False, str(e)


def send_craftland_share_on_client(client, target_id, map_code, chat_type=5):
    try:
        if not hasattr(client, 'CliEnts2') or not client.key:
            return False, "no socket"
        ok = send_craftland_share_sync(
            client.CliEnts2, int(client.id), int(target_id),
            int(chat_type), str(map_code), client.key, client.iv
        )
        if ok:
            print(f"{G}[SEND {client.id}] CRAFTLAND_SHARE map={map_code}{RS}")
            return True, "sent"
        return False, "craftland failed"
    except Exception as e:
        return False, str(e)


def send_refresh_on_client(client):
    try:
        if not hasattr(client, 'CliEnts2') or not client.key:
            return False, "no socket"
        pkt = RefLeSh(client.key, client.iv)
        if pkt:
            client.CliEnts2.send(pkt)
            log_send(client.id, "REFRESH", pkt)
            return True, "sent"
        return False, "RefLeSh failed"
    except Exception as e:
        return False, str(e)


def broadcast_squad_chat(message, chat_type=1, squad_id="0"):
    with connected_clients_lock:
        clients = list(connected_clients.values())
    ok = 0
    for c in clients:
        r, _ = send_squad_chat_on_client(c, message, chat_type, squad_id)
        if r: ok += 1
        time.sleep(0.05)
    return ok, len(clients)


def broadcast_global_chat(message):
    with connected_clients_lock:
        clients = list(connected_clients.values())
    ok = 0
    for c in clients:
        r, _ = send_global_chat_on_client(c, message)
        if r: ok += 1
        time.sleep(0.05)
    return ok, len(clients)


# ==================== HELP COMMAND HANDLER ====================
def _help_cooldown_ok(uid):
    """একজন user ৩০ সেকেন্ডে একবার /help পাবে"""
    if not uid:
        return True
    with help_cooldown_lock:
        now = time.time()
        last = help_cooldown.get(str(uid), 0)
        if now - last < HELP_COOLDOWN:
            return False
        help_cooldown[str(uid)] = now
        return True


def _send_group_message(client, text):
    """গ্রুপে মেসেজ পাঠায়"""
    try:
        if not client.key or not client.iv:
            return False
        if not hasattr(client, 'CliEnts2'):
            return False
        pkt = ChaT_sQ(str(text), 1, int(client.id), "0", client.key, client.iv)
        if pkt:
            client.CliEnts2.send(pkt)
            log_send(client.id, "GROUP_MSG", pkt)
            return True
    except Exception as e:
        print(f"{R}[SEND_MSG {getattr(client,'id','?')}] {e}{RS}")
    return False


def _handle_help_command(client, raw_bytes):
    """
    recv packet এর ভিতরে '/help', '/info', '/rules' খুঁজে reply দেয়
    """
    try:
        hex_str = raw_bytes.hex()

        # খুব ছোট packet skip
        if len(hex_str) < 40:
            return

        # chat packet type 1215 বা 0c দিয়ে শুরু হলে বেশি সম্ভাবনা
        # কিন্তু নিরাপদ পদ্ধতি: hex থেকে string decode করে keyword খুঁজি
        try:
            decoded = bytes.fromhex(hex_str).decode('utf-8', errors='ignore')
        except Exception:
            return

        low = decoded.lower()

        # /help /info /rules command খুঁজি
        want_help = '/help' in low or low.strip().endswith(' help')
        want_info = '/info' in low
        want_rules = '/rules' in low

        if not (want_help or want_info or want_rules):
            return

        # sender UID বের করার চেষ্টা (protobuf parse)
        sender_uid = None
        try:
            if '08' in hex_str:
                parsed = DeCode_PackEt(f'08{hex_str.split("08",1)[1]}')
                if parsed:
                    obj = json.loads(parsed)
                    # 여러 structure try
                    for path in [
                        ('5','data','1','data'),
                        ('5','data','3','data','31','data'),
                        ('5','data','31','data'),
                    ]:
                        cur = obj
                        ok = True
                        for p in path:
                            if isinstance(cur, dict) and p in cur:
                                cur = cur[p]
                            else:
                                ok = False
                                break
                        if ok and isinstance(cur, (str, int)):
                            sender_uid = str(cur)
                            break
        except Exception:
            pass

        # cooldown check (শুধু help/info/rules এর জন্য)
        if not _help_cooldown_ok(sender_uid):
            print(f"{Y}[HELP {client.id}] cooldown for {sender_uid}{RS}")
            return

        # reply পাঠাই
        if want_help:
            print(f"{G}[HELP {client.id}] ➜ /help detected (sender={sender_uid}){RS}")
            _send_group_message(client, HELP_MESSAGE)
        elif want_info:
            print(f"{G}[HELP {client.id}] ➜ /info detected{RS}")
            _send_group_message(client, INFO_MESSAGE)
        elif want_rules:
            print(f"{G}[HELP {client.id}] ➜ /rules detected{RS}")
            _send_group_message(client, RULES_MESSAGE)

    except Exception as e:
        print(f"{R}[HELP parse error {getattr(client,'id','?')}] {e}{RS}")


# ==================== FF CLIENT ====================
class FF_CLient():
    def __init__(self, uid, password):
        self.id = uid
        self.password = password
        self.key = None
        self.iv = None
        self.running = True        self._reconnect_attempts = 0
        self.Get_FiNal_ToKen_0115()

    def Connect_SerVer_OnLine(self, Token, tok, host, port, key, iv, host2, port2):
        try:
            self.AutH_ToKen_0115 = tok
            self.CliEnts2 = socket.create_connection((host2, int(port2)), timeout=10)
            self.CliEnts2.send(bytes.fromhex(self.AutH_ToKen_0115))
            with connected_clients_lock:
                if self.id not in connected_clients:
                    connected_clients[self.id] = self
                    print(f"{G}✅ Online: {self.id} (Total: {len(connected_clients)}){RS}")
        except Exception as e:
            print(f"{R}❌ Online error {self.id}: {e}{RS}")
            self._schedule_reconnect()
            return
        while self.running:
            try:
                self.CliEnts2.settimeout(30)
                self.DaTa2 = self.CliEnts2.recv(99999)
                if not self.DaTa2:
                    print(f"{Y}⚠️ Socket2 closed: {self.id}{RS}")
                    break

                log_recv(self.id, self.DaTa2)

                # 🔥 /help command detect
                try:
                    _handle_help_command(self, self.DaTa2)
                except Exception:
                    pass

                if '0500' in self.DaTa2.hex()[0:4] and len(self.DaTa2.hex()) > 30:
                    self.packet = json.loads(DeCode_PackEt(f'08{self.DaTa2.hex().split("08",1)[1]}'))
                    self.AutH = self.packet['5']['data']['7']['data']
            except socket.timeout: continue
            except Exception as e:
                print(f"{R}[RECV err {self.id}] {e}{RS}")
                break

        if self.running:
            self._schedule_reconnect()

    def Connect_SerVer(self, Token, tok, host, port, key, iv, host2, port2):
        self.AutH_ToKen_0115 = tok
        try:
            self.CliEnts = socket.create_connection((host, int(port)), timeout=10)
            self.CliEnts.send(bytes.fromhex(self.AutH_ToKen_0115))
            self.DaTa = self.CliEnts.recv(1024)
            threading.Thread(target=self.Connect_SerVer_OnLine, args=(Token, tok, host, port, key, iv, host2, port2), daemon=True).start()
        except Exception as e:
            print(f"{R}❌ Conn error {self.id}: {e}{RS}")
            self._schedule_reconnect()
            return
        self.key = key
        self.iv = iv
        with connected_clients_lock:
            if self.id not in connected_clients:
                connected_clients[self.id] = self
                print(f"{G}✅ Registered: {self.id}{RS}")
        while self.running:
            try:
                self.CliEnts.settimeout(30)
                self.DaTa = self.CliEnts.recv(1024)
                if not self.DaTa:
                    print(f"{Y}⚠️ Socket1 closed: {self.id}{RS}")
                    break
                log_recv(self.id + ":c1", self.DaTa)
                # Socket1 থেকেও help detect করা যায়
                try:
                    _handle_help_command(self, self.DaTa)
                except Exception:
                    pass
            except socket.timeout: continue
            except Exception: break

        if self.running:
            self._schedule_reconnect()

    def _schedule_reconnect(self):
        if not self.running:
            return
        self._reconnect_attempts += 1
        wait = min(5 + self._reconnect_attempts * 2, 30)
        print(f"{Y}♻️ Scheduling reconnect for {self.id} in {wait}s (attempt #{self._reconnect_attempts}){RS}")
        t = threading.Timer(wait, self._do_reconnect)
        t.daemon = True
        t.start()

    def _do_reconnect(self):
        if not self.running:
            return
        try:
            if hasattr(self, 'CliEnts'):
                try: self.CliEnts.close()
                except: pass
            if hasattr(self, 'CliEnts2'):
                try: self.CliEnts2.close()
                except: pass
        except: pass
        with connected_clients_lock:
            connected_clients.pop(self.id, None)
        with account_lock:
            account_objects.pop(self.id, None)

        print(f"{G}🔄 Reconnecting {self.id}...{RS}")
        acc = {'id': self.id, 'password': self.password}
        threading.Thread(target=start_account, args=(acc,), daemon=True).start()

    def GeT_Key_Iv(self, serialized_data):
        my_message = xKEys.MyMessage()
        my_message.ParseFromString(serialized_data)
        timestamp, key, iv = my_message.field21, my_message.field22, my_message.field23
        ts_obj = Timestamp(); ts_obj.FromNanoseconds(timestamp)
        return ts_obj.seconds * 1_000_000_000 + ts_obj.nanos, key, iv

    def Guest_GeneRaTe(self, uid, password):
        url = "https://100067.connect.garena.com/oauth/guest/token/grant"
        headers = {
            "Host": "100067.connect.garena.com",
            "User-Agent": "GarenaMSDK/4.0.19P4(G011A ;Android 9;en;US;)",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "close",
        }
        data = {
            "uid": uid, "password": password, "response_type": "token",
            "client_type": "2",
            "client_secret": "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3",
            "client_id": "100067",
        }
        try:
            resp = requests.post(url, headers=headers, data=data, timeout=10).json()
            at, oid = resp['access_token'], resp['open_id']
            time.sleep(0.2)
            print(f'{C}🔐 Login: {self.id}{RS}')
            return self.ToKen_GeneRaTe(at, oid)
        except:
            time.sleep(10)
            return self.Guest_GeneRaTe(uid, password)

    def GeT_LoGin_PorTs(self, jwt_token, payload, dynamic_url="https://clientbp.ggpolarbear.com"):
        url = f'{dynamic_url}/GetLoginData'
        headers = {
            'Expect': '100-continue',
            'Authorization': f'Bearer {jwt_token}',
            'X-Unity-Version': '2022.3.47f1', 'X-GA': 'v1 1', 'ReleaseVersion': 'OB54',
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'UnityPlayer/2022.3.47f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)',
            'Connection': 'close', 'Accept-Encoding': 'deflate, gzip',
        }
        try:
            resp = requests.post(url, headers=headers, data=payload, verify=False, timeout=10)
            data = json.loads(DeCode_PackEt(resp.content.hex()))
            a1, a2 = data['32']['data'], data['14']['data']
            return a1[:-6], a1[-5:], a2[:-6], a2[-5:]
        except:
            return None, None, None, None

    def ToKen_GeneRaTe(self, access_token, open_id):
        url = f"{DYNAMIC_SERVER_URL}/MajorLogin"
        dynamic_host = DYNAMIC_SERVER_URL.split("//")[-1].split("/")[0]
        headers = {
            'X-Unity-Version': '2022.3.47f1', 'ReleaseVersion': CURRENT_OB,
            'Content-Type': 'application/x-www-form-urlencoded', 'X-GA': 'v1 1',
            'User-Agent': 'UnityPlayer/2022.3.47f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)',
            'Host': dynamic_host, 'Connection': 'Keep-Alive', 'Accept-Encoding': 'gzip'
        }
        try:
            ml = MajoRLoGinrEq_pb2.MajorLogin()
            ml.event_time = str(datetime.now())[:-7]
            ml.game_name = "free fire"
            emulators = [
                {"name": "BlueStacks 5", "software": "Android OS 9 / API-28 (x86_64/BlueStacks)"},
                {"name": "LDPlayer 9", "software": "Android OS 11 / API-30 (x86_64/LDPlayer)"},
                {"name": "MSI App Player", "software": "Android OS 9 / API-28 (x86_64/MSI)"},
                {"name": "NoxPlayer", "software": "Android OS 7 / API-25 (x86/Nox)"}
            ]
            pc_hw = [
                {"cpu": "Intel(R) Core(TM) i7-10700K CPU @ 3.80GHz", "gpu": "NVIDIA GeForce RTX 3060"},
                {"cpu": "AMD Ryzen 7 5800X 8-Core Processor", "gpu": "AMD Radeon RX 6700 XT"},
                {"cpu": "Intel(R) Core(TM) i5-12400F CPU @ 2.50GHz", "gpu": "NVIDIA GeForce GTX 1660 SUPER"},
                {"cpu": "Intel(R) Core(TM) i9-12900K CPU @ 3.20GHz", "gpu": "NVIDIA GeForce RTX 3080"}
            ]
            emu = random.choice(emulators)
            pc = random.choice(pc_hw)
            ml.platform_id = 1; ml.platform_sdk_id = 1
            ml.device_type = "Emulator"
            ml.system_hardware = "x86_64"
            ml.system_software = emu["software"]
            ml.client_version = FREEFIRE_VERSION_NAME
            ml.client_version_code = "2019120828"
            ml.telecom_operator = "WIFI"
            ml.network_operator_a = "00000"
            ml.network_type = "WIFI"
            ml.network_type_a = "WIFI"
            ml.screen_width = 1920; ml.screen_height = 1080; ml.screen_dpi = "320"
            ml.processor_details = pc["cpu"]
            ml.memory = random.choice([4096, 8192, 16384])
            ml.gpu_renderer = pc["gpu"]
            ml.gpu_version = "OpenGL ES 3.2"
            ml.graphics_api = "OpenGLES3"
            uid_ = str(uuid.uuid4()).upper()
            ml.unique_device_id = f"{emu['name'].split()[0]}|{uid_}"
            ml.language = "en"
            ml.open_id = open_id; ml.open_id_type = "4"; ml.login_open_id_type = 4
            ml.access_token = access_token; ml.login_by = 3
            ml.origin_platform_type = "4"; ml.primary_platform_type = "4"
            ma = ml.memory_available; ma.version = 55; ma.hidden_value = random.randint(80, 98)
            ml.external_storage_total = 256000
            ml.external_storage_available = random.randint(50000, 150000)
            ml.internal_storage_total = 256000
            ml.internal_storage_available = random.randint(40000, 100000)
            ml.library_path = f"/data/app/com.dts.freefireth/lib/{emu['name'].lower()}"
            ml.library_token = f"emu_token_{uuid.uuid4().hex[:16]}"
            ml.client_using_version = "7428b253defc164018c604a1ebbfebdf"
            ml.supported_astc_bitset = 16383
            ml.analytics_detail = b"FwQVTgUPX1UaUllDDwcWCRBpWAUOUgsvA1snWlBaO1kFYg=="
            ml.loading_time = random.randint(1500, 4000)
            ml.release_channel = "official"; ml.if_push = 1; ml.is_vpn = 0
            ml.cpu_type = 1; ml.cpu_architecture = "x86_64"
            ml.android_engine_init_flag = 110009
            raw = ml.SerializeToString()
            cipher = AES.new(b'Yg&tc%DEuh6%Zc^8', AES.MODE_CBC, b'6oyZDr22E3ychjM%')
            payload = cipher.encrypt(pad(raw, 16))
        except Exception as e:
            print(f"Pack err: {e}"); time.sleep(5)
            return self.ToKen_GeneRaTe(access_token, open_id)

        resp = requests.post(url, headers=headers, data=payload, verify=False, timeout=10)
        if resp.status_code == 200:
            try:
                data = json.loads(DeCode_PackEt(resp.content.hex()))
                jwt_token = data['8']['data']
                combined, key, iv = self.GeT_Key_Iv(resp.content)
                ip, port, ip2, port2 = self.GeT_LoGin_PorTs(jwt_token, payload)
                return jwt_token, key, iv, combined, ip, port, ip2, port2
            except:
                time.sleep(5); return self.ToKen_GeneRaTe(access_token, open_id)
        else:
            time.sleep(5); return self.ToKen_GeneRaTe(access_token, open_id)

    def Get_FiNal_ToKen_0115(self):
        try:
            result = self.Guest_GeneRaTe(self.id, self.password)
            if not result:
                time.sleep(5); return self.Get_FiNal_ToKen_0115()
            token, key, iv, ts, ip, port, ip2, port2 = result
            if not all([ip, port, ip2, port2]):
                time.sleep(5); return self.Get_FiNal_ToKen_0115()
            self.JwT_ToKen = token
            try:
                import jwt as jwtlib
                decoded = jwtlib.decode(token, options={"verify_signature": False})
                account_id = decoded.get('account_id')
                enc_acc = hex(account_id)[2:]
                hex_ts = DecodE_HeX(ts)
                self.JwT_ToKen_ = token.encode().hex()
                print(f'{C}🆔 UID: {account_id}{RS}')
            except:
                time.sleep(5); return self.Get_FiNal_ToKen_0115()
            try:
                enc_len = len(EnC_PacKeT(self.JwT_ToKen_, key, iv)) // 2
                header = hex(enc_len)[2:]
                length = len(enc_acc)
                pad = '00000000'
                if length == 9: pad = '0000000'
                elif length == 8: pad = '00000000'
                elif length == 10: pad = '000000'
                elif length == 7: pad = '000000000'
                self.Header = f'0115{pad}{enc_acc}{hex_ts}00000{header}'
                self.FiNal_ToKen_0115 = self.Header + EnC_PacKeT(self.JwT_ToKen_, key, iv)
            except:
                time.sleep(5); return self.Get_FiNal_ToKen_0115()
            self.AutH_ToKen = self.FiNal_ToKen_0115
            self.Connect_SerVer(self.JwT_ToKen, self.AutH_ToKen, ip, port, key, iv, ip2, port2)
            return self.AutH_ToKen, key, iv
        except:
            time.sleep(5); return self.Get_FiNal_ToKen_0115()

    def stop(self):
        self.running = False
        try:
            if hasattr(self, 'CliEnts'): self.CliEnts.close()
        except: pass
        try:
            if hasattr(self, 'CliEnts2'): self.CliEnts2.close()
        except: pass


# ==================== RUNNERS ====================
def start_account(account):
    uid = str(account['id'])
    try:
        obj = FF_CLient(account['id'], account['password'])
        with account_lock:
            account_objects[uid] = obj
    except Exception as e:
        print(f"{R}❌ Login fail {uid}: {e}{RS}")
        time.sleep(3)
        t = threading.Timer(3, start_account, args=(account,))
        t.daemon = True
        t.start()


def run_accounts():
    print(f"{Y}⚙️ Logging in {len(ACCOUNTS)} accounts...{RS}")
    for acc in ACCOUNTS:
        t = threading.Thread(target=start_account, args=(acc,), daemon=True)
        t.start()
        time.sleep(0.5)


def reset_accounts():
    global ACCOUNTS
    print(f"{Y}🔄 Reset...{RS}")
    with account_lock:
        for uid in list(account_objects.keys()):
            try: account_objects[uid].stop()
            except: pass
        account_objects.clear()
    with connected_clients_lock:
        connected_clients.clear()
    time.sleep(1)
    ACCOUNTS = load_accounts("accs.txt")
    if ACCOUNTS:
        run_accounts()
        return True, f"Reset complete. {len(ACCOUNTS)} accounts logging in."
    return False, "Reset done but accs.txt empty."


# ==================== FLASK ====================
LOGIN_TEMPLATE = '''<!DOCTYPE html><html><head><meta charset="UTF-8"><title>MAHIR GROUP | Login</title>
<style>body{margin:0;font-family:sans-serif;background:#05050a;color:#fff;display:flex;justify-content:center;align-items:center;min-height:100vh;}
.box{background:rgba(10,10,25,0.9);padding:40px;border-radius:16px;border:1px solid rgba(255,0,127,0.3);max-width:400px;width:90%;text-align:center;box-shadow:0 0 60px rgba(255,0,127,0.15);}
h1{background:linear-gradient(135deg,#ff007f,#7f00ff);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:5px;font-size:2rem;}
p{color:#00ffcc;letter-spacing:3px;font-size:0.8rem;margin-bottom:25px;text-transform:uppercase;}
input{width:100%;padding:14px;background:rgba(0,0,0,0.5);border:1px solid rgba(255,255,255,0.1);border-radius:10px;color:#fff;font-size:1rem;outline:none;box-sizing:border-box;margin-bottom:15px;}
input:focus{border-color:#ff007f;}button{width:100%;padding:14px;background:linear-gradient(135deg,#ff007f,#7f00ff);border:none;border-radius:10px;color:#fff;font-size:1.1rem;font-weight:700;cursor:pointer;letter-spacing:2px;}
.error{color:#ff4444;margin-top:15px;}</style></head><body>
<div class="box"><h1>MAHIR GROUP</h1><p>Access Panel</p>
<form method="POST"><input type="password" name="password" placeholder="Enter Password" required>
<button type="submit">UNLOCK</button>{% if error %}<div class="error">{{ error }}</div>{% endif %}</form></div></body></html>'''


HTML_TEMPLATE = '''<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MAHIR GROUP PANEL</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',sans-serif;}
body{background:linear-gradient(135deg,#060417,#0e0b30,#130a24);min-height:100vh;color:#fff;padding:20px;}
.container{max-width:1200px;margin:0 auto;}
.header{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:15px;padding-bottom:20px;border-bottom:1px solid rgba(255,255,255,0.05);margin-bottom:25px;}
.logo{font-size:2rem;font-weight:800;background:linear-gradient(135deg,#ff007f,#7f00ff);-webkit-background-clip:text;-webkit-text-fill-color:transparent;}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:15px;margin-bottom:25px;}
.stat{background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-radius:12px;padding:18px;text-align:center;}
.stat .label{font-size:0.7rem;color:rgba(255,255,255,0.4);text-transform:uppercase;letter-spacing:1px;}
.stat .value{font-size:1.8rem;font-weight:800;color:#ff007f;margin-top:5px;}
.card{background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);border-radius:12px;padding:20px;margin-bottom:20px;}
.card h3{font-size:1rem;margin-bottom:12px;color:#00d4ff;display:flex;align-items:center;gap:8px;}
.btn{padding:10px 18px;border:none;border-radius:8px;font-weight:600;cursor:pointer;font-size:0.85rem;display:inline-flex;align-items:center;gap:6px;transition:0.3s;}
.btn-primary{background:linear-gradient(135deg,#ff007f,#7f00ff);color:#fff;}
.btn-primary:hover{transform:translateY(-2px);box-shadow:0 5px 20px rgba(255,0,127,0.3);}
.btn-danger{background:linear-gradient(135deg,#ff0844,#ffb199);color:#fff;}
.btn-success{background:linear-gradient(135deg,#00b09b,#96c93d);color:#fff;}
.btn-outline{background:transparent;border:1px solid rgba(255,255,255,0.15);color:#fff;}
.btn-outline:hover{background:rgba(255,255,255,0.05);}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:8px;margin-top:10px;}
.acc-item{background:rgba(0,212,255,0.05);padding:8px 12px;border-radius:8px;font-family:monospace;font-size:0.8rem;color:#00d4ff;border:1px solid rgba(0,212,255,0.1);}
.toast{position:fixed;bottom:20px;right:20px;background:rgba(0,0,0,0.9);padding:14px 20px;border-radius:10px;border-left:4px solid #00ffcc;z-index:999;max-width:320px;}
.toast.error{border-left-color:#ff4444;}
.upload-area{border:2px dashed rgba(255,255,255,0.1);border-radius:10px;padding:20px;text-align:center;cursor:pointer;transition:0.3s;}
.upload-area:hover{border-color:#ff007f;background:rgba(255,0,127,0.03);}
.upload-area.dragover{border-color:#ff007f;background:rgba(255,0,127,0.05);}
.upload-area p{font-size:0.85rem;color:rgba(255,255,255,0.4);margin-top:8px;}
.btn-sm{padding:6px 12px;font-size:0.75rem;}
.chat-row{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px;}
.chat-row input, .chat-row select{flex:1;min-width:120px;padding:10px 14px;background:rgba(0,0,0,0.4);border:1px solid rgba(255,255,255,0.1);border-radius:8px;color:#fff;outline:none;font-size:0.85rem;}
.chat-row input:focus{border-color:#00d4ff;}
</style></head><body>
<div class="container">
<div class="header">
<div><div class="logo">🎯 MAHIR GROUP PANEL</div>
<div style="color:rgba(255,255,255,0.3);font-size:0.8rem;">Auto 10s Cycle • Auto 5min Restart • Auto Reconnect • /help Command</div></div>
<div><a href="/logout" class="btn btn-outline btn-sm">LOGOUT</a></div>
</div>
<div class="stats">
<div class="stat"><div class="label">Connected</div><div class="value" id="accCount">0</div></div>
<div class="stat"><div class="label">Total</div><div class="value" id="totalCount">0</div></div>
<div class="stat"><div class="label">Auto Cycle</div><div class="value" style="font-size:1.2rem;" id="autoStatus">RUNNING (10s)</div></div>
</div>
<div class="card"><h3>⚡ CONTROLS</h3>
<div style="display:flex;gap:10px;flex-wrap:wrap;">
<button class="btn btn-primary" onclick="sendGroupNow()">🚀 Create Group Now</button>
<button class="btn btn-warning" onclick="toggleAuto()" id="toggleBtn" style="background:linear-gradient(135deg,#ffaa00,#ff6600);color:#000;">⏸ Stop Auto</button>
<button class="btn btn-success" onclick="resetAccounts()">🔄 Reset Accounts</button>
<button class="btn btn-outline" onclick="restartAllNow()">♻️ Restart All Now</button>
</div></div>

<div class="card"><h3>💬 CHAT CONTROLS</h3>
<div class="chat-row">
<input type="text" id="chatMsg" placeholder="Enter message..." value="MAHIR GROUP 🔥">
<select id="chatType">
<option value="squad">Squad Chat</option>
<option value="global">Global Chat</option>
</select>
<button class="btn btn-primary" onclick="sendChat()">📨 Send Chat</button>
</div>
<div class="chat-row" style="margin-top:10px;">
<button class="btn btn-outline" onclick="sendHelpNow()">📖 Send /help Reply</button>
<button class="btn btn-outline" onclick="sendInfoNow()">ℹ️ Send /info Reply</button>
<button class="btn btn-outline" onclick="sendRulesNow()">📜 Send /rules Reply</button>
</div></div>

<div class="card"><h3>🎨 CRAFTLAND SHARE</h3>
<div class="chat-row">
<input type="text" id="craftMapCode" placeholder="Map Code (e.g. 12345)">
<input type="text" id="craftTargetId" placeholder="Target UID">
<button class="btn btn-primary" onclick="sendCraftland()">🗺️ Share Map</button>
</div></div>

<div class="card"><h3>🔄 EXTRA ACTIONS</h3>
<div style="display:flex;gap:10px;flex-wrap:wrap;">
<button class="btn btn-outline" onclick="sendRefresh()">♻️ Refresh All</button>
</div></div>

<div class="card"><h3>📁 UPLOAD accs.txt</h3>
<div class="upload-area" id="uploadArea">
<p>📁 Click or Drag & Drop accs.txt</p>
<input type="file" id="fileInput" accept=".txt" style="display:none;">
<div id="uploadStatus" style="font-size:0.75rem;color:rgba(255,255,255,0.3);margin-top:8px;">No file uploaded</div>
</div></div>
<div class="card"><h3>👥 CONNECTED ACCOUNTS</h3>
<div class="grid" id="accGrid"><div style="color:rgba(255,255,255,0.3);">Loading...</div></div></div>
<div class="card"><h3>📜 LOGS</h3>
<div id="logBox" style="background:rgba(0,0,0,0.4);border-radius:8px;padding:12px;font-family:monospace;font-size:0.75rem;color:#00ffcc;height:200px;overflow-y:auto;">
<div>[System] MAHIR GROUP PANEL ready</div></div></div>
</div>
<script>
function toast(m,t='info'){const e=document.createElement('div');e.className='toast'+(t==='error'?' error':'');e.textContent=m;document.body.appendChild(e);setTimeout(()=>e.remove(),3500);}
function log(m){const b=document.getElementById('logBox');const d=document.createElement('div');d.textContent=`[${new Date().toLocaleTimeString()}] ${m}`;b.appendChild(d);b.scrollTop=b.scrollHeight;if(b.children.length>100)b.removeChild(b.firstChild);}
function refreshStatus(){fetch('/api/status').then(r=>r.json()).then(d=>{
if(d.success){document.getElementById('accCount').textContent=d.connected;
document.getElementById('totalCount').textContent=d.total;
document.getElementById('autoStatus').textContent=d.auto?'RUNNING (10s)':'PAUSED';
document.getElementById('toggleBtn').innerHTML=d.auto?'⏸ Stop Auto':'▶️ Start Auto';
const g=document.getElementById('accGrid');
if(d.accounts.length===0){g.innerHTML='<div style="color:rgba(255,255,255,0.3);">No accounts connected</div>';}
else{g.innerHTML=d.accounts.map(a=>`<div class="acc-item">${a.uid} 🟢</div>`).join('');}}}).catch(()=>{});}
function sendGroupNow(){log('🚀 Creating group...');fetch('/api/send-group',{method:'POST'}).then(r=>r.json()).then(d=>{
if(d.success){toast('✅ '+d.message,'success');log('✅ '+d.message);}else toast('❌ '+d.message,'error');});}
function resetAccounts(){if(!confirm('⚠️ Reset all accounts?'))return;log('🔄 Resetting...');fetch('/api/reset',{method:'POST'}).then(r=>r.json()).then(d=>{
if(d.success){toast('✅ '+d.message,'success');log('✅ '+d.message);}else toast('❌ '+d.message,'error');});}
function toggleAuto(){fetch('/api/toggle-auto',{method:'POST'}).then(r=>r.json()).then(d=>{
if(d.success){toast((d.auto?'▶️ ':'⏸ ')+d.message,'success');log((d.auto?'▶️ ':'⏸ ')+d.message);refreshStatus();}});}
function restartAllNow(){if(!confirm('♻️ Restart ALL accounts now?'))return;log('♻️ Restarting all...');fetch('/api/restart-all',{method:'POST'}).then(r=>r.json()).then(d=>{
if(d.success){toast('✅ '+d.message,'success');log('✅ '+d.message);}else toast('❌ '+d.message,'error');});}
function sendHelpNow(){fetch('/api/send-help',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({type:'help'})}).then(r=>r.json()).then(d=>{
if(d.success){toast('✅ '+d.message,'success');log('📖 '+d.message);}else toast('❌ '+d.message,'error');});}
function sendInfoNow(){fetch('/api/send-help',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({type:'info'})}).then(r=>r.json()).then(d=>{
if(d.success){toast('✅ '+d.message,'success');log('ℹ️ '+d.message);}else toast('❌ '+d.message,'error');});}
function sendRulesNow(){fetch('/api/send-help',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({type:'rules'})}).then(r=>r.json()).then(d=>{
if(d.success){toast('✅ '+d.message,'success');log('📜 '+d.message);}else toast('❌ '+d.message,'error');});}
function sendChat(){
  const msg=document.getElementById('chatMsg').value;
  const type=document.getElementById('chatType').value;
  if(!msg){toast('❌ Enter message','error');return;}
  log(`📨 Sending ${type} chat: ${msg}`);
  fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:msg,type:type})})
  .then(r=>r.json()).then(d=>{
    if(d.success){toast('✅ '+d.message,'success');log('✅ '+d.message);}
    else toast('❌ '+d.message,'error');
  });
}
function sendCraftland(){
  const code=document.getElementById('craftMapCode').value;
  const tid=document.getElementById('craftTargetId').value;
  if(!code||!tid){toast('❌ Map code & target UID required','error');return;}
  fetch('/api/craftland',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({map_code:code,target_id:tid})})
  .then(r=>r.json()).then(d=>{
    if(d.success){toast('✅ '+d.message,'success');log('✅ '+d.message);}
    else toast('❌ '+d.message,'error');
  });
}
function sendRefresh(){fetch('/api/refresh',{method:'POST'}).then(r=>r.json()).then(d=>{
  if(d.success){toast('✅ '+d.message,'success');log('✅ '+d.message);}
  else toast('❌ '+d.message,'error');});}
const ua=document.getElementById('uploadArea'),fi=document.getElementById('fileInput');
ua.addEventListener('click',()=>fi.click());
ua.addEventListener('dragover',e=>{e.preventDefault();ua.classList.add('dragover');});
ua.addEventListener('dragleave',()=>ua.classList.remove('dragover'));
ua.addEventListener('drop',e=>{e.preventDefault();ua.classList.remove('dragover');if(e.dataTransfer.files.length)uploadFile(e.dataTransfer.files[0]);});
fi.addEventListener('change',function(){if(this.files.length)uploadFile(this.files[0]);});
function uploadFile(f){const fd=new FormData();fd.append('file',f);
document.getElementById('uploadStatus').textContent='⏳ Uploading...';
fetch('/api/upload-accs',{method:'POST',body:fd}).then(r=>r.json()).then(d=>{
if(d.success){document.getElementById('uploadStatus').innerHTML=`✅ ${d.total} accounts loaded`;
toast('✅ '+d.message,'success');log('✅ '+d.message);refreshStatus();}
else{document.getElementById('uploadStatus').textContent='❌ '+d.message;toast('❌ '+d.message,'error');}});}
setInterval(refreshStatus,3000);refreshStatus();
</script></body></html>'''


def login_required(f):
    @wraps(f)
    def w(*a, **k):
        if not session.get('logged_in'): return redirect(url_for('login_page'))
        return f(*a, **k)
    return w


@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('index'))
        return render_template_string(LOGIN_TEMPLATE, error='Invalid Password!')
    return render_template_string(LOGIN_TEMPLATE, error=None)


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login_page'))


@app.route('/')
@login_required
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/status')
@login_required
def api_status():
    with connected_clients_lock:
        uids = list(connected_clients.keys())
    return jsonify({'success': True, 'connected': len(uids), 'total': len(ACCOUNTS),
                    'auto': auto_running,
                    'accounts': [{'uid': u, 'online': True} for u in uids]})


@app.route('/api/send-group', methods=['POST'])
@login_required
def api_send_group():
    try:
        s, t = create_group_with_all_accounts()
        return jsonify({'success': s > 0, 'message': f'Sent from {s}/{t} accounts'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/reset', methods=['POST'])
@login_required
def api_reset():
    try:
        ok, msg = reset_accounts()
        return jsonify({'success': ok, 'message': msg})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/toggle-auto', methods=['POST'])
@login_required
def api_toggle_auto():
    global auto_running
    auto_running = not auto_running
    return jsonify({'success': True, 'auto': auto_running,
                    'message': 'Auto cycle ' + ('started' if auto_running else 'stopped')})


@app.route('/api/restart-all', methods=['POST'])
@login_required
def api_restart_all():
    try:
        with account_lock:
            uids = list(account_objects.keys())
        for uid in uids:
            try:
                with account_lock:
                    obj = account_objects.get(uid)
                if obj: obj.stop()
            except: pass
        with connected_clients_lock:
            connected_clients.clear()
        with account_lock:
            account_objects.clear()
        time.sleep(1)
        run_accounts()
        return jsonify({'success': True, 'message': f'Restart triggered for {len(ACCOUNTS)} accounts'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/send-help', methods=['POST'])
@login_required
def api_send_help():
    """ম্যানুয়ালি গ্রুপে help/info/rules পাঠায়"""
    try:
        data = request.get_json() or {}
        htype = (data.get('type') or 'help').lower()

        if htype == 'help': text = HELP_MESSAGE
        elif htype == 'info': text = INFO_MESSAGE
        elif htype == 'rules': text = RULES_MESSAGE
        else: return jsonify({'success': False, 'message': 'Unknown type'}), 400

        with connected_clients_lock:
            clients = list(connected_clients.values())
        ok = 0
        for c in clients:
            if _send_group_message(c, text):
                ok += 1
            time.sleep(0.05)
        return jsonify({'success': ok > 0, 'message': f'{htype} sent {ok}/{len(clients)}'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    try:
        data = request.get_json() or {}
        msg = data.get('message', '').strip()
        ctype = data.get('type', 'squad')
        if not msg:
            return jsonify({'success': False, 'message': 'Empty message'}), 400
        if ctype == 'global':
            ok, total = broadcast_global_chat(msg)
            return jsonify({'success': ok > 0, 'message': f'Global chat sent {ok}/{total}'})
        else:
            ok, total = broadcast_squad_chat(msg, chat_type=1, squad_id="0")
            return jsonify({'success': ok > 0, 'message': f'Squad chat sent {ok}/{total}'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/craftland', methods=['POST'])
@login_required
def api_craftland():
    try:
        data = request.get_json() or {}
        map_code = str(data.get('map_code', '')).strip()
        target_id = str(data.get('target_id', '')).strip()
        if not map_code or not target_id:
            return jsonify({'success': False, 'message': 'map_code & target_id required'}), 400
        with connected_clients_lock:
            clients = list(connected_clients.values())
        ok = 0
        for c in clients:
            r, _ = send_craftland_share_on_client(c, target_id, map_code)
            if r: ok += 1
            time.sleep(0.05)
        return jsonify({'success': ok > 0, 'message': f'Craftland shared {ok}/{len(clients)}'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/refresh', methods=['POST'])
@login_required
def api_refresh():
    try:
        with connected_clients_lock:
            clients = list(connected_clients.values())
        ok = 0
        for c in clients:
            r, _ = send_refresh_on_client(c)
            if r: ok += 1
            time.sleep(0.05)
        return jsonify({'success': ok > 0, 'message': f'Refresh sent {ok}/{len(clients)}'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/upload-accs', methods=['POST'])
@login_required
def api_upload_accs():
    if 'file' not in request.files: return jsonify({'success': False, 'message': 'No file'}), 400
    f = request.files['file']
    if not f.filename.endswith('.txt'): return jsonify({'success': False, 'message': 'Only .txt'}), 400
    try:
        content = f.read().decode('utf-8')
        with open('accs.txt', 'w', encoding='utf-8') as fp: fp.write(content)
        global ACCOUNTS
        ACCOUNTS = load_accounts('accs.txt')
        Thread(target=run_accounts, daemon=True).start()
        return jsonify({'success': True, 'message': f'Uploaded {len(ACCOUNTS)} accounts. Logging in...', 'total': len(ACCOUNTS)})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/health')
def health(): return jsonify({'status': 'ok', 'connected': len(connected_clients), 'auto': auto_running})


# ==================== MAIN ====================
def main():
    print(f"""
    {C}{BOLD}
    ╔══════════════════════════════════════════════════════════════════════╗
    ║   🎯 MAHIR GROUP SYSTEM v5.0 (Help + Restart + Reconnect) 🎯         ║
    ║                                                                      ║
    ║     🔄 Auto Cycle: প্রতি ১০ সেকেন্ডে EXIT → RECREATE → RECRUIT       ║
    ║     ♻️  Auto Restart: প্রতি ৫ মিনিটে সব account restart              ║
    ║     🩺 Auto Reconnect: account বন্ধ হলে সাথে সাথে চালু               ║
    ║     📖 /help Command: গ্রুপে কেউ /help লিখলে সুন্দর মেসেজ           ║
    ║                                                                      ║
    ║     💬 Chat / Craftland / Refresh — xC4 থেকে                         ║
    ║     🌐 Web Panel: http://127.0.0.1:8080                             ║
    ║     🔑 Admin Pass: {ADMIN_PASSWORD}                                          ║
    ╚══════════════════════════════════════════════════════════════════════╝
    {RS}
    """)

    Thread(target=run_accounts, daemon=True).start()

    print(f"{Y}⏳ Waiting for accounts...{RS}")
    waited = 0
    while waited < 60:
        with connected_clients_lock:
            count = len(connected_clients)
        if count > 0:
            print(f"{G}✅ {count} accounts connected{RS}")
            break
        time.sleep(2); waited += 2

    time.sleep(3)
    create_group_with_all_accounts()

    # 🔄 Auto cycle (10s)
    Thread(target=auto_group_cycle_loop, daemon=True).start()

    # ♻️  Auto restart every 5 min
    Thread(target=auto_restart_all_loop, daemon=True).start()

    # 🩺 Auto reconnect dead clients every 5 sec
    Thread(target=auto_reconnect_dead_loop, daemon=True).start()

    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)


if __name__ == "__main__":
    try: import aiohttp
    except ImportError: os.system("pip install aiohttp")
    try: from protobuf_decoder.protobuf_decoder import Parser
    except ImportError: os.system("pip install protobuf-decoder")
    main()