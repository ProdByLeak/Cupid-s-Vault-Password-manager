import os
import msvcrt
import json
import time
import hashlib
import hmac
import base64

# --- Constants and Globals ---

LIGHT_BLUE = "\033[38;5;117m"
GREEN      = "\033[32m"
RED        = "\033[31m"
ORANGE     = "\033[38;5;208m"
RESET      = "\033[0m"
BOLD       = "\033[1m"
DIM        = "\033[2m"

CONSOLE_WIDTH   = 100
BANNER_LEFT_PAD = 28

TABS = [
    "Passwords",
    "Create Password",
    "New Group",
    "Delete Group",
    "Delete Password",
    "Change Passkey",
    "Themes",
]

passwords           = {}
passkey             = None
current_theme_name  = "Blue"
current_theme_color = None   # Set by load_theme()

# Absolute paths
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_FILE   = os.path.join(SCRIPT_DIR, "data.json")
THEMES_FILE = os.path.join(SCRIPT_DIR, "themes.json")

# Theme palette — name : (ANSI escape, gradient_start RGB, gradient_peak RGB)
# Pattern mirrors the originals: saturated mid-hue → lighter pastel of same hue
# Blue original:  (0, 100, 255) → (100, 200, 255)
# Pink original:  (255, 100, 180) → (255, 182, 220)
THEME_PALETTE = {
    "Blue":   ("\033[38;5;117m",  (0,   100, 255), (100, 200, 255)),
    "Green":  ("\033[32m",        (0,   130,  50), (60,  180, 100)),
    "Yellow": ("\033[33m",        (220, 180,   0), (255, 230, 100)),
    "Pink":   ("\033[38;5;218m",  (255, 100, 180), (255, 182, 220)),
    "White":  ("\033[97m",        (160, 160, 180), (220, 220, 235)),
    "Orange": ("\033[38;5;208m",  (230, 110,   0), (255, 190, 100)),
    "Cyan":   ("\033[36m",        (0,   180, 210), (100, 230, 245)),
    "Red":    ("\033[31m",        (210,  40,  60), (255, 130, 140)),
    "Purple": ("\033[38;5;135m",  (120,  40, 220), (190, 130, 255)),
}
THEME_NAMES = list(THEME_PALETTE.keys())

# --- Encryption ---
# Pure stdlib: PBKDF2-HMAC-SHA256 key derivation + SHA-256 block stream cipher (XOR)
# Salt (16 bytes) + HMAC tag (32 bytes) + ciphertext, all base64-encoded.
# The passkey is used as the encryption password — data cannot be decrypted without it.

_ENC_MAGIC  = b"CVAULT1:"   # file header to detect encrypted vs plain
_SALT_LEN   = 16
_HMAC_LEN   = 32
_PBKDF2_IT  = 200_000       # PBKDF2 iteration count (NIST recommended minimum)

def _derive_key(password: str, salt: bytes) -> bytes:
    """Derive a 32-byte key from the password using PBKDF2-HMAC-SHA256."""
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_IT, dklen=32)

def _xor_stream(data: bytes, key: bytes) -> bytes:
    """Encrypt/decrypt bytes using a SHA-256 counter-mode stream cipher."""
    out     = bytearray(len(data))
    counter = 0
    buf     = b""
    pos     = 0
    for i, byte in enumerate(data):
        if pos >= len(buf):
            buf  = hashlib.sha256(key + counter.to_bytes(8, "big")).digest()
            pos  = 0
            counter += 1
        out[i] = byte ^ buf[pos]
        pos += 1
    return bytes(out)

def encrypt_data(plaintext: str, password: str) -> bytes:
    """Encrypt a UTF-8 string and return raw bytes (magic + salt + hmac + ciphertext)."""
    salt       = os.urandom(_SALT_LEN)
    key        = _derive_key(password, salt)
    ciphertext = _xor_stream(plaintext.encode("utf-8"), key)
    mac        = hmac.new(key, salt + ciphertext, hashlib.sha256).digest()
    return _ENC_MAGIC + salt + mac + ciphertext

def decrypt_data(raw: bytes, password: str) -> str:
    """Decrypt raw bytes back to a UTF-8 string. Raises ValueError on bad passkey/tamper."""
    if not raw.startswith(_ENC_MAGIC):
        raise ValueError("Not an encrypted data file.")
    raw        = raw[len(_ENC_MAGIC):]
    salt       = raw[:_SALT_LEN]
    mac_stored = raw[_SALT_LEN:_SALT_LEN + _HMAC_LEN]
    ciphertext = raw[_SALT_LEN + _HMAC_LEN:]
    key        = _derive_key(password, salt)
    mac_check  = hmac.new(key, salt + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(mac_stored, mac_check):
        raise ValueError("Decryption failed: incorrect passkey or data tampered.")
    return _xor_stream(ciphertext, key).decode("utf-8")

def get_hl():
    """Return the active theme ANSI color code."""
    return current_theme_color if current_theme_color else LIGHT_BLUE

def get_gradient_stops():
    """Return (start_rgb, peak_rgb) for the current theme's banner gradient."""
    entry = THEME_PALETTE.get(current_theme_name, THEME_PALETTE["Blue"])
    return entry[1], entry[2]

# --- Banner ---

BANNER = r"""
                                                                
                         ▄▄ ▄                          ▄▄       
                  ▀▀     ██ ▀                          ██  ██   
▄████ ██ ██ ████▄ ██  ▄████  ▄█▀▀▀   ██ ██  ▀▀█▄ ██ ██ ██ ▀██▀▀ 
██    ██ ██ ██ ██ ██  ██ ██  ▀███▄   ██▄██ ▄█▀██ ██ ██ ██  ██   
▀████ ▀██▀█ ████▀ ██▄ ▀████  ▄▄▄█▀    ▀█▀  ▀█▄██ ▀██▀█ ██  ██   
            ██                                                  
"""

def color_text(text, r, g, b):
    return f"\033[38;2;{r};{g};{b}m{text}{RESET}"

def interpolate_color(c1, c2, factor):
    return (
        int(c1[0] + (c2[0] - c1[0]) * factor),
        int(c1[1] + (c2[1] - c1[1]) * factor),
        int(c1[2] + (c2[2] - c1[2]) * factor),
    )

def create_gradient_banner():
    """Render the banner with the same two-stop left-to-right sweep as the
    originals: gradient_start → gradient_peak across each line."""
    grad_start, grad_peak = get_gradient_stops()

    padding         = " " * BANNER_LEFT_PAD
    printable_lines = BANNER.strip('\n').split('\n')

    max_text_length = 0
    for line in printable_lines:
        if not line.strip():
            continue
        end_idx   = len(line.rstrip())
        start_idx = len(line) - len(line.lstrip())
        max_text_length = max(max_text_length, end_idx - start_idx)

    output = []
    for line in printable_lines:
        if not line.strip() and len(line) < 3:
            continue
        start_pad_len = len(line) - len(line.lstrip())
        start_pad     = line[:start_pad_len]
        content       = line.lstrip()
        colored       = ""
        char_count    = 0
        for ch in content:
            if ch.isspace():
                colored += ch
                continue
            pos = char_count / max_text_length if max_text_length else 0
            r, g, b = interpolate_color(grad_start, grad_peak, pos)
            colored += color_text(ch, r, g, b)
            char_count += 1
        output.append(f"{padding}{start_pad}{colored}{RESET}")

    return '\n'.join(output) + '\n'

# --- UI Helpers ---

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

def get_menu_padding_size():
    max_tab_length   = max(len(tab) for tab in TABS)
    total_line_width = max_tab_length + 2
    return max(0, (CONSOLE_WIDTH // 2) - (total_line_width // 2)) + 7

def section_header(title):
    """Print a bold section header — plain like the original."""
    print(f"{BOLD}{title}{RESET}")

def instruction(text):
    """Print a plain instruction line."""
    print(text)

def success(text):
    """Print a plain confirmation/success message."""
    print(text)

def themed_input(prompt):
    """Standard input — plain like the original."""
    return input(prompt)

# --- Key Input ---

def read_key():
    try:
        ch = msvcrt.getch()
        if ch.lower() == b"q":
            clear_screen()
            os._exit(0)
        if ch in (b"\r", b"\n"):
            return "ENTER"
        if ch == b"\xe0" or ch == b"\x00":
            ch2 = msvcrt.getch()
            if ch2 == b"H":
                return "UP"
            if ch2 == b"P":
                return "DOWN"
        if ch.lower() == b"b":
            return "B"
        if ch.lower() == b"y":
            return "Y"
        if ch.lower() == b"n":
            return "N"
        if ch.lower() == b"r":
            return "R"
        return None
    except ImportError:
        instruction("\n[Warning: Arrow key functions disabled. Press ENTER, B, Y, N, R, or Q.]")
        while True:
            try:
                entered = input()
                if entered == '':          return 'ENTER'
                if entered.lower() == 'b': return 'B'
                if entered.lower() == 'y': return 'Y'
                if entered.lower() == 'n': return 'N'
                if entered.lower() == 'r': return 'R'
                if entered.lower() == 'q': os._exit(0)
            except EOFError:
                pass

def get_masked_input(prompt):
    """Masked input — shows '*' instead of typed characters."""
    try:
        if os.name != 'nt':
            raise ImportError
        import sys
        sys.stdout.write(prompt)
        sys.stdout.flush()
        input_list = []
        while True:
            char = msvcrt.getch()
            if char in (b'\r', b'\n'):
                sys.stdout.write('\n')
                break
            elif char == b'\x08':
                if input_list:
                    sys.stdout.write('\b \b')
                    sys.stdout.flush()
                    input_list.pop()
            elif char in (b'\xe0', b'\x00'):
                msvcrt.getch()
            elif char:
                try:
                    char_str = char.decode()
                    if char_str.isprintable() and len(char_str) == 1:
                        sys.stdout.write('*')
                        sys.stdout.flush()
                        input_list.append(char_str)
                except UnicodeDecodeError:
                    pass
        return "".join(input_list)
    except ImportError:
        instruction("\n[Warning: Masked input disabled. Using regular input.]")
        return input(prompt)

# --- Data I/O ---

def save_data():
    """Serialize and encrypt the passwords + passkey to DATA_FILE."""
    data      = {"passwords": passwords, "passkey": passkey}
    plaintext = json.dumps(data, indent=4)
    try:
        # Encrypt when a passkey is set; fall back to plain JSON if not yet set
        # (only on very first run before passkey creation)
        if passkey:
            raw = encrypt_data(plaintext, passkey)
            with open(DATA_FILE, "wb") as f:
                f.write(raw)
        else:
            with open(DATA_FILE, "w") as f:
                f.write(plaintext)
    except Exception as e:
        print(f"\n{RED}{BOLD}*** CRITICAL SAVE ERROR ***{RESET}")
        print(f"{RED}Failed to write to file: {DATA_FILE}{RESET}")
        print(f"{RED}Error details: {e}{RESET}")
        input("Press ENTER to continue (Data was NOT saved)...")

def load_data():
    """Load and decrypt the data file, handling both encrypted and plain formats."""
    global passwords, passkey
    data = {"passwords": {}, "passkey": None}
    try:
        if not os.path.exists(DATA_FILE) or os.path.getsize(DATA_FILE) == 0:
            return

        with open(DATA_FILE, "rb") as f:
            raw = f.read()

        if raw.startswith(_ENC_MAGIC):
            # Encrypted file — need the stored passkey to decrypt.
            # On startup the passkey is embedded inside the encrypted blob,
            # so we must do a two-pass: first decrypt with a prompt if needed.
            # However, passkey is already stored inside the data so we decrypt
            # using the passkey that's inside — we bootstrap via a temp read.
            # Strategy: prompt once on first load if passkey unknown.
            _load_encrypted(raw)
        else:
            # Plain JSON (legacy or pre-passkey state)
            loaded = json.loads(raw.decode("utf-8"))
            passwords.clear()
            passwords.update(loaded.get("passwords", {}))
            passkey = loaded.get("passkey", None)
            # Migrate old flat format to grouped format
            is_old_format = (
                any(isinstance(v, str) for v in passwords.values())
                and all(isinstance(k, str) for k in passwords.keys())
            )
            if is_old_format and "Default Group" not in passwords:
                temp = passwords.copy()
                passwords.clear()
                passwords["Default Group"] = temp
            # Migrate plain JSON to encrypted format immediately if passkey present
            if passkey:
                save_data()

    except Exception as e:
        passwords.clear()
        passkey = None
        if os.path.exists(DATA_FILE):
            print(f"\n[Warning] Data file corrupt or unreadable. Initializing new data state.")

def _load_encrypted(raw: bytes):
    """Decrypt an encrypted data file, prompting for passkey if needed."""
    global passwords, passkey

    # We need the passkey to decrypt, but it's stored inside.
    # Prompt the user to enter it on startup.
    while True:
        clear_screen()
        print(f"{BOLD}Cupid's Vault — Unlock{RESET}")
        pk = get_masked_input("\nEnter your passkey to unlock the vault: ")
        if not pk:
            print(f"\n{RED}Passkey cannot be empty.{RESET}")
            input("Press ENTER to try again...")
            continue
        try:
            plaintext = decrypt_data(raw, pk)
            loaded    = json.loads(plaintext)
            passwords.clear()
            passwords.update(loaded.get("passwords", {}))
            passkey = loaded.get("passkey", None)
            # If passkey inside file doesn't match what was typed, reject
            if passkey != pk:
                passwords.clear()
                passkey = None
                print(f"\n{RED}Incorrect passkey.{RESET}")
                input("Press ENTER to try again...")
                continue
            break
        except ValueError:
            print(f"\n{RED}Incorrect passkey or data corrupted.{RESET}")
            input("Press ENTER to try again...")

def save_theme(theme_name):
    """Persist the chosen theme name to themes.json."""
    try:
        with open(THEMES_FILE, "w") as f:
            json.dump({"theme": theme_name}, f, indent=4)
    except Exception as e:
        print(f"\n{RED}{BOLD}*** THEME SAVE ERROR ***{RESET}")
        print(f"{RED}Failed to write theme file: {THEMES_FILE}{RESET}")
        print(f"{RED}Error details: {e}{RESET}")
        input("Press ENTER to continue...")

def load_theme():
    """Load saved theme from themes.json; auto-creates with Blue default if missing."""
    global current_theme_color, current_theme_name
    if not os.path.exists(THEMES_FILE):
        save_theme("Blue")
        current_theme_name  = "Blue"
        current_theme_color = THEME_PALETTE["Blue"][0]
        return
    try:
        with open(THEMES_FILE, "r") as f:
            if os.path.getsize(THEMES_FILE) > 0:
                data = json.load(f)
                name = data.get("theme", "Blue")
                if name not in THEME_PALETTE:
                    name = "Blue"
                current_theme_name  = name
                current_theme_color = THEME_PALETTE[name][0]
            else:
                save_theme("Blue")
                current_theme_name  = "Blue"
                current_theme_color = THEME_PALETTE["Blue"][0]
    except Exception:
        save_theme("Blue")
        current_theme_name  = "Blue"
        current_theme_color = THEME_PALETTE["Blue"][0]

# --- Screens ---

def themes_screen():
    """Interactive theme selection screen."""
    global current_theme_color, current_theme_name
    selected = 0
    for i, name in enumerate(THEME_NAMES):
        if name == current_theme_name:
            selected = i
            break

    delay_active = True
    while True:
        clear_screen()
        section_header("Themes")
        instruction("\nUse UP/DOWN to select a theme, ENTER to apply, B to go back.\n")

        for i, name in enumerate(THEME_NAMES):
            color  = THEME_PALETTE[name][0]
            tag    = f" {DIM}({RESET}\033[97mactive{RESET}{DIM}){RESET}" if name == current_theme_name else ""
            prefix = ">" if i == selected else " "
            if i == selected:
                print(f"{prefix} {color}{BOLD}{name}{RESET}{tag}")
            else:
                print(f"{prefix} {color}{name}{RESET}{tag}")
            if delay_active:
                time.sleep(0.08)

        delay_active = False
        key = read_key()
        if key == "UP":
            selected = (selected - 1) % len(THEME_NAMES)
        elif key == "DOWN":
            selected = (selected + 1) % len(THEME_NAMES)
        elif key == "B":
            return
        elif key == "ENTER":
            chosen              = THEME_NAMES[selected]
            current_theme_name  = chosen
            current_theme_color = THEME_PALETTE[chosen][0]
            save_theme(chosen)
            success(f"\nTheme set to {BOLD}{chosen}{RESET}.")
            input("Press ENTER to continue...")
            return

def main_menu():
    selected     = 0
    delay_active = True
    padding_size = get_menu_padding_size()
    padding      = " " * padding_size

    while True:
        clear_screen()
        print("\n")
        print(create_gradient_banner())
        print("\n\n")

        for i, tab in enumerate(TABS):
            if i == selected:
                print(f"{padding}  {get_hl()}{BOLD}<{tab}>{RESET}")
            else:
                print(f"{padding}  {tab}")
            if delay_active:
                time.sleep(0.1)

        delay_active = False
        key = read_key()
        if key == "UP":
            selected = (selected - 1) % len(TABS)
        elif key == "DOWN":
            selected = (selected + 1) % len(TABS)
        elif key == "ENTER":
            delay_active = True
            tab_name = TABS[selected]
            if   tab_name == "Passwords":       passwords_tab()
            elif tab_name == "Create Password": create_password_screen()
            elif tab_name == "New Group":       create_group_screen()
            elif tab_name == "Delete Group":    delete_group_screen()
            elif tab_name == "Delete Password": delete_password_screen()
            elif tab_name == "Change Passkey":  change_passkey_screen()
            elif tab_name == "Themes":          themes_screen()

def passwords_tab():
    if not passwords:
        clear_screen()
        section_header("Passwords")
        print("\nNo groups or passwords saved yet.")
        instruction("\nPress B to go back to the Menu.")
        while True:
            if read_key() == "B":
                return
        return

    selected_group = 0
    delay_active   = True

    while True:
        group_names = list(passwords.keys())
        if not group_names:
            return

        clear_screen()
        section_header("Groups")
        instruction("\nUse UP/DOWN to select, ENTER to open a group, B to go back to the Menu.\n")

        if selected_group >= len(group_names):
            selected_group = max(0, len(group_names) - 1)

        for i, group in enumerate(group_names):
            prefix = ">" if i == selected_group else " "
            count  = len(passwords.get(group, {}))
            line   = f"{group} ({count} passwords)"
            if i == selected_group:
                print(f"{prefix} {get_hl()}{BOLD}{line}{RESET}")
            else:
                print(f"{prefix} {line}")
            if delay_active:
                time.sleep(0.1)

        delay_active = False
        key = read_key()
        if key == "UP":
            selected_group = (selected_group - 1) % len(group_names)
        elif key == "DOWN":
            selected_group = (selected_group + 1) % len(group_names)
        elif key == "B":
            return
        elif key == "ENTER":
            delay_active = True
            view_group_passwords(group_names[selected_group])

def view_group_passwords(group_name):
    if group_name not in passwords or not passwords.get(group_name):
        return

    selected     = 0
    delay_active = True

    while True:
        if group_name not in passwords or not passwords[group_name]:
            return

        clear_screen()
        section_header(f"Group: {group_name}")
        instruction("\nUse UP/DOWN to select, ENTER to view a password, B to go back to groups.\n")

        labels = list(passwords[group_name].keys())
        if selected >= len(labels):
            selected = max(0, len(labels) - 1)

        for i, label in enumerate(labels):
            masked = "*" * 10
            prefix = ">" if i == selected else " "
            line   = f"{label}: {masked}"
            if i == selected:
                print(f"{prefix} {get_hl()}{BOLD}{line}{RESET}")
            else:
                print(f"{prefix} {line}")
            if delay_active:
                time.sleep(0.1)

        delay_active = False
        key = read_key()
        if key == "UP":
            selected = (selected - 1) % len(labels)
        elif key == "DOWN":
            selected = (selected + 1) % len(labels)
        elif key == "B":
            return
        elif key == "ENTER":
            view_password_flow(group_name, labels[selected])

def view_password_flow(group_name, label):
    global passkey

    if passkey is None:
        clear_screen()
        print(f"\n{RED}No passkey set. Create a passkey first.{RESET}")
        input(f"\nPress ENTER to go back.")
        return

    while True:
        clear_screen()
        section_header(f"[{group_name}] {label}")
        entered = get_masked_input("\nEnter passkey: ")

        if entered == passkey:
            break
        else:
            print(f"\n{RED}Incorrect passkey.{RESET}  R = Retry   B = Back to group view.")
            while True:
                key = read_key()
                if key == "R":
                    break
                elif key == "B":
                    return

    entry    = passwords.get(group_name, {}).get(label, {"password": "[Password not found]"})
    pwd      = entry["password"] if isinstance(entry, dict) else entry
    username = entry.get("username", "") if isinstance(entry, dict) else ""

    while True:
        clear_screen()
        section_header(f"[{group_name}] {label}")
        print(f"\nPassword: {get_hl()}{pwd}{RESET}")
        if username:
            print(f"User:     {get_hl()}{username}{RESET}")
        instruction("\nENTER = back to group view   B = back to main menu")
        key = read_key()
        if key == "ENTER":
            return
        elif key == "B":
            raise_back_to_menu()

def create_group_screen():
    clear_screen()
    section_header("New Group")

    group_name = themed_input("\nEnter new group name: ")

    if not group_name:
        print(f"\n{RED}Group name cannot be empty. The group was not created.{RESET}")
    elif group_name in passwords:
        print(f"\n{RED}Group '{group_name}' already exists.{RESET}")
    else:
        passwords[group_name] = {}
        save_data()
        success(f"\nGroup '{group_name}' created successfully!")

    input(f"\nPress ENTER to return to the main menu...")

def delete_group_screen():
    global passkey
    if not passwords:
        clear_screen()
        section_header("Delete Group")
        print(f"\n{RED}No Groups.{RESET}")
        input(f"\nPress ENTER to go back to the menu.")
        return

    selected     = 0
    delay_active = True

    while True:
        clear_screen()
        section_header("Delete Group")
        instruction("\nUse UP/DOWN to select, ENTER to delete, B to go back to the menu.\n")

        group_names = list(passwords.keys())
        if not group_names:
            print(f"{RED}No Groups.{RESET}")
            input(f"\nPress ENTER to go back to the menu.")
            return

        for i, group in enumerate(group_names):
            prefix = ">" if i == selected else " "
            count  = len(passwords.get(group, {}))
            line   = f"{group} ({count} passwords)"
            if i == selected:
                print(f"{prefix} {get_hl()}{BOLD}{line}{RESET}")
            else:
                print(f"{prefix} {line}")
            if delay_active:
                time.sleep(0.1)

        delay_active = False
        key = read_key()
        if key == "UP":
            selected = max(0, (selected - 1) % len(group_names))
        elif key == "DOWN":
            selected = (selected + 1) % len(group_names)
        elif key == "B":
            return
        elif key == "ENTER":
            delay_active    = True
            group_to_delete = group_names[selected]
            count           = len(passwords[group_to_delete])

            if passkey is None:
                print(f"\n{RED}No passkey set. Cannot authorize deletion.{RESET}")
                input("Press ENTER to go back...")
                continue

            entered = get_masked_input("\nPasskey: ")
            if entered != passkey:
                print(f"\n{RED}Incorrect passkey. Deletion cancelled.{RESET}")
                input("Press ENTER to go back...")
                continue

            print(f"\n{RED}WARNING:{RESET} Deleting '{get_hl()}{group_to_delete}{RESET}' will remove ALL {count} passwords inside it.")
            os.write(1, (
                f"Are you sure? (Y/{RED}N{RESET}): "
            ).encode())

            confirm_key = None
            while confirm_key not in ("Y", "N"):
                confirm_key = read_key()

            print(f"{confirm_key}")
            if confirm_key == 'Y':
                del passwords[group_to_delete]
                save_data()
                success(f"\nGroup '{group_to_delete}' and all its passwords have been deleted.")
                if selected >= len(passwords):
                    selected = max(0, selected - 1)
            else:
                print(f"\n{RED}Deletion cancelled.{RESET}")
                input("Press ENTER to continue...")
            if confirm_key == 'Y':
                continue

def select_group_for_password(entry, label):
    group_names = list(passwords.keys())
    if not group_names:
        print(f"\n{RED}No groups exist. You must create one now.{RESET}")
        new_group_name = themed_input("Enter a new group name to create: ")
        if new_group_name:
            passwords[new_group_name] = {}
            group_names = [new_group_name]
        else:
            print(f"{RED}Group creation cancelled. The password was not saved.{RESET}")
            return

    selected     = 0
    delay_active = True

    while True:
        clear_screen()
        section_header("Select Group")
        instruction(f"\nPassword for '{label}' will be stored in the selected group.")
        instruction("Use UP/DOWN to select, ENTER to confirm.\n")

        for i, group in enumerate(group_names):
            prefix = ">" if i == selected else " "
            if i == selected:
                print(f"{prefix} {get_hl()}{BOLD}{group}{RESET}")
            else:
                print(f"{prefix} {group}")
            if delay_active:
                time.sleep(0.1)

        delay_active = False
        key = read_key()
        if key == "UP":
            selected = (selected - 1) % len(group_names)
        elif key == "DOWN":
            selected = (selected + 1) % len(group_names)
        elif key == "ENTER":
            selected_group = group_names[selected]
            passwords[selected_group][label] = entry
            save_data()
            success(f"\nPassword '{label}' saved to group '{selected_group}'.")
            return

def create_password_screen():
    clear_screen()
    section_header("Create Password")

    if not passwords:
        print(f"\n{RED}No groups exist. Please use the 'New Group' option first.{RESET}")
        input("Press ENTER to return to the main menu...")
        return

    new_password = themed_input("\nCreate Password: ")
    if not new_password:
        print(f"\n{RED}Password cannot be empty. The password was not saved.{RESET}")
        input("Press ENTER to return to the main menu...")
        return

    username = themed_input("\nCreate Email/Username: ")

    label = themed_input("\nCreate Label: ")
    if not label:
        print(f"\n{RED}No label provided. The password was not saved.{RESET}")
        input(f"\nPress ENTER to return to the main menu...")
        return

    entry = {"password": new_password, "username": username}
    select_group_for_password(entry, label)
    input(f"\nPress ENTER to return to the main menu...")

def delete_password_screen():
    if not passwords:
        clear_screen()
        section_header("Delete Password")
        print(f"\n{RED}No groups or passwords exist yet.{RESET}")
        input(f"\nPress ENTER to go back to the menu.")
        return

    selected_group = 0
    delay_active   = True

    while True:
        group_names = list(passwords.keys())
        if not group_names:
            return

        clear_screen()
        section_header("Delete Password — Select Group")
        instruction("\nUse UP/DOWN to select a group, ENTER to view passwords for deletion, B to go back.\n")

        if selected_group >= len(group_names):
            selected_group = max(0, len(group_names) - 1)

        for i, group in enumerate(group_names):
            prefix = ">" if i == selected_group else " "
            count  = len(passwords.get(group, {}))
            line   = f"{group} ({count} passwords)"
            if i == selected_group:
                print(f"{prefix} {get_hl()}{BOLD}{line}{RESET}")
            else:
                print(f"{prefix} {line}")
            if delay_active:
                time.sleep(0.1)

        delay_active = False
        key = read_key()
        if key == "UP":
            selected_group = (selected_group - 1) % len(group_names)
        elif key == "DOWN":
            selected_group = (selected_group + 1) % len(group_names)
        elif key == "B":
            return
        elif key == "ENTER":
            delay_active = True
            delete_passwords_in_group(group_names[selected_group])

def delete_passwords_in_group(group_name):
    global passkey

    if group_name not in passwords or not passwords[group_name]:
        clear_screen()
        section_header(f"Group: {group_name}")
        print(f"\n{RED}This group is empty.{RESET}")
        input(f"\nPress ENTER to go back...")
        return

    selected     = 0
    delay_active = True

    while True:
        if group_name not in passwords or not passwords[group_name]:
            return

        clear_screen()
        section_header(f"Delete Password — Group: {group_name}")
        instruction("\nUse UP/DOWN to select, ENTER to delete, B to go back to groups.\n")

        labels = list(passwords[group_name].keys())
        if not labels:
            print(f"{RED}No passwords in this group.{RESET}")
            input(f"\nPress ENTER to go back...")
            return

        if selected >= len(labels):
            selected = max(0, len(labels) - 1)

        for i, label in enumerate(labels):
            masked = "*" * 10
            prefix = ">" if i == selected else " "
            line   = f"{label}: {masked}"
            if i == selected:
                print(f"{prefix} {get_hl()}{BOLD}{line}{RESET}")
            else:
                print(f"{prefix} {line}")
            if delay_active:
                time.sleep(0.1)

        delay_active = False
        key = read_key()
        if key == "UP":
            selected = (selected - 1) % len(labels)
        elif key == "DOWN":
            selected = (selected + 1) % len(labels)
        elif key == "B":
            return
        elif key == "ENTER":
            label_to_delete = labels[selected]

            if passkey is None:
                clear_screen()
                print(f"\n{RED}No passkey set. Cannot authorize deletion.{RESET}")
                input("Press ENTER to continue...")
                continue

            clear_screen()
            section_header(f"Confirm Deletion: {label_to_delete}")
            entered = get_masked_input("\nEnter passkey to confirm deletion: ")

            if entered != passkey:
                print(f"\n{RED}Incorrect passkey. Deletion cancelled.{RESET}")
                input("Press ENTER to continue...")
                continue

            del passwords[group_name][label_to_delete]
            save_data()
            success(f"\nPassword '{label_to_delete}' has been deleted.")
            input("Press ENTER to continue...")

            if not passwords[group_name]:
                return

def raise_back_to_menu():
    raise BackToMenu()

class BackToMenu(Exception):
    pass

def startup_create_passkey():
    global passkey
    clear_screen()
    section_header("First-Time Passkey Setup")
    instruction("\nYou must create a passkey to secure your stored passwords.")
    while passkey is None:
        new_pk = get_masked_input("\nEnter new passkey: ")
        if new_pk:
            passkey = new_pk
            save_data()
            success("\nPasskey successfully created.")
            input("Press ENTER to continue to the main menu...")
        else:
            print(f"{RED}Passkey cannot be empty. Please try again.{RESET}")

def change_passkey_screen():
    global passkey
    clear_screen()
    section_header("Change Passkey")

    if passkey is None:
        print(f"\n{RED}No existing passkey. A passkey should have been created on startup.{RESET}")
        input("Press ENTER to return to the main menu...")
        return

    old = get_masked_input("\nEnter existing passkey: ")
    if old != passkey:
        print(f"\n{RED}Incorrect passkey. Passkey change cancelled.{RESET}")
        input("Press ENTER to return to the main menu...")
        return

    new_pk = get_masked_input("\nEnter new passkey: ")
    if new_pk:
        passkey = new_pk
        success("\nPasskey successfully changed.")
        save_data()
    else:
        print(f"{RED}New passkey cannot be empty. The passkey was not changed.{RESET}")

    input("Press ENTER to return to the main menu...")

# --- Entry Point ---

if __name__ == "__main__":
    os.system("")   # Enable ANSI escape codes on Windows

    load_theme()    # Load theme first so unlock screen renders correctly
    load_data()     # Prompts for passkey if vault is encrypted

    if passkey is None:
        # Brand new vault — no data file yet, create passkey for the first time
        startup_create_passkey()

    while True:
        try:
            main_menu()
        except BackToMenu:
            continue
