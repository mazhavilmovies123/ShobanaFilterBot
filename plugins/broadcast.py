from pyrogram import Client, filters
import datetime
import time
from database.users_chats_db import db
from info import ADMINS
from utils import broadcast_messages
import asyncio

# =============================
# ⚙️ CONFIGURATION
# =============================
BROADCAST_BATCH_SIZE = 500  # Process 500 users at a time
BROADCAST_SLEEP = 1         # Delay to avoid flood limits


# =============================
# 🚀 BROADCAST HANDLER
# =============================
@Client.on_message(filters.command("broadcast") & filters.user(ADMINS) & filters.reply)
async def broadcast(bot, message):
    """Admin-only broadcast command that sends the replied message to all users."""

    users = await db.get_all_users()
    b_msg = message.reply_to_message

    # ⏳ Initial broadcast message
    sts = await message.reply_text("📢 **Broadcast Started!**\n\n🕒 Preparing messages...")

    start_time = time.time()
    total_users = await db.total_users_count()

    done, blocked, deleted, failed, success = 0, 0, 0, 0, 0

    # ==================================
    # 📬 Internal function to send message
    # ==================================
    async def send_message(user):
        nonlocal success, blocked, deleted, failed

        user_id = int(user["id"])
        pti, status = await broadcast_messages(user_id, b_msg)

        if pti:
            success += 1
        else:
            if status == "Blocked":
                blocked += 1
                await db.delete_user(user_id)
            elif status == "Deleted":
                deleted += 1
                await db.delete_user(user_id)
            else:
                failed += 1

    # =============================
    # 🔁 Broadcasting Loop
    # =============================
    tasks = []
    async for user in users:
        tasks.append(send_message(user))
        done += 1

        # 🧩 Process batch
        if len(tasks) >= BROADCAST_BATCH_SIZE:
            await asyncio.gather(*tasks)
            tasks = []

            await sts.edit_text(
                f"📣 **Broadcast Progress**\n\n"
                f"👥 Total Users: `{total_users}`\n"
                f"✅ Completed: `{done}` / `{total_users}`\n\n"
                f"📬 Sent: `{success}`\n"
                f"🚫 Blocked: `{blocked}`\n"
                f"🗑️ Deleted: `{deleted}`\n"
                f"⚠️ Failed: `{failed}`\n\n"
                f"⏳ Please wait... Sending next batch 🔄"
            )

            await asyncio.sleep(BROADCAST_SLEEP)

    # Process any remaining tasks
    if tasks:
        await asyncio.gather(*tasks)

    # =============================
    # 🏁 Final Report
    # =============================
    time_taken = datetime.timedelta(seconds=int(time.time() - start_time))
    await sts.edit_text(
        f"✅ **Broadcast Completed Successfully!**\n\n"
        f"🕓 Time Taken: `{time_taken}`\n"
        f"👥 Total Users: `{total_users}`\n\n"
        f"📬 Success: `{success}`\n"
        f"🚫 Blocked: `{blocked}`\n"
        f"🗑️ Deleted: `{deleted}`\n"
        f"⚠️ Failed: `{failed}`\n\n"
        f"🎉 All done! Thank you for your patience 💪"
    )
