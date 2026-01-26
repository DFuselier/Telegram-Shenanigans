import os
import subprocess
import time
import shutil

# MAIN MENU/SCRIPT LAUNCHER

def main():
    """
    Displays the main menu and runs the chosen script.
    """f
    ascii_art = r"""
====================================================================================
░▀█▀░█▀▀░░░█▀▀░█░█░█▀▀░▀█▀░█░░░█░░░█▀█░█▀▄░█▀▀
░░█░░█░█░░░█▀▀░█░█░▀▀█░░█░░█░░░█░░░█▀█░█░█░█▀▀
░░▀░░▀▀▀░░░▀░░░▀▀▀░▀▀▀░▀▀▀░▀▀▀░▀▀▀░▀░▀░▀▀░░▀▀▀                                        
fu·sil·lade /ˌfyo͞ozəˈläd/
noun
a series of shots (telegram accounts) fired simultaneously or in rapid succession      
@Donray Fuselier for any questions or concerns! 
===================================================================================      
    """
    print(ascii_art)
    
    print("Please choose a script to run:")
    print("  1: Open links from the first .txt file found")
    print("  2: Process and launch Telegram accounts")
    
    choice = input("Enter your choice (1 or 2): ")
    
    if choice == '1':
        links_file = find_first_txt_file()
        if links_file:
            open_links_from_file(links_file)
        else:
            print("\nError: No .txt file found in the current directory.")
    elif choice == '2':
        process_directories()
    else:
        print("\nInvalid choice. Please run the script again and enter 1 or 2.")
    
    print("\nScript finished.")

# SCRIPT 1: Open Links from File

def open_links_from_file(filename):
    """
    Reads a text file and opens each line in Firefox, hiding terminal output.
    """
    if not os.path.exists(filename):
        print(f"Error: The file '{filename}' was not found.")
        return

    with open(filename, 'r') as file:
        for line in file:
            url = line.strip()
            
            if url:
                print(f"Opening: {url}")
                command = f"firefox --new-tab {url}"
                
                subprocess.Popen(command, shell=True, 
                                 stdout=subprocess.DEVNULL, 
                                 stderr=subprocess.DEVNULL)
                
                time.sleep(0.5)

def find_first_txt_file():
    """
    Searches the current directory for the first file ending with .txt.
    Returns the filename if found, otherwise returns None.
    """
    for filename in os.listdir('.'):
        if filename.endswith(".txt"):
            print(f"Found text file: {filename}")
            return filename
    return None

# SCRIPT 2: Process and Launch Telegram Accounts

def process_directories():
    """
    Scans a parent directory for subdirectories, finds 'tdata' within them,
    creates Telegram instances, and moves the 'tdata' folders.
    """
    home_dir = os.path.expanduser('~')
    script_path = os.path.join(home_dir, 'Desktop', 'create_tg.sh')

    if not os.path.isfile(script_path):
        print(f"Error: Script not found at '{script_path}'")
        return

    parent_dir_path = input("Enter the path to the parent directory: ")

    if not os.path.isdir(parent_dir_path):
        print(f"Error: '{parent_dir_path}' is not a valid directory.")
        return

    dirs_to_process = [d for d in os.listdir(parent_dir_path) if os.path.isdir(os.path.join(parent_dir_path, d))]
    
    print(f"\nDEBUG: Found the following directories to process: {dirs_to_process}")

    if not dirs_to_process:
        print("No subdirectories found to process.")
        return

    dir_count = len(dirs_to_process)
    print(f"Found {dir_count} director(y/ies). Starting process...")
    print("-" * 40)

    for i, dirname in enumerate(dirs_to_process):
        print(f"\n--- LOOP {i+1} STARTING for directory: '{dirname}' ---")
        
        base_name = dirname
        current_subdir_path = os.path.join(parent_dir_path, dirname)
        
        print(f"({i+1}/{dir_count}) Creating instance for ID: {base_name}")
        subprocess.run([script_path, base_name])

        print(f"--> Searching for 'tdata' in '{dirname}'...")
        found_tdata_path = None
        
        for root, dirs, files in os.walk(current_subdir_path):
            if 'tdata' in dirs:
                found_tdata_path = os.path.join(root, 'tdata')
                break
        
        if found_tdata_path:
            print(f"--> 'tdata' found! Preparing to copy.")
            destination_path = f"/home/REDACTED/telegram_dir_{base_name}/.local/share/TelegramDesktop"
            
            if os.path.isdir(destination_path):
                shutil.rmtree(destination_path)
            os.makedirs(destination_path)

            shutil.copytree(found_tdata_path, os.path.join(destination_path, 'tdata'))
            print(f"--> Successfully copied 'tdata' for ID {base_name}.")
        else:
            print(f"--> Error: 'tdata' folder not found in '{dirname}'.")
        
        new_script_name = f"launch_tg_{base_name}.sh"
        if os.path.isfile(new_script_name):
            print(f"--> Launching: {new_script_name}")
            subprocess.Popen([f"./{new_script_name}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            print(f"--> Error: Could not find '{new_script_name}' to launch.")

        print(f"--- LOOP {i+1} FINISHED for directory: '{dirname}' ---")
        print("-" * 40)
        time.sleep(1)

    print("\nProcessing complete.")

# SCRIPT ENTRY POINT

if __name__ == "__main__":
    # This line at the bottom is what starts the whole script by calling the main menu.
    main()
