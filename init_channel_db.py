import sqlite3
conn = sqlite3.connect("state_channels.db")
conn.execute("CREATE TABLE IF NOT EXISTS nonces (agent_address TEXT PRIMARY KEY, current_nonce INTEGER)")
conn.commit()
conn.close()
