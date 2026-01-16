import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import pytz
import urllib.parse
import smtplib
import unicodedata
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr

# --- BELANGRIJK: PLAK HIER DE URL VAN JE GOOGLE SHEET ---
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1OAF5Y4TIVMUUM1xXzcRY2VpMw2dF9vPA5Z4NtZr2gTg/edit?gid=0#gid=0"

# --- 1. CONFIGURATIE LADEN ---
def load_config():
    scope = [
        'https://spreadsheets.google.com/feeds', 
        'https://www.googleapis.com/auth/drive',
        'https://www.googleapis.com/auth/calendar'
    ]
    creds_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    try:
        if "docs.google.com" in SPREADSHEET_URL:
            sh = client.open_by_url(SPREADSHEET_URL)
        else:
            sh = client.open("EU_Lezingen_Master")

        ws = sh.worksheet("Config")
        data = ws.get_all_values()
        config = {row[0]: row[1] for row in data if len(row) > 1 and row[0] != "KEY"}
        return config, client
    except Exception as e:
        st.error(f"Kan configuratie niet laden. Fout: {e}")
        return {}, client

if 'config_data' not in st.session_state:
    conf, cli = load_config()
    st.session_state.config_data = conf
    st.session_state.gspread_client = cli

conf = st.session_state.config_data

# --- VARIABELEN ---
SPEAKER_NAME = conf.get("SPEAKER_NAME", "Nog niet bekend")
SPEAKER_ROLE = conf.get("SPEAKER_ROLE", "")
SPEAKER_BIO = conf.get("SPEAKER_BIO", "")
SPEAKER_LINKEDIN = conf.get("SPEAKER_LINKEDIN", "")
EVENT_IMAGE = conf.get("EVENT_IMAGE", "")

# CONTACT EMAIL
CONTACT_EMAIL = "eustudiegroep@gmail.com"

try:
    EVENT_DATE = datetime.strptime(conf.get("EVENT_DATE", "2026-01-01"), "%Y-%m-%d").date()
except:
    EVENT_DATE = datetime.now().date()

def parse_time_str(t_str):
    try:
        return datetime.strptime(t_str, "%H:%M:%S").time()
    except:
        return datetime.strptime("00:00:00", "%H:%M:%S").time()

TIME_DINNER = datetime.combine(EVENT_DATE, parse_time_str(conf.get("TIME_DINNER", "18:00:00")))
TIME_LECTURE = datetime.combine(EVENT_DATE, parse_time_str(conf.get("TIME_LECTURE", "19:30:00")))
TIME_END = datetime.combine(EVENT_DATE, parse_time_str(conf.get("TIME_END", "21:00:00")))

LOC_DINNER_NAME = conf.get("LOC_DINNER_NAME", "")
LOC_DINNER_ADDR = conf.get("LOC_DINNER_ADDR", "")
LOC_LECTURE_NAME = conf.get("LOC_LECTURE_NAME", "")
LOC_LECTURE_ADDR = conf.get("LOC_LECTURE_ADDR", "")

# LINKS
def get_maps_link(conf_key, name, addr):
    link = conf.get(conf_key, "")
    if link and "http" in link:
        return link
    return f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(name + ' ' + addr)}"

MAPS_DINNER = get_maps_link("LINK_MAPS_DINNER", LOC_DINNER_NAME, LOC_DINNER_ADDR)
MAPS_LECTURE = get_maps_link("LINK_MAPS_LECTURE", LOC_LECTURE_NAME, LOC_LECTURE_ADDR)

LINK_VIDEO = conf.get("LINK_VIDEO", "")
LINK_PAYMENT = conf.get("LINK_PAYMENT", "")

SHEET_NAME_CURRENT = conf.get("CURRENT_SHEET_NAME", "Backup_Sheet")

CLOCK_DINNER = "🕕"
CLOCK_LECTURE = "🕢"
ams_tz = pytz.timezone('Europe/Amsterdam')

# --- 2. HELPER FUNCTIES ---

def get_month_details(date_obj):
    months = {1: ("januari", "❄️"), 2: ("februari", "🌨️"), 3: ("maart", "🌱"), 4: ("april", "🌷"), 5: ("mei", "☀️"), 6: ("juni", "⛱️"), 7: ("juli", "🍦"), 8: ("augustus", "🌾"), 9: ("september", "🍂"), 10: ("oktober", "🎃"), 11: ("november", "🌧️"), 12: ("december", "🎄")}
    return months[date_obj.month]

def get_dutch_day_name(date_obj):
    days = {0: "Maandag", 1: "Dinsdag", 2: "Woensdag", 3: "Donderdag", 4: "Vrijdag", 5: "Zaterdag", 6: "Zondag"}
    return days[date_obj.weekday()]

def save_to_sheet(name, email, attend_type, dinner_choice):
    client = st.session_state.gspread_client
    try:
        if "docs.google.com" in SPREADSHEET_URL:
            sheet = client.open_by_url(SPREADSHEET_URL).worksheet(SHEET_NAME_CURRENT)
        else:
            sheet = client.open("EU_Lezingen_Master").worksheet(SHEET_NAME_CURRENT)
            
        timestamp = datetime.now(ams_tz).strftime("%d-%m-%Y %H:%M:%S")
        sheet.append_row([name, email, attend_type, dinner_choice, timestamp])
    except gspread.WorksheetNotFound:
        st.error(f"Fout: Tabblad '{SHEET_NAME_CURRENT}' bestaat niet.")
        raise
    except Exception as e:
        st.error(f"Fout bij opslaan: {e}")
        raise

def force_ascii(text):
    if not isinstance(text, str): text = str(text)
    text = text.replace('\xa0', ' ').replace('\u202F', ' ')
    text = unicodedata.normalize('NFKD', text)
    return text.encode('ascii', 'ignore').decode('ascii').strip()

# --- CALENDAR API FUNCTIE (Alleen voor Organisator) ---
def manage_calendar_event_organizer_only(title, start_dt, end_dt, location, description, search_query):
    try:
        creds_dict = st.secrets["gcp_service_account"]
        creds = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=['https://www.googleapis.com/auth/calendar']
        )
        service = build('calendar', 'v3', credentials=creds)
        calendar_id = CONTACT_EMAIL 
        
        time_min = (start_dt - timedelta(minutes=15)).isoformat() + 'Z' 
        time_max = (end_dt + timedelta(minutes=15)).isoformat() + 'Z'
        
        events_result = service.events().list(
            calendarId=calendar_id, 
            timeMin=time_min, 
            timeMax=time_max, 
            singleEvents=True,
            q=search_query
        ).execute()
        events = events_result.get('items', [])
        
        event_body = {
            'summary': title,
            'location': location,
            'description': description,
            'start': {
                'dateTime': start_dt.isoformat(),
                'timeZone': 'Europe/Amsterdam',
            },
            'end': {
                'dateTime': end_dt.isoformat(),
                'timeZone': 'Europe/Amsterdam',
            },
        }

        if events:
            event_id = events[0]['id']
            service.events().update(calendarId=calendar_id, eventId=event_id, body=event_body).execute()
        else:
            service.events().insert(calendarId=calendar_id, body=event_body).execute()
            
        return True
    except Exception as e:
        st.error(f"Fout met Google Calendar Sync ({search_query}): {e}")
        return False

# --- WEB COMPONENT ---
def render_program_card(emoji, title, clock_emoji, time_str, loc_name, loc_addr, map_url=None, is_video=False, time_suffix=""):
    with st.container(border=True):
        st.markdown(f"#### {emoji} {title}")
        st.markdown(f"**{clock_emoji} {time_str}** {time_suffix}")
        if is_video:
             st.markdown(f"**📍 Google Meet** (Videolink · [Open Link]({loc_addr}))")
        else:
            st.markdown(f"**📍 {loc_name}** ({loc_addr} · [Route]({map_url}))")

# --- EMAIL FUNCTIE (Terug naar ICS) ---
def send_confirmation_email(to_email, name, attend_type, dinner_choice, full_subject_line, google_link, ics_content):
    try:
        raw_sender = st.secrets["email"]["sender_email"]
        raw_password = st.secrets["email"]["app_password"]
        
        smtp_sender = force_ascii(raw_sender)
        smtp_password = force_ascii(raw_password)
        safe_to_email = force_ascii(to_email)
        
        msg = MIMEMultipart("mixed")
        msg['From'] = formataddr(("EU Studiegroep", smtp_sender))
        msg.add_header('Reply-To', CONTACT_EMAIL)
        msg['To'] = safe_to_email
        msg['Subject'] = force_ascii(full_subject_line)

        is_online = "Online" in attend_type
        keuze_samenvatting = "Online aanwezig (via videolink)" if is_online else ("Fysiek aanwezig mét diner" if "Ja" in dinner_choice else "Fysiek aanwezig (alleen lezing)")

        html_body = f"""
        <html><body style="font-family: Arial, sans-serif; line-height: 1.5; color: #333;">
            <p>Beste {name},</p>
            <p>Leuk dat je erbij bent op <strong>{EVENT_DATE.day} {get_month_details(EVENT_DATE)[0]} {EVENT_DATE.year}</strong>! 👋 Hier zijn je details:</p>
            <div style="background-color: #f9f9f9; padding: 15px; border-radius: 5px; border: 1px solid #ddd; margin-bottom: 25px;">
                <p style="margin: 0;">📝 <strong>Jouw keuze:</strong> {keuze_samenvatting}</p>
            </div>
            
            <h3 style="margin-top: 0;">Programma</h3>
        """
        if is
