import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, time
import urllib.parse

# --- 1. BEVEILIGING (PASSWORD CHECK) ---
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

# --- 3. UI ---
st.set_page_config(page_title="Admin: Nieuwe Lezing", page_icon="🛠️", layout="wide")
st.title("🛠️ Organisator Dashboard")
st.success("Ingelogd. Gebruik dit formulier om de volgende lezing klaar te zetten.")

with st.form("event_form"):
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📅 Datum & Tijd")
        event_date = st.date_input("Datum Lezing")
        time_dinner = st.time_input("Starttijd Diner", value=time(18, 0))
        time_lecture = st.time_input("Starttijd Lezing", value=time(19, 30))
        time_end = st.time_input("Eindtijd", value=time(21, 0))
        
        st.subheader("👤 Spreker Info")
        speaker_name = st.text_input("Naam Spreker")
        speaker_role = st.text_input("Rol / Functie")
        speaker_bio = st.text_area("Biografie", height=150)
        speaker_img = st.text_input("Link naar foto (URL)")
        speaker_linkedin = st.text_input("Link naar LinkedIn")

    with c2:
        st.subheader("📍 Locaties")
        # Diner
        loc_dinner_name = st.text_input("Naam Restaurant", "Restaurant & Pizzeria Lucca Due")
        loc_dinner_addr = st.text_input("Adres Restaurant", "Haarlemmerstraat 130, Amsterdam")
        # Default Google Maps link genereren
        def_maps_din = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote('Restaurant & Pizzeria Lucca Due Haarlemmerstraat 130, Amsterdam')}"
        link_maps_dinner = st.text_input("Google Maps Link Diner", def_maps_din)
        
        st.markdown("---")
        
        # Lezing
        loc_lecture_name = st.text_input("Naam Locatie Lezing", "De Piramide")
        loc_lecture_addr = st.text_input("Adres Locatie Lezing", "Haarlemmer Houttuinen, Amsterdam")
        # Default Google Maps link genereren
        def_maps_lec = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote('De Piramide Haarlemmer Houttuinen, Amsterdam')}"
        link_maps_lecture = st.text_input("Google Maps Link Lezing", def_maps_lec)
        
        st.subheader("🔗 Links")
        link_video = st.text_input("Google Meet / Video Link")
        link_payment = st.text_input("Betaalverzoek Link (Bunq/Tikkie)")

    st.markdown("---")
    submitted = st.form_submit_button("💾 Opslaan & Live Zetten", type="primary")

if submitted:
    try:
        client = get_client()
        sh = client.open("EU_Lezingen_Master")
        
        # Naam van het tabblad bepalen
        maand_namen = {1:"Januari", 2:"Februari", 3:"Maart", 4:"April", 5:"Mei", 6:"Juni", 7:"Juli", 8:"Augustus", 9:"September", 10:"Oktober", 11:"November", 12:"December"}
        sheet_name = f"Aanmeldingen_{maand_namen[event_date.month]}_{event_date.year}"
        
        # Check of tabblad bestaat
        try:
            sh.worksheet(sheet_name)
            st.warning(f"⚠️ Het tabblad '{sheet_name}' bestond al. We gebruiken deze.")
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title=sheet_name, rows="100", cols="6")
            ws.append_row(["Naam", "Email", "Type", "Diner Keuze", "Tijdstempel"])
            st.success(f"✅ Nieuw tabblad '{sheet_name}' aangemaakt.")

        # Config wegschrijven
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
            ["LINK_MAPS_DINNER", link_maps_dinner],   # NIEUW
            ["LOC_LECTURE_NAME", loc_lecture_name],
            ["LOC_LECTURE_ADDR", loc_lecture_addr],
            ["LINK_MAPS_LECTURE", link_maps_lecture], # NIEUW
            ["LINK_VIDEO", link_video],
            ["LINK_PAYMENT", link_payment],
            ["CURRENT_SHEET_NAME", sheet_name]
        ]
        
        ws_config = sh.worksheet("Config")
        ws_config.clear()
        ws_config.update(config_data) 
        
        st.balloons()
        st.success("✅ Configuratie opgeslagen! De bezoekers-app is nu geüpdatet.")
        
    except Exception as e:
        st.error(f"Fout: {e}")
