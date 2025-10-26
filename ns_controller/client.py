import json
import socket
import struct

import streamlit as st

SERVER_HOST = "localhost"
SERVER_PORT = 9000


# MessageType values must match server
class MessageType:
    PING = 0
    NORMAL = 1
    GET_STATE = 2
    MACRO_START = 3
    MACRO_STOP = 4
    PAUSE_MACRO = 5
    RESUME_MACRO = 6
    LIST_MACROS = 7
    LOAD_MACRO = 8
    SAVE_MACRO = 9
    DELETE_MACRO = 10
    GET_MACRO_STATUS = 11


# Helper to send/receive messages
class MacroClient:
    def __init__(self, host=SERVER_HOST, port=SERVER_PORT):
        self.host = host
        self.port = port
        self.sock = None

    def connect(self):
        self.sock = socket.create_connection((self.host, self.port))

    def close(self):
        if self.sock:
            self.sock.close()
            self.sock = None

    def send(self, msg_type: int, payload: bytes = b"") -> bytes:
        self.sock.sendall(bytes([msg_type]) + payload)
        return self.sock.recv(4096)

    def list_macros(self):
        self.connect()
        resp = self.send(MessageType.LIST_MACROS)
        self.close()
        try:
            return json.loads(resp.decode())
        except Exception:
            return []

    def load_macro(self, name: str):
        self.connect()
        name_bytes = name.encode()
        payload = struct.pack(">H", len(name_bytes)) + name_bytes
        resp = self.send(MessageType.LOAD_MACRO, payload)
        self.close()
        try:
            return json.loads(resp.decode())
        except Exception:
            return None

    def save_macro(self, name: str, macro_text: str):
        """Save a macro. Can be NXBT text format or JSON."""
        self.connect()
        name_bytes = name.encode()
        macro_bytes = macro_text.encode()
        payload = struct.pack(">H", len(name_bytes)) + name_bytes + struct.pack(">I", len(macro_bytes)) + macro_bytes
        resp = self.send(MessageType.SAVE_MACRO, payload)
        self.close()
        return resp.decode()

    def delete_macro(self, name: str):
        self.connect()
        name_bytes = name.encode()
        payload = struct.pack(">H", len(name_bytes)) + name_bytes
        resp = self.send(MessageType.DELETE_MACRO, payload)
        self.close()
        return resp.decode()

    def start_macro(self, macro_data, repeat=None):
        """Start a macro. Can be dict, JSON string, or NXBT text."""
        self.connect()
        if isinstance(macro_data, str):
            # It's NXBT text - wrap it in JSON so server can parse it
            # Server will receive a JSON string, then check isinstance(macro_data, str)
            macro_json = json.dumps(macro_data)
        else:
            # It's a dict
            if repeat is not None:
                macro_data["repeat"] = repeat
            macro_json = json.dumps(macro_data)

        macro_bytes = macro_json.encode()
        payload = struct.pack(">I", len(macro_bytes)) + macro_bytes
        resp = self.send(MessageType.MACRO_START, payload)
        self.close()
        return resp.decode()

    def stop_macro(self):
        self.connect()
        resp = self.send(MessageType.MACRO_STOP)
        self.close()
        return resp.decode()

    def pause_macro(self):
        self.connect()
        resp = self.send(MessageType.PAUSE_MACRO)
        self.close()
        return resp.decode()

    def resume_macro(self):
        self.connect()
        resp = self.send(MessageType.RESUME_MACRO)
        self.close()
        return resp.decode()

    def get_macro_status(self):
        """Get the current status of the macro runner."""
        self.connect()
        resp = self.send(MessageType.GET_MACRO_STATUS)
        self.close()
        try:
            return json.loads(resp.decode())
        except Exception:
            return {"running": False, "paused": False}

    def get_state(self):
        self.connect()
        resp = self.send(MessageType.GET_STATE)
        self.close()
        try:
            return json.loads(resp.decode())
        except Exception:
            return None


client = MacroClient()

st.set_page_config(page_title="NS Controller", layout="wide")
st.title("🎮 Nintendo Switch Controller")

# Create three columns for layout
col1, col2, col3 = st.columns([2, 2, 1])

with col3:
    st.subheader("📊 Status")
    status = client.get_macro_status()
    if status["running"]:
        if status["paused"]:
            st.warning("⏸️ Paused")
        else:
            st.success("▶️ Running")
    else:
        st.info("⏹️ Stopped")

    # Controller state
    with st.expander("Controller State"):
        state = client.get_state()
        if state:
            st.json(state)

with col1:
    st.subheader("📝 Create/Edit Macro")

    # Tab for creating new or editing existing
    tab1, tab2 = st.tabs(["New Macro", "Load Existing"])

    with tab1:
        new_macro_name = st.text_input("Macro Name", key="new_name")
        st.markdown("**NXBT Macro Syntax:**")
        st.code("""# Example macro
B 0.1s
0.1s
A 0.2s
L_STICK@+000+100 0.5s

# Loop example
LOOP 10
    A 0.1s
    0.1s""", language="python")

        new_macro_text = st.text_area(
            "Macro Content (NXBT syntax or JSON)",
            height=300,
            key="new_text",
            placeholder="B 0.1s\n0.5s\nA 0.1s"
        )

        col_save, col_run = st.columns(2)
        with col_save:
            if st.button("💾 Save", use_container_width=True):
                if new_macro_name and new_macro_text:
                    result = client.save_macro(new_macro_name, new_macro_text)
                    if "ERR" in result:
                        st.error(result)
                    else:
                        st.success(f"Saved '{new_macro_name}'")
                        st.rerun()
                else:
                    st.error("Name and content required")

        with col_run:
            if st.button("▶️ Run Now", use_container_width=True, type="primary"):
                if new_macro_text:
                    result = client.start_macro(new_macro_text, repeat=None)
                    if "ERR" in result:
                        st.error(result)
                    else:
                        st.success("Macro started")
                        st.rerun()
                else:
                    st.error("Content required")

    with tab2:
        macros = client.list_macros()
        if macros:
            selected_macro = st.selectbox("Select Macro to Edit", macros, key="edit_select")
            if selected_macro:
                macro_data = client.load_macro(selected_macro)
                if macro_data:
                    # Show source if available, otherwise JSON
                    if isinstance(macro_data, dict) and "source" in macro_data:
                        edit_text = macro_data["source"]
                    else:
                        edit_text = json.dumps(macro_data, indent=2)

                    edited_text = st.text_area(
                        "Edit Macro Content",
                        value=edit_text,
                        height=300,
                        key="edit_text"
                    )

                    col_update, col_delete = st.columns(2)
                    with col_update:
                        if st.button("💾 Update", use_container_width=True):
                            result = client.save_macro(selected_macro, edited_text)
                            if "ERR" in result:
                                st.error(result)
                            else:
                                st.success(f"Updated '{selected_macro}'")
                                st.rerun()

                    with col_delete:
                        if st.button("🗑️ Delete", use_container_width=True):
                            result = client.delete_macro(selected_macro)
                            if "ERR" in result:
                                st.error(result)
                            else:
                                st.warning(f"Deleted '{selected_macro}'")
                                st.rerun()
        else:
            st.info("No saved macros yet")

with col2:
    st.subheader("🎬 Run Macros")

    macros = client.list_macros()
    if macros:
        selected_run_macro = st.selectbox("Select Macro", macros, key="run_select")

        if selected_run_macro:
            macro_data = client.load_macro(selected_run_macro)

            # Show preview
            with st.expander("Preview Macro"):
                if isinstance(macro_data, dict) and "source" in macro_data:
                    st.code(macro_data["source"], language="python")
                else:
                    st.json(macro_data)

            # Repeat options
            repeat_option = st.radio(
                "Repeat Mode",
                ["Infinite (until stopped)", "Specific count"],
                key="repeat_mode"
            )

            repeat_value = None
            if repeat_option == "Specific count":
                repeat_value = st.number_input("Repeat Count", min_value=1, value=1, key="repeat_count")

            # Control buttons
            st.markdown("---")
            col_start, col_pause, col_stop = st.columns(3)

            with col_start:
                if st.button("▶️ Start", use_container_width=True, type="primary"):
                    result = client.start_macro(macro_data, repeat=repeat_value)
                    if "ERR" in result:
                        st.error(result)
                    else:
                        st.success("Started!")
                        st.rerun()

            with col_pause:
                if status["running"] and not status["paused"]:
                    if st.button("⏸️ Pause", use_container_width=True):
                        result = client.pause_macro()
                        if "ERR" in result:
                            st.error(result)
                        else:
                            st.info("Paused")
                            st.rerun()
                elif status["paused"]:
                    if st.button("▶️ Resume", use_container_width=True):
                        result = client.resume_macro()
                        if "ERR" in result:
                            st.error(result)
                        else:
                            st.success("Resumed")
                            st.rerun()
                else:
                    st.button("⏸️ Pause", use_container_width=True, disabled=True)

            with col_stop:
                if st.button("⏹️ Stop", use_container_width=True):
                    result = client.stop_macro()
                    if "ERR" in result:
                        st.error(result)
                    else:
                        st.warning("Stopped")
                        st.rerun()
    else:
        st.info("No macros available. Create one first!")

# Auto-refresh status every 2 seconds
if status["running"]:
    st.markdown("---")
    st.caption("🔄 Auto-refreshing... (macro is running)")
    import time
    time.sleep(2)
    st.rerun()
