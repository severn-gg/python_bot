import re
import mysql.connector
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# Validasi format nomor rekening: 00000-00-00000
def is_valid_rekening(rek):
    return re.fullmatch(r"\d{5}-\d{2}-\d{5}", rek)

# Koneksi database rekening (remote)
db_rekening = {
    'host': 'qh98k.h.filess.io',
    'port': 61002,
    'user': 'tengz_betweenwho',
    'password': 'e912d03d17534f7cfbc64a365eb0571b60b3af11',
    'database': 'tengz_betweenwho'
}

# Koneksi database histori (lokal)
db_histori = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '',
    'database': 'db_histori_local'
}

# Buat tabel histori jika belum ada
try:
    conn = mysql.connector.connect(**db_histori)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS histori_cek_saldo (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id BIGINT,
            username VARCHAR(255),
            first_name VARCHAR(255),
            last_name VARCHAR(255),
            nomor_rekening VARCHAR(20),
            saldo DECIMAL(15,2),
            waktu DATETIME
        )
    """)
    conn.commit()
    conn.close()
except mysql.connector.Error as e:
    print(f"[!] Gagal membuat tabel histori: {e}")

# Handler untuk /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📲 Silakan kirim nomor rekening Anda (format: 00000-00-00000).")

# Handler untuk /histori
async def histori(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        conn = mysql.connector.connect(**db_histori)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT nomor_rekening, saldo, waktu, username, first_name, last_name
            FROM histori_cek_saldo
            WHERE user_id = %s
            ORDER BY waktu DESC
            LIMIT 10
        """, (user_id,))
        results = cursor.fetchall()
        conn.close()

        if results:
            pesan = "📄 Histori pengecekan terakhir:\n"
            for rek, saldo, waktu, username, first_name, last_name in results:
                uname = f"@{username}" if username else "-"
                nama = f"{first_name} {last_name[0]}." if last_name else first_name
                waktu_str = waktu.strftime('%Y-%m-%d %H:%M')
                pesan += f"• {rek} | Rp{saldo:,.0f} | {waktu_str} | {uname} | {nama}\n"
        else:
            pesan = "ℹ️ Belum ada histori pengecekan ditemukan."

    except mysql.connector.Error as e:
        pesan = f"⚠️ Gagal mengambil histori: {e}"

    await update.message.reply_text(pesan)

# Handler pesan utama
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if not is_valid_rekening(text):
        await update.message.reply_text("❌ Format rekening tidak valid. Gunakan format: 00000-00-00000")
        return

    rekening = text
    try:
        conn = mysql.connector.connect(**db_rekening)
        cursor = conn.cursor()
        cursor.execute("SELECT saldo FROM Accounts WHERE account_number = %s", (rekening,))
        result = cursor.fetchone()
        conn.close()

        if result:
            saldo = result[0]
            await update.message.reply_text(f"✅ Saldo rekening {rekening} adalah Rp{saldo:,.2f}")

            # Simpan histori ke database lokal
            try:
                conn_hist = mysql.connector.connect(**db_histori)
                cursor_hist = conn_hist.cursor()
                cursor_hist.execute("""
                    INSERT INTO histori_cek_saldo (user_id, username, first_name, last_name, nomor_rekening, saldo, waktu)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    update.effective_user.id,
                    update.effective_user.username or "",
                    update.effective_user.first_name or "",
                    update.effective_user.last_name or "",
                    rekening,
                    saldo,
                    datetime.now()
                ))
                conn_hist.commit()
                conn_hist.close()
            except mysql.connector.Error as e:
                print(f"[!] Gagal menyimpan histori: {e}")
        else:
            await update.message.reply_text("❌ Nomor rekening tidak ditemukan.")
    except mysql.connector.Error as e:
        await update.message.reply_text(f"⚠️ Gagal mengakses database rekening: {e}")

# Jalankan bot
if __name__ == '__main__':
    app = ApplicationBuilder().token("7760891685:AAHi4jFDuAjKtQ9uvf_Kr8QsUGcrNGYQUp8").build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("histori", histori))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🤖 Bot cek saldo aktif dan siap digunakan...")
    app.run_polling()
