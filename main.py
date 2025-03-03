import os
import json
import re
import uuid
from telegram.constants import ParseMode
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

# Hardcoded Bot Token
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OWNER_ID = 7923505251

# Persistent storage file
DATA_FILE = "data.json"

# Load existing data
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
else:
    data = {"sudo_users": [], "blacklist": [], "reports": [], "appeals": [], "users": []}

def save_data():
    """Save the data persistently to JSON file."""
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type != "private":
        return
    
    user_id = update.message.from_user.id  # Get the user's ID
    
    # Check if user is not already in the data file
    if user_id not in data.get("users", []):
        data["users"].append(user_id)
        save_data()  # Save to the JSON file
    
    text = (
        "🚀 <b>Welcome to Covalent Federation Bot</b>\n\n"
        "This bot helps you report users for a Federation ban and submit appeals for unbans.\n\n"
        "📌 <b>How to Use</b>\n"
        "➖ <code>/report &lt;user_id&gt; &lt;reason&gt;</code> – Report a user for misconduct\n"
        "➖ <code>/appeal &lt;user_id&gt; &lt;reason&gt;</code> – Request a review of your ban\n\n"
        "⚠️ <b>Important Notes</b>\n"
        "❌ False reports may result in a blacklist from using this bot.\n"
        "📸 Ensure you provide a valid reason with supporting evidence.\n\n"
        "💬 Need help? Contact us at <b>@CovalentOS</b>."
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat_id in data["blacklist"]:  # Access blacklist properly
        await update.message.reply_text("🚫 <b>You are blacklisted from reporting.</b>", parse_mode="HTML")
        return

    args = context.args
    if len(args) < 2 or not re.fullmatch(r"\d+", args[0]):
        await update.message.reply_text("⚠️ <b>Usage:</b> <code>/report &lt;user_id&gt; &lt;reason&gt;</code>", parse_mode="HTML")
        return

    report_id = str(uuid.uuid4())[:8]  # Generate short unique ID
    reported_user_id, reason = args[0], " ".join(args[1:])
    context.user_data['report'] = {
        'id': report_id,
        'reported_user_id': reported_user_id,
        'reason': reason,
        'evidence': [],
        'reporting_user_id': update.message.chat_id,
        'status': 'Pending'
    }

    keyboard = [[InlineKeyboardButton("✅ Yes", callback_data="report_evidence_yes"),
                 InlineKeyboardButton("❌ No", callback_data="report_evidence_no")]]
    
    await update.message.reply_text(
        "📌 <b>Do you want to submit evidence?</b>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

async def appeal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat_id in data["blacklist"]:  # Access blacklist properly
        await update.message.reply_text("🚫 <b>You are blacklisted from appealing.</b>", parse_mode="HTML")
        return

    args = context.args
    if len(args) < 2 or not re.fullmatch(r"\d+", args[0]):
        await update.message.reply_text("⚠️ <b>Usage:</b> <code>/appeal &lt;user_id&gt; &lt;reason&gt;</code>", parse_mode="HTML")
        return

    appeal_id = str(uuid.uuid4())[:8]  # Generate short unique ID
    appealed_user_id, reason = args[0], " ".join(args[1:])
    context.user_data['appeal'] = {
        'id': appeal_id,
        'appealed_user_id': appealed_user_id,
        'reason': reason,
        'evidence': [],
        'appealing_user_id': update.message.chat_id,
        'status': 'Pending'
    }

    keyboard = [[InlineKeyboardButton("✅ Yes", callback_data="appeal_evidence_yes"),
                 InlineKeyboardButton("❌ No", callback_data="appeal_evidence_no")]]
    
    await update.message.reply_text(
        "📌 <b>Do you want to submit evidence?</b>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Handle evidence submission
    if query.data == "report_evidence_yes":
        await query.message.reply_text("📸 <b>Send your evidence</b> (images/videos).", parse_mode="HTML")
    elif query.data == "report_evidence_no":
        data['reports'].append(context.user_data.pop('report', None))
        save_data()
        await query.message.reply_text("✅ <b>Your report has been submitted!</b>", parse_mode="HTML")
    elif query.data == "appeal_evidence_yes":
        await query.message.reply_text("📸 <b>Send your evidence</b> (images/videos).", parse_mode="HTML")
    elif query.data == "appeal_evidence_no":
        data['appeals'].append(context.user_data.pop('appeal', None))
        save_data()
        await query.message.reply_text("✅ <b>Your appeal has been submitted!</b>", parse_mode="HTML")
    
    # Handle delete actions
    elif query.data.startswith("delete_report_"):
        report_id = query.data.split("_")[-1]
        data['reports'] = [r for r in data['reports'] if r["id"] != report_id]
        save_data()
        await query.message.edit_text("🗑️ <b>Report deleted successfully.</b>", parse_mode="HTML")

    elif query.data.startswith("delete_appeal_"):
        appeal_id = query.data.split("_")[-1]
        data['appeals'] = [a for a in data['appeals'] if a["id"] != appeal_id]
        save_data()
        await query.message.edit_text("🗑️ <b>Appeal deleted successfully.</b>", parse_mode="HTML")

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.effective_attachment[-1].get_file()

    os.makedirs("evidence", exist_ok=True)
    file_path = f"evidence/{file.file_id}.jpg"
    await file.download_to_drive(file_path)

    if 'report' in context.user_data:
        context.user_data['report']['evidence'].append(file_path)
        await update.message.reply_text("📥 <b>Evidence received.</b> Send more or type <code>/done</code> if finished.", parse_mode="HTML")
    elif 'appeal' in context.user_data:
        context.user_data['appeal']['evidence'].append(file_path)
        await update.message.reply_text("📥 <b>Evidence received.</b> Send more or type <code>/done</code> if finished.", parse_mode="HTML")

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'report' in context.user_data:
        data['reports'].append(context.user_data.pop('report'))  # Append to the reports list in the data dictionary
        save_data()
        await update.message.reply_text("✅ <b>Your report has been submitted!</b>", parse_mode="HTML")
    elif 'appeal' in context.user_data:
        data['appeals'].append(context.user_data.pop('appeal'))  # Append to the appeals list in the data dictionary
        save_data()
        await update.message.reply_text("✅ <b>Your appeal has been submitted!</b>", parse_mode="HTML")

async def view_reports(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat_id not in data["sudo_users"] and update.message.chat_id != OWNER_ID:
        return
    
    for report in data['reports']:
        keyboard = [
            [InlineKeyboardButton("✅ Approve", callback_data=f"approve_report_{report['id']}"),
             InlineKeyboardButton("❌ Reject", callback_data=f"reject_report_{report['id']}")],
            [InlineKeyboardButton("📂 Check Evidence", callback_data=f"evidence_report_{report['id']}")],
            [InlineKeyboardButton("🗑 Delete", callback_data=f"delete_report_{report['id']}")]
        ]
        await update.message.reply_text(
            f"📝 <b>Report ID:</b> <code>{report['id']}</code>\n"
            f"👤 <b>Reported By:</b> <code>{report['reporting_user_id']}</code>\n"
            f"👤 <b>Reported User:</b> <code>{report['reported_user_id']}</code>\n"
            f"📌 <b>Reason:</b> {report['reason']}\n"
            f"📌 <b>Status:</b> <code>{report['status']}</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def view_appeals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat_id not in data["sudo_users"] and update.message.chat_id != OWNER_ID:
        return
    
    for appeal in data['appeals']:
        keyboard = [
            [InlineKeyboardButton("✅ Approve", callback_data=f"approve_appeal_{appeal['id']}"),
             InlineKeyboardButton("❌ Reject", callback_data=f"reject_appeal_{appeal['id']}")],
            [InlineKeyboardButton("📂 Check Evidence", callback_data=f"evidence_appeal_{appeal['id']}")],
            [InlineKeyboardButton("🗑 Delete", callback_data=f"delete_appeal_{appeal['id']}")]
        ]
        await update.message.reply_text(
            f"📝 <b>Appeal ID:</b> <code>{appeal['id']}</code>\n"
            f"👤 <b>Appealed By:</b> <code>{appeal['appealing_user_id']}</code>\n"
            f"👤 <b>Appealed User:</b> <code>{appeal['appealed_user_id']}</code>\n"
            f"📌 <b>Reason:</b> {appeal['reason']}\n"
            f"📌 <b>Status:</b> <code>{appeal['status']}</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def approve_or_reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, report_type, report_id = query.data.split("_")

    if report_type == "report":
        for report in data['reports']:
            if report["id"] == report_id:
                report["status"] = "Approved" if action == "approve" else "Rejected"
                save_data()
                await query.message.edit_text(
                    f"✅ <b>Report ID:</b> <code>{report_id}</code> has been <b>{action}d</b>.",
                    parse_mode="HTML"
                )
                return

    elif report_type == "appeal":
        for appeal in data['appeals']:
            if appeal["id"] == report_id:
                appeal["status"] = "Approved" if action == "approve" else "Rejected"
                save_data()
                await query.message.edit_text(
                    f"✅ <b>Appeal ID:</b> <code>{report_id}</code> has been <b>{action}d</b>.",
                    parse_mode="HTML"
                )
                return

async def check_evidence(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    report_type, report_id = query.data.split("_")[1:]
    evidence_list = []

    if report_type == "report":
        for report in data['reports']:
            if report["id"] == report_id:
                evidence_list = report["evidence"]
                break
    elif report_type == "appeal":
        for appeal in data['appeals']:
            if appeal["id"] == report_id:
                evidence_list = appeal["evidence"]
                break

    if not evidence_list:
        await query.message.reply_text("❌ <b>No evidence provided</b> for this request.", parse_mode="HTML")
    else:
        for file_path in evidence_list:
            if file_path.endswith((".jpg", ".jpeg", ".png", ".heic", ".webp", ".gif", ".heif", ".raw")):
                await query.message.reply_photo(photo=open(file_path, "rb"), caption="🖼 <b>Evidence Image</b>", parse_mode="HTML")
            elif file_path.endswith((".mp4", ".mov", ".avi", ".mkv")):
                await query.message.reply_video(video=open(file_path, "rb"), caption="🎥 <b>Evidence Video</b>", parse_mode="HTML")
            else:
                await query.message.reply_text(f"⚠️ <b>Unsupported file format:</b> <code>{file_path}</code>", parse_mode="HTML")

async def add_sudo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat_id != OWNER_ID:
        await update.message.reply_text(
            "❌ You do not have permission to perform this action!",
            parse_mode="HTML"
        )
        return

    args = context.args
    if args and re.fullmatch(r"\d+", args[0]):
        sudo_user_id = int(args[0])
        
        # Check if the user is already a sudo user
        if sudo_user_id not in data["sudo_users"]:
            data["sudo_users"].append(sudo_user_id)
            save_data()
            await update.message.reply_text(f"✅ <b>User {sudo_user_id} added as sudo user.</b>", parse_mode="HTML")
        else:
            await update.message.reply_text(f"⚠️ <b>User {sudo_user_id} is already a sudo user.</b>", parse_mode="HTML")
    else:
        await update.message.reply_text(
            "❌ Invalid input. Please provide a valid user ID.",
            parse_mode="HTML"
        )

async def remove_sudo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat_id != OWNER_ID:
        await update.message.reply_text(
            "❌ You do not have permission to perform this action!",
            parse_mode="HTML"
        )
        return

    args = context.args
    if not args or not re.fullmatch(r"\d+", args[0]):
        await update.message.reply_text(
            "❌ Invalid input. Please provide a valid user ID.",
            parse_mode="HTML"
        )
        return

    user_id = int(args[0])
    
    if user_id not in data["sudo_users"]:
        await update.message.reply_text(
            f"❌ <b>User ID:</b> <code>{user_id}</code> is not a sudo user.",
            parse_mode="HTML"
        )
        return

    data["sudo_users"].remove(user_id)
    save_data()

    await update.message.reply_text(
        f"❌ <b>Sudo user removed!</b>\n👤 <b>User ID:</b> <code>{user_id}</code>",
        parse_mode="HTML"
    )

async def blacklist_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🚫 Blacklist a user from using the bot."""
    if update.message.from_user.id not in data["sudo_users"] and update.message.from_user.id != OWNER_ID:
        return

    args = context.args
    if args and re.fullmatch(r"\d+", args[0]):
        user_id = int(args[0])
        data["blacklist"].append(user_id)
        save_data()
        await update.message.reply_text(
            f"🚫 <b>User Blacklisted</b>\n👤 <b>User ID:</b> <code>{user_id}</code>",
            parse_mode="HTML"
        )

async def unblacklist_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """✅ Remove a user from the blacklist."""
    if update.message.from_user.id not in data["sudo_users"] and update.message.from_user.id != OWNER_ID:
        return

    args = context.args
    if args and re.fullmatch(r"\d+", args[0]):
        user_id = int(args[0])
        if user_id in data["blacklist"]:
            data["blacklist"].remove(user_id)
            save_data()
            await update.message.reply_text(
                f"✅ <b>User Removed from Blacklist</b>\n👤 <b>User ID:</b> <code>{user_id}</code>",
                parse_mode="HTML"
            )
        else:
            await update.message.reply_text(
                f"ℹ️ <b>User Not Found in Blacklist</b>\n👤 <b>User ID:</b> <code>{user_id}</code>",
                parse_mode="HTML"
            )

async def view_blacklist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📜 View all blacklisted users."""
    if update.message.from_user.id not in data["sudo_users"] and update.message.from_user.id != OWNER_ID:
        return

    if not data["blacklist"]:
        await update.message.reply_text("✅ <b>No users are blacklisted.</b>", parse_mode="HTML")
    else:
        blacklist_text = "\n".join(f"👤 <code>{user_id}</code>" for user_id in blacklist)
        await update.message.reply_text(
            f"📜 <b>Blacklisted Users:</b>\n{blacklist_text}",
            parse_mode="HTML"
        )

async def message_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📩 Send a message from the bot to a user who reported or appealed."""
    if update.message.chat_id not in data["sudo_users"] and update.message.chat_id != OWNER_ID:
        return

    args = context.args
    if len(args) < 2 or not re.fullmatch(r"\d+", args[0]):
        await update.message.reply_text(
            "❌ <b>Invalid Usage!</b>\n📝 <b>Usage:</b> <code>/message &lt;user_id&gt; &lt;text&gt;</code>",
            parse_mode="HTML"
        )
        return

    user_id = int(args[0])
    message_text = " ".join(args[1:])

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"📩 <b>Message from Admin:</b>\n\n{message_text}",
            parse_mode="HTML"
        )
        await update.message.reply_text(
            f"✅ <b>Message Sent!</b>\n👤 <b>User ID:</b> <code>{user_id}</code>",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(
            f"⚠️ <b>Failed to Send Message</b>\n💬 <b>Error:</b> <code>{str(e)}</code>",
            parse_mode="HTML"
        )

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    # Check if the user is the owner only
    if user_id != OWNER_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    # Get the message to broadcast
    broadcast_message = ' '.join(context.args)
    
    if not broadcast_message:
        await update.message.reply_text("Please provide a message to broadcast.")
        return

    # Format the broadcast message with HTML (bold, monospaced, and emojis)
    formatted_message = (
        f"💬 <b>Broadcast Message:</b>\n\n"
        f"<b>{broadcast_message}</b>\n\n"
    )

    # Send the broadcast message to all users
    for user in data.get("users", []):
        try:
            await context.bot.send_message(user, formatted_message, parse_mode=ParseMode.HTML)
        except Exception as e:
            print(f"Error sending message to user {user}: {e}")
    
    await update.message.reply_text("📤 Broadcast sent successfully!")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("report", report, filters=filters.ChatType.PRIVATE))
    app.add_handler(CommandHandler("appeal", appeal, filters=filters.ChatType.PRIVATE))
    app.add_handler(CallbackQueryHandler(approve_or_reject, pattern="^(approve|reject)_(report|appeal)_.+$"))
    app.add_handler(CallbackQueryHandler(check_evidence, pattern="^evidence_(report|appeal)_.+$"))
    app.add_handler(CallbackQueryHandler(button_handler))  # This should come after specific handlers
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, handle_media))
    app.add_handler(CommandHandler("done", done))
    app.add_handler(CommandHandler("viewreports", view_reports))
    app.add_handler(CommandHandler("viewappeals", view_appeals))
    app.add_handler(CommandHandler("addsudo", add_sudo))
    app.add_handler(CommandHandler("removesudo", remove_sudo))
    app.add_handler(CommandHandler("blacklist", blacklist_user))
    app.add_handler(CommandHandler("unblacklist", unblacklist_user))
    app.add_handler(CommandHandler("viewblacklist", view_blacklist))
    app.add_handler(CommandHandler("message", message_user))
    app.add_handler(CommandHandler("broadcast", broadcast))
    
    app.run_polling()

if __name__ == "__main__":
    main()