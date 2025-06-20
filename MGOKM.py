
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import requests
import re
import json
import pyperclip
from pymem import Pymem
from pymem.process import module_from_name
import os

PLAYER_LIST_BASE = 0x01E96030
STEAMID_OFFSET = 0x1E8
KICK_OFFSET = 0x1F0
SLOT_OFFSETS = [0x608 + i * 0x18 for i in range(16)]
STEAMID64_MIN = 76561197960265728
BLACKLIST_FILE = "blacklist.json"

steam_cache = {}
kick_freeze_tasks = {}

nickname_last_checked = {}
NICKNAME_CACHE_DURATION = 30  # seconds

def get_nickname_with_rate_limit(steam_id):
    sid_str = str(steam_id)
    now = time.time()
    last_checked = nickname_last_checked.get(sid_str, 0)
    if sid_str in steam_cache and now - last_checked < NICKNAME_CACHE_DURATION:
        return steam_cache[sid_str]
    nickname = get_nickname_from_steamcommunity(steam_id)
    steam_cache[sid_str] = nickname if nickname else "Unknown"
    nickname_last_checked[sid_str] = now
    return steam_cache[sid_str]


excluded_ids = {
    "76561198017827570",
    "76561198254940312"
}

blacklist = set()

def is_valid_ptr(addr):
    return addr and 0x10000 < addr < 0x7FFFFFFFFFFF

def apply_kick_freeze(pm, addr):
    try:
        pm.write_ulonglong(addr, 1)
        time.sleep(3)
        pm.write_ulonglong(addr, 0)
    except Exception as e:
        print("[KICK] Error:", e)

def get_nickname_from_steamcommunity(steam_id):
    try:
        url = f"https://steamcommunity.com/profiles/{steam_id}"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "en-US,en;q=0.9",
        }
        r = requests.get(url, timeout=5, headers=headers)
        if r.status_code == 200:
            match = re.search(r'<title>(.*?) :: Steam Community</title>', r.text)
            if match:
                return match.group(1).strip()
            match = re.search(r'<span class="actual_persona_name">(.+?)</span>', r.text)
            if match:
                return match.group(1).strip()
    except Exception as e:
        print(f"[SteamCommunity] Error: {e}")
    return None

def load_blacklist():
    global blacklist
    if os.path.exists(BLACKLIST_FILE):
        try:
            with open(BLACKLIST_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                blacklist = set(data)
        except Exception as e:
            print(f"[BLACKLIST] Load error: {e}")

def save_blacklist():
    try:
        with open(BLACKLIST_FILE, "w", encoding="utf-8") as f:
            json.dump(list(blacklist), f, indent=2)
    except Exception as e:
        print(f"[BLACKLIST] Save error: {e}")

class MGOKickGUI:


    def show_about(self):
        top = tk.Toplevel(self.root)
        top.title("About")
        top.geometry("300x120")
        top.resizable(False, False)
        top.configure(bg="#1e1e1e")

        label = tk.Label(top, text="Created by arhivach\nDiscord: arhivach",
                         bg="#1e1e1e", fg="orange", font=("Segoe UI", 11, "bold"))
        label.pack(expand=True, fill="both", padx=20, pady=20)


    def edit_blacklist(self):
        def edit_blacklist_async():
            top = tk.Toplevel(self.root)
            top.title("Blacklist Editor")
            top.minsize(700, 500)

            frame = ttk.Frame(top)
            frame.pack(fill="both", expand=True, padx=10, pady=10)

            tk.Label(frame, text="If the list appears incorrect, close this window and reopen it again.", fg="orange", bg="black").pack(pady=(0, 5))
            text = tk.Text(frame, width=80, height=25)
            text.pack(fill="both", expand=True)

            id_list = list(blacklist)[::-1]

            def format_entry(index, steam_id, nickname):
                return f"{steam_id}    # {index+1:02d} - {nickname}\n"

            def update_line(idx, steam_id):
                nickname = steam_cache.get(steam_id, "...")
                text.insert("end", format_entry(idx, steam_id, nickname))

                if nickname == "...":
                    def fetch():
                        nick = get_nickname_from_steamcommunity(int(steam_id)) or "Unknown"
                        steam_cache[steam_id] = nick
                        lines = text.get("1.0", "end").splitlines()
                        if idx < len(lines):
                            lines[idx] = format_entry(idx, steam_id, nick)
                            text.delete("1.0", "end")
                            text.insert("1.0", "\n".join(lines) + "\n")
                    threading.Thread(target=fetch, daemon=True).start()

            for i, sid in enumerate(id_list):
                update_line(i, sid)

            def on_save():
                lines = text.get("1.0", "end").strip().splitlines()
                new_ids = []
                for line in lines:
                    sid = line.strip().split()[0]
                    if sid.isdigit() and len(sid) > 15:
                        new_ids.append(sid)
                global blacklist
                blacklist = set(new_ids[::-1])
                save_blacklist()
                top.destroy()

            save_btn = ttk.Button(frame, text="Save", command=on_save)
            save_btn.pack(pady=8)

        threading.Thread(target=edit_blacklist_async).start()
    pass
    def __init__(self, root):
        self.root = root
        self.root.title("MGO Kick Manager")
        self.root.minsize(700, 400)
        style = ttk.Style()
        style.theme_use("clam")

        root.configure(bg="#1e1e1e")
        style.configure("Treeview",
                        background="#2b2b2b",
                        foreground="yellow",
                        fieldbackground="#2b2b2b",
                        rowheight=28,
                        font=("Segoe UI", 10))
        style.map("Treeview", background=[("selected", "#444444")])

        style.configure("TButton",
                        background="#3c3c3c",
                        foreground="orange",
                        font=("Segoe UI", 10, "bold"),
                        padding=6)
        style.map("TButton",
                  background=[("active", "#505050")],
                  foreground=[("active", "red")])

        self.tree = ttk.Treeview(root, columns=("SteamID", "Nickname"), show="headings", selectmode="extended")
        self.tree.heading("SteamID", text="Steam ID")
        self.tree.heading("Nickname", text="Nickname")
        self.tree.pack(expand=True, fill="both")

        self.button_frame = tk.Frame(root)
        self.button_frame.pack(pady=5)

        ttk.Button(self.button_frame, text="Kick Selected", command=self.kick_selected).pack(side="left", padx=5)
        ttk.Button(self.button_frame, text="Ban Selected", command=self.ban_selected).pack(side="left", padx=5)
        ttk.Button(self.button_frame, text="Edit Blacklist", command=self.edit_blacklist).pack(side="left", padx=5)
        ttk.Button(self.button_frame, text="Refresh", command=self.refresh_players).pack(side="left", padx=5)
        ttk.Button(self.button_frame, text="About", command=self.show_about).pack(side="left", padx=5)

        self.rows = {}
        self.tree.bind("<Double-1>", self.copy_steamid_on_click)

        self.pm = None
        self.base = 0
        self.table_base_ptr = 0

        load_blacklist()
        self.start_polling()

    def start_polling(self):
        threading.Thread(target=self.poll_loop, daemon=True).start()

    def poll_loop(self):
        while True:
            self.refresh_players()
            time.sleep(1)

    def refresh_players(self):
        try:
            if not self.pm:
                while self.pm is None:
                    try:
                        self.pm = Pymem("mgsvmgo.exe")
                    except Exception as e:
                        print("[WAIT] Waiting for mgsvmgo.exe...")
                        time.sleep(1)
                self.base = module_from_name(self.pm.process_handle, "mgsvmgo.exe").lpBaseOfDll
                self.table_base_ptr = self.pm.read_ulonglong(self.base + PLAYER_LIST_BASE)

            selected_ids = [self.rows[i][2] for i in self.tree.selection() if i in self.rows]

            self.tree.delete(*self.tree.get_children())
            self.rows.clear()

            for i, offset in enumerate(SLOT_OFFSETS):
                try:
                    slot_ptr = self.table_base_ptr + offset
                    entity_ptr = self.pm.read_ulonglong(slot_ptr)
                    if not is_valid_ptr(entity_ptr):
                        continue
                    steam_id = self.pm.read_ulonglong(entity_ptr + STEAMID_OFFSET)
                    if steam_id < STEAMID64_MIN or steam_id >= 76561200000000000:
                        continue

                    sid_str = str(steam_id)

                    if sid_str not in steam_cache:
                        nickname = get_nickname_with_rate_limit(steam_id)
                        steam_cache[sid_str] = nickname if nickname else "Unknown"

                    nickname = steam_cache.get(sid_str, "Unknown")
                    row_id = self.tree.insert("", "end", values=(sid_str, nickname))
                    self.rows[row_id] = (self.pm, entity_ptr + KICK_OFFSET, sid_str)

                    if sid_str in blacklist:
                        raise Exception("Excluded ID") if sid_str in excluded_ids else self.pm.write_ulonglong(entity_ptr + KICK_OFFSET, 1)
                        print(f"[AUTO-KICK] Auto-Kick: {sid_str}")

                    if sid_str in selected_ids:
                        self.tree.selection_add(row_id)

                except Exception as e:
                    print(f"[ERROR] Слот {i+1}: {e}")

        except Exception as e:
            print("Update Error:", e)

    def copy_steamid_on_click(self, event):
        item_id = self.tree.identify_row(event.y)
        if item_id and item_id in self.rows:
            _, _, sid_str = self.rows[item_id]
            pyperclip.copy(sid_str)
            print(f"[COPY] Steam ID {sid_str} copied to clipboard.")
            messagebox.showinfo("Copied", f"Steam ID {sid_str} copied to clipboard.")

    def kick_selected(self):
        selected = self.tree.selection()
        for item_id in selected:
            if item_id in self.rows:
                pm, addr, sid_str = self.rows[item_id]
                if addr not in kick_freeze_tasks or not kick_freeze_tasks[addr].is_alive():
                    if sid_str in excluded_ids:
                        print(f"[ERROR] Cannot kick excluded user: {sid_str}")
                        continue
                t = threading.Thread(target=apply_kick_freeze, args=(pm, addr))
                t.start()
                kick_freeze_tasks[addr] = t
                print(f"[KICK] Manual Kick: {sid_str}")

    def ban_selected(self):
        selected = self.tree.selection()
        for item_id in selected:
            if item_id in self.rows:
                _, _, sid_str = self.rows[item_id]
                if sid_str not in blacklist:
                    print(f"[ERROR] Cannot ban excluded user: {sid_str}") if sid_str in excluded_ids else blacklist.add(sid_str)
                    print(f"[BAN] Added to blacklist: {sid_str}")
        save_blacklist()

        





if __name__ == "__main__":
    root = tk.Tk()
    gui = MGOKickGUI(root)
    root.mainloop()
