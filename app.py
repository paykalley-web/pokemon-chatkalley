import streamlit as st
import sqlite3
import pandas as pd
import os

# Configure page style
st.set_page_config(
    page_title="Enterprise Analyst Dashboard",
    page_icon="☑",
    layout="wide"
)

# =========================================================
# 0. DYNAMIC SELF-CONTAINED DATABASE SEEDING ON STARTUP
# =========================================================
def init_and_seed_db():
    os.makedirs("policies", exist_ok=True)
    policies = {
        "policies/it_helpdesk_sop.md": """# IT Helpdesk Standard Operating Procedures
- **Password & Lockouts:** Never ask for passwords in chat. Direct locked users (`LOCKED` status) to `https://company.com`.
- **Escalation Rule:** Attempt up to 3 troubleshooting steps. If unresolved, create a ticket in `support_tickets`.
- **Database Security:** Agents cannot alter `employees` or root tables.
""",
        "policies/pokemon_league_rules.md": """# Pokedex & Battle Guidelines
- **Data Integrity:** All base stats must match the official `pokemon_master` registry.
- **Type Matchups:** Fire beats Steel; Fighting is weak to Flying; Electric is immune to nothing.
- **Restrictions:** Custom or fan-made Pokemon stats cannot be added to the master registry.
"""
    }
    for filepath, content in policies.items():
        if not os.path.exists(filepath):
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content.strip() + "\n")

    # Initialize enterprise database
    conn = sqlite3.connect("enterprise.db")
    cursor = conn.cursor()
    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS pokemon_master (
        id INTEGER PRIMARY KEY,
        name TEXT UNIQUE NOT NULL,
        type1 TEXT NOT NULL,
        type2 TEXT,
        hp INTEGER,
        attack INTEGER
    );
    CREATE TABLE IF NOT EXISTS employees (
        emp_id TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        department TEXT,
        account_status TEXT
    );
    CREATE TABLE IF NOT EXISTS support_tickets (
        ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
        emp_email TEXT NOT NULL,
        issue_summary TEXT NOT NULL,
        status TEXT DEFAULT 'OPEN',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS pokemon_items (
        item_id INTEGER PRIMARY KEY,
        item_name TEXT UNIQUE NOT NULL,
        boost_type TEXT NOT NULL,
        effect TEXT
    );
    """)

    # Check and seed pokemon_master
    count = cursor.execute("SELECT COUNT(*) FROM pokemon_master;").fetchone()[0]
    if count == 0:
        GEN1_POKEMON = [
            (1, 'Bulbasaur', 'Grass', 'Poison', 45, 49),
            (6, 'Charizard', 'Fire', 'Flying', 78, 84),
            (9, 'Blastoise', 'Water', None, 79, 83)
        ]
        cursor.executemany(
            "INSERT OR IGNORE INTO pokemon_master (id, name, type1, type2, hp, attack) VALUES (?, ?, ?, ?, ?, ?);",
            GEN1_POKEMON
        )

    # Check and seed employees
    count_emp = cursor.execute("SELECT COUNT(*) FROM employees;").fetchone()[0]
    if count_emp == 0:
        cursor.executescript("""
        INSERT INTO employees (emp_id, email, department, account_status) VALUES
        ('EMP001', 'alex@company.com', 'Engineering', 'ACTIVE'),
        ('EMP002', 'sarah@company.com', 'Marketing', 'LOCKED');
        """)

    # Check and seed pokemon_items
    count_items = cursor.execute("SELECT COUNT(*) FROM pokemon_items;").fetchone()[0]
    if count_items == 0:
        cursor.executescript("""
        INSERT INTO pokemon_items (item_id, item_name, boost_type, effect) VALUES
        (1, 'Charizardite Y', 'Fire', 'Boosts special attack and triggers Drought weather.'),
        (2, 'Blastoisinite', 'Water', 'Boosts defense and enables Mega Launcher ability.');
        """)

    conn.commit()
    conn.close()

# Perform Seeding automatically on layout render
init_and_seed_db()

# =========================================================
# 1. CORE LAYOUT AND WEB APP FUNCTIONALITY
# =========================================================
api_key = os.environ.get("GOOGLE_API_KEY", "")
if not api_key:
    try:
        from google.colab import userdata
        api_key = userdata.get("GOOGLE_API_KEY")
    except Exception:
        pass

st.title("☑ Enterprise Intelligence Analyst Dashboard")
st.markdown("### Live Database Schema Evolution, Comparison Suite, and Operational Telemetry")

with st.sidebar:
    st.header("☑ Security & Configuration")
    if api_key:
        st.success("Gemini API Key: Configured \u2705")
    else:
        st.error("Gemini API Key: Missing \u274c")

    st.header("↗ Cost & Token Telemetry")
    st.metric(label="Total Estimated USD Cost", value="$0.000225")
    st.metric(label="Accumulated Prompt Tokens", value="1,200")
    st.metric(label="Accumulated Output Tokens", value="450")

col1, col2 = st.columns([1, 1])

with col1:
    st.header("| Pokemon Battle Power Compare")
    st.markdown("Select two Pokemon to calculate their relative Power Index (HP + Attack) and perform a direct comparison.")

    try:
        conn = sqlite3.connect("file:enterprise.db?mode=ro", uri=True)
        df_pkmn = pd.read_sql_query("SELECT id, name, type1, type2, hp, attack FROM pokemon_master ORDER BY name ASC;", conn)
        conn.close()

        p1 = st.selectbox("Select First Pokemon", df_pkmn["name"].tolist(), index=0)
        p2 = st.selectbox("Select Second Pokemon", df_pkmn["name"].tolist(), index=min(1, len(df_pkmn)-1))

        row1 = df_pkmn[df_pkmn["name"] == p1].iloc[0]
        row2 = df_pkmn[df_pkmn["name"] == p2].iloc[0]

        power1 = int(row1["hp"]) + int(row1["attack"])
        power2 = int(row2["hp"]) + int(row2["attack"])

        comp_data = {
            "Stat": ["HP", "Attack", "Total Battle Power"],
            p1: [row1["hp"], row1["attack"], power1],
            p2: [row2["hp"], row2["attack"], power2]
        }

        df_comp = pd.DataFrame(comp_data)
        st.table(df_comp)

        if power1 > power2:
            st.success(f"*** **{p1}** has higher total battle power than **{p2}** by **{power1 - power2}** points!")
        elif power2 > power1:
            st.success(f"*** **{p2}** has higher total battle power than **{p1}** by **{power2 - power1}** points!")
        else:
            st.info("\u2032 Both Pokemon have equal battle power indexes!")

    except Exception as e:
        st.warning(f"Could not load comparison tool: {e}")

with col2:
    st.header("↗ Dynamic Database Schema Explorer")
    st.markdown("Discover what tables and fields are currently active in our secure MCP layer:")

    try:
        conn = sqlite3.connect("file:enterprise.db?mode=ro", uri=True)
        cur = conn.cursor()
        tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]

        selected_tab = st.selectbox("Select Live Table to Inspect Structure", tables)
        if selected_tab:
            cols = pd.read_sql_query(f"PRAGMA table_info({selected_tab});", conn)
            st.dataframe(cols[["name", "type", "pk"]])

            st.markdown(f"**Preview rows from `{selected_tab}`:**")
            preview = pd.read_sql_query(f"SELECT * FROM {selected_tab} LIMIT 5;", conn)
            st.dataframe(preview)
        conn.close()
    except Exception as e:
        st.error(f"Schema error: {e}")
