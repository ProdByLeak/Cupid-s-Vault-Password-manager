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
    # Fallback for non-Windows systems where msvcrt is unavailable
    try:
        if os.name != 'nt':
            raise ImportError
            
        import sys
        
        sys.stdout.write(prompt)
        sys.stdout.flush()

        input_list = []
        while True:
            char = msvcrt.getch()
            
            # Enter key (ASCII 13 or \r)
            if char in (b'\r', b'\n'):
                sys.stdout.write('\n')
                break
                
            # Backspace key (ASCII 8 or \x08)
            elif char == b'\x08':
                if input_list:
                    # Erase character: backspace, space, backspace
                    sys.stdout.write('\b \b')
                    sys.stdout.flush()
                    input_list.pop()
                    
            # Extended key code (e.g., arrow keys, F-keys). 
            elif char in (b'\xe0', b'\x00'):
                msvcrt.getch() # Consume the second byte and ignore the sequence entirely.
                
            # Any other single-byte character that is printable
            elif char:
                try:
                    char_str = char.decode()
                    if char_str.isprintable() and len(char_str) == 1:
                        sys.stdout.write('*')
                        sys.stdout.flush()
                        input_list.append(char_str) 
                except UnicodeDecodeError:
                    # Ignore bytes that can't be decoded as a printable char
                    pass
                
        return "".join(input_list)
        
    except ImportError:
        # Fallback for non-Windows or if msvcrt import fails
        print(f"\n[Warning: Masked input disabled. Use regular input.]")
        return input(prompt)


def save_data():
    """Writes the current passwords and passkey to the unencrypted JSON data file."""
    data = {"passwords": passwords, "passkey": passkey}
    try:
        # Use DATA_FILE which now points to the absolute path
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        # DO NOT FAIL SILENTLY: Print the error to debug the file system issue
        print(f"\n{RED}*** CRITICAL SAVE ERROR ***{RESET}")
        print(f"Failed to write to file: {DATA_FILE}")
        print(f"Error details: {e}")
        input("Press ENTER to continue (Data was NOT saved)...")


def load_data():
    """
    Attempts to load data from the JSON file. If any error occurs, initializes clean data.
    """
    global passwords, passkey
    
    # 1. Default assumption: clean slate
    data = {"passwords": {}, "passkey": None}
    
    # 2. Attempt to load the file
    try:
        # Use DATA_FILE which now points to the absolute path
        with open(DATA_FILE, "r") as f:
            # Check if file is non-empty before attempting JSON load
            if os.path.getsize(DATA_FILE) > 0:
                data = json.load(f)
            else:
                # Treat empty file as an error that needs fixing
                raise ValueError("Data file is empty.")
                
        # 3. Successful load: apply data
        passwords.clear()
        passwords.update(data.get("passwords", {}))
        passkey = data.get("passkey", None)
        
        # Backward compatibility check: convert old {label: password} structure to new group structure
        is_old_format = any(isinstance(v, str) for v in passwords.values()) and all(isinstance(k, str) for k in passwords.keys())
        
        if is_old_format and 'Default Group' not in passwords:
            temp_passwords = passwords.copy()
            passwords.clear()
            passwords["Default Group"] = temp_passwords
            # Save immediately to ensure new structure is used
            save_data()
            
    except Exception as e:
        # 4. Error handling (File Not Found, JSON Decode Error, Empty File, etc.)
        # Clear in-memory data
        passwords.clear()
        passkey = None
        
        # Log the error and prompt user (only if the file actually existed but was corrupt)
        if os.path.exists(DATA_FILE):
             print(f"\n[{ORANGE}Warning{RESET}] Data file corrupt. Initializing new data state.")


def main_menu():
    selected = 0
    delay_active = True  # Flag to control the delayed draw
    
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
                time.sleep(0.1)  # Delay runs only when delay_active is True
        
        delay_active = False # Disable delay after the first draw or redraw from a sub-menu

        key = read_key()
        if key == "UP":
            selected = (selected - 1) % len(TABS)
        elif key == "DOWN":
            selected = (selected + 1) % len(TABS)
        elif key == "ENTER":
            # Re-enable the delay flag when returning from a function call
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
                delete_password_screen()
            elif tab_name == "Change Passkey":
                change_passkey_screen()
        
        # If UP/DOWN pressed, we loop back up and delay_active is False, so no sleep occurs.


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
        # Check if the list of groups is empty after returning from a sub-operation
        group_names = list(passwords.keys())
        if not group_names:
            return  # Go back to main_menu if all groups were deleted

        clear_screen()
        print(BOLD + "Groups" + RESET)
        print("\nUse UP/DOWN to select, ENTER to open a group, B to go back to the Menu.\n")
        
        # Ensure selected_group index is safe
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
    # Check if the group was deleted while we were navigating back
    if group_name not in passwords:
        return

    group_passwords = passwords.get(group_name, {})
    if not group_passwords:
        # If the group is empty (e.g. all passwords deleted), return to group view
        return 

    labels = list(group_passwords.keys())
    selected = 0
    delay_active = True 

    while True:
        # Check if the group still exists and is not empty
        if group_name not in passwords or not passwords[group_name]:
            return
            
        clear_screen()
        print(BOLD + f"Group: {group_name}" + RESET)
        print("\nUse UP/DOWN to select, ENTER to view a password, B to go back to groups.\n")
        
        # Refresh labels list and adjust index
        labels = list(passwords[group_name].keys())
        if selected >= len(labels):
            selected = max(0, len(labels) - 1)

        for i, label in enumerate(labels):
            masked = "*" * len(group_passwords[label])
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
        
        # MASKED INPUT for Passkey
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
    
    pwd = passwords.get(group_name, {}).get(label, "[Password not found]")
    while True:
        clear_screen()
        print(BOLD + f"[{group_name}] {label}" + RESET) 
        print(f"\nPassword: {LIGHT_BLUE}{pwd}{RESET}\n")
        print("ENTER = back to group view")
        print("B = back to main menu")
        key = read_key()
        if key == "ENTER":
            return
        elif key == "B":
            raise_back_to_menu()


def create_group_screen():
    clear_screen()
    print(BOLD + "New Group" + RESET)
    
    # Regular INPUT for Group Name
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
                
            # MASKED INPUT for Passkey
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


def select_group_for_password(new_password, label):
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
            passwords[selected_group][label] = new_password
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
        
    # --- CHANGE START ---
    # REGULAR INPUT: Allows the user to see the characters they are typing for the new password.
    new_password = input("Enter new password: ")
    # --- CHANGE END ---
    
    if not new_password:
        print("\nPassword cannot be empty. The password was not saved.")
        input("Press ENTER to return to the main menu...")
        return
        
    print("\nWhat is this password for?")
    # Regular INPUT for Label
    label = input("[label]: ")
    
    if label:
        select_group_for_password(new_password, label)
    else:
        print("\nNo label provided. The password was not saved.")
    
    input("\nPress ENTER to return to the main menu...")
    return


def delete_password_screen():
    global passkey
    all_passwords = {}
    for group, items in passwords.items():
        for label in items:
            all_passwords[f"[{group}] {label}"] = (group, label)

    if not all_passwords:
        clear_screen()
        print(BOLD + "Delete Password" + RESET)
        print("\nNo Passwords.")
        input("\nPress ENTER to go back to the menu.")
        return

    display_labels = list(all_passwords.keys())
    selected = 0
    delay_active = True 

    while True:
        clear_screen()
        print(BOLD + "Delete Password" + RESET)
        print("\nUse UP/DOWN to select, ENTER to delete, B to go back to the menu.\n")
        
        all_passwords = {}
        for group, items in passwords.items():
            for label in items:
                all_passwords[f"[{group}] {label}"] = (group, label)

        display_labels = list(all_passwords.keys())

        if not display_labels:
            print("No Passwords.")
            input("\nPress ENTER to go back to the menu.")
            return

        for i, disp_label in enumerate(display_labels):
            prefix = ">" if i == selected else " "
            line = f"{disp_label}"
            if i == selected:
                print(f"{prefix} {LIGHT_BLUE}{line}{RESET}")
            else:
                print(f"{prefix} {line}")

            if delay_active: 
                time.sleep(0.1)

        delay_active = False 

        key = read_key()
        if key == "UP":
            selected = max(0, (selected - 1) % len(display_labels))
        elif key == "DOWN":
            selected = (selected + 1) % len(display_labels)
        elif key == "B":
            return
        elif key == "ENTER":
            delay_active = True 
            disp_label_to_delete = display_labels[selected]
            group_name, label_to_delete = all_passwords[disp_label_to_delete]
            
            if passkey is None:
                print("\nNo passkey set. Cannot authorize deletion.")
                input("Press ENTER to go back...")
                continue
                
            # MASKED INPUT for Passkey
            entered = get_masked_input("\nPasskey: ")
            
            if entered != passkey:
                print("\nIncorrect passkey. Deletion cancelled.")
                input("Press ENTER to go back...")
                continue
            
            del passwords[group_name][label_to_delete]
            
            if not passwords[group_name]:
                print(f"\nDeleted: {label_to_delete}. Group '{group_name}' is now empty.")
            else:
                print(f"\nDeleted: {label_to_delete} from group: {group_name}")
            
            save_data()
            
            if selected >= len(display_labels) - 1:
                selected = max(0, selected - 1)
            
            continue


def raise_back_to_menu():
    raise BackToMenu()


class BackToMenu(Exception):
    pass


def startup_create_passkey():
    """Handles the initial creation of the passkey and GUARANTEES data.json is created."""
    global passkey
    clear_screen()
    print(BOLD + "First-Time Passkey Setup" + RESET)
    print("\nYou must create a passkey to secure your stored passwords.")
    while passkey is None:
        # MASKED INPUT for New Passkey
        new_pk = get_masked_input("\nEnter new passkey: ")
        if new_pk:
            passkey = new_pk
            # CRITICAL FIX: Call save_data() here to create the file immediately
            save_data()
            print("\nPasskey successfully created.")
            # The previous file creation status prompt is now removed.
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

    # MASKED INPUT for Existing Passkey
    old = get_masked_input("\nEnter existing passkey: ")
    
    if old != passkey:
        print("\nIncorrect passkey. Passkey change cancelled.")
        input("Press ENTER to return to the main menu...")
        return

    # MASKED INPUT for New Passkey
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
    # This call initializes VT100/ANSI support on Windows
    os.system("") 
    
    # 1. Attempt to load existing data (which sets passkey=None if file is missing/corrupt)
    load_data()
    
    # 2. If passkey is None (first run or corruption), go to startup menu
    if passkey is None:
        startup_create_passkey()
        
    # 3. Start main loop
    while True:
        try:
            main_menu()
        except BackToMenu:
            continue