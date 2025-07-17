import re
import mysql.connector
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# Status per user untuk menentukan langkah1
user_state = {}

# Konfigurasi koneksi database server
db_config = {
    'host': 'qh98k.h.filess.io',
    'port': 61002,
    'user': 'tengz_betweenwho',
    'password': 'e912d03d17534f7cfbc64a365eb0571b60b3af11',
    'database': 'tengz_betweenwho'
}

def connect_db():
    return mysql.connector.connect(**db_config)

# Validasi format rekening (contoh: 00002-02-00006)
def is_valid_rekening(rekening: str) -> bool:
    return bool(re.fullmatch(r"\d{5}-\d{2}-\d{5}", rekening))

# Handler /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_state[user_id] = "awaiting_rekening"
    await update.message.reply_text("Selamat datang!\nSilakan kirim nomor rekening Anda (format: 00000-00-00000).")

# Handler pesan biasa
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()

    # Tahap awal jika user belum memulai
    if user_id not in user_state:
        user_state[user_id] = "awaiting_rekening"
        await update.message.reply_text("Silakan kirim nomor rekening Anda (format: 00000-00-00000).")
        return

    # Tahap pengisian rekening
    if user_state[user_id] == "awaiting_rekening":
        if not is_valid_rekening(text):
            await update.message.reply_text("❌ Format salah. Gunakan: 00000-00-00000")
            return

        try:
            conn = connect_db()
            cursor = conn.cursor()

            # Ambil saldo dari tabel Accounts
            cursor.execute("SELECT saldo FROM Accounts WHERE account_number = %s", (text,))
            result = cursor.fetchone()

            if result:
                saldo = result[0]
                await update.message.reply_text(f"✅ Rekening: {text}\n💰 Saldo Anda: Rp{saldo:,}")
            else:
                # Jika tidak ditemukan, bantu debug
                cursor.execute("SELECT account_number FROM Accounts")
                daftar = [row[0] for row in cursor.fetchall()]
                daftar_joined = "\n".join(daftar)
                await update.message.reply_text(f"ℹ️ Nomor rekening tidak ditemukan.\n📋 Tersedia:\n{daftar_joined}")

            user_state[user_id] = "done"
            cursor.close()
            conn.close()

        except mysql.connector.Error as err:
            await update.message.reply_text(f"⚠️ Terjadi kesalahan database:\n{err}")

# Main: Menjalankan aplikasi bot
if __name__ == '__main__':
    app = ApplicationBuilder().token("7760891685:AAHi4jFDuAjKtQ9uvf_Kr8QsUGcrNGYQUp8").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Bot sedang berjalan...")
    app.run_polling()
