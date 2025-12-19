import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pytz
import urllib.parse
import smtplib
import unicodedata
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- 1. CONFIGURATIE LADEN (DYNAMISCH) ---
def load_config():
    # 1a. Verbinding maken
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    try:
        sh = client.open("EU_Lezingen_Master")
        ws = sh.worksheet("Config")
        data = ws.get_all_values()
        # Zet om naar dictionary: { "SPEAKER_NAME": "Robert...", ... }
        # We slaan rij 0 (headers) over als die er zijn, of filteren lege regels
        config = {row[0]: row[1] for row in data if len(row) > 1 and row[0] != "KEY"}
        return config, client
    except Exception as e:
        st.error(f"Kan configuratie niet laden uit Google Sheets: {e}")
        return {}, client

# Config inladen (sessie state caching om traagheid te voorkomen)
if 'config_data' not in st.session_state:
    conf, cli = load_config()
    st.session_state.config_data = conf
    st.session_state.gspread_client = cli

conf = st.session_state.config_data

# --- VARIABELEN TOEWIJZEN ---
# Als de sheet leeg is, gebruiken we een fallback string om crashes te voorkomen
SPEAKER_NAME = conf.get("SPEAKER_NAME", "Nog niet bekend")
SPEAKER_ROLE = conf.get("SPEAKER_ROLE", "")
SPEAKER_BIO = conf.get("SPEAKER_BIO", "")
SPEAKER_LINKEDIN = conf.get("SPEAKER_LINKEDIN", "")
EVENT_IMAGE = conf.get("EVENT_IMAGE", "")

# Datum parsing
try:
    EVENT_DATE = datetime.strptime(conf.get("EVENT_DATE", "2026-01-01"), "%Y-%m-%d").date()
except:
    EVENT_DATE = datetime.now().date()

# Tijd parsing helper
def parse_time_str(t_str):
    try:
        return datetime.strptime(t_str, "%H:%M:%S").time()
    except:
        return datetime.strptime("00:00:00", "%H:%M:%S").time()

t_din = parse_time_str(conf.get("TIME_DINNER", "18:00:00"))
t_lec = parse_time_str(conf.get("TIME_LECTURE", "19:30:00"))
t_end = parse_time_str(conf.get("TIME_END", "21:00:00"))

# Combineer datum en tijd voor berekeningen
TIME_DINNER = datetime.combine(EVENT_DATE, t_din)
TIME_LECTURE = datetime.combine(EVENT_DATE, t_lec)
TIME_END = datetime.combine(EVENT_DATE, t_end)

# Locaties
LOC_DINNER_NAME = conf.get("LOC_DINNER_NAME", "")
LOC_DINNER_ADDR = conf.get("LOC_DINNER_ADDR", "")
LOC_LECTURE_NAME = conf.get("LOC_LECTURE_NAME", "")
LOC_LECTURE_ADDR = conf.get("LOC_LECTURE_ADDR", "")

# Links
MAPS_DINNER = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(LOC_DINNER_NAME + ' ' + LOC_DINNER_ADDR)}"
MAPS_LECTURE = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(LOC_LECTURE_NAME + ' ' + LOC_LECTURE_ADDR)}"
LINK_VIDEO = conf.get("LINK_VIDEO", "")
LINK_PAYMENT = conf.get("LINK_PAYMENT", "")

# Sheet naam voor opslaan
SHEET_NAME_CURRENT = conf.get("CURRENT_SHEET_NAME", "Backup_Sheet")
MASTER_SHEET_NAME = "EU_Lezingen_Master"

# Emoji's
CLOCK_DINNER = "🕕"
CLOCK_LECTURE = "🕢"

ams_tz = pytz.timezone('Europe/Amsterdam')

# --- 2. HELPER FUNCTIES ---

def get_month_details(date_obj):
    months = {
        1:  ("januari", "❄️"), 2:  ("februari", "🌨️"), 3:  ("maart", "🌱"),
        4:  ("april", "🌷"), 5:  ("mei", "☀️"), 6:  ("juni", "⛱️"),
        7:  ("juli", "🍦"), 8:  ("augustus", "🌾"), 9:  ("september", "🍂"),
        10: ("oktober", "🎃"), 11: ("november", "🌧️"), 12: ("december", "🎄")
    }
    return months[date_obj.month]

def get_dutch_day_name(date_obj):
    days = {0: "Maandag", 1: "Dinsdag", 2: "Woensdag", 3: "Donderdag", 4: "Vrijdag", 5: "Zaterdag", 6: "Zondag"}
    return days[date_obj.weekday()]

def save_to_sheet(name, email, attend_type, dinner_choice):
    # We gebruiken de client die al geladen is
    client = st.session_state.gspread_client
    # Open master sheet en pak het specifieke maand-tabblad
    try:
        sheet = client.open(MASTER_SHEET_NAME).worksheet(SHEET_NAME_CURRENT)
        timestamp = datetime.now(ams_tz).strftime("%d-%m-%Y %H:%M:%S")
        sheet.append_row([name, email, attend_type, dinner_choice, timestamp])
    except gspread.WorksheetNotFound:
        st.error(f"Fout: Het tabblad '{SHEET_NAME_CURRENT}' bestaat niet in '{MASTER_SHEET_NAME}'. Vraag de organisator om de setup te draaien.")
        raise

def force_ascii(text):
    if not isinstance(text, str):
        text = str(text)
    text = text.replace('\xa0', ' ').replace('\u202F', ' ')
    text = unicodedata.normalize('NFKD', text)
    return text.encode('ascii', 'ignore').decode('ascii').strip()

# --- WEB COMPONENT: PROGRAMMA KAART ---
def render_program_card(emoji, title, clock_emoji, time_str, loc_name, loc_addr, map_url=None, is_video=False, time_suffix=""):
    with st.container(border=True):
        st.markdown(f"#### {emoji} {title}")
        st.markdown(f"**{clock_emoji} {time_str}** {time_suffix}")
        
        if is_video:
             st.markdown(f"**📍 Google Meet** (Videolink · [Open Link]({loc_addr}))")
        else:
            st.markdown(f"**📍 {loc_name}** ({loc_addr} · [Route]({map_url}))")

# --- EMAIL FUNCTIE ---
def send_confirmation_email(to_email, name, attend_type, dinner_choice, full_subject_line, google_link, ics_content):
    try:
        raw_sender = st.secrets["email"]["sender_email"]
        raw_password = st.secrets["email"]["app_password"]

        smtp_sender = force_ascii(raw_sender)
        smtp_password = force_ascii(raw_password)
        safe_to_email = force_ascii(to_email)
        safe_title = force_ascii(full_subject_line)
        
        msg = MIMEMultipart("mixed")
        msg['From'] = smtp_sender
        msg['To'] = safe_to_email
        msg['Subject'] = safe_title 

        msg_body = MIMEMultipart("alternative")

        is_online = "Online" in attend_type
        keuze_samenvatting = "Online aanwezig (via videolink)" if is_online else ("Fysiek aanwezig mét diner" if "Ja" in dinner_choice else "Fysiek aanwezig (alleen lezing)")

        # HTML BODY
        html_body = f"""
        <html>
          <body style="font-family: Arial, sans-serif; line-height: 1.5; color: #333;">
            <p>Beste {name},</p>
            <p>Leuk dat je erbij bent op <strong>{EVENT_DATE.day} {get_month_details(EVENT_DATE)[0]} {EVENT_DATE.year}</strong>! 👋 Hier zijn je details:</p>
            
            <div style="background-color: #f9f9f9; padding: 15px; border-radius: 5px; border: 1px solid #ddd; margin-bottom: 25px;">
                <p style="margin: 0;">📝 <strong>Jouw keuze:</strong> {keuze_samenvatting}</p>
            </div>
            <h3 style="margin-top: 0;">Programma</h3>
        """

        if is_online:
            html_body += f"""
            <div style="margin-bottom: 15px; border: 1px solid #eee; border-left: 4px solid #4285F4; padding: 15px; border-radius: 4px;">
                <p style="margin: 0; font-weight: bold; font-size: 1.1em; margin-bottom: 5px;">🎤 Lezing (Online)</p>
                <p style="margin: 0 0 5px 0;"><strong>{CLOCK_LECTURE} {TIME_LECTURE.strftime('%H:%M')}</strong> (aanvang)</p>
                <p style="margin: 0;">📍 <strong>Google Meet</strong> (Videolink · <a href="{LINK_VIDEO}" target="_blank" style="color: #4285F4; text-decoration: none;">Open Link</a>)</p>
            </div>
            """
        else:
            if "Ja" in dinner_choice:
                html_body += f"""
                <div style="margin-bottom: 15px; border: 1px solid #eee; border-left: 4px solid #ff9800; padding: 15px; border-radius: 4px;">
                    <p style="margin: 0; font-weight: bold; font-size: 1.1em; margin-bottom: 5px;">🍕 Diner</p>
                    <p style="margin: 0 0 5px 0;"><strong>{CLOCK_DINNER} {TIME_DINNER.strftime('%H:%M')}</strong> (aanvang)</p>
                    <p style="margin: 0;">📍 <strong>{LOC_DINNER_NAME}</strong> ({LOC_DINNER_ADDR} · <a href="{MAPS_DINNER}" target="_blank" style="color: #4285F4; text-decoration: none;">Route</a>)</p>
                </div>
                """
            html_body += f"""
            <div style="margin-bottom: 15px; border: 1px solid #eee; border-left: 4px solid #4caf50; padding: 15px; border-radius: 4px;">
                <p style="margin: 0; font-weight: bold; font-size: 1.1em; margin-bottom: 5px;">🎤 Lezing</p>
                <p style="margin: 0 0 5px 0;"><strong>{CLOCK_LECTURE} {TIME_LECTURE.strftime('%H:%M')}</strong> (aanvang)</p>
                <p style="margin: 0;">📍 <strong>{LOC_LECTURE_NAME}</strong> ({LOC_LECTURE_ADDR} · <a href="{MAPS_LECTURE}" target="_blank" style="color: #4285F4; text-decoration: none;">Route</a>)</p>
            </div>
            """

        html_body += f"""
            <br>
            <a href="{google_link}" target="_blank" style="background-color:#4285F4; color:white; padding:10px 15px; text-decoration:none; border-radius:5px; font-weight:bold;">
               📅 Zet in Google Agenda
            </a>
            <br><br>
            <p>De officiële agenda-uitnodiging (voor Outlook/Apple) vind je ook als bijlage bij deze mail.</p>
            <p>Tot dan!<br>Groet,<br><strong>EU Studiegroep</strong> 🇪🇺</p>
          </body>
        </html>
        """
        
        # TEXT BODY
        text_body = f"Beste {name},\n\nLeuk dat je erbij bent! Jouw keuze: {keuze_samenvatting}\n\nZie HTML mail voor details en links."

        part1 = MIMEText(text_body, 'plain', 'utf-8')
        part2 = MIMEText(html_body, 'html', 'utf-8')
        msg_body.attach(part1)
        msg_body.attach(part2)
        msg.attach(msg_body)

        if ics_content:
            part_ics = MIMEText(ics_content, 'calendar; method=REQUEST', 'utf-8')
            part_ics.add_header('Content-Disposition', 'attachment', filename='invite.ics')
            msg.attach(part_ics)

        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(smtp_sender, smtp_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error(f"Fout bij verzenden email: {e}")
        return False

def create_google_cal_link(title, start_dt, end_dt, location, description):
    fmt = "%Y%m%dT%H%M%S"
    dates = f"{start_dt.strftime(fmt)}/{end_dt.strftime(fmt)}"
    base_url = "https://calendar.google.com/calendar/render"
    safe_desc = description
    params = {"action": "TEMPLATE", "text": title, "dates": dates, "details": safe_desc, "location": location, "ctz": "Europe/Amsterdam"}
    return f"{base_url}?{urllib.parse.urlencode(params)}"

def create_ics_content(title, start_dt, end_dt, location, description):
    fmt = "%Y%m%dT%H%M%S"
    now_fmt = datetime.now().strftime(fmt)
    safe_desc = description.replace("\n", "\\n")
    return f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//LezingApp//NL
METHOD:REQUEST
BEGIN:VEVENT
UID:{now_fmt}@lezingapp
DTSTAMP:{now_fmt}
DTSTART:{start_dt.strftime(fmt)}
DTEND:{end_dt.strftime(fmt)}
SUMMARY:{title}
DESCRIPTION:{safe_desc}
LOCATION:{location}
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR"""

# --- 3. UI OPBOUW ---

st.set_page_config(page_title="Aanmelding Lezing", page_icon="🇪🇺")

maand_naam, maand_emoji = get_month_details(EVENT_DATE)
dag_naam = get_dutch_day_name(EVENT_DATE)
datum_zonder_nul = f"{EVENT_DATE.day} {maand_naam}" 

# TITELS
page_title = f"🇪🇺 Studiegroep {maand_emoji} {maand_naam.capitalize()} {EVENT_DATE.year}"
invite_title = f"{page_title} ({SPEAKER_NAME})"
email_base_title = f"EU Studiegroep {maand_naam.capitalize()} {EVENT_DATE.year}"

# HEADER
st.title(page_title)
st.markdown(f"## {SPEAKER_NAME}")
st.markdown(f"*{SPEAKER_ROLE}*")
if EVENT_IMAGE:
    st.image(EVENT_IMAGE, use_container_width=True)
st.write(SPEAKER_BIO)
if SPEAKER_LINKEDIN:
    st.link_button("👔 LinkedIn profiel", SPEAKER_LINKEDIN)

st.divider()

# PROGRAMMA
st.markdown(f"### 📅 {dag_naam} {datum_zonder_nul} {EVENT_DATE.year}")
st.markdown("") 

render_program_card(
    emoji="🍕", title="Diner", clock_emoji=CLOCK_DINNER, time_str=TIME_DINNER.strftime('%H:%M'),
    loc_name=LOC_DINNER_NAME, loc_addr=LOC_DINNER_ADDR, map_url=MAPS_DINNER, time_suffix="(aanvang)"
)
render_program_card(
    emoji="🎤", title="Lezing", clock_emoji=CLOCK_LECTURE, time_str=TIME_LECTURE.strftime('%H:%M'),
    loc_name=LOC_LECTURE_NAME, loc_addr=LOC_LECTURE_ADDR, map_url=MAPS_LECTURE, time_suffix="(aanvang)"
)

st.divider()

# KOSTEN
st.markdown("### 💶 Kosten")
st.write("Om alles te kunnen bekostigen vragen we om een kleine bijdrage.")
st.markdown("""
* **Per lezing:** € 10,-
* **Half seizoen (5 lezingen):** € 40,-
* **Heel seizoen (10 lezingen):** € 60,-
""")
st.write("Klik op onderstaande knop om te betalen (vul zelf het goede bedrag en je naam in).")
if LINK_PAYMENT:
    st.link_button("💳 Betaalverzoek openen", LINK_PAYMENT)
else:
    st.warning("Nog geen betaallink ingesteld.")

st.divider()

# AANMELDEN
st.markdown("### 📝 Aanmelden")
basis_vraag = st.radio(f"Ben je erbij op {datum_zonder_nul}?", ["Selecteer...", "Ja", "Nee"], index=0)

if basis_vraag == "Nee":
    # CSS voor rode knop
    st.markdown("""<style>div[data-testid="stForm"] button {background-color: #dc3545 !important; color: white !important; border: none; font-weight: bold;} div[data-testid="stForm"] button:hover {background-color: #bb2d3b !important; color: white !important;}</style>""", unsafe_allow_html=True)
    st.write("Jammer! Laat hieronder je naam achter om je officieel af te melden.")
    with st.form("afmeld_form"):
        c_voor, c_achter = st.columns(2)
        with c_voor: voornaam = st.text_input("Voornaam")
        with c_achter: achternaam = st.text_input("Achternaam")
        email = st.text_input("Emailadres (optioneel)")
        if st.form_submit_button("Verstuur afmelding"):
            if not voornaam or not achternaam: st.error("Vul je naam in.")
            else:
                try:
                    save_to_sheet(f"{voornaam} {achternaam}", email, "Afgemeld", "-")
                    st.success("Afmelding geregistreerd.")
                except Exception as e: st.error(f"Fout: {e}")

elif basis_vraag == "Ja":
    # CSS voor groene knop
    st.markdown("""<style>div[data-testid="stForm"] button {background-color: #28a745 !important; color: white !important; border: none; font-weight: bold;} div[data-testid="stForm"] button:hover {background-color: #218838 !important; color: white !important;}</style>""", unsafe_allow_html=True)
    attendance_type = st.radio("Hoe wil je de lezing bijwonen?", ["Fysiek aanwezig", "Online (Videolink)"])
    
    with st.form("registration_form"):
        c_voor, c_achter = st.columns(2)
        with c_voor: voornaam = st.text_input("Voornaam")
        with c_achter: achternaam = st.text_input("Achternaam")
        email = st.text_input("Emailadres (voor invite/videolink)", placeholder="jouw@email.nl")
        
        join_dinner = "Nee (Online)" 
        if attendance_type == "Fysiek aanwezig":
            join_dinner = st.radio("Eet je vooraf mee?", [
                f"Ja, diner + lezing (start {TIME_DINNER.strftime('%H:%M')})",
                f"Nee, alleen lezing (start {TIME_LECTURE.strftime('%H:%M')})"
            ])
        
        if st.form_submit_button("Bevestig Aanmelding"):
            if not voornaam or not achternaam or not email: st.error("Vul alle velden in.")
            else:
                full_name = f"{voornaam} {achternaam}"
                
                # Setup vars voor bevestiging
                cal_loc = LINK_VIDEO if "Online" in attendance_type else f"{LOC_LECTURE_NAME}, {LOC_LECTURE_ADDR}"
                cal_desc = f"Spreker: {SPEAKER_NAME}\n{SPEAKER_BIO}"
                msg_keuze = "de online lezing" if "Online" in attendance_type else ("diner en lezing" if "Ja" in join_dinner else "alleen de lezing")
                msg_start = TIME_LECTURE.strftime('%H:%M') if "Online" in attendance_type else (TIME_DINNER.strftime('%H:%M') if "Ja" in join_dinner else TIME_LECTURE.strftime('%H:%M'))
                msg_loc_nm = "Google Meet" if "Online" in attendance_type else (LOC_DINNER_NAME if "Ja" in join_dinner else LOC_LECTURE_NAME)
                msg_loc_url = LINK_VIDEO if "Online" in attendance_type else (MAPS_DINNER if "Ja" in join_dinner else MAPS_LECTURE)

                google_url = create_google_cal_link(invite_title, (TIME_DINNER if "Ja" in join_dinner else TIME_LECTURE), TIME_END, cal_loc, cal_desc)
                ics_data = create_ics_content(invite_title, (TIME_DINNER if "Ja" in join_dinner else TIME_LECTURE), TIME_END, cal_loc, cal_desc)

                try:
                    save_to_sheet(full_name, email, attendance_type, join_dinner)
                    st.success(f"✅ Bedankt {voornaam}! Je staat op de lijst voor **{msg_keuze}**. Tot **{datum_zonder_nul}** (aanvang **{msg_start}** bij **[{msg_loc_nm}]({msg_loc_url})**).")
                    if email and "@" in email:
                        sent = send_confirmation_email(email, voornaam, attendance_type, join_dinner, f"{email_base_title} Bevestiging", google_url, ics_data)
                        if sent: st.info(f"📧 Bevestiging + Agenda-invite verstuurd naar {email}")
                    
                    st.divider()
                    st.markdown("### 📅 Zet direct in je agenda")
                    c_g, c_i = st.columns(2)
                    with c_g: st.markdown(f'''<a href="{google_url}" target="_blank"><button style="width:100%; background-color:#4285F4; color:white; border:none; padding:10px; border-radius:5px; font-weight:bold; cursor:pointer;">Google Agenda ↗</button></a>''', unsafe_allow_html=True)
                    with c_i: st.download_button("Download Outlook / iCal 📥", ics_data, "lezing.ics", "text/calendar", use_container_width=True)
                except Exception as e: st.error(f"Fout: {e}")

st.markdown("---")
st.markdown("### 🙋 Vragen?")
st.write("Heb je vragen of lukt het aanmelden niet? Stuur ons gerust een mailtje.")
mailto = f"mailto:studiegroepeu@gmail.com?subject={urllib.parse.quote(f'Vraag lezing {maand_naam} - {SPEAKER_NAME}')}"
st.markdown(f'''<a href="{mailto}" target="_blank" style="text-decoration:none;"><button style="background-color:#6c757d;color:white;border:none;padding:8px 16px;border-radius:5px;cursor:pointer;font-size:16px;">📧 E-mail ons</button></a>''', unsafe_allow_html=True)