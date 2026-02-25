import imaplib
import email
from email.header import decode_header


from google import genai
import os
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

GMAIL_EMAIL= os.getenv("GMAIL_EMAIL")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

client = genai.Client(api_key=GEMINI_API_KEY)

def connect_to_gmail():
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_EMAIL, GMAIL_APP_PASSWORD)
        print("Підключено до GMAIL!")
        return mail
    except Exception as e:
        print(f"Помилка підключення:{e}")
        return None

def decode_email_subject(subject):
    decoded_parts = decode_header(subject)
    decoded_subject = ""
    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            decoded_subject += part.decode(encoding or "utf-8", errors="ignore")
        else:
            decoded_subject += part
    return decoded_subject

def get_mail_body(msg):
    body = ""

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                try:
                    body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                    break
                except:
                    pass
    else:
        try:
            body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
        except:
            body = "Не вдалося декодувати текст"
    
    return body

def get_emails(mail, max_emails=5):
    try:
        mail.select("INBOX") # "SPAM", "SENT"
        status, messages = mail.search(None, "ALL") # "UNSEEN", "FROM ___@gmail.com"
        email_ids = messages[0].split()
        email_ids = email_ids[-max_emails:]

        emails = []
        for email_id in reversed(email_ids):
            status, msg_data = mail.fetch(email_id, "(RFC822)")
            # [b'1 (RFC822 {1234}', b'...email content...', b')']
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject = decode_email_subject(msg.get("Subject", "Буз теми"))
                    sende = msg.get("From", "невідомий")
                    date = msg.get("Date", "Невідома дата")
                    body = get_mail_body(msg)

                    emails.append({
                        "subject": subject,
                        "from": sende,
                        "date": date,
                        "body": body[:500]
                    })    
        return emails
    except Exception as e:
        print(f"Помилка отримання листів: {e}")
        return []

def analyze_emails_with_ai(emails):
    """Аналізує листи через Gemini AI"""
    if not emails:
        print("Немає листів")
        return

    print(f"\nЗнайдено {len(emails)} листів. Аналізую...\n")

    for i, email_data in enumerate(emails, 1):
        print(f"{'=' * 70}")
        print(f"Лист #{i}")
        print(f"{'=' * 70}")
        print(f"Від: {email_data['from']}")
        print(f"Тема: {email_data['subject']}")
        print(f"Дата: {email_data['date']}")
        print(f"\nПочаток тексту:\n{email_data['body'][:200]}...")

        # Аналіз через AI
        prompt = f"""
        Проаналізуй цей email українською мовою:

        Від: {email_data['from']}
        Тема: {email_data['subject']}
        Текст: {email_data['body']}

        Дай коротку відповідь:
        1. Про що лист (1 речення)
        2. Чи потрібна дія від мене? (так/ні, яка)
        3. Пріоритет (низький/середній/високий)
        """
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            print(f"\nАналіз AI:\n{response.text}")
        except Exception as e:
            print(f"\nПомилка AI: {e}")

        print(f"{'=' * 70}\n")

def main():
    print("Підключення до Gmail...")
    mail = connect_to_gmail()
    if not email:
        return
    
    print("Отримання листів...")
    emails = get_emails(mail,max_emails=5)

    mail.close()
    mail.logout()

    analyze_emails_with_ai(emails)
    print("Готово!")

if __name__ == "__main__":
    main()