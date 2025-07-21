import re
import mysql.connector
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# Konfigurasi database
db_config = {
    'host': 'qh98k.h.filess.io',
    'port': 61002,
    'user': 'tengz_betweenwho',
    'password': 'e912d03d17534f7cfbc64a365eb0571b60b3af11',
    'database': 'tengz_betweenwho'
}

def connect_db():
    return mysql.connector.connect(**db_config)

def is_valid_rekening(rek: str) -> bool:
    return re.fullmatch(r"\d{5}-\d{2}-\d{5}", rek)

def ensure_histori_table():
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS histori_cek_saldo (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT,
                username VARCHAR(255),
                account_number VARCHAR(20),
                saldo INT,
                waktu DATETIME
            );
        """)
        conn.commit()
        cursor.close()
        conn.close()
    except mysql.connector.Error as err:
        print("Gagal membuat tabel histori:", err)

# /start handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Silakan kirim nomor rekening Anda (format: 00000-00-00000).",
        parse_mode="Markdown"
    )

# /histori handler
async def histori(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT account_number, saldo, waktu FROM histori_cek_saldo
            WHERE user_id = %s
            ORDER BY waktu DESC LIMIT 5
        """, (user_id,))
        rows = cursor.fetchall()
        if rows:
            msg = "📜 Histori cek saldo terakhir:\n\n"
            for row in rows:
                rek, saldo, waktu = row
                waktu_str = waktu.strftime("%d-%m-%Y %H:%M")
                msg += f"• {rek} - Rp{saldo:,} ({waktu_str})\n"
            await update.message.reply_text(msg, parse_mode="Markdown")
        else:
            await update.message.reply_text("📭 Belum ada histori cek saldo.")
        cursor.close()
        conn.close()
    except mysql.connector.Error as err:
        await update.message.reply_text(f"⚠️ Kesalahan saat akses histori:\n`{err}`", parse_mode="Markdown")

# Handler untuk pesan biasa
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if re.fullmatch(r"(?i)halo", text):
        await update.message.reply_text(
            "👋 Silakan kirim nomor rekening Anda (format: 00000-00-00000).",
            parse_mode="Markdown"
        )
        return

    if is_valid_rekening(text):
        rekening = text
        try:
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute("SELECT saldo FROM Accounts WHERE account_number = %s", (rekening,))
            result = cursor.fetchone()

            if result:
                saldo = result[0]
                await update.message.reply_text(
                    f"✅ Nomor Rekening: {rekening}\n💰 Saldo Anda: Rp{saldo:,}",
                    parse_mode="Markdown"
                )

                # Simpan histori
                cursor.execute("""
                    INSERT INTO histori_cek_saldo (user_id, username, account_number, saldo, waktu)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    update.effective_user.id,
                    update.effective_user.username or "",
                    rekening,
                    saldo,
                    datetime.now()
                ))
                conn.commit()

                
            else:
                cursor.execute("SELECT account_number FROM Accounts")
                daftar = [f"{row[0]}" for row in cursor.fetchall()]
                daftar_joined = "\n".join(daftar)
                await update.message.reply_text(
                    f"❌ Nomor rekening tidak ditemukan.\n\n📋 Daftar tersedia:\n{daftar_joined}",
                    parse_mode="Markdown"
                )
            cursor.close()
            conn.close()
        except mysql.connector.Error as err:
            await update.message.reply_text(f"⚠️ Terjadi kesalahan database:\n`{err}`", parse_mode="Markdown")
        return

    await update.message.reply_text(
        "⚠️ Format salah. Gunakan format: 00000-00-00000.",
        parse_mode="Markdown"
    )

# MAIN
if __name__ == '__main__':
    ensure_histori_table()
    app = ApplicationBuilder().token("7760891685:AAHi4jFDuAjKtQ9uvf_Kr8QsUGcrNGYQUp8").build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("histori", histori))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🤖 Bot cek saldo aktif...")
    app.run_polling()
