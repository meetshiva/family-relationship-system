from relationship_patterns import CHAIN_TO_RELATION
from streamlit_agraph import agraph, Node, Edge, Config
import streamlit as st
import pandas as pd
import gspread
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.service_account import Credentials as SACredentials
from google.oauth2.credentials import Credentials as OAuthCredentials
from google_auth_oauthlib.flow import (InstalledAppFlow)
from google.oauth2 import service_account
import os
import requests

validation_failed = False
py_patterns = True    # Set to True to get the relationship from py_patterns file
gs_patterns = False   # Set to True to get the relationship from Google sheet patterns sheet
show_greetings_flag = True
send_email_flag = False
perfomance_needed = False
PHOTO_FOLDER_ID = "17qtspO2EVTvB1C7oRQc3-TXAbbjXggoi"
EVENT_INVITATION_FOLDER_ID = "1WqXhqehrSXsxXTuQbGKQqJeePyWFJCZZ"
local_dev = False

st.set_page_config(page_title="Family Relationships System",layout="wide")

# =====================================================
# SESSION STATE INITIALIZATION
# =====================================================

defaults = {
    "update_verified": False,
    "org_verified": False,
    "org_name": "",
    "organizer_mobile": "",
    "upd_ph_no": "",
    "upd_status": "Alive",
    "upd_marital": "",
    "upd_anniv": "",
    "upd_email": "",
    "upd_gothram": "",
    "upd_occ": "",
    "upd_paddr": "",
    "upd_perm": "",
    "upd_comments": ""
}

defaults = {

    "verified": False,
    "save_msg": "",
    "reset_flag": False,
    "show_test_pin": False,
    "show_graph": False,
    "show_details": False,
    "logs": []

}


for k, v in defaults.items():

    if k not in st.session_state:

        st.session_state[k] = v
        
    
c1, c2 = st.columns([1,11])

with c1:

    if local_dev:
        st.image(r"C:\Shiva_Folder\3_Documents\1_Education\Python\GPT_Family_Rship_Project\Photos\Main_Page_Logo.jpg",width=80)
    else:
        st.image("assets/Main_Page_Logo.jpg",width=80)

with c2:

    st.title("Welcome to Family Relationships System")
    
st.markdown("""
<style>

/* ---------- MAIN BACKGROUND ---------- */
.stApp {
    background: linear-gradient(to right, #eef2f3, #dfe9f3);
}


/* ---------- TITLE ---------- */
h1 {
    color: #003366;
    text-align: left;
    font-weight: 800;
    font-size: 42px;
    margin-top: 10px;
}


/* ---------- INPUT BOXES ---------- */
.stTextInput > div > div > input {
    border-radius: 10px;
    border: 1px solid #b0c4de;
    padding: 10px;
    font-size: 16px;
}


/* ---------- BUTTONS ---------- */
.stButton button {
    background-color: #0059b3;
    color: white;
    border-radius: 10px;
    border: none;
    padding: 10px 25px;
    font-size: 16px;
    font-weight: bold;
    transition: 0.3s;
}

.stButton button:hover {
    background-color: #003d80;
    color: white;
}


/* ---------- SUCCESS BOX ---------- */
.stSuccess {
    border-radius: 10px;
    background-color: #d4edda;
    color: #155724;
    font-size: 16px;
}


/* ---------- ERROR BOX ---------- */
.stError {
    border-radius: 10px;
    background-color: #f8d7da;
    color: #721c24;
    font-size: 16px;
}


/* ---------- DATAFRAME ---------- */
[data-testid="stDataFrame"] {
    border-radius: 12px;
    border: 1px solid #d0d7de;
    overflow: hidden;
}


/* ---------- SIDEBAR ---------- */
section[data-testid="stSidebar"] {
    background-color: #f5f7fa;
}


/* ---------- EXPANDER ---------- */
.streamlit-expanderHeader {
    font-weight: bold;
    color: #003366;
    font-size: 16px;
}

</style>
""", unsafe_allow_html=True)

def log(msg, level="INFO"):
    if not st.session_state.get("debug", False):
        return

    if "logs" not in st.session_state:
        st.session_state.logs = []

    st.session_state.logs.append({
        "Time": datetime.now().strftime("%H:%M:%S"),
        "Level": level,
        "Message": msg
    })
    
# ---------- CONNECT ----------
def connect(sheet):
    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    if local_dev:
        creds = SACredentials.from_service_account_file("credentials.json",scopes=SCOPES)
    else:
        creds = SACredentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]),
        scopes=SCOPES)
    
    #st.write("Service Account:",creds.service_account_email)
    
    client = gspread.authorize(creds)
    return client.open("Family_Tree_New").worksheet(sheet)

# ---------- RESET ----------
def reset_form():
    st.session_state.reset_flag = True
    st.session_state.verified = False

if st.session_state.reset_flag:
    for k in ["aadhaar","name","dob","parent","couple","mobile","paddr","perm","comments"]:
        if k in st.session_state:
            del st.session_state[k]
    st.session_state.reset_flag = False

# ---------- HELPERS ----------
def get_row(a):
    log(f"Fetching row for ID: {a}", "INFO")

    r = rship_df[rship_df["AADHAAR_NUM"] == str(a)]

    if not r.empty:
        log(f"Found row → Parent: {r.iloc[0]['RELATIVE_AADHAAR']}", "INFO")
        return r.iloc[0]
    else:
        log("No row found", "WARN")
        return None
    

def get_name(a):
    r = get_row(a)
    return r["MEMBER_NAME"] if r is not None else str(a)

def get_master(a):
    r = master_df[master_df["AADHAAR_NUM"] == str(a)]
    return r.iloc[0] if not r.empty else None
    
def show_full_details(aadhaar):
    row = master_df[master_df["AADHAAR_NUM"] == str(aadhaar)]
    if row.empty:
        st.warning("No details found")
        return

    row = row.iloc[0]

    for col in master_df.columns:
        st.write(f"{col}: {row.get(col,'')}")

def get_drive_image_url(photo_url):

    photo_url = str(photo_url).strip()

    if "/file/d/" in photo_url:

        file_id = (
            photo_url
            .split("/file/d/")[1]
            .split("/")[0]
        )

        return (
            "https://drive.usercontent.google.com/download"
            f"?id={file_id}&export=view&authuser=0"
        )

    return photo_url
    
def show_details_grid(source, target):

    src = get_master(source)
    tgt = get_master(target)

    if src is None or tgt is None:
        return

    fields = [
        "MEMBER_NAME",
        "GENDER",
        "PH_NO",
        "DOB",
        "STATUS",
        "MARITAL_STATUS",
        "GOTHRAM",
        "OCCUPATION",
        "PRESENT_ADD",
        "PERMANENT_ADD",
        "COMMENTS"
    ]

    rows = []

    for field in fields:

        rows.append({
            "FIELD_NAME": field,
            "SOURCE_DETAILS": (
                ""
                if pd.isna(src.get(field, ""))
                else str(src.get(field, ""))
            ),
            "TARGET_DETAILS": (
                ""
                if pd.isna(tgt.get(field, ""))
                else str(tgt.get(field, ""))
            )
        })

    df = pd.DataFrame(rows)

    styled_df = df.style.set_properties(
        subset=["FIELD_NAME"],
        **{
            "font-weight": "bold"
        }
    ).set_table_styles([
        {
            'selector': 'th',
            'props': [
                ('font-weight', '900'),
                ('background-color', '#0059b3'),
                ('color', 'white'),
                ('text-align', 'center'),
                ('font-size', '16px')
            ]
        }
    ])

    st.dataframe(
        styled_df,
         width="stretch",
        hide_index=True
    )
    
    # ====================================
    # ADD BELOW THE DATAFRAME
    # ====================================

    c1, c2 = st.columns(2)

    with c1:

        st.markdown("### Source Photo")

        source_photo = src.get("PHOTO", "")

        if source_photo and \
            str(source_photo).strip():

            st.write("Source Photo URL:", source_photo)
            st.image(
                get_drive_image_url(source_photo),
                width=200
            )
        else:
            st.info(
                "Photo not uploaded"
            )
        

    with c2:

        st.markdown("### Target Photo")

        target_photo = tgt.get("PHOTO", "")

        if target_photo and \
            str(target_photo).strip():

            st.write("Target Photo URL:", target_photo)
            st.image(
                get_drive_image_url(target_photo),
                width=200
            )
        else:
            st.info(
                "Photo not uploaded"
            )


def validate_member_exists(source, target):

    src_exists = not master_df[
        master_df["AADHAAR_NUM"] == str(source)
    ].empty

    tgt_exists = not master_df[
        master_df["AADHAAR_NUM"] == str(target)
    ].empty

    if not src_exists:
        return False, "Source Aadhaar"

    if not tgt_exists:
        return False, "Target Aadhaar"

    return True, ""

def run_relationship_test():

    test_sheet = connect("TEST_RSHIP")

    # Clear old data only
    test_sheet.batch_clear(["A2:G"])

    ids = list(rship_df["AADHAAR_NUM"].unique())

    progress = st.progress(0)

    combinations = []

    # Build combinations
    for src in ids:
        for tgt in ids:

            if src == tgt:
                continue

            combinations.append((src, tgt))

    total_combinations = len(combinations)

    # ✅ STORE ALL RESULTS HERE
    rows_to_insert = []

    for i, (src, tgt) in enumerate(combinations):

        try:

            path = build_path(src, tgt)

            if not path:

                relationship = "No Relation"
                path_text = ""
                chain_text = ""

            else:

                chain = build_chain(path)

                relationship = match_relationship(
                    chain,
                    src,
                    tgt
                )

                # SOURCE → TARGET
                path_forward = path[::1]

                path_text = format_path_with_relationship(
                    path_forward
                )

                chain_text = ".".join(
                    chain.split(".")[::1]
                )

            # ✅ ADD TO MEMORY
            rows_to_insert.append([

                src,
                tgt,

                get_name(src),
                get_name(tgt),

                relationship,

                path_text,
                chain_text

            ])

        except Exception as e:

            rows_to_insert.append([

                src,
                tgt,

                get_name(src),
                get_name(tgt),

                f"ERROR: {str(e)}",

                "",
                ""

            ])

        progress.progress((i + 1) / total_combinations)

    # ✅ SINGLE BULK WRITE
    if rows_to_insert:
        test_sheet.append_rows(rows_to_insert)

    st.success(
        f"Testing completed for {total_combinations} combinations"
    )
def show_family_tree():

    nodes = []
    edges = []

    added_nodes = set()
    id_map = {}

    # ---------- FIND ROOT MEMBERS ----------
    root_ids = set(

        rship_df[
            rship_df["RELATIVE_AADHAAR"]
            .fillna("")
            .astype(str)
            .str.strip() == ""
        ]["AADHAAR_NUM"].astype(str)

    )

    # ---------- CREATE NODES ----------
    for _, row in master_df.iterrows():

        #aadhaar = str(row["AADHAAR_NUM"])
        #name = str(row["MEMBER_NAME"])
        aadhaar = str(row["AADHAAR_NUM"])
        name = str(row["MEMBER_NAME"])

        node_id = f"N{len(id_map)+1}"

        id_map[aadhaar] = node_id

        gender = str(
            row.get("GENDER", "")
        ).upper()

        # ---------- ROOT NODE ----------
        if aadhaar in root_ids:

            color = "#FFD700"      # Gold
            size = 30
            shape = "diamond"

            borderWidth = 8

            font = {
                "size": 40,
                "face": "Tahoma",
                "bold": True,
                "color": "#8B0000"
            }

            shadow = True

        # ---------- NORMAL MEMBERS ----------
        else:

            color = (
                "#87CEEB"
                if gender == "M"
                else "#FFB6C1"
            )

            size = 20

            shape = "dot"

            borderWidth = 1

            font = {
                "size": 12,
                "face": "Tahoma"
            }

            shadow = False

        # ---------- ADD NODE ----------
        if aadhaar not in added_nodes:

            nodes.append(

                Node(

                    id=node_id,

                    label=name,

                    title=name,
                    
                    size=size,

                    color=color,

                    shape=shape,

                    borderWidth=borderWidth,

                    shadow=shadow,

                    font=font
                )
            )

            added_nodes.add(aadhaar)

    # ---------- CREATE EDGES ----------
    for _, row in rship_df.iterrows():

        child = str(row["AADHAAR_NUM"])

        parent = str(
            row["RELATIVE_AADHAAR"]
        )

        rel = str(
            row.get(
                "RSHIP_TO_AADHAAR_NUM",
                ""
            )
        )

        if parent and parent != "nan":

            edges.append(

                Edge(

                    source=id_map.get(parent),

                    target=id_map.get(child),

                    label=rel,

                    smooth={
                        "type": "curvedCW",
                        "roundness": 0.2
                    },

                    font={
                        "size": 14,
                        "align": "middle"
                    },

                    color="#A9A9A9"
                )
            )

    # ---------- GRAPH CONFIG ----------
    config = Config(

        width="100%",

        height=1000,

        directed=True,

        physics=False,

        hierarchical={

            "enabled": True,

            "levelSeparation": 180,

            "nodeSpacing": 250,

            "treeSpacing": 250,

            "blockShifting": True,

            "edgeMinimization": True,

            "parentCentralization": True,

            "direction": "UD",

            "sortMethod": "directed"
        },

        nodeHighlightBehavior=True,

        highlightColor="#F7A7A6",

        collapsible=True
    )

    # ---------- SHOW GRAPH ----------
    agraph(
        nodes=nodes,
        edges=edges,
        config=config
    )

def send_greetings():

    today = datetime.now()

    today_day_month = today.strftime("%d-%b")

    birthday_people = []

    anniv_people = []

    for _, row in master_df.iterrows():

        status = str(
            row.get("STATUS", "")
        ).strip().upper()

        if status != "ALIVE":
            continue

        name = str(
            row.get("MEMBER_NAME", "")
        )

        email = str(
            row.get("EMAIL_ID", "")
        ).strip()

        dob = str(
            row.get("DOB", "")
        ).strip()

        anniv = str(
            row.get("MRG_ANNIV_DATE", "")
        ).strip()

        # ---------- BIRTHDAY ----------
        try:

            if dob:

                dob_day_month = datetime.strptime(
                    dob,
                    "%d-%b-%Y"
                ).strftime("%d-%b")

                if dob_day_month == today_day_month:

                    photo = str(
                        row.get("PHOTO", "")
                    ).strip()

                    birthday_people.append(
                        (name, email, photo)
                    )

        except:
            pass

        # ---------- ANNIVERSARY ----------
        try:

            if anniv:

                anniv_day_month = datetime.strptime(
                    anniv,
                    "%d-%b-%Y"
                ).strftime("%d-%b")

                if anniv_day_month == today_day_month:

                    photo = str(
                        row.get("PHOTO", "")
                    ).strip()

                    anniv_people.append(
                        (name, email, photo)
                    )

        except:
            pass

    return birthday_people, anniv_people

def send_invitation(
    subject,
    html,
    attachment_path=None
):
    file_id = "1kdXBAFI3MWTgVrJFVcUyZFa5VDHLgIv6"
    download_url = (
        "https://drive.google.com/uc?export=download&id="
        + file_id
    )

    r = requests.get(download_url)

    with open("event_invitation.jpg", "wb") as f:
        f.write(r.content)
    recipients = []

    for _, row in master_df.iterrows():

        status = str(
            row.get("STATUS", "")
        ).strip().upper()

        email = str(
            row.get("EMAIL_ID", "")
        ).strip()

        if (
            status == "ALIVE"
            and email != ""
        ):

            recipients.append(email)

    for email in recipients:

        try:

            send_email(
                email,
                subject,
                html,
                "event_invitation.jpg"
            )

        except Exception as e:

            st.error(
                f"Failed to send email to "
                f"{email}: {e}"
            )

    return len(recipients)
    
def send_email(
    to_email,
    subject,
    html,
    image_path=None
):

    sender_email = "familyrelationshipsystem@gmail.com"

    app_password = "dpke qqgw anrw zqit"

    try:

        # ---------- ROOT MESSAGE ----------
        msg = MIMEMultipart("mixed")

        msg["Subject"] = subject
        msg["From"] = sender_email
        msg["To"] = to_email

        # ---------- RELATED PART ----------
        related = MIMEMultipart("related")

        # ---------- HTML PART ----------
        alt = MIMEMultipart("alternative")

        html_part = MIMEText(
            html,
            "html"
        )

        alt.attach(html_part)

        related.attach(alt)

        # ---------- INLINE IMAGE ----------
        if image_path:

            with open(image_path, "rb") as img:

                mime_img = MIMEImage(
                    img.read()
                )

                mime_img.add_header(
                    "Content-ID",
                    "<member_photo>"
                )

                mime_img.add_header(
                    "Content-Disposition",
                    "inline"
                )

                related.attach(mime_img)

        # ---------- ATTACH RELATED ----------
        msg.attach(related)

        # ---------- SEND ----------
        server = smtplib.SMTP(
            "smtp.gmail.com",
            587
        )

        server.starttls()

        server.login(
            sender_email,
            app_password
        )

        server.send_message(msg)

        server.quit()

        return True

    except Exception as e:

        st.error(
            f"Email failed: {str(e)}"
        )

        return False

SCOPES = [
    "https://www.googleapis.com/auth/drive.file"
]

def get_drive_service_local():

    creds = None

    if os.path.exists("token.json"):

        creds = OAuthCredentials.from_authorized_user_file(
            "token.json",
            SCOPES
        )

    if not creds or not creds.valid:

        flow = InstalledAppFlow.from_client_secrets_file(
            "oauth_client.json",
            SCOPES
        )

        creds = flow.run_local_server(
            port=0
        )

        with open(
            "token.json",
            "w"
        ) as token:

            token.write(
                creds.to_json()
            )

    return build(
        "drive",
        "v3",
        credentials=creds
    )

def get_drive_service_old():

    
    creds = service_account.Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]),
        scopes=SCOPES)

    return build(
        "drive",
        "v3",
        credentials=creds
    )

def get_drive_service():

    creds = OAuthCredentials(
        token=None,
        refresh_token=st.secrets["gdrive_oauth"]["refresh_token"],
        token_uri=st.secrets["gdrive_oauth"]["token_uri"],
        client_id=st.secrets["gdrive_oauth"]["client_id"],
        client_secret=st.secrets["gdrive_oauth"]["client_secret"],
        scopes=SCOPES
    )

    return build(
        "drive",
        "v3",
        credentials=creds
    )
    
def upload_photo_to_drive(
    uploaded_file,
    aadhaar,
    name
):

    if local_dev:
        drive_service = get_drive_service_local()
    else:
        drive_service = get_drive_service()

    safe_name = (
    str(name)
    .strip()
    .replace(" ", "_")
    )

    temp_file = (
        f"{aadhaar}_{safe_name}.jpg"
    )

    with open(temp_file, "wb") as f:

        f.write(
            uploaded_file.getbuffer()
        )

    file_metadata = {

        "name": (f"{aadhaar}_{safe_name}.jpg"),

        "parents": [PHOTO_FOLDER_ID]
    }

    media = MediaFileUpload(
        temp_file,
        resumable=True
    )

    try:
        file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id"
        ).execute()

    except Exception as e:
        st.error(str(e))
        raise

    file_id = file.get("id")

    drive_service.permissions().create(
        fileId=file_id,
        body={
            "type": "anyone",
            "role": "reader"
        }
    ).execute()

    return (
        f"https://drive.google.com/file/d/"
        f"{file_id}/view"
    )

def upload_event_invitation_to_drive(
    uploaded_file,
    aadhaar,
    event_name,
    event_date
):

    if local_dev:
        drive_service = get_drive_service_local()
    else:
        drive_service = get_drive_service()

    safe_event_name = (
        str(event_name)
        .strip()
        .replace(" ", "_")
        .replace("/", "_")
    )

    event_date_str = (
        event_date.strftime("%d-%b-%Y")
    )

    extension = (
        uploaded_file.name
        .split(".")[-1]
    )

    file_name = (
        f"{aadhaar}_"
        f"{safe_event_name}_"
        f"{event_date_str}."
        f"{extension}"
    )

    temp_file = file_name

    with open(temp_file, "wb") as f:

        f.write(
            uploaded_file.getbuffer()
        )

    file_metadata = {

        "name": file_name,

        "parents": [
            EVENT_INVITATION_FOLDER_ID
        ]
    }

    media = MediaFileUpload(
        temp_file,
        resumable=True
    )

    file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id"
    ).execute()

    file_id = file.get("id")

    drive_service.permissions().create(
        fileId=file_id,
        body={
            "type": "anyone",
            "role": "reader"
        }
    ).execute()

    return (
        f"https://drive.google.com/file/d/"
        f"{file_id}/view"
    )
    
def get_age_difference(source, target):
    try:
        s_dob = pd.to_datetime(get_master(source)["DOB"])
        t_dob = pd.to_datetime(get_master(target)["DOB"])

        return abs((s_dob - t_dob).days) / 365.25

    except:
        return 0
        
def format_path_with_relationship(path_ids):
    formatted = []

    for i, pid in enumerate(path_ids):
        row = get_row(pid)
        name = get_name(pid)

        #LAST NODE (TARGET) → NO SUFFIX
        if i == len(path_ids) - 1:
            formatted.append(name)
            continue

        if row is not None:
            rel = row.get("RSHIP_TO_AADHAAR_NUM", "")

            if rel:
                #label = f"{name}(is {rel} of)"
                label = f"{name}"
            else:
                #label = f"{name}(ROOT)"
                label = f"{name}"
        else:
            label = name

        formatted.append(label)

    return " → ".join(formatted)

# ---------- PATH ----------
def get_ancestry(a):
    path=[]
    while True:
        r=get_row(a)
        if r is None: break
        path.append(a)
        p = str(r["RELATIVE_AADHAAR"]).strip()

        log(f"{a} → Parent: {p}", "INFO")
        if p=="" or p=="nan": 
           log("Reached ROOT", "INFO")
           break
        a=p
    return path

def build_path(s,t):
    log("=== BUILD PATH START ===", "INFO")

    src = get_ancestry(s)
    tgt = get_ancestry(t)

    log(f"Source ancestry: {src}", "INFO")
    log(f"Target ancestry: {tgt}", "INFO")

    common = next((x for x in src if x in tgt), None)

    if not common:
        log("No common ancestor found", "ERROR")
        return []

    log(f"Common ancestor: {common}", "INFO")

    up = src[:src.index(common)+1]
    down = tgt[:tgt.index(common)]
    down.reverse()

    final_path = up + down

    log(f"Final path: {final_path}", "INFO")

    return final_path

# ---------- CHAIN ----------
def build_chain(path):
    chain=[]
    log("--- Building chain ---", "INFO")

    for p in path:
        r = get_row(p)
        if r is None:
            log(f"No row for {p}", "WARN")
            continue

        rel = r.get("RSHIP_TO_AADHAAR_NUM","") or "R"
        g = r.get("GENDER","")

        log(f"{p} → {rel}({g})", "INFO")

        chain.append(f"{rel}({g})")

    return ".".join(chain)

# ---------- DOB ----------
def is_source_younger(s,t):
    try:
        s=pd.to_datetime(get_master(s)["DOB"])
        t=pd.to_datetime(get_master(t)["DOB"])
        return s>t
    except:
        return False

# ---------- UNKNOWN LOG ----------
def log_unknown(s,t,path,chain):
    try:
        connect("Unknown_RSHIPS").append_row([s,t," → ".join(path),chain])
    except:
        pass

if py_patterns: 
    # ---------- LOAD ----------
    @st.cache_data
    def load_data():
        m = connect("FAMILY_MEMBERS_MASTER")
        r = connect("FAMILY_MEMBERS_RSHIPS")

        mdf = pd.DataFrame(m.get_all_records())
        rdf = pd.DataFrame(r.get_all_records())

        mdf.columns = [c.upper() for c in mdf.columns]
        rdf.columns = [c.upper() for c in rdf.columns]

        mdf["AADHAAR_NUM"] = mdf["AADHAAR_NUM"].astype(str)
        rdf["AADHAAR_NUM"] = rdf["AADHAAR_NUM"].astype(str)
        rdf["RELATIVE_AADHAAR"] = rdf["RELATIVE_AADHAAR"].astype(str)

        return mdf, rdf

    master_df, rship_df = load_data()
    b1, b2, b3, b4 = st.columns(4)

    with b1:
        refresh_clicked = st.button(
            "🔄 Refresh Data(py)",
             width="stretch"
        )

    with b2:

        show_birthdays = st.button(
            "🎂 Today's Birthdays",
             width="stretch"
        )

    with b3:

        show_anniv = st.button(
            "💍 Today's Marriage Anniversaries",
             width="stretch"
        )
    # ---------- REFRESH ----------
    if refresh_clicked:

        st.cache_data.clear()

        st.success(
            "Data refreshed successfully"
        )

        st.rerun()

    # ---------- SESSION ----------
    for k in ["verified","save_msg","reset_flag"]:
        if k not in st.session_state:
            st.session_state[k] = False if k!="save_msg" else ""
            
    # ---------- MATCH ----------
    def match_relationship(chain, source, target):

        src_row = get_row(source)
        tgt_row = get_row(target)

        src_parent = str(src_row.get("RELATIVE_AADHAAR","")) if src_row is not None else ""
        tgt_parent = str(tgt_row.get("RELATIVE_AADHAAR","")) if tgt_row is not None else ""

        age_gap = get_age_difference(source, target)
        
        # SON CASE
        if chain == "S(M).S(M)":
            return "Son" if is_source_younger(source, target) else "Father"
            
            # ---------- S(M).S(M).S(M) ----------
        if chain == "S(M).S(M).S(M)":

            # Same parent + close age → Brother
            if src_parent and src_parent == tgt_parent and age_gap <= 35:
                return "Brother"

            # Large age gap → Grand Son / Grand Father
            return "Grand Father" if is_source_younger(source, target) else "Grand Son"
            
                # ---------- S(M).S(M).S(M) ----------
        if chain == "S(M).S(M).D(F)":

            # Same parent + close age → Brother
            if src_parent and src_parent == tgt_parent and age_gap <= 35:
                return "Brother"

            # Large age gap → Grand Daughter / Grand Father
            return "Grand Father" if is_source_younger(source, target) else "Grand Daughter"

        # DAUGHTER CASE
        if chain in ["D(F).D(F)", "D(F).W(F)", "D(F).R(F)"]:
            return "Daughter" if is_source_younger(source, target) else "Mother"


        # ---------- EXISTING LOGIC (UNCHANGED) ----------         
        if chain in CHAIN_TO_RELATION:
            return CHAIN_TO_RELATION[chain]

        return "Unknown"

    # ---------- MAIN ----------
    # ---------- FULL TEST ----------
    TEST_PIN = "417655"

    # =====================================================
    # RUN TEST BUTTON
    # =====================================================

    with b4:
        if st.button("🧪 Run Full Relationship Test"):
            st.session_state.show_test_pin = True
    # =====================================================
    # SHOW PIN SECTION
    # =====================================================

    if st.session_state.get("show_test_pin", False):

        entered_pin = st.text_input(
            "Enter Test Execution PIN",
            type="password",
            key="test_pin"
        )

        c1, c2 = st.columns(2)

        # ---------- VERIFY ----------
        with c1:

            if st.button("✅ Verify & Run Test"):

                if entered_pin == TEST_PIN:

                    st.success("PIN verified successfully")

                    run_relationship_test()

                    st.session_state.show_test_pin = False

                else:

                    st.error("Invalid PIN")

        # ---------- CANCEL ----------
        with c2:

            if st.button("❌ Cancel Test"):

                st.session_state.show_test_pin = False

                st.rerun()
            
    debug_mode = st.checkbox("Enable Debug Logs", value=False)
    st.session_state.debug = debug_mode

    if show_greetings_flag:
        # =====================================================
        # SHOW GREETINGS
        # =====================================================
        # ---------- BIRTHDAYS ----------
        if show_birthdays:
            birthdays, anniversaries = send_greetings()

            st.markdown(
                "## 🎂 Today's Birthdays"
            )
            if birthdays:

                for name, email, photo in birthdays:

                    st.success(
                        f"🎉 Happy Birthday {name}"
                    )

                    if send_email_flag:
                        if email:

                            subject = \
                                f"Happy Birthday {name} 🎂"

                            html = f"""
                            <html>

                            <body style="
                                font-family: Arial;
                                text-align: left;
                                padding: 20px;
                            ">

                                <h2>
                                    Dear {name},
                                </h2>

                                <p style="
                                    font-size:18px;
                                    line-height:1.8;
                                ">

                                    Wishing you a very Happy Birthday 🎉🎂

                                    <br><br>

                                    May your day be filled with joy,
                                    health and happiness.

                                </p>

                                <br>

                                {
                                    '<img src="cid:member_photo" '
                                    'width="300" '
                                    'style="border-radius:15px;'
                                    'border:3px solid #0059b3;">'
                                    if photo else ''
                                }

                                <br><br>

                                <h3 style="
                                    color:#0059b3;
                                ">

                                    Best Wishes,
                                    <br>

                                    Family Relationship System

                                </h3>

                            </body>

                            </html>
                            """

                            sent = send_email(
                                email,
                                subject,
                                html,
                                photo
                            )

                            if sent:

                                st.info(
                                    f"Birthday email sent to {name}"
                                )
            else:
                st.info(
                    "No birthdays today"
                )

        # ---------- ANNIVERSARIES ----------
        if show_anniv:
            birthdays, anniversaries = send_greetings()

            st.markdown(
                "## 💍 Today's Marriage Anniversaries"
            )
            if anniversaries:
                for name, email, photo in anniversaries:

                    st.success(
                        f"💐 Happy Marriage Anniversary {name}"
                    )

                    if send_email_flag:
                        if email:

                            subject = \
                                f"Happy Marriage Anniversary {name} 💍"

                            html = f"""
                            <html>

                            <body style="
                                font-family: Arial;
                                text-align: left;
                                padding: 20px;
                            ">

                                <h2>
                                    Dear {name},
                                </h2>

                                <p style="
                                    font-size:18px;
                                    line-height:1.8;
                                ">

                                    Wishing you a very Happy Marriage Anniversary 💐

                                    <br><br>

                                    May your life continue to be filled with love and happiness.

                                </p>

                                <br>

                                {
                                    '<img src="cid:member_photo" '
                                    'width="300" '
                                    'style="border-radius:15px;'
                                    'border:3px solid #0059b3;">'
                                    if photo else ''
                                }

                                <br><br>

                                <h3 style="
                                    color:#0059b3;
                                ">

                                    Best Wishes,
                                    <br>

                                    Family Relationship System

                                </h3>

                            </body>

                            </html>
                            """

                            sent = send_email(
                                email,
                                subject,
                                html,
                                photo
                            )

                            if sent:

                                st.info(
                                    f"Anniversary email sent to {name}"
                                )
            else:
                st.info(
                    "No marriage anniversaries today"
                )
    if perfomance_needed:

        with st.form("relationship_form"):

            c1, c2 = st.columns(2)

            source = c1.text_input(
                "Source Aadhaar"
            )

            target = c2.text_input(
                "Target Aadhaar"
            )

            b1, b2 = st.columns(2)

            with b1:

                find_relationship = st.form_submit_button(
                    "Find Relationship"
                )

            with b2:

                show_tree = st.form_submit_button(
                    "🌳 Show Entire Family Tree"
                )
            if show_tree:
                st.session_state.show_graph = True

    else:
        with st.form("relationship_form"):

            c1, c2 = st.columns(2)

            source = c1.text_input(
                "Source Aadhaar"
            )

            target = c2.text_input(
                "Target Aadhaar"
            )

            b1, b2 = st.columns(2)

            with b1:

                find_relationship = st.form_submit_button(
                    "Find Relationship"
                )

            with b2:

                show_tree = st.form_submit_button(
                    "🌳 Show Entire Family Tree"
                )
            if show_tree:
                st.session_state.show_graph = True
        
    if find_relationship:
        if st.session_state.get("debug", False):
            st.session_state.logs = []
        
        if not source.strip() or not target.strip():

            st.error("Please enter both Source and Target Aadhaar numbers")
            st.stop()
            
        path = build_path(source,target)

        if not path:

            valid, missing_side = validate_member_exists(
                source,
                target
            )

            if not valid:

                st.error(
                    f"No relationship found because "
                    f"{missing_side} member details do not exist"
                )

            else:

                st.error("No relationship path found")
        else:
            names=[get_name(p) for p in path]
            chain=build_chain(path)
            rel=match_relationship(chain,source,target)
            
            st.success(f"{source}({get_name(source)}) is {rel} of {target}({get_name(target)})")
            #st.success(f"{source}({get_name(source)}) {target}({get_name(target)})")
            path_forward = path[::1]
            st.write("Path:", format_path_with_relationship(path_forward))
            chain_forward = ".".join(chain.split(".")[::1])
            st.write("Chain:", chain_forward)
            # Relationship Level
            st.write(f"Relationship Level: {len(path)}")

            if rel != "Unknown":    #Show Source and Target details only if the relationship found
                #st.markdown("### Source and Target Details")

                st.session_state.show_details = True
                st.session_state.detail_source = source
                st.session_state.detail_target = target

                #show_details_grid(source, target)

            # ✅ UNKNOWN RELATIONSHIP
            else:
               log_unknown(source,target,names,chain)
           
            if st.session_state.get("debug", False):
                    st.markdown("---")
                    with st.expander("🔍 Debug Logs"):
                        if st.session_state.get("debug", False):
                            st.markdown("---")
                            with st.expander("🔍 Debug Logs"):

                                logs = st.session_state.get("logs", [])

                                if logs:
                                    df_logs = pd.DataFrame(logs)

                                    def highlight(row):
                                        if row["Level"] == "ERROR":
                                            return ['background-color: #ffcccc'] * len(row)
                                        elif row["Level"] == "WARN":
                                            return ['background-color: #fff3cd'] * len(row)
                                        else:
                                            return [''] * len(row)

                                    st.dataframe(df_logs.style.apply(highlight, axis=1),  width="stretch")
                                else:
                                    st.info("No logs available")
    
    if st.session_state.show_graph:

        c1, c2 = st.columns([8,1])

        with c2:

            if st.button(
                "❌ Close",key="close_family_tree"
            ):

                st.session_state.show_graph = False

                st.rerun()
        show_family_tree()

    if st.session_state.get(
        "show_details",
        False
    ):

        c1, c2 = st.columns([8,1])

        with c2:

            if st.button(
                "❌ Close",key="close_details"
            ):

                st.session_state.show_details = False

                st.rerun()

        st.markdown(
            "### Source and Target Details"
        )

        show_details_grid(
            st.session_state.detail_source,
            st.session_state.detail_target
        )       
        
    # ---------- ADD MEMBER ----------
    with st.expander("➕ Add Family Member"):
        if st.session_state.save_msg:
            st.success(st.session_state.save_msg)
            st.session_state.save_msg = ""

        st.subheader("* Indicates required fields")
        st.subheader("Step 1: Before adding member, first Verify your relative Aadhaar existence")
        verify_input = st.text_input("*Enter your own Parent/Brother/sister/spouse Aadhaar")

        if st.button("Verify"):
            if verify_input in master_df["AADHAAR_NUM"].values:
                st.success(f"Verified: {get_name(verify_input)}")
                st.session_state.verified=True
            else:
                st.error("Aadhaar not found")
                st.session_state.verified=False

        if st.session_state.verified:
            with st.form("family_member_add_form"):
                st.subheader("Step 2: Enter your details correctly")

                aadhaar = st.text_input("*AADHAAR")
                name = st.text_input("*Name")
                gender = st.selectbox("*Gender",["","M","F"], disabled=not st.session_state.verified)

                dob = st.text_input("*DOB (DD-MON-YYYY)", disabled=not st.session_state.verified).upper()
                mobile = st.text_input("Mobile", disabled=not st.session_state.verified)

                parent = st.text_input("*Relative Aadhaar", disabled=not st.session_state.verified)

                relation = st.selectbox(
                    "*Relationship to Relative[S-SON/D-DAUGHTER/F-FATHER/M-MOTHER/H-HUSBAND/W-WIFE]",
                    ["","S","D","F","M","H","W"],
                    disabled=not st.session_state.verified
                )

                couple_input = ""
                #if relation in ["H","W"]:
                #    couple_input = st.text_input("*Enter your Couple Identification Num(HusbandAadhaar(12 digits)WifeAadhaar(12 digits) Ex:100000000056100000000058",disabled=not st.session_state.verified)

                marital_ui = st.selectbox(
                    "*Marital Status [M-Married/S-Single/D-Divorced]",
                    ["","M","S","D"],
                    disabled=not st.session_state.verified
                )

                couple_input = st.text_input("*If married, Enter your Couple Identification Num(HusbandAadhaar(12 digits)WifeAadhaar(12 digits) Ex:100000000056100000000058",disabled=not st.session_state.verified)
                #couple_input = st.text_input("*Enter your Couple Identification Num(HusbandAadhaar(12 digits)WifeAadhaar(12 digits) Ex:100000000056100000000058",disabled=(not st.session_state.verified or relation not in ["H", "W"]))
                #couple_input = st.text_input("*If married, Couple Identification Number",disabled=(not st.session_state.verified or relation in ["H","W"]))
                mrg_anniv_date = ""

                #if marital_ui == "M":

                #    mrg_anniv_date = st.text_input("Enter Marriage Anniversary Date (DD-MON-YYYY)").upper()
            
                mrg_anniv_date = st.text_input("*If married, Enter Marriage Anniversary Date (DD-MON-YYYY)").upper()
                email_id = st.text_input("Email ID", disabled=not st.session_state.verified)
                got_hram = st.text_input("Gothram", disabled=not st.session_state.verified)
                occupation = st.text_input("Occupation", disabled=not st.session_state.verified)
                paddr = st.text_area("Present Address", disabled=not st.session_state.verified)
                perm = st.text_area("Permanent Address", disabled=not st.session_state.verified)
                comments = st.text_area("Enter Comments, If any", disabled=not st.session_state.verified)
                photo_file = st.file_uploader(
                    "Upload Photo",
                    type=["jpg", "jpeg", "png"]
                )                
                passcode = st.text_input("*Set your Passcode, minimum 4 characters (Remember this)",
                    type="password",disabled=not st.session_state.verified
                )

                confirm_passcode = st.text_input(
                    "*Re-enter your Passcode",
                    type="password",
                    disabled=not st.session_state.verified
                )
                col1,col2=st.columns(2)

                save_member = col1.form_submit_button("Save Member",disabled=not st.session_state.verified)

                cancel_member = col2.form_submit_button("Cancel") 
                if cancel_member:
                    reset_form()
                    st.rerun()
                    
                marital_map={"M":"Married","S":"Single","D":"Divorced"}
                if save_member:
                    validation_failed = False
                    #load_data()

                    # ---------- AADHAAR_NUM VALIDATION ----------
                    if not aadhaar.strip():

                        st.error("AADHAAR_NUM cannot be blank")
                        validation_failed = True
                    if aadhaar in master_df["AADHAAR_NUM"].values:
                        st.error("Entered Aadhaar already exists")
                        validation_failed = True
                    # ---------- NAME VALIDATION ----------
                    if not name.strip():

                        st.error("NAME cannot be blank")
                        validation_failed = True
                    # ---------- GENDER VALIDATION ----------
                    if not gender.strip():

                        st.error("GENDER cannot be blank")
                        validation_failed = True
                    # ---------- MOBILE VALIDATION ----------
                    mobile = str(mobile).strip()

                    # Validate ONLY if user entered value
                    if mobile != "":

                        if not mobile.isdigit():

                            st.error(
                                "Mobile number must contain only digits"
                            )

                            validation_failed = True

                        elif len(mobile) != 10:

                            st.error(
                                "Mobile number must be exactly 10 digits"
                            )

                            validation_failed = True

                    # ---------- VALIDATE RELATIVE AADHAAR ----------
                    if not parent.strip():
                        st.error("RELATIVE AADHAAR cannot be blank")
                        validation_failed = True
                        
                    else:
                        relative_exists = not master_df[
                        master_df["AADHAAR_NUM"] == str(parent)].empty

                        if not relative_exists:
                            st.error("Entered Relative Aadhaar does not exist")
                            validation_failed = True
                        
                    # ---------- VERIFY STEP1 vs STEP2 ----------
                    if str(parent).strip() != str(verify_input).strip():
                        st.error(
                            "Relative Aadhaar must match "
                            "the Aadhaar verified in Step 1"
                        )

                        validation_failed = True
                    
                    # ---------- Relationship to Relative VALIDATION ----------
                    if not relation.strip():
                        st.error("Relationship to Relative cannot be blank")
                        validation_failed = True
                        
                    # ---------- Marital Status VALIDATION ----------
                    if not marital_ui.strip():
                        st.error("Marital Status cannot be blank")
                        validation_failed = True

                    # SON/DAUGHTER VALIDATION (REGEX LOGIC)
                    if relation in ["S","D"]:
                        # ---------- CHECK COUPLE ID ----------
                        parent_row = get_master(parent)

                        existing_couple_id = ""

                        if parent_row is not None:
                            existing_couple_id = str(
                                parent_row.get(
                                    "COUPLE_IDENTIFICATION_NUM",
                                    ""
                                )
                            ).strip()

                        if not existing_couple_id:

                            st.warning("Your parents not registered as couple, for that you have to update their COUPLE_IDENTIFICATION_NUM,Cancel this form and Go to Update Couple Identification Number section and fill the details ")
                            validation_failed = True
                        
                    # ---------- DOB VALIDATION ----------
                    if not dob.strip():

                        st.error("DOB cannot be blank")
                        validation_failed = True

                    try:

                        dob_dt = datetime.strptime(
                            dob,
                            "%d-%b-%Y"
                        )

                        dob = dob_dt.strftime("%d-%b-%Y").upper()

                    except:

                        st.error(
                            "DOB format must be DD-MON-YYYY"
                        )

                        validation_failed = True

                    # ---------- ANNIVERSARY DATE VALIDATION ----------
                    if marital_ui == "M":

                        # HUSBAND/WIFE VALIDATION
                        if relation in ["H","W"]:
                            if not (len(couple_input)==24 and couple_input.isdigit()):
                                st.error("Invalid Couple Identification Number")
                                validation_failed = True
                            
                        if not mrg_anniv_date.strip():

                            st.error(
                                "Marriage Anniversary Date "
                                "cannot be blank if Married"
                            )

                            validation_failed = True

                        try:

                            anniv_dt = datetime.strptime(
                                mrg_anniv_date,
                                "%d-%b-%Y"
                            )

                            mrg_anniv_date = anniv_dt.strftime(
                                "%d-%b-%Y"
                            ).upper()

                        except:

                            st.error(
                                "Marriage Anniversary Date format "
                                "must be DD-MON-YYYY"
                            )

                            validation_failed = True
                        
                    # ---------- PASSCODE VALIDATION ----------
                    if not passcode.strip():

                        st.error(
                            "Passcode cannot be blank"
                        )

                        validation_failed = True

                    if passcode != confirm_passcode:

                        st.error(
                            "Passcode and Re-enter Passcode do not match"
                        )

                        validation_failed = True
                        
                    if len(passcode) < 4:

                        st.error(
                            "Passcode must be at least 4 characters"
                        )

                        validation_failed = True
                        
                    if validation_failed:
                        st.stop()
                    
                    photo_url = ""

                    if photo_file:

                        st.write("Step 1 - Before upload")
                        photo_url = upload_photo_to_drive(
                            photo_file,
                            aadhaar,
                            name
                        )
                        st.write("Step 2 - Upload completed")                    
                                    
                    # MASTER WRITE
                    st.write("Step 3 - Connecting sheet")
                    m_sheet = connect("FAMILY_MEMBERS_MASTER")
                    st.write("Step 4 - Connected")
                    headers = [h.upper() for h in m_sheet.row_values(1)]

                    m_dict={
                        "AADHAAR_NUM":aadhaar,
                        "MEMBER_NAME":name.upper(),
                        "GENDER":gender,
                        "PH_NO":mobile,
                        "DOB":dob,
                        "MARITAL_STATUS":marital_map.get(marital_ui,""),
                        "MRG_ANNIV_DATE": mrg_anniv_date,
                        "EMAIL_ID": email_id,
                        "GOTHRAM":got_hram,
                        "OCCUPATION":occupation,
                        "STATUS":"Alive",
                        "COUPLE_IDENTIFICATION_NUM": couple_input if relation in ["H","W"] else "",
                        "PHOTO": photo_url,
                        "PRESENT_ADD":paddr,
                        "PERMANENT_ADD":perm,
                        "COMMENTS":comments,
                        "PASSCODE": "'" + str(passcode)
                    }

                    m_row=[m_dict.get(h,"") for h in headers]
                    st.write("Step 5 - Writing MASTER record")
                    m_sheet.append_row(m_row)
                    st.write("Step 6 - Record MASTER written")

                    # RSHIPS WRITE
                    r_sheet = connect("FAMILY_MEMBERS_RSHIPS")
                    r_headers = [h.upper() for h in r_sheet.row_values(1)]

                    r_dict={
                        "AADHAAR_NUM":aadhaar,
                        "MEMBER_NAME":name.upper(),
                        "RELATIVE_AADHAAR":parent,
                        "RSHIP_TO_AADHAAR_NUM":relation,
                        "GENDER":gender,
                        "DOB":dob
                    }

                    r_row=[r_dict.get(h,"") for h in r_headers]
                    st.write("Step 7 - Writing RSHIPS record")
                    r_sheet.append_row(r_row)
                    st.write("Step 8 - Writing RSHIPS record")

                    st.cache_data.clear()
                    st.session_state.save_msg="Member Details saved Successfully"
                    reset_form()
                    st.rerun()
     
    # =====================================================
    # UPDATE COUPLE IDENTIFICATION NUM
    # =====================================================
    with st.expander("✏️ Update Couple Identification Number"):

        with st.form("couple_id_update_form"):
            f1, f2 = st.columns(2)

            father_aadhaar = f1.text_input(
                "Enter Father Aadhaar:"
            )

            mother_aadhaar = f2.text_input(
                "Enter Mother Aadhaar:"
            )

            update_couple = st.form_submit_button("Update Couple Identification Number")
            if update_couple:

                # ---------- VALIDATE FATHER ----------
                father_exists = not master_df[
                    master_df["AADHAAR_NUM"]
                    == str(father_aadhaar)
                ].empty

                if not father_exists:

                    st.error(
                        "Father Aadhaar details "
                        "not present, please add "
                        "that member first"
                    )

                    st.stop()

                # ---------- VALIDATE MOTHER ----------
                mother_exists = not master_df[
                    master_df["AADHAAR_NUM"]
                    == str(mother_aadhaar)
                ].empty

                if not mother_exists:

                    st.error(
                        "Mother Aadhaar details "
                        "not present, please add "
                        "that member first"
                    )

                    st.stop()

                # ---------- GENERATE COUPLE ID ----------
                couple_id = (
                    str(father_aadhaar)
                    + str(mother_aadhaar)
                )

                # ---------- UPDATE BOTH MEMBERS ----------
                master_sheet = connect(
                    "FAMILY_MEMBERS_MASTER"
                )

                records = master_sheet.get_all_records()

                for idx, row in enumerate(records, start=2):

                    aadhaar = str(
                        row.get("AADHAAR_NUM","")
                    )

                    if aadhaar in [
                        str(father_aadhaar),
                        str(mother_aadhaar)
                    ]:

                        col_index = (
                            master_df.columns
                            .get_loc(
                                "COUPLE_IDENTIFICATION_NUM"
                            ) + 1
                        )

                        master_sheet.update_cell(
                            idx,
                            col_index,
                            couple_id
                        )

                #st.success("COUPLE_IDENTIFICATION_NUM updated successfully, now you can add your details")
                st.cache_data.clear()
                st.session_state.save_msg="COUPLE_IDENTIFICATION_NUM updated successfully, now you can add your details"
                st.rerun()
    
    # ====================
    # Update Family Member
    # ====================
    with st.expander("✏️ Update Family Member"):

        st.subheader("Step 1: Validate Member")

        upd_aadhaar = st.text_input(
            "Enter Aadhaar:",
            key="upd_aadhaar"
        )

        upd_passcode = st.text_input(
            "Enter Passcode:",
            type="password",
            key="upd_passcode"
        )

        if st.button("Validate"):

            #st.write("Entered Aadhaar:", repr(upd_aadhaar))
            #st.write("Entered Passcode:", repr(upd_passcode))

            #st.write(master_df[["AADHAAR_NUM", "PASSCODE", "MEMBER_NAME"]].head(64))
            
            member = master_df[
                (
                    master_df["AADHAAR_NUM"]
                    .astype(str)
                    .str.strip()
                    == str(upd_aadhaar).strip()
                )
                &
                (
                    master_df["PASSCODE"].astype(str).str.replace("'", "", regex=False)== str(upd_passcode).strip()
                )
            ]

            if member.empty:

                st.error(
                    "Invalid Aadhaar or Passcode"
                )

                st.session_state.update_verified = False

            else:

                row = member.iloc[0]
                st.session_state.update_verified = True

                st.session_state.update_name = row["MEMBER_NAME"]

                st.session_state.upd_ph_no = row.get("PH_NO","")
                st.session_state.upd_status = row.get("STATUS","Alive")
                st.session_state.upd_marital = row.get("MARITAL_STATUS","")
                st.session_state.upd_anniv = row.get("MRG_ANNIV_DATE","")
                st.session_state.upd_email = row.get("EMAIL_ID","")
                st.session_state.upd_gothram = row.get("GOTHRAM","")
                st.session_state.upd_occ = row.get("OCCUPATION","")
                st.session_state.upd_paddr = row.get("PRESENT_ADD","")
                st.session_state.upd_perm = row.get("PERMANENT_ADD","")
                st.session_state.upd_comments = row.get("COMMENTS","")

                st.success(
                    f"Good day! {row['MEMBER_NAME']}"
                )
    
        if st.session_state.get("update_verified", False):

            with st.form("update_member_form"):

                ph_no = st.text_input(
                    "Mobile:",
                    value=st.session_state.upd_ph_no
                )

                status = st.selectbox(
                    "Status:",
                    ["Alive","Expired"],
                    index=0 if st.session_state.upd_status=="Alive" else 1
                )
                marital_ui = st.selectbox(
                    "*Marital Status [M-Married/S-Single/D-Divorced]:",
                    ["","M","S","D"]
                )

                mrg_anniv_date = st.text_input(
                    "*Marriage Anniversary Date (DD-MON-YYYY):",
                    value=str(st.session_state.upd_anniv)
                )

                email_id = st.text_input(
                    "Email ID:",
                    value=str(st.session_state.upd_email)
                )

                gothram = st.text_input(
                    "Gothram:",
                    value=str(st.session_state.upd_gothram)
                )

                occupation = st.text_input(
                    "Occupation:",
                    value=str(st.session_state.upd_occ)
                )

                paddr = st.text_area(
                    "Present Address:",
                    value=str(st.session_state.upd_paddr)
                )

                perm_addr = st.text_area(
                    "Permanent Address:",
                    value=str(st.session_state.upd_perm)
                )

                comments = st.text_area(
                    "Comments:",
                    value=str(st.session_state.upd_comments)
                )

                c1,c2 = st.columns(2)

                update_btn = c1.form_submit_button(
                    "Update"
                )

                cancel_btn = c2.form_submit_button(
                    "Cancel"
                )
                if cancel_btn:
                    st.session_state.update_verified = False
                    st.rerun()
                    
                if st.session_state.save_msg:
                    st.success(st.session_state.save_msg)
                    st.session_state.save_msg=""
                    
                if update_btn:

                    master_sheet = connect(
                        "FAMILY_MEMBERS_MASTER"
                    )

                    records = master_sheet.get_all_records()

                    updated = False

                    marital_map={"M":"Married","S":"Single","D":"Divorced"}
                    for idx, row in enumerate(records, start=2):

                        if str(row["AADHAAR_NUM"]) == str(upd_aadhaar):

                            col_map = {

                                "PH_NO": ph_no,
                                "STATUS": status,
                                "MARITAL_STATUS": marital_map[marital_ui],
                                "MRG_ANNIV_DATE": mrg_anniv_date,
                                "EMAIL_ID": email_id,
                                "GOTHRAM": gothram,
                                "OCCUPATION": occupation,
                                "PRESENT_ADD": paddr,
                                "PERMANENT_ADD": perm_addr,
                                "COMMENTS": comments

                            }

                            headers = master_sheet.row_values(1)

                            for col_name, val in col_map.items():

                                col_num = headers.index(col_name) + 1

                                master_sheet.update_cell(
                                    idx,
                                    col_num,
                                    val
                                )

                            updated = True

                            break

                    if updated:

                        st.cache_data.clear()
                        st.session_state.save_msg="Member Details updated Successfully"
                        st.session_state.update_verified = False
                        reset_form()
                        #st.rerun()

                    else:

                        st.error(
                            "Member not found for update"
                        )
    # =====================================================
    # INVITE FAMILY MEMBERS
    # =====================================================

    with st.expander("📨 Want to invite family members to your family event?"):

        st.subheader("Step 1: Validate Organizer")

        org_aadhaar = st.text_input(
            "Enter Aadhaar:",
            key="org_aadhaar"
        )

        org_passcode = st.text_input(
            "Enter Passcode:",
            type="password",
            key="org_passcode"
        )

        if st.button(
            "Validate Organizer"
        ):

            member = master_df[
                (
                    master_df["AADHAAR_NUM"]
                    .astype(str)
                    .str.strip()
                    ==
                    str(org_aadhaar).strip()
                )
                &
                (
                    master_df["PASSCODE"]
                    .astype(str)
                    .str.replace(
                        "'",
                        "",
                        regex=False
                    )
                    .str.strip()
                    ==
                    str(org_passcode).strip()
                )
            ]

            if member.empty:

                st.error(
                    "Invalid Aadhaar or Passcode"
                )

                st.session_state.org_verified = False

            else:

                row = member.iloc[0]

                status = str(
                    row.get(
                        "STATUS",
                        ""
                    )
                ).strip().upper()
                
                st.session_state.org_name = row[
                    "MEMBER_NAME"
                ]
                

                if status != "ALIVE":

                    st.error(
                        "Organizer must be ALIVE."
                    )

                    st.session_state.org_verified = False

                    st.stop()

                st.session_state.org_verified = True

                st.session_state.organizer_mobile = str(
                    row.get(
                        "PH_NO",
                        ""
                    )
                )

                st.success(
                    f"Good day! {row['MEMBER_NAME']}"
                )

        # =================================================
        # EVENT DETAILS
        # =================================================

        if st.session_state.get(
            "org_verified",
            False
        ):

            #st.info(f"Organizer : "f"{st.session_state.org_name}")

            with st.form(
                "Invitation_form"
            ):

                event_name = st.text_input(
                    "Enter Event Name:"
                )

                event_desc = st.text_area(
                    "Enter Description of the Event:"
                )
                
                event_date = st.date_input(
                    "Event Date:"
                )
                
                #st.caption(f"Selected Event Date: {event_date.strftime('%d-%b-%Y')}")
                #st.text_input("Selected Event Date",value=event_date.strftime("%d-%b-%Y"),disabled=True)

                event_photo = st.file_uploader(
                    "Upload Photo / Invitation:",
                    type=[
                        "jpg",
                        "jpeg",
                        "png",
                        "pdf"
                    ]
                )

                recipient_option = st.radio(

                    "Invitation Type:",

                    [
                        "Send to all members registered in the system",

                        "Send to specific people"
                    ]
                )

                selected_members = pd.DataFrame()

                # =========================================
                # SPECIFIC PEOPLE GRID
                # =========================================

                if recipient_option == \
                    "Send to specific people":

                    display_df = master_df[
                        (
                            master_df["STATUS"]
                            .astype(str)
                            .str.upper()
                            == "ALIVE"
                        )
                        &
                        (
                            master_df["EMAIL_ID"]
                            .astype(str)
                            .str.strip()
                            != ""
                        )
                    ][
                        [
                            "MEMBER_NAME",
                            "GOTHRAM",
                            "PRESENT_ADD",
                            "PERMANENT_ADD",
                            "EMAIL_ID"
                        ]
                    ].copy()

                    display_df.insert(
                        0,
                        "Select",
                        False
                    )

                    edited_df = st.data_editor(
                        display_df,
                        hide_index=True,
                         width="stretch"
                    )

                    selected_members = edited_df[
                        edited_df["Select"]
                    ]

                c1, c2 = st.columns(2)

                send_invite = c1.form_submit_button(
                    "📨 Send Invitations"
                )

                cancel_invite = c2.form_submit_button(
                    "❌ Cancel"
                )

            # =============================================
            # CANCEL
            # =============================================

            if cancel_invite:

                st.session_state.org_verified = False

                st.rerun()

            # =============================================
            # SEND
            # =============================================

            if send_invite:

                validation_failed = False

                if not event_name.strip():

                    st.error(
                        "Event Name cannot be blank"
                    )

                    validation_failed = True

                if not event_desc.strip():

                    st.error(
                        "Event Description cannot be blank"
                    )

                    validation_failed = True
                
                if validation_failed:

                    st.stop()

                # =====================================
                # PREPARE ATTACHMENT
                # =====================================

                attachment_path = None

                # User uploaded invitation
                attachment_url = ""
                if event_photo:

                    attachment_path = event_photo.name

                    with open(
                        attachment_path,
                        "wb"
                    ) as f:

                        f.write(
                            event_photo.getbuffer()
                        )

                # No upload -> Use Google Drive image
                else:

                    file_id = "1kdXBAFI3MWTgVrJFVcUyZFa5VDHLgIv6"

                    download_url = (
                        f"https://drive.google.com/uc?export=download&id={file_id}"
                    )

                    r = requests.get(download_url)

                    if r.status_code != 200:

                        st.error(
                            "Unable to download invitation image from Google Drive"
                        )

                        st.stop()

                    attachment_path = "event_invitation.jpg"

                    with open(
                        attachment_path,
                        "wb"
                    ) as f:

                        f.write(r.content)

                event_sheet = connect(
                    "EVENT_DETAILS"
                )

                created_ts = datetime.now().strftime(
                    "%d-%b-%Y %H:%M:%S"
                )

                total_recipients = (
                    len(selected_members)
                    if recipient_option ==
                       "Send to specific people"
                    else
                    len(
                        master_df[
                            (master_df["STATUS"]
                             .astype(str)
                             .str.upper() == "ALIVE")
                            &
                            (master_df["EMAIL_ID"]
                             .astype(str)
                             .str.strip() != "")
                        ]
                    )
                )
                
                # =====================================
                # EMAIL SUBJECT
                # =====================================

                subject = event_name

                organizer_mobile = \
                    st.session_state.get(
                        "organizer_mobile",
                        ""
                    )

                html = f"""
                <html>

                <body style="
                    font-family:Arial;
                    text-align:left;
                    padding:20px;
                ">

                    <p style="
                        font-size:18px;
                        line-height:1.8;
                    ">

                        {event_desc}

                    </p>

                    <br>

                    <p>

                        Contact No:
                        {organizer_mobile}

                    </p>

                    <br>

                    <h3>

                        Best Regards,

                        <br>

                        Family Relationships System

                    </h3>

                </body>

                </html>
                """

                # =====================================
                # SEND TO ALL MEMBERS
                # =====================================

                if recipient_option == \
                    "Send to all members registered in the system":

                    count = send_invitation(
                        subject,
                        html,
                        attachment_path
                    )
                    if count>0:                     
                        attachment_url = (
                                upload_event_invitation_to_drive(
                                    event_photo,
                                    org_aadhaar,
                                    event_name,
                                    event_date
                                )
                            )
                        event_row = [

                            event_name,                                   # EVENT_NAME

                            event_desc,                                   # EVENT_DESCRIPTION

                            event_date.strftime("%d-%b-%Y"),              # EVENT_DATE

                            org_aadhaar,                                  # ORGANIZER_AADHAAR

                            st.session_state.org_name,                    # ORGANIZER_NAME

                            st.session_state.organizer_mobile,            # ORGANIZER_MOBILE

                            recipient_option,                             # INVITATION_TYPE

                            total_recipients,                             # TOTAL_RECIPIENTS

                            attachment_url,                               # ATTACHMENT_URL

                            created_ts                                    # CREATED_TS
                        ]                        
                        event_sheet.append_row(
                            event_row,
                            value_input_option="USER_ENTERED"
                        )
                    
                    if count>0:
                        st.success(
                            f"{count} invitation(s) sent successfully"
                        )

                # =====================================
                # SEND TO SPECIFIC MEMBERS
                # =====================================

                else:

                    sent_count = 0

                    for _, row in \
                        selected_members.iterrows():

                        email = str(
                            row["EMAIL_ID"]
                        ).strip()

                        if email:

                            try:

                                send_email(
                                    email,
                                    subject,
                                    html,
                                    attachment_path
                                )

                                sent_count += 1

                            except Exception as e:

                                st.error(
                                    f"Failed to send email to "
                                    f"{email}: {e}"
                                )

                    if sent_count>0:                     
                        attachment_url = (
                                upload_event_invitation_to_drive(
                                    event_photo,
                                    org_aadhaar,
                                    event_name,
                                    event_date
                                )
                            )
                        event_row = [

                            event_name,                                   # EVENT_NAME

                            event_desc,                                   # EVENT_DESCRIPTION

                            event_date.strftime("%d-%b-%Y"),              # EVENT_DATE

                            org_aadhaar,                                  # ORGANIZER_AADHAAR

                            st.session_state.org_name,                    # ORGANIZER_NAME

                            st.session_state.organizer_mobile,            # ORGANIZER_MOBILE

                            recipient_option,                             # INVITATION_TYPE

                            total_recipients,                             # TOTAL_RECIPIENTS

                            attachment_url,                               # ATTACHMENT_URL

                            created_ts                                    # CREATED_TS
                        ]                        
                        event_sheet.append_row(
                            event_row,
                            value_input_option="USER_ENTERED"
                        )
                    
                    if sent_count>0:
                        st.success(
                            f"{sent_count} invitation(s) sent successfully"
                        )                    
if gs_patterns:
    # ---------- LOAD ----------
    @st.cache_data
    def load_data():
        m = connect("FAMILY_MEMBERS_MASTER")
        r = connect("FAMILY_MEMBERS_RSHIPS")
        f = connect("Get_Final_Relationship")
        
        mdf = pd.DataFrame(m.get_all_records())
        rdf = pd.DataFrame(r.get_all_records())
        fdf = pd.DataFrame(f.get_all_records())
        
        mdf.columns = [c.upper() for c in mdf.columns]
        rdf.columns = [c.upper() for c in rdf.columns]
        fdf.columns = [c.upper() for c in fdf.columns]    

        mdf["AADHAAR_NUM"] = mdf["AADHAAR_NUM"].astype(str)
        rdf["AADHAAR_NUM"] = rdf["AADHAAR_NUM"].astype(str)
        rdf["RELATIVE_AADHAAR"] = rdf["RELATIVE_AADHAAR"].astype(str)

        return mdf, rdf, fdf

    master_df, rship_df, final_rel_df = load_data()
    b1, b2, b3, b4 = st.columns(4)

    with b1:
        refresh_clicked = st.button(
            "🔄 Refresh Data(gs)",
             width="stretch"
        )

    with b2:

        show_birthdays = st.button(
            "🎂 Today's Birthdays",
             width="stretch"
        )

    with b3:

        show_anniv = st.button(
            "💍 Today's Marriage Anniversaries",
             width="stretch"
        )
    # ---------- REFRESH ----------
    if refresh_clicked:

        st.cache_data.clear()

        st.success(
            "Data refreshed successfully"
        )

        st.rerun()

    # ---------- SESSION ----------
    for k in ["verified","save_msg","reset_flag"]:
        if k not in st.session_state:
            st.session_state[k] = False if k!="save_msg" else ""

    # ---------- MATCH ----------
    def match_relationship(chain, source, target):

        src_row = get_row(source)
        tgt_row = get_row(target)

        src_parent = str(src_row.get("RELATIVE_AADHAAR","")) if src_row is not None else ""
        tgt_parent = str(tgt_row.get("RELATIVE_AADHAAR","")) if tgt_row is not None else ""

        age_gap = get_age_difference(source, target)
        
        # SON CASE
        if chain == "S(M).S(M)":
            return "Father" if is_source_younger(source, target) else "Son"
            
            # ---------- S(M).S(M).S(M) ----------
        if chain == "S(M).S(M).S(M)":

            # Same parent + close age → Brother
            if src_parent and src_parent == tgt_parent and age_gap <= 35:
                return "Brother"

            # Large age gap → Grand Son / Grand Father
            return "Grand Father" if is_source_younger(source, target) else "Grand Son"
            
                # ---------- S(M).S(M).S(M) ----------
        if chain == "S(M).S(M).D(F)":

            # Same parent + close age → Brother
            if src_parent and src_parent == tgt_parent and age_gap <= 35:
                return "Brother"

            # Large age gap → Grand Daughter / Grand Father
            return "Grand Father" if is_source_younger(source, target) else "Grand Daughter"

        # DAUGHTER CASE
        if chain in ["D(F).D(F)", "D(F).W(F)", "D(F).R(F)"]:
            return "Mother" if is_source_younger(source, target) else "Daughter"


        # =====================================================
        # DYNAMIC LOOKUP FROM SHEET
        # =====================================================

        rel_row = final_rel_df[
            final_rel_df["RSHIP_CHAIN"] == chain
        ]

        if not rel_row.empty:
            return rel_row.iloc[0]["RELATIONSHIP"]

        return "Unknown"

    # ---------- MAIN ----------
    # ---------- FULL TEST ----------
    TEST_PIN = "417655"   # Change this PIN

    with b4:
        if st.button("🧪 Run Full Relationship Test"):
            st.session_state.show_test_pin = True

    # =====================================================
    # SHOW PIN SECTION
    # =====================================================

    if st.session_state.get("show_test_pin", False):

        entered_pin = st.text_input(
            "Enter Test Execution PIN",
            type="password",
            key="test_pin"
        )

        c1, c2 = st.columns(2)

        # ---------- VERIFY ----------

        with c1:

            if st.button("✅ Verify & Run Test"):

                if entered_pin == TEST_PIN:

                    st.success("PIN verified successfully")

                    run_relationship_test()

                    st.session_state.show_test_pin = False

                else:

                    st.error("Invalid PIN")


        with c2:

            if st.button("❌ Cancel Test"):

                st.session_state.show_test_pin = False

                st.rerun()
    debug_mode = st.checkbox("Enable Debug Logs", value=False)
    st.session_state.debug = debug_mode
    if show_greetings_flag:
        # =====================================================
        # SHOW GREETINGS
        # =====================================================
        # ---------- BIRTHDAYS ----------
        if show_birthdays:
            birthdays, anniversaries = send_greetings()

            st.markdown(
                "## 🎂 Today's Birthdays"
            )
            if birthdays:

                for name, email, photo in birthdays:

                    st.success(
                        f"🎉 Happy Birthday {name}"
                    )

                    if send_email_flag:
                        if email:

                            subject = \
                                f"Happy Birthday {name} 🎂"

                            html = f"""
                            <html>

                            <body style="
                                font-family: Arial;
                                text-align: left;
                                padding: 20px;
                            ">

                                <h2>
                                    Dear {name},
                                </h2>

                                <p style="
                                    font-size:18px;
                                    line-height:1.8;
                                ">

                                    Wishing you a very Happy Birthday 🎉🎂

                                    <br><br>

                                    May your day be filled with joy,
                                    health and happiness.

                                </p>

                                <br>

                                {
                                    '<img src="cid:member_photo" '
                                    'width="300" '
                                    'style="border-radius:15px;'
                                    'border:3px solid #0059b3;">'
                                    if photo else ''
                                }

                                <br><br>

                                <h3 style="
                                    color:#0059b3;
                                ">

                                    Best Wishes,
                                    <br>

                                    Family Relationship System

                                </h3>

                            </body>

                            </html>
                            """

                            sent = send_email(
                                email,
                                subject,
                                html,
                                photo
                            )

                            if sent:

                                st.info(
                                    f"Birthday email sent to {name}"
                                )
            else:
                st.info(
                    "No birthdays today"
                )

        # ---------- ANNIVERSARIES ----------
        if show_anniv:
            birthdays, anniversaries = send_greetings()

            st.markdown(
                "## 💍 Today's Marriage Anniversaries"
            )
            if anniversaries:
                for name, email, photo in anniversaries:

                    st.success(
                        f"💐 Happy Marriage Anniversary {name}"
                    )

                    if send_email_flag:
                        if email:

                            subject = \
                                f"Happy Marriage Anniversary {name} 💍"

                            html = f"""
                            <html>

                            <body style="
                                font-family: Arial;
                                text-align: left;
                                padding: 20px;
                            ">

                                <h2>
                                    Dear {name},
                                </h2>

                                <p style="
                                    font-size:18px;
                                    line-height:1.8;
                                ">

                                    Wishing you a very Happy Marriage Anniversary 💐

                                    <br><br>

                                    May your life continue to be filled with love and happiness.

                                </p>

                                <br>

                                {
                                    '<img src="cid:member_photo" '
                                    'width="300" '
                                    'style="border-radius:15px;'
                                    'border:3px solid #0059b3;">'
                                    if photo else ''
                                }

                                <br><br>

                                <h3 style="
                                    color:#0059b3;
                                ">

                                    Best Wishes,
                                    <br>

                                    Family Relationship System

                                </h3>

                            </body>

                            </html>
                            """

                            sent = send_email(
                                email,
                                subject,
                                html,
                                photo
                            )

                            if sent:

                                st.info(
                                    f"Anniversary email sent to {name}"
                                )
            else:
                st.info(
                    "No marriage anniversaries today"
                )
    if perfomance_needed:
        with st.form("relationship_form"):

            c1, c2 = st.columns(2)

            source = c1.text_input(
                "Source Aadhaar"
            )

            target = c2.text_input(
                "Target Aadhaar"
            )

            b1, b2 = st.columns(2)

            with b1:

                find_relationship = st.form_submit_button(
                    "Find Relationship"
                )

            with b2:

                show_tree = st.form_submit_button(
                    "🌳 Show Entire Family Tree"
                )
    else:
        message_placeholder = st.empty()
        c1,c2 = st.columns(2)
        source = c1.text_input("*Source Aadhaar")
        target = c2.text_input("*Target Aadhaar")

        b1, b2 = st.columns(2)

        with b1:
            find_relationship = st.button("Find Relationship")

        with b2:
            show_tree = st.button("🌳 Show Entire Family Tree")
        
    if find_relationship:
        if st.session_state.get("debug", False):
            st.session_state.logs = []
        
        if not source.strip() or not target.strip():

            st.error(
                    f"Please enter both Source and Target Aadhaar numbers"
                )
            st.stop()
            
        path = build_path(source,target)

        if not path:

            valid, missing_side = validate_member_exists(
                source,
                target
            )

            if not valid:

                st.error(
                    f"No relationship found because "
                    f"{missing_side} member details do not exist"
                )

            else:

                st.error("No relationship path found")
        else:
            names=[get_name(p) for p in path]
            chain=build_chain(path)
            rel=match_relationship(chain,source,target)
            
            st.success(f"{source}({get_name(source)}) is {rel} of {target}({get_name(target)})")
            #st.success(f"{source}({get_name(source)}) {target}({get_name(target)})")
            path_forward = path[::1]
            st.write("Path:", format_path_with_relationship(path_forward))
            chain_forward = ".".join(chain.split(".")[::1])
            st.write("Chain:", chain_forward)
            # Relationship Level
            st.write(f"Relationship Level: {len(path)}")

            if rel != "Unknown":    #Show Source and Target details only if the relationship found
                st.markdown("### Source and Target Details")

                show_details_grid(source, target)

            # ✅ UNKNOWN RELATIONSHIP
            else:
               log_unknown(source,target,names,chain)
           
            if st.session_state.get("debug", False):
                    st.markdown("---")
                    with st.expander("🔍 Debug Logs"):
                        if st.session_state.get("debug", False):
                            st.markdown("---")
                            with st.expander("🔍 Debug Logs"):

                                logs = st.session_state.get("logs", [])

                                if logs:
                                    df_logs = pd.DataFrame(logs)

                                    def highlight(row):
                                        if row["Level"] == "ERROR":
                                            return ['background-color: #ffcccc'] * len(row)
                                        elif row["Level"] == "WARN":
                                            return ['background-color: #fff3cd'] * len(row)
                                        else:
                                            return [''] * len(row)

                                    st.dataframe(df_logs.style.apply(highlight, axis=1),  width="stretch")
                                else:
                                    st.info("No logs available")
    
    if show_tree:
        show_family_tree()
        
    # ---------- ADD MEMBER ----------
    with st.sidebar:

        st.header("Add Family Member")

        st.subheader("* Indicates required fields")
        st.subheader("Step 1: Before adding member, first Verify your relative Aadhaar existence")
        verify_input = st.text_input("*Enter your own Parent/Brother/sister/spouse Aadhaar")

        if st.button("Verify"):
            if verify_input in master_df["AADHAAR_NUM"].values:
                st.success(f"Verified: {get_name(verify_input)}")
                st.session_state.verified=True
            else:
                st.error("Not found")
                st.session_state.verified=False

        st.subheader("Step 2: Enter your details correctly")

        aadhaar = st.text_input("*AADHAAR", disabled=not st.session_state.verified)
        name = st.text_input("*Name", disabled=not st.session_state.verified)
        gender = st.selectbox("*Gender",["","M","F"], disabled=not st.session_state.verified)

        dob = st.text_input("*DOB (DD-MON-YYYY)", disabled=not st.session_state.verified).upper()
        mobile = st.text_input("Mobile", disabled=not st.session_state.verified)

        parent = st.text_input("Relative Aadhaar", disabled=not st.session_state.verified)

        relation = st.selectbox(
            "Relationship to Relative[S-SON/D-DAUGHTER/F-FATHER/M-MOTHER/H-HUSBAND/W-WIFE]",
            ["","S","D","F","M","H","W"],
            disabled=not st.session_state.verified
        )

        couple_input = ""
        if relation in ["H","W"]:
            couple_input = st.text_input("*Enter your Couple Identification Num(HusbandAadhaar(12 digits)WifeAadhaar(12 digits) Ex:100000000056100000000058",disabled=not st.session_state.verified)

        marital_ui = st.selectbox(
            "*Marital Status [M-Married/S-Single/D-Divorced]",
            ["","M","S","D"],
            disabled=not st.session_state.verified
        )

        mrg_anniv_date = ""

        if marital_ui == "M":

            mrg_anniv_date = st.text_input("Enter Marriage Anniversary Date (DD-MON-YYYY)").upper()
    
        email_id = st.text_input("Email ID", disabled=not st.session_state.verified)
        got_hram = st.text_input("Gothram", disabled=not st.session_state.verified)
        occupation = st.text_input("Occupation", disabled=not st.session_state.verified)
        paddr = st.text_area("Present Address", disabled=not st.session_state.verified)
        perm = st.text_area("Permanent Address", disabled=not st.session_state.verified)
        comments = st.text_area("Enter Comments, If any", disabled=not st.session_state.verified)

        col1,col2=st.columns(2)

        if col1.button("Save Member", disabled=not st.session_state.verified):

            # ---------- AADHAAR_NUM VALIDATION ----------
            if not aadhaar.strip():

                st.error("AADHAAR_NUM cannot be blank")
                st.stop()
            if aadhaar in master_df["AADHAAR_NUM"].values:
                st.error("Entered Aadhaar is already exists")
                st.stop()
            # ---------- NAME VALIDATION ----------
            if not name.strip():

                st.error("NAME cannot be blank")
                st.stop()
            # ---------- GENDER VALIDATION ----------
            if not gender.strip():

                st.error("GENDER cannot be blank")
                st.stop()
            # ---------- MOBILE VALIDATION ----------
            mobile = str(mobile).strip()

            # Validate ONLY if user entered value
            if mobile != "":

                if not mobile.isdigit():

                    st.error(
                        "Mobile number must contain only digits"
                    )

                    st.stop()

                elif len(mobile) != 10:

                    st.error(
                        "Mobile number must be exactly 10 digits"
                    )

                    st.stop()

            marital_map={"M":"Married","S":"Single","D":"Divorced"}

            #parent = st.text_input("*Relative Aadhaar",value=verify_input,disabled=not st.session_state.verified)
            
                # ---------- VALIDATE RELATIVE AADHAAR ----------
            relative_exists = not master_df[
                master_df["AADHAAR_NUM"] == str(parent)
            ].empty

            if not relative_exists:

                st.error(
                    "Entered Relative Aadhaar does not exist"
                )

                st.stop()
            # ---------- VERIFY STEP1 vs STEP2 ----------
            if str(parent).strip() != str(verify_input).strip():

                st.error(
                    "Relative Aadhaar must match "
                    "the Aadhaar verified in Step 1"
                )

                st.stop()
                
            # ---------- Relationship to Relative VALIDATION ----------
            if not relation.strip():

                st.error("Relationship to Relative cannot be blank")
                st.stop()
            # ---------- Marital Status VALIDATION ----------
            if not marital_ui.strip():

                st.error("Marital Status cannot be blank")
                st.stop()
                
            # SON/DAUGHTER VALIDATION (REGEX LOGIC)
            if relation in ["S","D"]:
                # ---------- CHECK COUPLE ID ----------
                parent_row = get_master(parent)

                existing_couple_id = ""

                if parent_row is not None:
                    existing_couple_id = str(
                        parent_row.get(
                            "COUPLE_IDENTIFICATION_NUM",
                            ""
                        )
                    ).strip()

                if not existing_couple_id:

                    st.warning(
                    "Your parents not registered as couple, for that you have to update their COUPLE_IDENTIFICATION_NUM ")
                    update_choice = st.radio(
                        "Do you want to update "
                        "COUPLE_IDENTIFICATION_NUM?",
                        ["No","Yes"],
                        horizontal=True
                    )

                    if update_choice == "Yes":

                        st.info(
                            "Goto Step3 and Enter your "
                            "Father and Mother Aadhaar Numbers"
                        )
                    # ❌ STOP SAVE PROCESS
                    st.stop()                        
            # HUSBAND/WIFE VALIDATION
            if relation in ["H","W"]:
                if not (len(couple_input)==24 and couple_input.isdigit()):
                    st.error("Invalid Couple Identification Number")
                    st.stop()

            # ---------- DOB VALIDATION ----------
            if not dob.strip():

                st.error("DOB cannot be blank")
                st.stop()

            try:

                dob_dt = datetime.strptime(
                    dob,
                    "%d-%b-%Y"
                )

                dob = dob_dt.strftime("%d-%b-%Y").upper()

            except:

                st.error(
                    "DOB format must be DD-MON-YYYY"
                )

                st.stop()

            # ---------- ANNIVERSARY DATE VALIDATION ----------
            if marital_ui == "M":

                if not mrg_anniv_date.strip():

                    st.error(
                        "Marriage Anniversary Date "
                        "cannot be blank for Married"
                    )

                    st.stop()

                try:

                    anniv_dt = datetime.strptime(
                        mrg_anniv_date,
                        "%d-%b-%Y"
                    )

                    mrg_anniv_date = anniv_dt.strftime(
                        "%d-%b-%Y"
                    ).upper()

                except:

                    st.error(
                        "Marriage Anniversary Date format "
                        "must be DD-MON-YYYY"
                    )

                    st.stop()
                    
            # MASTER WRITE
            m_sheet = connect("FAMILY_MEMBERS_MASTER")
            headers = [h.upper() for h in m_sheet.row_values(1)]

            m_dict={
                "AADHAAR_NUM":aadhaar,
                "MEMBER_NAME":name,
                "GENDER":gender,
                "PH_NO":mobile,
                "DOB":dob,
                "MARITAL_STATUS":marital_map[marital_ui],
                "MRG_ANNIV_DATE": mrg_anniv_date,
                "EMAIL_ID": email_id,
                "GOTHRAM":got_hram,
                "OCCUPATION":occupation,
                "STATUS":"Alive",
                "COUPLE_IDENTIFICATION_NUM": couple_input if relation in ["H","W"] else "",
                "PRESENT_ADD":paddr,
                "PERMANENT_ADD":perm,
                "COMMENTS":comments
            }

            m_row=[m_dict.get(h,"") for h in headers]
            m_sheet.append_row(m_row)

            # RSHIPS WRITE
            r_sheet = connect("FAMILY_MEMBERS_RSHIPS")
            r_headers = [h.upper() for h in r_sheet.row_values(1)]

            r_dict={
                "AADHAAR_NUM":aadhaar,
                "MEMBER_NAME":name,
                "RELATIVE_AADHAAR":parent,
                "RSHIP_TO_AADHAAR_NUM":relation,
                "GENDER":gender,
                "DOB":dob
            }

            r_row=[r_dict.get(h,"") for h in r_headers]
            r_sheet.append_row(r_row)

            st.cache_data.clear()
            st.session_state.save_msg="Member Details saved Successfully"
            reset_form()
            st.rerun()

        if col2.button("Cancel"):
            reset_form()
            st.rerun()
        if st.session_state.save_msg:
            st.success(st.session_state.save_msg)
            st.session_state.save_msg=""            
        # =====================================================
        # STEP 3 - UPDATE COUPLE IDENTIFICATION NUM
        # =====================================================

        st.markdown("---")
        st.markdown("## Update Couple Identification Number")

        f1, f2 = st.columns(2)

        father_aadhaar = f1.text_input(
            "Father Aadhaar"
        )

        mother_aadhaar = f2.text_input(
            "Mother Aadhaar"
        )

        if st.button("Update Couple Identification Number"):

            # ---------- VALIDATE FATHER ----------
            father_exists = not master_df[
                master_df["AADHAAR_NUM"]
                == str(father_aadhaar)
            ].empty

            if not father_exists:

                st.error(
                    "Father Aadhaar details "
                    "not present, please add "
                    "that member first"
                )

                st.stop()

            # ---------- VALIDATE MOTHER ----------
            mother_exists = not master_df[
                master_df["AADHAAR_NUM"]
                == str(mother_aadhaar)
            ].empty

            if not mother_exists:

                st.error(
                    "Mother Aadhaar details "
                    "not present, please add "
                    "that member first"
                )

                st.stop()

            # ---------- GENERATE COUPLE ID ----------
            couple_id = (
                str(father_aadhaar)
                + str(mother_aadhaar)
            )

            # ---------- UPDATE BOTH MEMBERS ----------
            master_sheet = connect(
                "FAMILY_MEMBERS_MASTER"
            )

            records = master_sheet.get_all_records()

            for idx, row in enumerate(records, start=2):

                aadhaar = str(
                    row.get("AADHAAR_NUM","")
                )

                if aadhaar in [
                    str(father_aadhaar),
                    str(mother_aadhaar)
                ]:

                    col_index = (
                        master_df.columns
                        .get_loc(
                            "COUPLE_IDENTIFICATION_NUM"
                        ) + 1
                    )

                    master_sheet.update_cell(
                        idx,
                        col_index,
                        couple_id
                    )

            st.success(
                "COUPLE_IDENTIFICATION_NUM "
                "updated successfully, now you can add your details"
            )
            st.cache_data.clear()
            st.session_state.save_msg="COUPLE_IDENTIFICATION_NUM updated successfully, now you can add your details"
            st.rerun()