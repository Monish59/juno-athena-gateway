# JUNO-Athena Research Gateway main app
import streamlit as st
from utils import abilities, audit, db, groups, collab, library_api, lit_api, support, onboarding
import datetime

USE_RT = False  # flip to True when Supabase ready

st.set_page_config(page_title="JUNO-Athena Research Gateway", layout="wide")

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "user_email" not in st.session_state:
    st.session_state["user_email"] = ""
if "full_name" not in st.session_state:
    st.session_state["full_name"] = ""
if "consent" not in st.session_state:
    st.session_state["consent"] = False
if "active_group" not in st.session_state:
    st.session_state["active_group"] = None
if "project_id" not in st.session_state:
    st.session_state["project_id"] = None

def login_flow():
    st.title("Login — JUNO-Athena Research Gateway")
    with st.form(key="login_form"):
        full_name = st.text_input("Full Name", value=st.session_state.get("full_name", ""))
        email = st.text_input("Email (institutional)", value=st.session_state.get("user_email", ""))
        passkey = st.text_input("Passkey (from Athena)", type="password")
        labcode = st.text_input("Lab Access Code (optional)")
        with open("COPY_PRIVACY.md") as f:
            st.markdown(f.read())
        consent = st.checkbox("I consent to research logging for reproducibility (ARGOS audit).")
        submit = st.form_submit_button("Login")
    if submit:
        if not (full_name and email and passkey and consent):
            st.error("All fields and consent are required.")
            return
        if not library_api.is_passkey_valid(email, passkey):
            st.error("Invalid credentials or passkey.")
            audit.log_event("login_failed", {"email":email})
            return
        st.session_state["logged_in"] = True
        st.session_state["user_email"] = email
        st.session_state["full_name"] = full_name
        st.session_state["consent"] = consent
        audit.log_event("login", {"email":email, "name":full_name, "consent":consent})
        st.success(f"Welcome, {support.respectful_name(full_name)}. Logging you in...")
        st.experimental_rerun()

def license_check(email):
    valid, msg = lit_api.validate_license_for_user(email)
    return valid, msg

def show_onboarding():
    st.title(onboarding.INTRO_TITLE)
    for pt in onboarding.INTRO_POINTS:
        st.markdown(f"- {pt}")
    st.info("You may close this window to continue.")

def show_daily_brief(email):
    st.sidebar.title(onboarding.DAILY_BRIEF_TITLE)
    lic_ok, lic_msg = lit_api.validate_license_for_user(email)
    if lic_ok:
        st.sidebar.success("License: Active")
    else:
        st.sidebar.warning(f"License: {lic_msg}")
    st.sidebar.info("Check for new supervisor comments and group updates.")

def sidebar_nav():
    from utils.support import respectful_name, part_of_day
    hello = respectful_name(st.session_state.get("full_name","Researcher"))
    st.sidebar.success(f"Good {part_of_day()}, {hello}. Athena is online. ARGOS systems nominal.")
    nav = st.sidebar.radio("Navigate", [
        "Search", "Review Builder", "Manuscript Writer", "Library", "Groups", "Results", "Mentor"
    ], key="nav_tabs")
    return nav

def gated_section(ability, label="Advanced feature"):
    email = st.session_state["user_email"]
    if not abilities.has_ability(email, ability):
        st.warning(f"🔒 {label} (Request Access)")
        if st.button(f"Request {label} Access"):
            audit.notify_mentor({"type":"ability_request","ability":ability,"email":email,"name":st.session_state.get("full_name","")})
            st.info("Request sent to mentor.")
        return False
    return True

@st.cache_data(show_spinner=False)
def cached_full_search(q, y1, y2, primary):
    return lit_api.full_search_details(q, y1, y2, primary)

def tab_search():
    st.header("🔍 Literature Search")
    q = st.text_input("Query")
    y1, y2 = st.slider("Year Range", 2018, datetime.date.today().year, (2019, datetime.date.today().year))
    excl_reviews = st.checkbox("Exclude reviews (primary only)")
    if st.button("Search"):
        audit.log_event("search", {"q":q,"years":[y1,y2],"primary":excl_reviews})
        st.info(lit_api.quick_search_headline(q, y1, y2, excl_reviews))
        res = cached_full_search(q, y1, y2, excl_reviews)
        for r in res["records"]:
            st.markdown(f"- **{r['year']}** {r['title']} *(type: {r['type']})*")
        st.caption(res["explanation"])

def tab_review_builder():
    st.header("📝 Review Builder")
    email = st.session_state["user_email"]
    user = st.session_state["full_name"]
    all_groups = groups.list_groups(email)
    group_names = {g["id"]: g["name"] for g in all_groups}
    group_id = st.selectbox("Group", options=list(group_names.keys()), format_func=lambda k: group_names[k])
    st.session_state["active_group"] = group_id
    projects = collab.list_projects(group_id)
    proj_names = {p["id"]: p["title"] for p in projects}
    sel = st.selectbox("Project", options=list(proj_names.keys())+["NEW"], format_func=lambda k: proj_names.get(k,"<Create new>"))
    if sel == "NEW":
        new_title = st.text_input("New Project Title")
        if st.button("Create Project"):
            pr = collab.create_project(group_id, new_title, email)
            st.session_state["project_id"] = pr["id"]
            st.experimental_rerun()
    else:
        st.session_state["project_id"] = sel
    if st.session_state["project_id"]:
        st.subheader("Add Finding")
        text = st.text_area("Finding")
        quality = st.selectbox("Quality", ["Preliminary", "Validated", "Gold"])
        msg_for_sup = st.checkbox("Message for Supervisor")
        if st.button("Add Finding"):
            collab.add_finding(st.session_state["project_id"], email, text, quality)
            audit.log_event("add_finding", {"project_id":st.session_state["project_id"],"quality":quality})
            if msg_for_sup:
                audit.notify_mentor({"type":"student_note","text":text,"user":email,"name":user})
            st.success("Finding added.")
        findings = collab.list_findings(st.session_state["project_id"])
        st.table(findings)

def tab_manuscript_writer():
    st.header("✍️ Manuscript Writer")
    typ = st.selectbox("Manuscript Type", ["Research Article", "Review", "Letter"])
    sections = st.multiselect("Sections", ["Intro", "Methods", "Results", "Discussion", "References"])
    style = st.selectbox("Style", ["APA-7", "Vancouver", "Custom"])
    draft = st.text_area("Draft", height=320)
    if st.button("Download Draft"):
        st.download_button("Download .txt", draft.encode(), file_name="draft.txt")

def tab_library():
    st.header("📚 Lab Library (Read-Only)")
    q = st.text_input("Search Library")
    year = st.number_input("Year (≤)", min_value=2018, max_value=datetime.date.today().year, value=datetime.date.today().year)
    col = st.selectbox("Collection", library_api.get_collections())
    if st.button("Search Library"):
        df = library_api.search_library(q, year, col)
        st.dataframe(df)
        doc_id = st.selectbox("Open Document", options=[""]+df["id"].tolist())
        if doc_id:
            doc = library_api.get_document(doc_id)
            if doc:
                st.write(doc)
                if "pdf_bytes" in doc:
                    st.download_button("Download PDF", doc["pdf_bytes"], file_name=f"{doc_id}.pdf")

def tab_groups():
    st.header("👥 Groups & Collaboration")
    email = st.session_state["user_email"]
    with st.expander("Create New Group"):
        gname = st.text_input("Group Name")
        if st.button("Create Group"):
            g = groups.create_group(gname, email)
            st.success(f"Group {gname} created.")
    all_groups = groups.list_groups(email)
    group_names = {g["id"]: g["name"] for g in all_groups}
    group_id = st.selectbox("Group", options=list(group_names.keys()))
    inv_email = st.text_input("Invite Member Email")
    role = st.selectbox("Role", ["editor", "viewer"])
    if st.button("Invite"):
        groups.invite_member(group_id, inv_email, role)
        st.info(f"Invited {inv_email} as {role}.")
    st.write("Members:")
    st.table(groups.list_members(group_id))

def tab_results():
    st.header("📈 Results (Placeholder)")
    st.info("Your completed runs will appear here. (CSV/PDF download coming soon)")

def tab_mentor():
    st.header("🧑‍🏫 Mentor / Supervisor Channel")
    st.info("Use this space to message your mentor, see supervisor comments, or request project guidance.")

def tab_collab_chat():
    st.header("💬 Collaboration Chat")
    pid = st.session_state.get("project_id")
    if not pid:
        st.info("Select a project in Review Builder first.")
        return
    name = support.respectful_name(st.session_state["full_name"])
    chat_input = st.text_area("Chat or /command", height=140, key="chat_input")
    if st.button("Send", key="send_chat"):
        from utils.command_parser import parse_command
        kind = "command" if chat_input.strip().startswith("/") else "message"
        collab.post_chat(pid, st.session_state["user_email"], name, chat_input, kind)
        audit.log_chat("user", chat_input)
        st.session_state["chat_input"] = ""
        st.experimental_rerun()
    poll_interval = st.sidebar.slider("Polling interval (seconds)", 2, 15, 5)
    feed = collab.list_chat(pid)[-200:]
    if st.button("Load older"):
        # load more history (implement as needed)
        pass
    for c in feed:
        badge = "CMD" if c["kind"]=="command" else "MSG"
        st.markdown(f"[{badge}] **{c['user_name']}**: {c['message']}")
    left, right = st.columns(2)
    with left:
        st.subheader("Athena Chat")
        ath_input = st.text_area("Ask Athena", height=140, key="athena_input")
        if st.button("Send to Athena"):
            collab.add_athena_chat(pid, name, "user", ath_input)
            audit.log_chat("athena_user", ath_input)
            reply = f"Athena: (placeholder reply to '{ath_input}')"
            collab.add_athena_chat(pid, "Athena", "assistant", reply)
            audit.log_chat("athena_assistant", reply)
            st.session_state["athena_input"] = ""
            st.experimental_rerun()
        ath_feed = collab.list_athena_chat(pid)[-50:]
        for c in ath_feed:
            st.markdown(f"**{c['role']}**: {c['text']}")
    with right:
        st.subheader("Supervisor Comments")
        sup_feed = collab.list_supervisor_comments(pid)
        for c in sup_feed:
            st.markdown(f"- {c['text']}")
            with st.expander("What this means (Athena)"):
                st.markdown(c.get("explained_text","No explanation."))

def heartbeat():
    audit.push_status({"user":st.session_state.get("user_email"),"page":st.session_state.get("nav_tabs")})

if not st.session_state["logged_in"]:
    login_flow()
    st.stop()
else:
    heartbeat()
    first_login = st.session_state.get("first_login", True)
    if first_login:
        show_onboarding()
        st.session_state["first_login"] = False
        st.stop()
    show_daily_brief(st.session_state["user_email"])
    valid, lic_msg = license_check(st.session_state["user_email"])
    if not valid:
        st.error(f"License Issue: {lic_msg}")
        if st.button("Request Renewal"):
            audit.notify_mentor({"type":"renewal_request","user":st.session_state["user_email"],"reason":"Continue projects"})
            st.info("Renewal request sent to mentor.")
        st.warning("Read-only mode: You can still access your groups and data.")
    nav = sidebar_nav()
    if nav == "Search":
        tab_search()
    elif nav == "Review Builder":
        tab_review_builder()
        tab_collab_chat()
    elif nav == "Manuscript Writer":
        tab_manuscript_writer()
    elif nav == "Library":
        tab_library()
    elif nav == "Groups":
        tab_groups()
    elif nav == "Results":
        tab_results()
    elif nav == "Mentor":
        tab_mentor()