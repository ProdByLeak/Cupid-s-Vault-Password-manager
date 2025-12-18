import os
import msvcrt
import json
import time 

# --- Constants and Globals ---

ORANGE = "\033[38;5;208m"
LIGHT_BLUE = "\033[38;5;117m"
GREEN = "\033[32m"
RED = "\033[31m"
RESET = "\033[0m"
BOLD = "\033[1m"

CONSOLE_WIDTH = 100 
BANNER_LEFT_PAD = 28 

TABS = [
    "Passwords",
    "Create Password",
    "New Group",
    "Delete Group",
    "Delete Password",
    "Change Passkey",
]

passwords = {}
passkey = None
# Dynamically determine the absolute path for the data file
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(SCRIPT_DIR, "data.json") 

# --- Banner Setup (Unchanged) ---

gradient_colors = [(0, 100, 255), (100, 200, 255), (0, 100, 255)]

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

def interpolate_color(color1, color2, factor):
    r = int(color1[0] + (color2[0] - color1[0]) * factor)
    g = int(color1[1] + (color2[1] - color1[1]) * factor)
    b = int(color1[2] + (color2[2] - color1[2]) * factor)
    return (r, g, b)

def get_menu_padding_size():
    max_tab_length = max(len(tab) for tab in TABS)
    total_line_width = max_tab_length + 2
    padding_size = max(0, (CONSOLE_WIDTH // 2) - (total_line_width // 2)) + 7
    return padding_size

def create_gradient_banner():
    padding = " " * BANNER_LEFT_PAD 
    printable_lines = BANNER.strip('\n').split('\n')
    
    max_text_length = 0
    for line in printable_lines:
        if not line.strip():
            continue
        start_index = len(line) - len(line.lstrip())
        end_index = len(line.rstrip())
        current_text_length = end_index - start_index
        max_text_length = max(max_text_length, current_text_length)

    output = []
    
    for line in printable_lines:
        if not line.strip() and len(line) < 3:
            continue
            
        start_padding_len = len(line) - len(line.lstrip())
        start_padding = line[:start_padding_len]
        
        content = line.lstrip()
        colored_content = ""
        current_char_count = 0
        
        for char in content:
            if char.isspace():
                colored_content += char
                continue
            
            position = current_char_count / max_text_length
            r, g, b = interpolate_color(gradient_colors[0], gradient_colors[1], position)
            
            colored_content += color_text(char, r, g, b)
            current_char_count += 1
        
        output.append(f"{padding}{start_padding}{colored_content}{RESET}") 
        
    return '\n'.join(output) + '\n'

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


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
        print("\n[Warning: Arrow key functions disabled. Press ENTER, B, Y, N, R, or Q.]")
        while True:
            try:
                entered = input()
                if entered == '': return 'ENTER'
                if entered.lower() == 'b': return 'B'
                if entered.lower() == 'y': return 'Y'
                if entered.lower() == 'n': return 'N'
                if entered.lower() == 'r': return 'R'
                if entered.lower() == 'q': os._exit(0)
            except EOFError:
                pass

# Masked Input Function (Used only for Passkey entry)
def get_masked_input(prompt):
    """Handles masked user input (shows '*' instead of characters)."""
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
        print(f"\n[Warning: Masked input disabled. Use regular input.]")
        return input(prompt)


def save_data():
    data = {"passwords": passwords, "passkey": passkey}
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"\n{RED}*** CRITICAL SAVE ERROR ***{RESET}")
        print(f"Failed to write to file: {DATA_FILE}")
        print(f"Error details: {e}")
        input("Press ENTER to continue (Data was NOT saved)...")

def load_data():
    global passwords, passkey
    
    data = {"passwords": {}, "passkey": None}
    
    try:
        with open(DATA_FILE, "r") as f:
            if os.path.getsize(DATA_FILE) > 0:
                data = json.load(f)
                
        passwords.clear()
        passwords.update(data.get("passwords", {}))
        passkey = data.get("passkey", None)
        
        is_old_format = any(isinstance(v, str) for v in passwords.values()) and all(isinstance(k, str) for k in passwords.keys())
        
        if is_old_format and 'Default Group' not in passwords:
            temp_passwords = passwords.copy()
            passwords.clear()
            passwords["Default Group"] = temp_passwords
            save_data()
            
    except Exception as e:
        passwords.clear()
        passkey = None
        if os.path.exists(DATA_FILE):
             print(f"\n[{ORANGE}Warning{RESET}] Data file corrupt. Initializing new data state.")

def main_menu():
    selected = 0
    delay_active = True  
    
    padding_size = get_menu_padding_size()
    padding = " " * padding_size

    while True:
        clear_screen()
        
        print("\n")
        
        print(create_gradient_banner())
        
        print("\n\n") 
        
        for i, tab in enumerate(TABS):
            prefix = " " 
            
            if i == selected:
                print(f"{padding}{prefix} {LIGHT_BLUE}<{tab}>{RESET}")
            else:
                print(f"{padding}{prefix} {tab}")
                
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
            if tab_name == "Passwords":
                passwords_tab()
            elif tab_name == "Create Password":
                create_password_screen()
            elif tab_name == "New Group":
                create_group_screen()
            elif tab_name == "Delete Group":
                delete_group_screen()
            elif tab_name == "Delete Password":
                delete_password_screen()  # Now uses group-based navigation
            elif tab_name == "Change Passkey":
                change_passkey_screen()

def passwords_tab():
    if not passwords:
        clear_screen()
        print(BOLD + "Passwords" + RESET)
        print("\nNo groups or passwords saved yet.")
        print("\nPress B to go back to the Menu.")
        while True:
            key = read_key()
            if key == "B":
                return
        return

    group_names = list(passwords.keys())
    selected_group = 0
    delay_active = True 

    while True:
        group_names = list(passwords.keys())
        if not group_names:
            return

        clear_screen()
        print(BOLD + "Groups" + RESET)
        print("\nUse UP/DOWN to select, ENTER to open a group, B to go back to the Menu.\n")
        
        if selected_group >= len(group_names):
            selected_group = max(0, len(group_names) - 1)

        for i, group in enumerate(group_names):
            prefix = ">" if i == selected_group else " "
            count = len(passwords.get(group, {}))
            line = f"{group} ({count} passwords)"
            if i == selected_group:
                print(f"{prefix} {LIGHT_BLUE}{line}{RESET}")
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
            group_name = group_names[selected_group]
            view_group_passwords(group_name)

def view_group_passwords(group_name):
    if group_name not in passwords:
        return

    group_passwords = passwords.get(group_name, {})
    if not group_passwords:
        return 

    labels = list(group_passwords.keys())
    selected = 0
    delay_active = True 

    while True:
        if group_name not in passwords or not passwords[group_name]:
            return
            
        clear_screen()
        print(BOLD + f"Group: {group_name}" + RESET)
        print("\nUse UP/DOWN to select, ENTER to view a password, B to go back to groups.\n")
        
        labels = list(passwords[group_name].keys())
        if selected >= len(labels):
            selected = max(0, len(labels) - 1)

        for i, label in enumerate(labels):
            entry = group_passwords[label]
            pwd = entry["password"] if isinstance(entry, dict) else entry
            masked = "*" * len(pwd)
            prefix = ">" if i == selected else " "
            line = f"{label}: {masked}"
            if i == selected:
                print(f"{prefix} {LIGHT_BLUE}{line}{RESET}")
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
            label = labels[selected]
            view_password_flow(group_name, label)

def view_password_flow(group_name, label):
    global passkey
    
    if passkey is None:
        clear_screen()
        print("\nNo passkey set. Create a passkey first.")
        input("\nPress ENTER to go back.")
        return

    while True:
        clear_screen()
        print(BOLD + f"[{group_name}] {label}" + RESET) 
        
        entered = get_masked_input("\nEnter passkey: ")
        
        if entered == passkey:
            break
        else:
            print(f"\n{RED}Incorrect{RESET}. R = Retry, B = Back to group view.")
            while True:
                key = read_key()
                if key == "R":
                    break
                elif key == "B":
                    return
    
    entry = passwords.get(group_name, {}).get(label, {"password": "[Password not found]"})
    pwd = entry["password"] if isinstance(entry, dict) else entry
    username = entry.get("username", "") if isinstance(entry, dict) else ""
    
    while True:
        clear_screen()
        print(BOLD + f"[{group_name}] {label}" + RESET) 
        print(f"\nPassword: {LIGHT_BLUE}{pwd}{RESET}")
        if username:
            print(f"User: {LIGHT_BLUE}{username}{RESET}")
        print("\nENTER = back to group view")
        print("B = back to main menu")
        key = read_key()
        if key == "ENTER":
            return
        elif key == "B":
            raise_back_to_menu()

def create_group_screen():
    clear_screen()
    print(BOLD + "New Group" + RESET)
    
    group_name = input("\nEnter new group name: ")
    
    if not group_name:
        print("\nGroup name cannot be empty. The group was not created.")
    elif group_name in passwords:
        print(f"\nGroup '{group_name}' already exists.")
    else:
        passwords[group_name] = {}
        save_data()
        print(f"\nGroup '{group_name}' created successfully!")
        
    input("\nPress ENTER to return to the main menu...")
    return

def delete_group_screen():
    global passkey
    if not passwords:
        clear_screen()
        print(BOLD + "Delete Group" + RESET)
        print("\nNo Groups.")
        input("\nPress ENTER to go back to the menu.")
        return

    group_names = list(passwords.keys())
    selected = 0
    delay_active = True 

    while True:
        clear_screen()
        print(BOLD + "Delete Group" + RESET)
        print("\nUse UP/DOWN to select, ENTER to delete, B to go back to the menu.\n")
        
        group_names = list(passwords.keys())
        if not group_names:
            print("No Groups.")
            input("\nPress ENTER to go back to the menu.")
            return

        for i, group in enumerate(group_names):
            prefix = ">" if i == selected else " "
            count = len(passwords.get(group, {}))
            line = f"{group} ({count} passwords)"
            if i == selected:
                print(f"{prefix} {LIGHT_BLUE}{line}{RESET}")
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
            delay_active = True 
            group_to_delete = group_names[selected]
            count = len(passwords[group_to_delete])
            
            if passkey is None:
                print("\nNo passkey set. Cannot authorize deletion.")
                input("Press ENTER to go back...")
                continue
                
            entered = get_masked_input("\nPasskey: ")
            
            if entered != passkey:
                print("\nIncorrect passkey. Deletion cancelled.")
                input("Press ENTER to go back...")
                continue

            print(f"\nWARNING: Deleting '{LIGHT_BLUE}{group_to_delete}{RESET}' will delete ALL {count} passwords inside it.")
            
            os.write(1, f"Are you sure you want to delete {LIGHT_BLUE}{group_to_delete}{RESET}? ({GREEN}Y{RESET}/{RED}N{RESET}): ".encode())
            
            confirm_key = None
            while confirm_key not in ("Y", "N"):
                 confirm_key = read_key()
            
            print(f"{confirm_key}")
            
            if confirm_key == 'Y':
                del passwords[group_to_delete]
                save_data()
                print(f"\nGroup '{group_to_delete}' and all its passwords have been deleted.")
                if selected >= len(passwords):
                    selected = max(0, selected - 1)
            else:
                print("\nDeletion cancelled.")
                input("Press ENTER to continue...")
            if confirm_key == 'Y':
                continue

def select_group_for_password(entry, label):
    group_names = list(passwords.keys())
    if not group_names:
        print("\nNo groups exist. You must create one now.")
        new_group_name = input("Enter a new group name to create: ")
        if new_group_name:
            passwords[new_group_name] = {}
            group_names = [new_group_name]
        else:
            print("Group creation cancelled. The password was not saved.")
            return

    selected = 0
    delay_active = True 

    while True:
        clear_screen()
        print(BOLD + "Select Group" + RESET)
        print(f"\nPassword for '{label}' will be stored in the selected group.")
        print("Use UP/DOWN to select, ENTER to confirm.\n")

        for i, group in enumerate(group_names):
            prefix = ">" if i == selected else " "
            if i == selected:
                print(f"{prefix} {LIGHT_BLUE}{group}{RESET}")
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
            print(f"\nPassword '{label}' saved to group '{selected_group}'.")
            return

def create_password_screen():
    clear_screen()
    print(BOLD + "Create Password" + RESET)

    if not passwords:
        print("\nNo groups exist. Please use the 'New Group' option first.")
        input("Press ENTER to return to the main menu...")
        return
        
    new_password = input("Enter new password: ")
    
    if not new_password:
        print("\nPassword cannot be empty. The password was not saved.")
        input("Press ENTER to return to the main menu...")
        return
        
    print("\nWhat is this password for?")
    label = input("[label]: ")
    
    if not label:
        print("\nNo label provided. The password was not saved.")
        input("\nPress ENTER to return to the main menu...")
        return
    
    username = input("Create Email/Username: ")
    
    entry = {
        "password": new_password,
        "username": username
    }
    
    select_group_for_password(entry, label)
    
    input("\nPress ENTER to return to the main menu...")
    return

# NEW: Delete Password via Group Navigation
def delete_password_screen():
    if not passwords:
        clear_screen()
        print(BOLD + "Delete Password" + RESET)
        print("\nNo groups or passwords exist yet.")
        input("\nPress ENTER to go back to the menu.")
        return

    # Reuse the same group selection logic as passwords_tab()
    group_names = list(passwords.keys())
    selected_group = 0
    delay_active = True 

    while True:
        group_names = list(passwords.keys())
        if not group_names:
            return

        clear_screen()
        print(BOLD + "Delete Password - Select Group" + RESET)
        print("\nUse UP/DOWN to select a group, ENTER to view passwords for deletion, B to go back.\n")

        if selected_group >= len(group_names):
            selected_group = max(0, len(group_names) - 1)

        for i, group in enumerate(group_names):
            prefix = ">" if i == selected_group else " "
            count = len(passwords.get(group, {}))
            line = f"{group} ({count} passwords)"
            if i == selected_group:
                print(f"{prefix} {LIGHT_BLUE}{line}{RESET}")
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
            group_name = group_names[selected_group]
            delete_passwords_in_group(group_name)

def delete_passwords_in_group(group_name):
    global passkey

    if group_name not in passwords or not passwords[group_name]:
        clear_screen()
        print(BOLD + f"Group: {group_name}" + RESET)
        print("\nThis group is empty.")
        input("\nPress ENTER to go back...")
        return

    labels = list(passwords[group_name].keys())
    selected = 0
    delay_active = True

    while True:
        if group_name not in passwords or not passwords[group_name]:
            return

        clear_screen()
        print(BOLD + f"Delete Password - Group: {group_name}" + RESET)
        print("\nUse UP/DOWN to select, ENTER to delete, B to go back to groups.\n")

        labels = list(passwords[group_name].keys())
        if not labels:
            print("No passwords in this group.")
            input("\nPress ENTER to go back...")
            return

        if selected >= len(labels):
            selected = max(0, len(labels) - 1)

        for i, label in enumerate(labels):
            entry = passwords[group_name][label]
            pwd = entry["password"] if isinstance(entry, dict) else entry
            masked = "*" * len(pwd)
            prefix = ">" if i == selected else " "
            line = f"{label}: {masked}"
            if i == selected:
                print(f"{prefix} {LIGHT_BLUE}{line}{RESET}")
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
                print("\nNo passkey set. Cannot authorize deletion.")
                input("Press ENTER to continue...")
                continue

            clear_screen()
            print(BOLD + f"Confirm Deletion: {label_to_delete}" + RESET)
            entered = get_masked_input("\nEnter passkey to confirm deletion: ")

            if entered != passkey:
                print("\nIncorrect passkey. Deletion cancelled.")
                input("Press ENTER to continue...")
                continue

            del passwords[group_name][label_to_delete]
            save_data()

            print(f"\nPassword '{label_to_delete}' has been deleted.")
            input("Press ENTER to continue...")

            # Refresh list after deletion
            if not passwords[group_name]:
                return  # Go back if group is now empty

def raise_back_to_menu():
    raise BackToMenu()

class BackToMenu(Exception):
    pass

def startup_create_passkey():
    global passkey
    clear_screen()
    print(BOLD + "First-Time Passkey Setup" + RESET)
    print("\nYou must create a passkey to secure your stored passwords.")
    while passkey is None:
        new_pk = get_masked_input("\nEnter new passkey: ")
        if new_pk:
            passkey = new_pk
            save_data()
            print("\nPasskey successfully created.")
            input("Press ENTER to continue to the main menu...")
        else:
            print("\nPasskey cannot be empty. Please try again.")

def change_passkey_screen():
    global passkey
    clear_screen()
    print(BOLD + "Change Passkey" + RESET)

    if passkey is None:
        print("\nNo existing passkey. A passkey should have been created on startup.")
        input("Press ENTER to return to the main menu...")
        return

    old = get_masked_input("\nEnter existing passkey: ")
    
    if old != passkey:
        print("\nIncorrect passkey. Passkey change cancelled.")
        input("Press ENTER to return to the main menu...")
        return

    new_pk = get_masked_input("\nEnter new passkey: ")
    if new_pk:
        passkey = new_pk
        print("\nPasskey successfully changed.")
        save_data()
    else:
        print("\nNew passkey cannot be empty. The passkey was not changed.")

    input("Press ENTER to return to the main menu...")
    return

if __name__ == "__main__":
    os.system("") 
    
    load_data()
    
    if passkey is None:
        startup_create_passkey()
        
    while True:
        try:
            main_menu()
        except BackToMenu:
            continue
