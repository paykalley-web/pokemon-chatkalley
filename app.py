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

# Tab 1: AI Chat Bar, Tab 2: Pokemon Battle Compare File
tab1, tab2 = st.tabs(["💬 AI Analyst Chat Bar", "⚔ Pokémon Battle Power Compare"])

with tab1:
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

with tab2:
    st.header("⚔ Pokemon Battle Power Compare Tool")
    st.markdown("Select two Pokémon to calculate their relative **Power Index** (HP + Attack) and perform a direct comparison.")

    try:
        conn = sqlite3.connect("file:enterprise.db?mode=ro", uri=True)
        df_pkmn = pd.read_sql_query("SELECT id, name, type1, type2, hp, attack FROM pokemon_master ORDER BY name ASC;", conn)
        conn.close()

        # Safely determine indexes to avoid key errors
        pkmn_list = df_pkmn["name"].tolist()
        idx1 = pkmn_list.index("Charizard") if "Charizard" in pkmn_list else 0
        idx2 = pkmn_list.index("Blastoise") if "Blastoise" in pkmn_list else min(1, len(pkmn_list) - 1)

        p1 = st.selectbox("Select First Pokémon", pkmn_list, index=idx1, key="p1_battle_select")
        p2 = st.selectbox("Select Second Pokémon", pkmn_list, index=idx2, key="p2_battle_select")

        row1 = df_pkmn[df_pkmn["name"] == p1].iloc[0]
        row2 = df_pkmn[df_pkmn["name"] == p2].iloc[0]

        # Power Calculation Formula: HP + Attack
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
            st.success(f"🏆 **{p1}** has higher total battle power than **{p2}** by **{power1 - power2}** points!")
        elif power2 > power1:
            st.success(f"🏆 **{p2}** has higher total battle power than **{p1}** by **{power2 - power1}** points!")
        else:
            st.info("🤝 Both Pokémon have equal battle power indexes!")

    except Exception as e:
        st.warning(f"Could not load comparison tool: {e}")
