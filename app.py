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
        if is_online:
            html_body += f"""<div style="margin-bottom: 15px; border: 1px solid #eee; border-left: 4px solid #4285F4; padding: 15px; border-radius: 4px;">
                <p style="margin: 0; font-weight: bold; font-size: 1.1em; margin-bottom: 5px;">🎤 Lezing (Online)</p>
                <p style="margin: 0 0 5px 0;"><strong>{CLOCK_LECTURE} {TIME_LECTURE.strftime('%H:%M')}</strong> (aanvang)</p>
                <p style="margin: 0;">📍 <strong>Google Meet</strong> (Videolink · <a href="{LINK_VIDEO}" target="_blank" style="color: #4285F4; text-decoration: none;">Open Link</a>)</p>
            </div>"""
        else:
            if "Ja" in dinner_choice:
                html_body += f"""<div style="margin-bottom: 15px; border: 1px solid #eee; border-left: 4px solid #ff9800; padding: 15px; border-radius: 4px;">
                    <p style="margin: 0; font-weight: bold; font-size: 1.1em; margin-bottom: 5px;">🍕 Diner</p>
                    <p style="margin: 0 0 5px 0;"><strong>{CLOCK_DINNER} {TIME_DINNER.strftime('%H:%M')}</strong> (aanvang)</p>
                    <p style="margin: 0;">📍 <strong>{LOC_DINNER_NAME}</strong> ({LOC_DINNER_ADDR} · <a href="{MAPS_DINNER}" target="_blank" style="color: #4285F4; text-decoration: none;">Route</a>)</p>
                </div>"""
            html_body += f"""<div style="margin-bottom: 15px; border: 1px solid #eee; border-left: 4px solid #4caf50; padding: 15px; border-radius: 4px;">
                <p style="margin: 0; font-weight: bold; font-size: 1.1em; margin-bottom: 5px;">🎤 Lezing</p>
                <p style="margin: 0 0 5px 0;"><strong>{CLOCK_LECTURE} {TIME_LECTURE.strftime('%H:%M')}</strong> (aanvang)</p>
                <p style="margin: 0;">📍 <strong>{LOC_LECTURE_NAME}</strong> ({LOC_LECTURE_ADDR} · <a href="{MAPS_LECTURE}" target="_blank" style="color: #4285F4; text-decoration: none;">Route</a>)</p>
            </div>"""

        # --- VIDEOLINK IN EMAIL ---
        html_body += f"""
        <div style="margin-top: 20px; padding: 10px; background-color: #e8f0fe; border-radius: 4px; border-left: 4px solid #1a73e8;">
            <p style="margin: 0; font-weight: bold; color: #1a73e8;">📹 Videolink</p>
            <p style="margin: 5px 0 0 0; font-size: 0.9em;">Mocht je (alsnog) online willen aansluiten, gebruik dan deze link:</p>
            <p style="margin: 5px 0 0 0;"><a href="{LINK_VIDEO}" target="_blank" style="color: #1a73e8; text-decoration: none;">{LINK_VIDEO}</a></p>
        </div>
        
        <br>
        <p>Gebruik de knop hieronder of de bijlage om het in je agenda te zetten:</p>
        <a href="{google_link}" target="_blank" style="background-color:#4285F4; color:white; padding:10px 15px; text-decoration:none; border-radius:5px; font-weight:bold;">📅 Zet in Google Agenda</a>
        
        <br><br><p>Tot dan!<br>Groet,<br><strong>EU Studiegroep</strong> 🇪🇺</p></body></html>"""
        
        msg_body = MIMEMultipart("alternative")
        msg_body.attach(MIMEText(f"Beste {name},\n\nLeuk dat je erbij bent! Zie HTML mail voor details en de videolink.", 'plain', 'utf-8'))
        msg_body.attach(MIMEText(html_body, 'html', 'utf-8'))
        msg.attach(msg_body)

        if ics_content:
            part = MIMEText(ics_content, 'calendar; method=REQUEST', 'utf-8')
            part.add_header('Content-Disposition', 'attachment', filename='invite.ics')
            msg.attach(part)

        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(smtp_sender, smtp_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error(f"Fout bij verzenden email: {e}")
        return False

def create_google_cal_link(title, start_dt, end_dt, location, description):
    params = {"action": "TEMPLATE", "text": title, "dates": f"{start_dt.strftime('%Y%m%dT%H%M%S')}/{end_dt.strftime('%Y%m%dT%H%M%S')}", "details": description, "location": location, "ctz": "Europe/Amsterdam"}
    return f"https://calendar.google.com/calendar/render?{urllib.parse.urlencode(params)}"

def create_ics_content(title, start_dt, end_dt, location, description):
    fmt = "%Y%m%dT%H%M%S"
    return f"BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//LezingApp//NL\nMETHOD:REQUEST\nBEGIN:VEVENT\nUID:{datetime.now().strftime(fmt)}@lezingapp\nDTSTAMP:{datetime.now().strftime(fmt)}\nDTSTART:{start_dt.strftime(fmt)}\nDTEND:{end_dt.strftime(fmt)}\nSUMMARY:{title}\nDESCRIPTION:{description.replace(chr(10), '\\n')}\nLOCATION:{location}\nSTATUS:CONFIRMED\nEND:VEVENT\nEND:VCALENDAR"

# --- 3. UI OPBOUW ---
st.set_page_config(page_title="Aanmelding Lezing", page_icon="🇪🇺", initial_sidebar_state="collapsed")

maand_naam, maand_emoji = get_month_details(EVENT_DATE)
dag_naam = get_dutch_day_name(EVENT_DATE)
datum_zonder_nul = f"{EVENT_DATE.day} {maand_naam}" 
invite_title = f"🇪🇺 Studiegroep {maand_emoji} {maand_naam.capitalize()} {EVENT_DATE.year} ({SPEAKER_NAME})"

st.title(f"🇪🇺 Studiegroep {maand_emoji} {maand_naam.capitalize()} {EVENT_DATE.year}")
st.markdown(f"## {SPEAKER_NAME}")
st.markdown(f"*{SPEAKER_ROLE}*")
if EVENT_IMAGE: st.image(EVENT_IMAGE, use_container_width=True)
st.write(SPEAKER_BIO)
if SPEAKER_LINKEDIN: st.link_button("👔 LinkedIn profiel", SPEAKER_LINKEDIN)

st.divider()
st.markdown(f"### 📅 {dag_naam} {datum_zonder_nul} {EVENT_DATE.year}")
st.markdown("") 

render_program_card("🍕", "Diner", CLOCK_DINNER, TIME_DINNER.strftime('%H:%M'), LOC_DINNER_NAME, LOC_DINNER_ADDR, MAPS_DINNER, time_suffix="(aanvang)")
render_program_card("🎤", "Lezing", CLOCK_LECTURE, TIME_LECTURE.strftime('%H:%M'), LOC_LECTURE_NAME, LOC_LECTURE_ADDR, MAPS_LECTURE, time_suffix="(aanvang)")

st.divider()
st.markdown("### 💶 Kosten")
st.write("Om alles te kunnen bekostigen vragen we om een kleine bijdrage.")
st.markdown("* **Per lezing:** € 10,-\n* **Half seizoen (5 lezingen):** € 40,-\n* **Heel seizoen (10 lezingen):** € 60,-")
st.write("Klik op onderstaande knop om te betalen (vul zelf het goede bedrag en je naam in).")
if LINK_PAYMENT: st.link_button("💳 Betaalverzoek openen", LINK_PAYMENT)

st.divider()
st.markdown("### 📝 Aanmelden")
basis_vraag = st.radio(f"Wil je de lezing op **{datum_zonder_nul}** (fysiek/online) bijwonen?", ["Selecteer...", "Ja", "Nee"], index=0)

if 'submission_success' not in st.session_state:
    st.session_state.submission_success = False
if 'success_data' not in st.session_state:
    st.session_state.success_data = {}

if basis_vraag == "Nee":
    st.markdown("""<style>div[data-testid="stForm"] button {background-color: #dc3545 !important; color: white !important; border: none; font-weight: bold;} div[data-testid="stForm"] button:hover {background-color: #bb2d3b !important; color: white !important;}</style>""", unsafe_allow_html=True)
    st.write("Jammer! Laat hieronder je naam achter om je officieel af te melden.")
    with st.form("afmeld_form"):
        c1, c2 = st.columns(2)
        with c1: vn = st.text_input("Voornaam")
        with c2: an = st.text_input("Achternaam")
        em = st.text_input("Emailadres (optioneel)")
        
        if st.form_submit_button("Verstuur afmelding"):
            if not vn or not an: st.error("Vul je naam in.")
            else:
                try:
                    save_to_sheet(f"{vn} {an}", em, "Afgemeld", "-")
                    st.success("Afmelding geregistreerd.")
                except Exception as e: st.error(f"Fout: {e}")

elif basis_vraag == "Ja":
    st.markdown("""<style>div[data-testid="stForm"] button {background-color: #28a745 !important; color: white !important; border: none; font-weight: bold;} div[data-testid="stForm"] button:hover {background-color: #218838 !important; color: white !important;}</style>""", unsafe_allow_html=True)
    att_type = st.radio("Hoe wil je de lezing bijwonen?", ["Fysiek aanwezig", "Online (Videolink)"])
    
    with st.form("registration_form"):
        c1, c2 = st.columns(2)
        with c1: vn = st.text_input("Voornaam")
        with c2: an = st.text_input("Achternaam")
        email = st.text_input("Emailadres (voor invite/videolink)", placeholder="jouw@email.nl")
        join_din = "Nee (Online)"
        if att_type == "Fysiek aanwezig":
            join_din = st.radio("Eet je vooraf mee?", [f"Ja, diner + lezing (start {TIME_DINNER.strftime('%H:%M')})", f"Nee, alleen lezing (start {TIME_LECTURE.strftime('%H:%M')})"])
        
        submitted = st.form_submit_button("Bevestig aanmelding")

    if submitted:
        if not vn or not an or not email:
            st.error("Vul alle velden in.")
        else:
            with st.status("Bezig met verwerken...", expanded=True) as status:
                st.write("Gegevens opslaan in Google Sheets...")
                try:
                    save_to_sheet(f"{vn} {an}", email, att_type, join_din)
                    
                    # LOGICA: JUISTE TIJD + LOCATIE VOOR GEBRUIKER
                    cal_desc = f"Videolink: {LINK_VIDEO}\n\nSpreker: {SPEAKER_NAME}\n{SPEAKER_BIO}"
                    
                    if "Online" in att_type: 
                        # Online gebruiker
                        msg_k, msg_l, msg_u = "de online lezing", "Google Meet", LINK_VIDEO
                        t_start, loc_final = TIME_LECTURE, f"{LOC_LECTURE_NAME} (Online)"
                    elif "Ja" in join_din: 
                        # Diner + Lezing gebruiker
                        msg_k, msg_l, msg_u = "diner en lezing", LOC_DINNER_NAME, MAPS_DINNER
                        t_start, loc_final = TIME_DINNER, f"{LOC_DINNER_NAME}, {LOC_DINNER_ADDR}"
                    else: 
                        # Alleen Lezing gebruiker
                        msg_k, msg_l, msg_u = "alleen de lezing", LOC_LECTURE_NAME, MAPS_LECTURE
                        t_start, loc_final = TIME_LECTURE, f"{LOC_LECTURE_NAME}, {LOC_LECTURE_ADDR}"
                    
                    # LINKS VOOR GEBRUIKER MAKEN
                    g_url = create_google_cal_link(invite_title, t_start, TIME_END, loc_final, cal_desc)
                    i_dat = create_ics_content(invite_title, t_start, TIME_END, loc_final, cal_desc)

                    if "@" in email:
                        st.write("Toevoegen aan Agenda Organisator...")
                        # ORGANISATOR KRIJGT WEL ALLES IN AGENDA
                        title_lezing = f"🎤 Lezing: {SPEAKER_NAME}"
                        loc_lezing = f"{LOC_LECTURE_NAME}, {LOC_LECTURE_ADDR}"
                        manage_calendar_event_organizer_only(title_lezing, TIME_LECTURE, TIME_END, loc_lezing, cal_desc, "Lezing")
                        
                        if "Ja" in join_din:
                            title_diner = f"🍕 Diner: {SPEAKER_NAME}"
                            desc_diner = f"Diner voorafgaand aan lezing {SPEAKER_NAME}.\nLocatie: {LOC_DINNER_NAME}"
                            loc_diner = f"{LOC_DINNER_NAME}, {LOC_DINNER_ADDR}"
                            manage_calendar_event_organizer_only(title_diner, TIME_DINNER, TIME_LECTURE, loc_diner, desc_diner, "Diner")

                        st.write("Bevestigingsmail versturen...")
                        if send_confirmation_email(email, vn, att_type, join_din, f"EU Studiegroep {maand_naam.capitalize()} {EVENT_DATE.year} Bevestiging", g_url, i_dat):
                            st.session_state.success_data["email_sent"] = True
                            st.session_state.success_data["email_addr"] = email
                    
                    st.session_state.submission_success = True
                    st.session_state.success_data = {
                        "vn": vn,
                        "msg_k": msg_k,
                        "msg_t": t_start,
                        "msg_l": msg_l,
                        "msg_u": msg_u,
                        "g_url": g_url,
                        "i_dat": i_dat,
                        "email_sent": st.session_state.success_data.get("email_sent", False),
                        "email_addr": email
                    }
                    
                    status.update(label="Aanmelding geslaagd!", state="complete", expanded=False)

                except Exception as e: 
                    status.update(label="Er ging iets mis", state="error")
                    st.error(f"Fout: {e}")

    if st.session_state.submission_success:
        data = st.session_state.success_data
        st.success(f"✅ Bedankt {data['vn']}! Je staat op de lijst voor **{data['msg_k']}**. Tot **{datum_zonder_nul}** (aanvang **{data['msg_t'].strftime('%H:%M')}** bij **[{data['msg_l']}]({data['msg_u']})**).")
        
        if data.get("email_sent"):
            st.info(f"📧 Bevestigingsmail verstuurd naar {data['email_addr']}.")
        
        st.divider()
        st.markdown("### 📅 Zet direct in je agenda")
        c_g, c_i = st.columns(2)
        with c_g: 
            st.markdown(f'''<a href="{data['g_url']}" target="_blank"><button style="width:100%; background-color:#4285F4; color:white; border:none; padding:10px; border-radius:5px; font-weight:bold; cursor:pointer;">Google Agenda ↗</button></a>''', unsafe_allow_html=True)
        with c_i: 
            st.download_button("Download Outlook / iCal 📥", data['i_dat'], "lezing.ics", "text/calendar", use_container_width=True)


st.markdown("---")
st.markdown("### 🙋 Vragen?")
st.write(f"Heb je vragen of lukt het aanmelden niet? Stuur ons gerust een mailtje ({CONTACT_EMAIL}).")

mailto = f"mailto:{CONTACT_EMAIL}?subject={urllib.parse.quote(f'Vraag lezing {maand_naam} - {SPEAKER_NAME}')}"

st.markdown(f'''<a href="{mailto}" target="_blank" style="text-decoration:none;">
<button title="{CONTACT_EMAIL}" style="background-color:#6c757d;color:white;border:none;padding:8px 16px;border-radius:5px;cursor:pointer;font-size:16px;">
📧 E-mail ons
</button></a>''', unsafe_allow_html=True)
