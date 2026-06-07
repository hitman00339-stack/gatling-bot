import re
import asyncio
import time
import os
import random
from pathlib import Path
from datetime import datetime
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.functions.messages import ImportChatInviteRequest
import aiohttp

# ——— TELEGRAM SETUP ———
api_id   = int(os.environ.get("API_ID",   "20725219"))
api_hash = os.environ.get("API_HASH", "6ac4741d62d33dcfc7adb6ef8aa09c45")

# ✅ StringSession for Railway
SESSION_STRING = os.environ.get("SESSION_STRING", "")

if SESSION_STRING:
    print("✅ Using StringSession from environment.")
    client = TelegramClient(StringSession(SESSION_STRING), api_id, api_hash)
else:
    print("⚠️ No SESSION_STRING - using local session file.")
    client = TelegramClient("session_auto_redeemer", api_id, api_hash)

# ——— CHANNELS ———
CHANNELS = [
    "https://t.me/+ktX-TUUVs5YxYzdl",
    "https://t.me/+IzPzNVO1kGo2NDc0"
]

# ——— FILE PATHS ———
TXT_PATH   = os.environ.get("TXT_PATH", r"C:\Users\LGP\Desktop\MTM\ALL NOS APRIL.txt")
LOG_FILE   = Path(__file__).with_name("redeemed_urls.log")
SUBMIT_URL = "https://mantripk.com/lottery-backend/glserver/cash/getRedPacket"

# ——— SPEED SETTINGS ———
FIRE_RATE      = 0.004
MAX_CONCURRENT = 100

TOO_FAST_KEYWORDS   = ["too fast", "frequent", "limit", "slow", "操作太频繁", "请稍后", "try again", "wait"]
FAKE_CODE_KEYWORDS  = ["invalid", "does not exist", "not found", "error", "不存在"]
EMPTY_GIFT_KEYWORDS = ["over", "empty", "finished", "0", "已经领完"]

# ——— GLOBALS ———
GLOBAL_SESSION    = None
PRELOADED_NUMBERS = []
RESOLVED_CHANNELS = []

USER_AGENTS = [
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12; Samsung Galaxy S21) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
]

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  HELPERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def log(msg: str):
    try:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat()}  {msg}\n")
    except:
        print(f"LOG: {msg}")

def validate_number(mobile):
    return re.match(r"^\+91\d{10}$", mobile) is not None

def load_numbers_to_memory():
    global PRELOADED_NUMBERS
    numbers = []
    try:
        # ── 1. Try PHONE_NUMBERS env variable ──
        numbers_env = os.environ.get("PHONE_NUMBERS", "")
        if numbers_env:
            for line in numbers_env.split(","):
                line = line.strip().replace(" ", "").replace("+91", "")
                if line.isdigit() and len(line) == 10:
                    formatted = "+91" + line
                    if validate_number(formatted):
                        numbers.append(formatted)
                        if len(numbers) >= 1200:
                            break
            PRELOADED_NUMBERS = numbers
            print(f"✅ Pre-loaded {len(PRELOADED_NUMBERS)} numbers from ENV.")
            return

        # ── 2. Try numbers.txt in same folder ──
        local_txt = Path(__file__).with_name("numbers.txt")
        if local_txt.exists():
            with open(local_txt, 'r', encoding='utf-8') as f:
                for line in f:
                    if len(numbers) >= 1200:
                        break
                    line = line.strip().replace(" ", "").replace("+91", "")
                    if line.isdigit() and len(line) == 10:
                        formatted = "+91" + line
                        if validate_number(formatted):
                            numbers.append(formatted)
            PRELOADED_NUMBERS = numbers
            print(f"✅ Pre-loaded {len(PRELOADED_NUMBERS)} numbers from numbers.txt.")
            return

        # ── 3. Fallback to hardcoded path (local PC only) ──
        if os.path.exists(TXT_PATH):
            with open(TXT_PATH, 'r', encoding='utf-8') as f:
                for line in f:
                    if len(numbers) >= 1200:
                        break
                    line = line.strip().replace(" ", "").replace("+91", "")
                    if line.isdigit() and len(line) == 10:
                        formatted = "+91" + line
                        if validate_number(formatted):
                            numbers.append(formatted)
            PRELOADED_NUMBERS = numbers
            print(f"✅ Pre-loaded {len(PRELOADED_NUMBERS)} numbers from TXT_PATH.")
            return

        print("❌ No numbers source found!")

    except Exception as e:
        print(f"❌ Error reading numbers: {e}")

def get_random_headers(gift_code: str, ip_index: int):
    fake_ip = f"103.45.{random.randint(1, 250)}.{ip_index % 250 + 1}"
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://mantricenter.com",
        "Referer": f"https://mantricenter.com/#/pages/person/gift?code={gift_code}",
        "X-Forwarded-For": fake_ip,
        "Connection": "keep-alive"
    }

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  PROBE + SUBMIT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def probe_code(code: str, test_number: str):
    payload = {"mobile": test_number, "code": code}
    try:
        async with GLOBAL_SESSION.post(
            SUBMIT_URL,
            data=payload,
            headers=get_random_headers(code, 0),
            timeout=5
        ) as response:
            if response.status == 200:
                data     = await response.json(content_type=None)
                res_msg  = data.get("resMsg", "").lower()
                res_code = data.get("res", -1)

                if any(kw in res_msg for kw in FAKE_CODE_KEYWORDS) and res_code != 1:
                    return code, False, False, res_msg
                if any(kw in res_msg for kw in EMPTY_GIFT_KEYWORDS):
                    return code, True, True, res_msg
                return code, True, False, res_msg

            elif response.status == 429:
                return code, True, False, "HTTP 429 Too Fast"

    except Exception as e:
        return code, False, False, f"Probe Exception: {e}"

    return code, False, False, "Connection Error"


async def submit_number(idx, mobile, gift_code, stats, retry_queue, semaphore):
    await asyncio.sleep(idx * FIRE_RATE)
    payload = {"mobile": mobile, "code": gift_code}
    headers = get_random_headers(gift_code, idx)

    try:
        async with semaphore:
            async with GLOBAL_SESSION.post(
                SUBMIT_URL,
                data=payload,
                headers=headers,
                timeout=10
            ) as response:

                if response.status == 429:
                    print(f"🔴 {mobile} | 429 RATE LIMIT")
                    retry_queue.append(mobile)
                    return

                if response.status == 200:
                    data     = await response.json(content_type=None)
                    res_msg  = data.get("resMsg", "")
                    res_code = data.get("res", -1)

                    if any(kw in res_msg.lower() for kw in TOO_FAST_KEYWORDS):
                        print(f"🐢 {mobile} | {res_msg}")
                        retry_queue.append(mobile)

                    elif res_code == 1 or "success" in res_msg.lower():
                        stats["success"] += 1
                        print(f"🎉 SUCCESS: {mobile} | {res_msg}")

                    elif any(kw in res_msg.lower() for kw in ["already", "used", "exist"]):
                        stats["already_used"] += 1
                        print(f"⚠️ {mobile} | {res_msg}")

                    elif any(kw in res_msg.lower() for kw in EMPTY_GIFT_KEYWORDS):
                        stats["empty"] += 1
                        print(f"🗑️ {mobile} | {res_msg}")

                    else:
                        stats["failed"] += 1
                        print(f"❌ {mobile} | {res_msg}")
                else:
                    stats["failed"] += 1
                    print(f"❌ {mobile} | HTTP ERROR {response.status}")

    except Exception as e:
        stats["failed"] += 1
        print(f"❌ {mobile} | CRASH: {str(e)[:50]}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  MAIN FIRE SEQUENCE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def process_real_code(gift_code: str):
    if not PRELOADED_NUMBERS:
        print("❌ No numbers loaded!")
        return

    numbers = list(PRELOADED_NUMBERS)
    random.shuffle(numbers)

    print(f"\n{'='*55}")
    print(f"🚀 GATLING GUN SEQUENCE: {gift_code}")
    print(f"📦 Numbers: {len(numbers)}")
    print(f"⏱️ Fire rate: {FIRE_RATE*1000:.1f}ms")
    print(f"{'='*55}\n")

    stats       = {"success": 0, "failed": 0, "already_used": 0, "empty": 0}
    retry_queue = []
    start       = time.time()
    semaphore   = asyncio.Semaphore(MAX_CONCURRENT)

    tasks = [
        submit_number(idx, m, gift_code, stats, retry_queue, semaphore)
        for idx, m in enumerate(numbers)
    ]
    await asyncio.gather(*tasks, return_exceptions=True)

    elapsed_wave1 = time.time() - start
    print(f"\n💥 Wave 1 done in {elapsed_wave1:.2f}s")
    print(
        f"✅ Success:{stats['success']} | "
        f"⚠️ Used:{stats['already_used']} | "
        f"🗑️ Empty:{stats['empty']} | "
        f"🔁 Retry:{len(retry_queue)}"
    )

    if retry_queue and stats["empty"] < 10:
        print(f"\n⏳ Retrying {len(retry_queue)} numbers...")
        await asyncio.sleep(1.0)
        retry_numbers = list(retry_queue)
        retry_queue.clear()
        tasks2 = [
            submit_number(idx, m, gift_code, stats, retry_queue, semaphore)
            for idx, m in enumerate(retry_numbers)
        ]
        await asyncio.gather(*tasks2, return_exceptions=True)

    elapsed = time.time() - start
    print(f"\n🏆 DONE in {elapsed:.2f}s | Total Success: {stats['success']}")
    log(
        f"CODE={gift_code} | Time={elapsed:.2f}s | "
        f"Success={stats['success']} | AlreadyUsed={stats['already_used']}"
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  TELEGRAM EVENT HANDLER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def on_new_message(event):
    message = (event.message.message or "").strip()

    try:
        chat = await event.get_chat()
        chat_title = getattr(chat, 'title', str(chat.id))
        print(f"📡 Message from: {chat_title}")
    except:
        pass

    codes = list(set(re.findall(r"code=([A-Za-z0-9]+)", message)))
    if not codes:
        return

    print(f"\n🔔 Found {len(codes)} potential code(s).")
    test_number = PRELOADED_NUMBERS[0] if PRELOADED_NUMBERS else "+919876543210"

    if len(codes) > 1:
        print("🕵️ Probing codes...")
        results = await asyncio.gather(*[probe_code(c, test_number) for c in codes])

        real_code = None
        for code, is_real, is_empty, msg in results:
            if is_real and is_empty:
                print(f"🗑️ Real but EMPTY: {code} ({msg})")
            elif is_real and not is_empty:
                real_code = code
                print(f"🎯 ACTIVE CODE: {real_code} ({msg})")
                break

        if real_code:
            await process_real_code(real_code)
        else:
            print("❌ All codes fake or empty.")
    else:
        code, is_real, is_empty, msg = await probe_code(codes[0], test_number)
        if is_real and not is_empty:
            print(f"🎯 Code active! ({msg})")
            await process_real_code(codes[0])
        else:
            print(f"❌ Code invalid or empty. ({msg})")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CHANNEL RESOLVER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def resolve_and_join_channel(invite_url: str):
    try:
        hash_match = re.search(r"t\.me/\+([A-Za-z0-9_-]+)", invite_url)
        if not hash_match:
            hash_match = re.search(r"t\.me/joinchat/([A-Za-z0-9_-]+)", invite_url)

        if not hash_match:
            print(f"❌ Cannot extract hash from: {invite_url}")
            return None

        invite_hash = hash_match.group(1)

        try:
            result = await client(ImportChatInviteRequest(invite_hash))
            if hasattr(result, 'chats') and result.chats:
                entity = result.chats[0]
                print(f"✅ Joined: {entity.title} (ID: {entity.id})")
                return entity
        except Exception as join_err:
            err_str = str(join_err).lower()
            if "already" in err_str or "user_already" in err_str:
                print(f"ℹ️ Already a member: {invite_url}")
            else:
                print(f"⚠️ Join result: {join_err}")

        try:
            entity = await client.get_entity(invite_url)
            if entity:
                print(f"✅ Resolved: {getattr(entity, 'title', entity.id)}")
                return entity
        except Exception as get_err:
            print(f"❌ get_entity failed: {get_err}")

        return None

    except Exception as e:
        print(f"❌ Channel resolve error: {e}")
        return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  MAIN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def main():
    global GLOBAL_SESSION, RESOLVED_CHANNELS

    print("⚙️ INITIALIZING GATLING GUN BOT...")
    load_numbers_to_memory()

    connector = aiohttp.TCPConnector(
        limit=MAX_CONCURRENT,
        ssl=False,
        keepalive_timeout=60
    )
    GLOBAL_SESSION = aiohttp.ClientSession(connector=connector)

    try:
        await GLOBAL_SESSION.options("https://mantripk.com")
        print("✅ Server connection OK.")
    except Exception:
        pass

    await client.start()
    print("✅ Telegram client started.")

    for ch in CHANNELS:
        entity = await resolve_and_join_channel(ch)
        if entity:
            RESOLVED_CHANNELS.append(entity)
        else:
            print(f"❌ Could not resolve: {ch}")

    if not RESOLVED_CHANNELS:
        print("❌ No channels resolved! Exiting.")
        await GLOBAL_SESSION.close()
        return

    for entity in RESOLVED_CHANNELS:
        client.add_event_handler(
            on_new_message,
            events.NewMessage(chats=[entity.id])
        )
        print(f"🎯 Listening: {getattr(entity, 'title', entity.id)}")

    print(f"\n👂 Locked on {len(RESOLVED_CHANNELS)} channels. Waiting...\n")

    try:
        await client.run_until_disconnected()
    finally:
        await GLOBAL_SESSION.close()


if __name__ == "__main__":
    asyncio.run(main())