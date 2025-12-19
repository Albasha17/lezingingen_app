import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, time
import urllib.parse

# --- 1. BEVEILIGING ---
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["passwords"]["admin_password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Wachtwoord", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Wachtwoord", type="password", on_change=password_entered, key="password")
        st.error("😕 Wachtwoord onjuist")
        return False
    else:
        return True

if not check_password():
    st.stop()

# --- 2. CONNECTIE HELPER ---
def get_client():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(creds)

# --- 3. HELPER: HTML GENERATOR VOOR MAILCHIMP ---
def generate_mailchimp_html(speaker, role, bio, img, date_obj, t_din, t_lec, l_din_n, l_din_a, map_din, l_lec_n, l_lec_a, map_lec, app_link):
    # Datums en tijden formatteren
    maanden = {1:"januari", 2:"februari", 3:"maart", 4:"april", 5:"mei", 6:"juni", 7:"juli", 8:"augustus", 9:"september", 10:"oktober", 11:"november", 12:"december"}
    date_str = f"{date_obj.day} {maanden[date_obj.month]} {date_obj.year}"
    din_str = t_din.strftime('%H:%M')
    lec_str = t_lec.strftime('%H:%M')

    # HTML Opbouw (Inline CSS voor maximale compatibiliteit)
    html = f"""
    <div style="font-family: Arial, sans-serif; color: #333333; line-height: 1.5; max-width: 600px; margin: 0 auto;">
        <h1 style="color: #0E3A73; margin-bottom: 5px;">EU Studiegroep {maanden[date_obj.month].capitalize()}</h1>
        <h2 style="margin-top: 0;">{speaker}</h2>
        <p style="font-style: italic; color: #666;">{role}</p>
        
        {f'<img src="{img}" alt="{speaker}" style="width: 100%; max-width: 600px; border-radius: 8px; margin: 15px 0;" />' if img else ''}
        
        <p>{bio.replace(chr(10), '<br>')}</p>
        
        <hr style="border: 0; border-top: 1px solid #eeeeee; margin: 25px 0;">
        
        <h3 style="margin-bottom: 5px;">📅 {date_str}</h3>
        <br>

        <div style="margin-bottom: 15px; border: 1px solid #eee; border-left: 4px solid #ff9800; padding: 15px; border-radius: 4px; background-color: #fff8e1;">
            <p style="margin: 0; font-weight: bold; font-size: 1.1em; margin-bottom: 5px;">🍕 Diner</p>
            <p style="margin: 0 0 5px 0;"><strong>🕕 {din_str}</strong> (aanvang)</p>
            <p style="margin: 0;">📍 <strong>{l_din_n}</strong> ({l_din_a} · <a href="{map_din}" target="_blank" style="color: #ff9800; text-decoration: none;">Route</a>)</p>
        </div>

        <div style="margin-bottom: 25px; border: 1px solid #eee; border-left: 4px solid #4caf50; padding: 15px; border-radius: 4px; background-color: #e8f5e9;">
            <p style="margin: 0; font-weight: bold; font-size: 1.1em; margin-bottom: 5px;">🎤 Lezing</p>
            <p style="margin: 0 0 5px 0;"><strong>🕢 {lec_str}</strong> (aanvang)</p>
            <p style="margin: 0;">📍 <strong>{l_lec_n}</strong> ({l_lec_a} · <a href="{map_lec}" target="_blank" style="color: #4caf50; text-decoration: none;">Route</a>)</p>
        </div>

        <div style="text-align: center; margin: 30px 0;">
            <a href="{app_link}" style="background-color: #28a745; color: #ffffff; padding: 15px 25px; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 18px; display: inline-block;">
               👉 Meld je hier aan
            </a>
            <p style="font-size: 12px; color: #888; margin-top: 10px;">(Of meld je af via dezelfde link)</p>
        </div>
    </div>
    """
    return html

# --- 4. UI ---
st.set_page_config(page_title="Admin: Nieuwe Lezing", page_icon="🛠️", layout="wide")
st.title("🛠️ Organisator Dashboard")

with st.form("event_form"):
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📅 Datum & Tijd")
        event_date = st.date_input("Datum Lezing")
        time_dinner = st.time_input("Starttijd Diner", value=time(18, 0))
        time_lecture = st.time_input("Starttijd Lezing", value=time(19, 30))
        time_end = st.time_input("Eindtijd", value=time(21, 0))
        
        st.subheader("👤 Spreker Info")
        speaker_name = st.text_input("Naam Spreker", "Robert de Groot")
        speaker_role = st.text_input("Rol / Functie", "Vice-President EIB")
        speaker_bio = st.text_area("Biografie", height=150)
        speaker_img = st.text_input("Link naar foto (URL)")
        speaker_linkedin = st.text_input("Link naar LinkedIn")

    with c2:
        st.subheader("📍 Locaties")
        # Diner
        loc_dinner_name = st.text_input("Naam Restaurant", "Restaurant & Pizzeria Lucca Due")
        loc_dinner_addr = st.text_input("Adres Restaurant", "Haarlemmerstraat 130, Amsterdam")
        def_maps_din = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote('Restaurant & Pizzeria Lucca Due Haarlemmerstraat 130, Amsterdam')}"
        link_maps_dinner = st.text_input("Google Maps Link Diner", def_maps_din)
        
        st.markdown("---")
        
        # Lezing
        loc_lecture_name = st.text_input("Naam Locatie Lezing", "De Piramide")
        loc_lecture_addr = st.text_input("Adres Locatie Lezing", "Haarlemmer Houttuinen, Amsterdam")
        def_maps_lec = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote('De Piramide Haarlemmer Houttuinen, Amsterdam')}"
        link_maps_lecture = st.text_input("Google Maps Link Lezing", def_maps_lec)
        
        st.subheader("🔗 Links")
        link_video = st.text_input("Google Meet / Video Link")
        link_payment = st.text_input("Betaalverzoek Link (Bunq/Tikkie)")

    st.markdown("---")
    submitted = st.form_submit_button("💾 Opslaan & Live Zetten", type="primary")

# --- VERWERKING ---
if submitted:
    try:
        client = get_client()
        sh = client.open("EU_Lezingen_Master")
        
        maand_namen = {1:"Januari", 2:"Februari", 3:"Maart", 4:"April", 5:"Mei", 6:"Juni", 7:"Juli", 8:"Augustus", 9:"September", 10:"Oktober", 11:"November", 12:"December"}
        sheet_name = f"Aanmeldingen_{maand_namen[event_date.month]}_{event_date.year}"
        
        try:
            sh.worksheet(sheet_name)
            st.warning(f"⚠️ Het tabblad '{sheet_name}' bestond al. We gebruiken deze.")
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title=sheet_name, rows="100", cols="6")
            ws.append_row(["Naam", "Email", "Type", "Diner Keuze", "Tijdstempel"])
            st.success(f"✅ Nieuw tabblad '{sheet_name}' aangemaakt.")

        config_data = [
            ["KEY", "VALUE"],
            ["SPEAKER_NAME", speaker_name],
            ["SPEAKER_ROLE", speaker_role],
            ["SPEAKER_BIO", speaker_bio],
            ["SPEAKER_LINKEDIN", speaker_linkedin],
            ["EVENT_IMAGE", speaker_img],
            ["EVENT_DATE", str(event_date)],
            ["TIME_DINNER", str(time_dinner)],
            ["TIME_LECTURE", str(time_lecture)],
            ["TIME_END", str(time_end)],
            ["LOC_DINNER_NAME", loc_dinner_name],
            ["LOC_DINNER_ADDR", loc_dinner_addr],
            ["LINK_MAPS_DINNER", link_maps_dinner],
            ["LOC_LECTURE_NAME", loc_lecture_name],
            ["LOC_LECTURE_ADDR", loc_lecture_addr],
            ["LINK_MAPS_LECTURE", link_maps_lecture],
            ["LINK_VIDEO", link_video],
            ["LINK_PAYMENT", link_payment],
            ["CURRENT_SHEET_NAME", sheet_name]
        ]
        
        ws_config = sh.worksheet("Config")
        ws_config.clear()
        ws_config.update(config_data) 
        
        st.balloons()
        st.success("✅ Configuratie succesvol opgeslagen!")
        
    except Exception as e:
        st.error(f"Fout: {e}")

# --- EXTRA: MAILCHIMP EXPORT ---
st.divider()
st.subheader("📢 Nieuwsbrief / Uitnodiging Export")
st.info("Gebruik dit om de uitnodiging voor Mailchimp te genereren. Vul eerst bovenstaand formulier in.")

# Veld voor de link naar de app
app_url_input = st.text_input("Link naar de Aanmeld App (kopieer de URL van je browser)", "https://jouw-app.streamlit.app")

if st.button("Genereer Mailchimp HTML"):
    # We gebruiken de variabelen uit de UI widgets van hierboven
    html_output = generate_mailchimp_html(
        speaker_name, speaker_role, speaker_bio, speaker_img,
        event_date, time_dinner, time_lecture,
        loc_dinner_name, loc_dinner_addr, link_maps_dinner,
        loc_lecture_name, loc_lecture_addr, link_maps_lecture,
        app_url_input
    )
    
    st.text_area("Kopieer deze code en plak in een 'Code Block' in Mailchimp:", html_output, height=300)
    st.caption("Tip: In Mailchimp kies je voor een blok 'Code' (of 'HTML') en plak je dit erin.")
