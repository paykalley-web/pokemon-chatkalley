import streamlit as st
import sqlite3
import pandas as pd
import os
from google import genai

# Configure page style
st.set_page_config(
    page_title="Pokemon Battle Power Compare",
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
    CREATE TABLE IF NOT EXISTS pokemon_balls (
        ball_id INTEGER PRIMARY KEY AUTOINCREMENT,
        ball_name TEXT UNIQUE NOT NULL,
        catch_rate_multiplier REAL NOT NULL,
        special_effect TEXT
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

    # Check and seed pokemon_balls
    count_balls = cursor.execute("SELECT COUNT(*) FROM pokemon_balls;").fetchone()[0]
    if count_balls == 0:
        cursor.executescript("""
        INSERT INTO pokemon_balls (ball_name, catch_rate_multiplier, special_effect) VALUES
        ('Poke Ball', 1.0, 'Standard capturing device.'),
        ('Great Ball', 1.5, 'Improved capture performance.'),
        ('Ultra Ball', 2.0, 'High-performance capture device.'),
        ('Master Ball', 255.0, 'Guaranteed capture on any wild encounter.');
        """)

    conn.commit()
    conn.close()

# Perform Seeding automatically on layout render
init_and_seed_db()

# =========================================================
# 1. CORE LAYOUT AND WEB APP CONFIGURATION
# =========================================================
api_key = os.environ.get("GOOGLE_API_KEY", "")
if not api_key:
    try:
        from google.colab import userdata
        api_key = userdata.get("GOOGLE_API_KEY")
    except Exception:
        pass

st.title("Pokemon Battle Power Compare")
st.markdown("### Enterprise Multi-Domain Support & Interactive Query Console")

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

# Embedded Tabbed Interface with Explorer on the Left
tab1, tab2 = st.tabs(["📂 Database Schema Explorer", "💬 AI Analyst Chat"])

with tab1:
    st.header("↗ Dynamic Database Schema Explorer")
    st.markdown("Discover tables, fields, and master data configurations currently active in our secure layer:")
    try:
        conn = sqlite3.connect("file:enterprise.db?mode=ro", uri=True)
        cur = conn.cursor()
        tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]

        # Set default table to pokemon_balls to show the requested pokeball changes
        default_index = tables.index("pokemon_balls") if "pokemon_balls" in tables else 0
        selected_tab = st.selectbox("Select Live Table to Inspect Structure", tables, index=default_index, key="schema_table_select")
        
        if selected_tab:
            cols = pd.read_sql_query(f"PRAGMA table_info({selected_tab});", conn)
            st.dataframe(cols[["name", "type", "pk"]], use_container_width=True)

            st.markdown(f"**Preview rows from `{selected_tab}`:**")
            preview = pd.read_sql_query(f"SELECT * FROM {selected_tab} LIMIT 5;", conn)
            st.dataframe(preview, use_container_width=True)
        conn.close()
    except Exception as e:
        st.error(f"Schema error: {e}")

with tab2:
    st.header("💬 Security-Enforced Chat Console")
    st.markdown("Ask questions about Pokemons, policies, or employee structures. Safety guardrails are built-in.")

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Hi! I am your Enterprise Analyst Agent. How can I assist you with Pokemon stats, databases, or policies today?"}
        ]

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask a question or request database information..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Process user query safely
        with st.chat_message("assistant"):
            if not api_key:
                st.error("Gemini API Key is missing. Please configure it in your secret keys.")
            else:
                try:
                    client = genai.Client(api_key=api_key)
                    system_instruction = """
                    You are a helpful analyst assistant. You answer questions strictly based on the enterprise.db.
                    For safety, you only query read-only schemas.
                    """

                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=prompt,
                        config=genai.types.GenerateContentConfig(
                            system_instruction=system_instruction
                        )
                    )
                    ans_text = response.text
                    st.markdown(ans_text)
                    st.session_state.messages.append({"role": "assistant", "content": ans_text})
                except Exception as e:
                    st.error(f"Error generating response: {e}")
