import subprocess
import os
import sys
import os
from PyQt5.QtCore import QCoreApplication

base_dir = os.path.dirname(os.path.abspath(sys.executable))

plugin_path = os.path.join(base_dir, 'Lib', 'site-packages', 'PyQt5', 'Qt5', 'plugins')

QCoreApplication.addLibraryPath(plugin_path)
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
import shutil
from QuantEngineLIB import *
import requests
import json
import re
import time
from mctools import RCONClient
from PIL import Image as PILImage
import random
import threading
import queue
import psutil
import pywinstyles

# Convert PIL Image to QPixmap
def pil_to_pixmap(pil_image):
    pil_image = pil_image.convert("RGBA")
    data = pil_image.tobytes("raw", "RGBA")
    qimage = QImage(data, pil_image.width, pil_image.height, QImage.Format_RGBA8888)
    return QPixmap.fromImage(qimage)
    
gamemode_str_to_num = {'survival': '0', 'creative': '1', 'adventure': '2', 'spectator': '3'}
gamemode_num_to_str = {'0': 'survival', '1': 'creative', '2': 'adventure', '3': 'spectator'}
difficulty_str_to_num = {'peaceful': '0', 'easy': '1', 'normal': '2', 'hard': '3'}
difficulty_num_to_str = {'0': 'peaceful', '1': 'easy', '2': 'normal', '3': 'hard'}

def is_numeric_version(version):
    parts = version.split('-')[0]
    nums = parts.split('.')
   
    if len(nums) < 2:
        return True
   
    minor = int(nums[1])
    return minor < 14
    
def get_java_path(version):
    parts = version.split('-')[0]
    nums = parts.split('.')
   
    if version in ["1.16.1", "1.16.4"]:
        base_dir = "System\\jdk8u462"
    else:
        if len(nums) < 2:
            base_dir = "System\\jdk8u462"
        else:
            major = int(nums[0])
            minor_str = nums[1]
           
            if '-' in minor_str:
                minor_str = minor_str.split('-')[0]
           
            minor = int(minor_str)
           
            if 19 <= minor <= 21:
                base_dir = "System\\jdk-21"
            elif minor == 18:
                base_dir = "System\\jdk-17.0.16"
            elif minor == 17 or minor == 16 or minor == 15:
                base_dir = "System\\jdk-16.0.2"
            else:
                base_dir = "System\\jdk8u462"
   
    return os.path.abspath(os.path.join(base_dir, "bin", "java.exe"))

paper_versions_file = "System\\Paper_versions.json"
defaults = {
    "allow-flight": "false",
    "allow-nether": "true",
    "difficulty": "easy",
    "enable-command-block": "true",
    "enable-rcon": "true",
    "gamemode": "survival",
    "hardcore": "false",
    "max-players": "20",
    "online-mode": "false",
    "pvp": "true",
    "rcon.port": "25579",
    "server-port": "25565",
    "spawn-protection": "0",
    "view-distance": "10"
}

def get_yml_value(file_path, key):
    if not os.path.exists(file_path):
        return 'disabled'
   
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                stripped = line.strip()
               
                if stripped.startswith(key + ':'):
                    value = stripped.split(':', 1)[1].strip().split()[0]
                    return value
    except Exception as e:
        print(f"Error reading yml: {e}")
   
    return 'disabled'

def update_yml(file_path, key, value):
    if not os.path.exists(file_path):
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(f"{key}: {value}\n")
       
        return
   
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
       
        for i, line in enumerate(lines):
            stripped = line.strip()
           
            if stripped.startswith(key + ':'):
                indent = len(line) - len(line.lstrip())
                lines[i] = ' ' * indent + f"{key}: {value}\n"
                break
        else:
            lines.append(f"{key}: {value}\n")
       
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
    except Exception as e:
        print(f"Error updating yml: {e}")

def Download_paper(version, destination_folder="."):
    try:
        with open(paper_versions_file, 'r', encoding='utf-8') as f:
            versions_data = json.load(f)
       
        if version not in versions_data['versions']:
            print(f"Version {version} not found in available versions")
            msg("Minecraft version error", "Critical error", "error")
            return
       
        url = versions_data['versions'][version]
        filename = os.path.basename(url)
       
        response = requests.get(url, stream=True)
        response.raise_for_status()
       
        file_path = os.path.join(destination_folder, filename)
       
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
       
        print(f"File downloaded to {file_path}")
    except FileNotFoundError:
        print(f"File {paper_versions_file} not found")
        msg("Error downloading server core", "Critical error", "error")
    except requests.exceptions.RequestException as e:
        print(f"Download error: {e}")
        msg("Error downloading server core", "Critical error", "error")
    except Exception as e:
        print(f"Failed to download file: {e}")
        msg("Error downloading server core", "Critical error", "error")

system_dir = "System"
servers_dir = os.path.join(system_dir, "Servers")
os.makedirs(servers_dir, exist_ok=True)
with open(paper_versions_file, 'r', encoding='utf-8') as f:
    versions_data = json.load(f)
versions_list = list(versions_data['versions'].keys())
latest_version = versions_data['latest']
versions_list_modded = ['1.21.1', '1.20.4', '1.20.2', '1.20.1', '1.19.2', '1.18.2', '1.17.1', '1.16.5']
versions_list_modded_display = [v + '-forge' for v in versions_list_modded]
latest_version_modded = '1.21.1'
latest_version_modded_display = latest_version_modded + '-forge'

def _on_mousewheel(event):
    canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

def process_exists(pid):
    try:
        output = subprocess.check_output(f'tasklist /fi "PID eq {pid}"').decode('utf-8')
        return str(pid) in output
    except:
        return False

def is_server_running(server_path):
    active_file = os.path.join(server_path, 'Active.tmp')
   
    if not os.path.exists(active_file):
        return False
   
    with open(active_file, 'r') as f:
        pid_str = f.read().strip()
   
    if not pid_str.isdigit():
        os.remove(active_file)
        return False
   
    pid = int(pid_str)
   
    if process_exists(pid):
        return True
    else:
        os.remove(active_file)
        return False

def escape_property(value):
    value = value.replace('\\', '\\\\').replace('\t', '\\t').replace('\r', '\\r').replace('\n', '\\n')
    value = ''.join(c if ord(c) < 128 else f'\\u{ord(c):04x}' for c in value)
    return value

def unescape_property(value):
    value = value.replace('\\t', '\t').replace('\\r', '\r').replace('\\n', '\n').replace('\\\\', '\\')
   
    def unicode_repl(m):
        return chr(int(m.group(1), 16))
   
    value = re.sub(r'\\u([0-9a-fA-F]{4})', unicode_repl, value)
    return value

def update_properties(properties_path, updates):
    if os.path.exists(properties_path):
        with open(properties_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
       
        for key, value in updates.items():
            escaped_value = escape_property(str(value))
            found = False
           
            for i, line in enumerate(lines):
                if line.strip().startswith(key + '='):
                    lines[i] = f"{key}={escaped_value}\n"
                    found = True
                    break
           
            if not found:
                lines.append(f"{key}={escaped_value}\n")
       
        with open(properties_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
    else:
        with open(properties_path, 'w', encoding='utf-8') as f:
            for key, value in updates.items():
                escaped_value = escape_property(str(value))
                f.write(f"{key}={escaped_value}\n")

def add_plugin(server_path):
    plugins_dir = os.path.join(server_path, 'plugins')
    os.makedirs(plugins_dir, exist_ok=True)
   
    file_paths = QFileDialog.getOpenFileNames(window, "Select plugin", "", "JAR files (*.jar)")[0]
   
    invalid = any(os.path.abspath(os.path.dirname(fp)) == os.path.abspath(plugins_dir) for fp in file_paths)
   
    if invalid:
        msg("This plugin is already on the server", "Error", "error")
        return
   
    for file_path in file_paths:
        shutil.copy2(file_path, plugins_dir)
   
    if file_paths:
        msg("Plugin(s) added", "Info", "info")

def remove_plugin(server_path):
    font3 = QFont()
    font3.setFamily("Play")
    font3.setPointSize(12)
    font3.setBold(True)
    font3.setWeight(75)
   
    plugins_dir = os.path.join(server_path, 'plugins')
   
    if not os.path.exists(plugins_dir):
        msg("Plugins directory does not exist", "Error", "error")
        return
   
    jar_files = [f for f in os.listdir(plugins_dir) if f.endswith('.jar')]
   
    dialog = QDialog(window)
    dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
    dialog.setWindowTitle("Remove plugin")
    dialog.setStyleSheet("background-color: #121214; color: white;")
    dialog.setFixedSize(300, 400)
   
    layout = QVBoxLayout()
   
    list_widget = QListWidget()
    list_widget.setSelectionMode(QAbstractItemView.MultiSelection)
   
    for jar in jar_files:
        list_widget.addItem(jar)
   
    layout.addWidget(list_widget)
   
    btn_layout = QHBoxLayout()
   
    delete_btn = QPushButton("Remove")
    delete_btn.setFont(font3)
    delete_btn.setStyleSheet("background-color: #2a2a2e; color: white; width: 100px;")
    delete_btn.setCursor(QCursor(Qt.PointingHandCursor))
   
    def delete_selected():
        selected = list_widget.selectedItems()
       
        if not selected:
            return
       
        file_paths = [os.path.join(plugins_dir, item.text()) for item in selected]
       
        for fp in file_paths:
            os.remove(fp)
       
        if file_paths:
            msg("Plugin(s) removed", "Info", "info")
       
        dialog.accept()
   
    delete_btn.clicked.connect(delete_selected)
   
    back_btn = QPushButton("Back")
    back_btn.setStyleSheet("background-color: #2a2a2e; color: white; width: 100px;")
    back_btn.setFont(font3)
    back_btn.setCursor(QCursor(Qt.PointingHandCursor))
    back_btn.clicked.connect(dialog.reject)
   
    btn_layout.addWidget(delete_btn)
    btn_layout.addWidget(back_btn)
   
    layout.addLayout(btn_layout)
   
    dialog.setLayout(layout)
    dialog.exec_()

def add_mod(server_path):
    mods_dir = os.path.join(server_path, 'mods')
    os.makedirs(mods_dir, exist_ok=True)
   
    file_paths = QFileDialog.getOpenFileNames(window, "Select mod", "", "JAR files (*.jar)")[0]
   
    invalid = any(os.path.abspath(os.path.dirname(fp)) == os.path.abspath(mods_dir) for fp in file_paths)
   
    if invalid:
        msg("Cannot add mod from server mods directory", "Error", "error")
        return
   
    for file_path in file_paths:
        shutil.copy2(file_path, mods_dir)
   
    if file_paths:
        msg("Mod(s) added", "Info", "info")

def remove_mod(server_path):
    font3 = QFont()
    font3.setFamily("Play")
    font3.setPointSize(12)
    font3.setBold(True)
    font3.setWeight(75)
   
    mods_dir = os.path.join(server_path, 'mods')
   
    if not os.path.exists(mods_dir):
        msg("Mods directory does not exist", "Error", "error")
        return
   
    jar_files = [f for f in os.listdir(mods_dir) if f.endswith('.jar')]
   
    dialog = QDialog(window)
    dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
    dialog.setWindowTitle("Remove mod")
    dialog.setStyleSheet("background-color: #121214; color: white;")
    dialog.setFixedSize(300, 400)
   
    layout = QVBoxLayout()
   
    list_widget = QListWidget()
    list_widget.setSelectionMode(QAbstractItemView.MultiSelection)
   
    for jar in jar_files:
        list_widget.addItem(jar)
   
    layout.addWidget(list_widget)
   
    btn_layout = QHBoxLayout()
   
    delete_btn = QPushButton("Remove")
    delete_btn.setFont(font3)
    delete_btn.setStyleSheet("background-color: #2a2a2e; color: white; width: 100px;")
    delete_btn.setCursor(QCursor(Qt.PointingHandCursor))
   
    def delete_selected():
        selected = list_widget.selectedItems()
       
        if not selected:
            return
       
        file_paths = [os.path.join(mods_dir, item.text()) for item in selected]
       
        for fp in file_paths:
            os.remove(fp)
       
        if file_paths:
            msg("Mod(s) removed", "Info", "info")
       
        dialog.accept()
   
    delete_btn.clicked.connect(delete_selected)
   
    back_btn = QPushButton("Back")
    back_btn.setStyleSheet("background-color: #2a2a2e; color: white; width: 100px;")
    back_btn.setFont(font3)
    back_btn.setCursor(QCursor(Qt.PointingHandCursor))
    back_btn.clicked.connect(dialog.reject)
   
    btn_layout.addWidget(delete_btn)
    btn_layout.addWidget(back_btn)
   
    layout.addLayout(btn_layout)
   
    dialog.setLayout(layout)
    dialog.exec_()

def open_server_folder(server_path):
    subprocess.Popen(f'explorer "{server_path}"')

def change_icon(server_path):
    world_dir = os.path.join(server_path, 'world')
    os.makedirs(world_dir, exist_ok=True)
   
    file_path = QFileDialog.getOpenFileName(window, "Select icon", "", "PNG files (*.png)")[0]
   
    if file_path:
        img = PILImage.open(file_path)
        img = img.resize((64, 64), PILImage.Resampling.LANCZOS)
        img.save(os.path.join(world_dir, 'icon.png'))
        msg("Icon changed", "Info", "info")

def upload_world(server_path):
    world_dir = QFileDialog.getExistingDirectory(window, "Select world directory")
   
    if world_dir:
        server_world = os.path.join(server_path, 'world')
       
        if os.path.exists(server_world):
            shutil.rmtree(server_world)
       
        shutil.copytree(world_dir, server_world)
        msg("World uploaded", "Info", "info")

def custom_askstring(title, prompt, **kwargs):
    dialog = QDialog(window)
    dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
   
    font3 = QFont()
    font3.setFamily("Play")
    font3.setPointSize(12)
    font3.setBold(True)
    font3.setWeight(75)
   
    dialog.setWindowTitle(title)
    dialog.setWindowIcon(QIcon(r'System/Textures/icon_base.ico'))
    dialog.setStyleSheet("background-color: #121214;")
    dialog.setFixedSize(300, 150)
   
    layout = QVBoxLayout()
   
    label = QLabel(prompt)
    label.setFont(font3)
    label.setStyleSheet("color: white;")
    layout.addWidget(label)
   
    entry = QLineEdit()
    entry.setStyleSheet("background-color: #2a2a2e; color: white;")
   
    if 'show' in kwargs and kwargs['show'] == '*':
        entry.setEchoMode(QLineEdit.Password)
   
    layout.addWidget(entry)
   
    btn_layout = QHBoxLayout()
   
    ok_btn = QPushButton("OK")
    ok_btn.setStyleSheet("background-color: #2a2a2e; color: white; width: 100px;")
    ok_btn.setFont(font3)
    ok_btn.setCursor(QCursor(Qt.PointingHandCursor))
    ok_btn.clicked.connect(dialog.accept)
   
    cancel_btn = QPushButton("Cancel")
    cancel_btn.setFont(font3)
    cancel_btn.setStyleSheet("background-color: #2a2a2e; color: white; width: 100px;")
    cancel_btn.setCursor(QCursor(Qt.PointingHandCursor))
    cancel_btn.clicked.connect(dialog.reject)
   
    btn_layout.addWidget(ok_btn)
    btn_layout.addWidget(cancel_btn)
   
    layout.addLayout(btn_layout)
   
    dialog.setLayout(layout)
   
    if dialog.exec_() == QDialog.Accepted:
        set_dark_window_color(dialog)
        return entry.text()
   
    return None

def delete_server(server_path, properties_path, server):
    prop = {}
   
    if os.path.exists(properties_path):
        with open(properties_path, 'r', encoding='utf-8') as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    k, v = line.strip().split('=', 1)
                    prop[k.strip()] = unescape_property(v.strip())
   
    password = custom_askstring("Server password", "Enter password to delete:", show='*')
   
    if password is None:
        return
   
    if password != prop.get('rcon.password', ''):
        msg("Incorrect password", "Error", "error")
        return
   
    font3 = QFont()
    font3.setFamily("Play")
    font3.setPointSize(12)
    font3.setBold(True)
    font3.setWeight(75)
   
    msgbox = QMessageBox(window)
    msgbox.setWindowFlags(msgbox.windowFlags() & ~Qt.WindowContextHelpButtonHint)
    msgbox.setWindowTitle("Confirm deletion")
    msgbox.setText(f"Are you sure you want to delete server '{server}'?\nThis action is irreversible!")
    msgbox.setFont(font3)
    msgbox.setStyleSheet("color: rgb(255, 255, 255);")
    msgbox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    msgbox.setDefaultButton(QMessageBox.No)
   
    reply = msgbox.exec_()
   
    if reply == QMessageBox.Yes:
        shutil.rmtree(server_path)
        msg("Server deleted", "Info", "info")
        back_to_selection()

def show_server_selection():
    global servers_label, scroll_frame, canvas, scrollbar, scrollable_frame, current_screen, button_frame
   
    current_screen = "selection"
   
    servers = [d for d in os.listdir(servers_dir) if os.path.isdir(os.path.join(servers_dir, d))]
   
    clear_window()
   
    centralwidget = QWidget()
    centralwidget.setStyleSheet("background-color: rgb(22, 28, 33); color: rgb(255, 255, 255);")
   
    topmenu = QLabel(centralwidget)
    topmenu.setGeometry(QRect(0, 0, 801, 91))
    topmenu.setStyleSheet("background-color: rgb(45, 57, 67);")
   
    textmain = QLabel(centralwidget)
    textmain.setGeometry(QRect(0, 5, 800, 71))
    font = QFont()
    font.setFamily("Play")
    font.setPointSize(36)
    font.setBold(True)
    font.setWeight(75)
    textmain.setFont(font)
    textmain.setStyleSheet("background-color: rgb(45, 57, 67);")
    textmain.setAlignment(Qt.AlignCenter)
    textmain.setText(" ConstructorMC")
   
    text2 = QLabel(centralwidget)
    text2.setGeometry(QRect(0, 95, 781, 21))
    font = QFont()
    font.setFamily("Play")
    font.setPointSize(14)
    font.setBold(True)
    font.setWeight(75)
    text2.setFont(font)
    text2.setAlignment(Qt.AlignBottom | Qt.AlignHCenter)
    text2.setText("Your servers:")
   
    createbutton = QPushButton(centralwidget)
    createbutton.setGeometry(QRect(670, 100, 100, 30))
   
    font = QFont()
    font.setFamily("Play")
    font.setPointSize(12)
    font.setBold(True)
    font.setWeight(75)
   
    createbutton.setFont(font)
    createbutton.setStyleSheet("""background-color: rgb(43, 135, 211); border-radius: 5px;""")
    createbutton.setText("+ Create")
    createbutton.clicked.connect(show_create_type_selection)
    createbutton.setCursor(QCursor(Qt.PointingHandCursor))
   
    server_scroll = QScrollArea(centralwidget)
    server_scroll.setGeometry(QRect(35, 130, 765, 470))
    server_scroll.setWidgetResizable(True)
    server_scroll.setFrameStyle(QScrollArea.NoFrame)
    server_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
   
    servers_container = QWidget()
   
    servers_layout = QVBoxLayout(servers_container)
    servers_layout.setSpacing(29)
    servers_layout.setAlignment(Qt.AlignTop)
   
    for i, server in enumerate(servers):
        server_path = os.path.join(servers_dir, server)
        running = is_server_running(server_path)
       
        modded_marker = os.path.join(server_path, 'modded.txt')
        is_modded = os.path.exists(modded_marker)
       
        version_ini = os.path.join(server_path, 'version.ini')
       
        if os.path.exists(version_ini):
            with open(version_ini, 'r') as f:
                version = f.read().strip()
        else:
            version = "Unknown"
       
        version_text = version + "-forge" if is_modded else version
       
        world_dir = os.path.join(server_path, 'world')
        icon_path = os.path.join(world_dir, 'icon.png')
       
        if os.path.exists(icon_path):
            img = PILImage.open(icon_path)
        else:
            if os.path.exists(default_icon):
                img = PILImage.open(default_icon)
            else:
                img = PILImage.new('RGB', (64, 64), color='gray')
       
        img = img.resize((64, 64), PILImage.Resampling.LANCZOS)
        pixmap = pil_to_pixmap(img)
       
        status_pixmap = QPixmap("System/Textures/on.png" if running else "System/Textures/off.png")
       
        server_item = QWidget()
        server_item.setFixedHeight(81)
        server_item.setMaximumWidth(321)
        server_item.setCursor(QCursor(Qt.PointingHandCursor))
        server_item.setStyleSheet("color: rgb(255, 255, 255); background-color: rgb(45, 57, 67); border-radius: 5px;")
       
        iconserver = QLabel(server_item)
        iconserver.setGeometry(QRect(10, 10, 64, 64))
        iconserver.setStyleSheet("background-color: rgb(45, 57, 67);")
        iconserver.setPixmap(pixmap)
        iconserver.setScaledContents(True)
       
        servername = QLabel(server_item)
        servername.setGeometry(QRect(80, 10, 201, 30))
        font = QFont()
        font.setFamily("Play")
        font.setPointSize(14)
        font.setBold(True)
        font.setWeight(75)
        servername.setFont(font)
        servername.setStyleSheet("color: rgb(255, 255, 255); background-color: rgb(45, 57, 67);")
        servername.setText(server)
       
        versionserver = QLabel(server_item)
        versionserver.setGeometry(QRect(80, 45, 71, 20))
        font = QFont()
        font.setPointSize(10)
        versionserver.setFont(font)
        versionserver.setStyleSheet("color: rgb(255, 255, 255); background-color: rgb(45, 57, 67);")
        versionserver.setText(version_text)
       
        statusico = QLabel(server_item)
        statusico.setGeometry(QRect(275, 25, 32, 32))
        statusico.setPixmap(status_pixmap)
        statusico.setScaledContents(True)
       
        server_item.mousePressEvent = lambda event, s=server: show_server_menu(s) if event.button() == Qt.LeftButton else None
        servers_layout.addWidget(server_item)
    servers_layout.addStretch()
    server_scroll.setWidget(servers_container)
    window.setCentralWidget(centralwidget)
monitored_servers = []
monitoring_after_id = None
rcon_after_ids = {}

def monitor_all_servers():
    global monitoring_after_id
   
    to_remove = []
   
    for server in monitored_servers:
        server_path = os.path.join(servers_dir, server)
       
        if not is_server_running(server_path):
            to_remove.append(server)
           
            if current_screen == "server_menu" and current_server == server:
                refresh_server_menu(server)
   
    for s in to_remove:
        monitored_servers.remove(s)
   
    if monitored_servers:
        monitoring_after_id = QTimer.singleShot(1000, monitor_all_servers)
    else:
        monitoring_after_id = None

def monitor_server_status(server):
    if server not in monitored_servers:
        monitored_servers.append(server)
   
    if monitoring_after_id is None and monitored_servers:
        monitor_all_servers()

def refresh_server_menu(server):
    show_server_menu(current_server)

def rename_server(server):
    global current_server
   
    old_path = os.path.join(servers_dir, server)
   
    new_name = custom_askstring("Rename", "Enter new server name:")
   
    if new_name is None:
        return
   
    invalid_chars = r'\/|:"*<>'
   
    if any(c in invalid_chars for c in new_name):
        msg("Invalid characters in server name", "Error", "error")
        return
   
    if len(new_name) > 16:
        msg("Server name cannot exceed 16 characters", "Error", "error")
        return
   
    new_path = os.path.join(servers_dir, new_name)
   
    if os.path.exists(new_path):
        msg("Server with this name already exists", "Error", "error")
        return
   
    os.rename(old_path, new_path)
   
    batch_path = os.path.join(new_path, 'start.bat')
   
    with open(batch_path, 'r', encoding='utf-8') as f:
        content = f.read()
   
    content = content.replace(f'title {server}', f'title {new_name}')
    content = content.replace(f'cd /d "{old_path}"', f'cd /d "{new_path}"')
   
    with open(batch_path, 'w', encoding='utf-8') as f:
        f.write(content)
   
    settings_title.setText(f"Server settings \"{new_name}\"")
   
    current_server = new_name
   
    msg("Name changed", "Info", "info")
   
    refresh_server_menu(server)

def rcon_check_thread(server_path, properties_path):
    prop = {}
   
    if os.path.exists(properties_path):
        with open(properties_path, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip() or line.strip().startswith('#'): continue
               
                if '=' in line:
                    k, v = line.strip().split('=', 1)
                    prop[k] = unescape_property(v)
   
    if prop.get('enable-rcon', 'false') != 'true':
        return False
   
    port = int(prop.get('rcon.port', '25575'))
    password = prop.get('rcon.password', '')
   
    if not password:
        return False
   
    try:
        rcon = RCONClient("127.0.0.1", port=port, timeout=0.5)
       
        if rcon.login(password):
            rcon.stop()
            return True
    except:
        pass
   
    return False

def check_rcon(server_path, properties_path, server):
    if not is_server_running(server_path):
        return
   
    q = queue.Queue()
   
    def thread_target():
        result = rcon_check_thread(server_path, properties_path)
        q.put(result)
   
    thread = threading.Thread(target=thread_target)
    thread.start()
   
    def check_queue():
        try:
            result = q.get_nowait()
           
            if result:
                if status_label and current_screen == "server_menu":
                    status_label.setText("Server is running properly")
                    status_label.setStyleSheet("font: 12pt Arial; color: green; background-color: rgb(45, 57, 67);")
            else:
                rcon_after_ids[server] = QTimer.singleShot(1000, lambda: check_rcon(server_path, properties_path, server))
           
            thread.join()
        except queue.Empty:
            rcon_after_ids[server] = QTimer.singleShot(500, check_queue)
   
    rcon_after_ids[server] = QTimer.singleShot(500, check_queue)

def show_server_menu(server):
    global gamemode_var, difficulty_var, allow_nether_var, allow_flight_var, enable_command_block_var, max_players_var, online_mode_var, pvp_var, server_port_var, hardcore_var, xmx_var, motd_var, anti_xray_var, settings_title, settings_frame, button_frame, warning_label, plugin_btn, icon_btn, delete_btn, upload_btn, unsaved_label, warning_label2, version_label, mod_btn, remove_plugin_btn, remove_mod_btn, open_folder_btn, status_label, view_distance_var, current_screen, current_server, centralwidget
   
    current_screen = "server_menu"
    current_server = server
   
    server_path = os.path.join(servers_dir, server)
    properties_path = os.path.join(server_path, 'server.properties')
    batch_path = os.path.join(server_path, 'start.bat')
    yml_file = os.path.join(server_path, 'config', 'paper-world-defaults.yml')
   
    modded_marker = os.path.join(server_path, 'modded.txt')
    is_modded = os.path.exists(modded_marker)
   
    block_file = os.path.join(server_path, 'users.json')
    is_blocked = os.path.exists(block_file)
   
    jar_files = [f for f in os.listdir(server_path) if f.endswith('.jar')]
   
    if not jar_files:
        msg("No jar file found", "Error", "error")
        show_server_selection()
        return
   
    jar = jar_files[0]
    running = is_server_running(server_path)
   
    prop = {}
   
    if os.path.exists(properties_path):
        with open(properties_path, 'r', encoding='utf-8') as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    prop[key] = unescape_property(value)
   
    version_ini = os.path.join(server_path, 'version.ini')
    version = "Unknown"
   
    if os.path.exists(version_ini):
        with open(version_ini, 'r') as f:
            version = f.read().strip()
   
    needs_numeric = is_numeric_version(version)
   
    gamemode = prop.get('gamemode', defaults['gamemode'])
   
    if needs_numeric and gamemode in gamemode_num_to_str:
        gamemode_var = gamemode_num_to_str[gamemode]
    else:
        gamemode_var = gamemode if gamemode in gamemode_str_to_num else 'survival'
   
    difficulty = prop.get('difficulty', defaults['difficulty'])
   
    if needs_numeric and difficulty in difficulty_num_to_str:
        difficulty_var = difficulty_num_to_str[difficulty]
    else:
        difficulty_var = difficulty if difficulty in difficulty_str_to_num else 'easy'
   
    allow_nether_var = prop.get('allow-nether', defaults['allow-nether']) == 'true'
    allow_flight_var = prop.get('allow-flight', defaults['allow-flight']) == 'true'
    enable_command_block_var = prop.get('enable-command-block', defaults['enable-command-block']) == 'true'
    max_players_var = prop.get('max-players', defaults['max-players'])
    online_mode_var = prop.get('online-mode', defaults['online-mode']) == 'true'
    pvp_var = prop.get('pvp', defaults['pvp']) == 'true'
    server_port_var = prop.get('server-port', defaults['server-port'])
    hardcore_var = prop.get('hardcore', defaults['hardcore']) == 'true'
    motd_var = prop.get('motd', server)
    view_distance_var = int(prop.get('view-distance', defaults['view-distance']))
   
    with open(batch_path, 'r', encoding='utf-8') as f:
        content = f.read()
   
    match = re.search(r'-Xmx(\d+)M', content)
    xmx_var = int(match.group(1)) if match else 4096
   
    if not is_modded:
        anti_xray_var = get_yml_value(yml_file, 'enabled') == 'true'
   
    clear_window()
   
    centralwidget = QWidget()
    centralwidget.setStyleSheet("background-color: rgb(22, 28, 33); color: rgb(255, 255, 255);")
   
    settingslabel = QLabel(centralwidget)
    settingslabel.setGeometry(QRect(35, 30, 731, 531))
    font = QFont()
    font.setPointSize(8)
    settingslabel.setFont(font)
    settingslabel.setStyleSheet("color: rgb(255, 255, 255); background-color: rgb(45, 57, 67); border-radius: 5px;")
   
    settings_title = QLabel(centralwidget)
    settings_title.setGeometry(QRect(40, 35, 721, 30))
    font = QFont()
    font.setFamily("Play")
    font.setPointSize(14)
    font.setBold(True)
    font.setWeight(75)
    settings_title.setFont(font)
    settings_title.setStyleSheet("color: rgb(255, 255, 255); background-color: rgb(45, 57, 67);")
    settings_title.setAlignment(Qt.AlignCenter)
    settings_title.setText(f"Server settings \"{server}\"")
   
    back_btn1 = QPushButton(centralwidget)
    back_btn1.setGeometry(QRect(35, 30, 100, 30))
    back_btn1.setFont(font)
    back_btn1.setStyleSheet("background-color: rgb(43, 135, 211); border-radius: 5px;")
    back_btn1.setText("Back")
    back_btn1.clicked.connect(show_server_selection)
    back_btn1.setCursor(QCursor(Qt.PointingHandCursor))
   
    window.setCentralWidget(centralwidget)
   
    version_label = QLabel(centralwidget)
    version_label.setGeometry(QRect(40, 70, 721, 20))
    font = QFont()
    font.setPointSize(10)
    version_label.setFont(font)
    version_label.setStyleSheet("color: rgb(255, 255, 255); background-color: rgb(45, 57, 67);")
    version_label.setAlignment(Qt.AlignCenter)
    version_label.setText(f"Version: {version}" + ("-forge" if is_modded else ""))
    netherallow = QCheckBox(centralwidget)
    netherallow.setGeometry(QRect(110, 240, 131, 16))
    font = QFont()
    font.setFamily("Play")
    font.setPointSize(10)
    font.setBold(True)
    font.setWeight(75)
   
    netherallow.setFont(font)
    netherallow.setStyleSheet("color: rgb(255, 255, 255); background-color: rgb(45, 57, 67);")
    netherallow.setIconSize(QSize(16, 16))
    netherallow.setChecked(allow_nether_var)
    netherallow.setTristate(False)
    netherallow.setText("Allow Nether")
   
    flyallow = QCheckBox(centralwidget)
    flyallow.setGeometry(QRect(110, 220, 131, 16))
    flyallow.setFont(font)
    flyallow.setStyleSheet("color: rgb(255, 255, 255); background-color: rgb(45, 57, 67);")
    flyallow.setIconSize(QSize(16, 16))
    flyallow.setChecked(allow_flight_var)
    flyallow.setTristate(False)
    flyallow.setText("Allow flight")
   
    ram = QSlider(centralwidget)
    ram.setGeometry(QRect(520, 328, 171, 20))
    font = QFont()
    font.setBold(False)
    font.setWeight(50)
    ram.setFont(font)
    ram.setStyleSheet("color: rgb(255, 255, 255); background-color: rgb(45, 57, 67); border-radius: 5px;")
    ram.setMinimum(512)
   
    max_ram = psutil.virtual_memory().total // (1024 * 1024)
    ram.setMaximum(max_ram)
    ram.setValue(xmx_var)
    ram.setOrientation(Qt.Horizontal)
    ram_text = QLabel(centralwidget)
    ram_text.setGeometry(QRect(360, 320, 141, 31))
    font = QFont()
    font.setFamily("Play")
    font.setPointSize(10)
    ram_text.setFont(font)
    ram_text.setStyleSheet("color: rgb(255, 255, 255); background-color: rgb(45, 57, 67);")
    ram_text.setText("Max memory (MB):")
   
    chunks_distance = QSlider(centralwidget)
    chunks_distance.setGeometry(QRect(520, 371, 171, 20))
    chunks_distance.setFont(font)
    chunks_distance.setStyleSheet("color: rgb(255, 255, 255); background-color: rgb(45, 57, 67); border-radius: 5px;")
    chunks_distance.setMinimum(8)
    chunks_distance.setMaximum(32)
    chunks_distance.setValue(view_distance_var)
    chunks_distance.setOrientation(Qt.Horizontal)
   
    chunks_text = QLabel(centralwidget)
    chunks_text.setGeometry(QRect(360, 363, 161, 31))
    chunks_text.setFont(font)
    chunks_text.setStyleSheet("color: rgb(255, 255, 255); background-color: rgb(45, 57, 67);")
    chunks_text.setText("Chunk view distance:")
   
    ram_value_label = QLabel(centralwidget)
    ram_value_label.setGeometry(QRect(700, 320, 61, 31))
    ram_value_label.setFont(font)
    ram_value_label.setStyleSheet("color: rgb(255, 255, 255); background-color: rgb(45, 57, 67);")
    ram_value_label.setText(str(xmx_var))
    ram.valueChanged.connect(lambda value: ram_value_label.setText(str(value)))
   
    chunks_value_label = QLabel(centralwidget)
    chunks_value_label.setGeometry(QRect(700, 363, 61, 31))
    chunks_value_label.setFont(font)
    chunks_value_label.setStyleSheet("color: rgb(255, 255, 255); background-color: rgb(45, 57, 67);")
    chunks_value_label.setText(str(view_distance_var))
    chunks_distance.valueChanged.connect(lambda value: chunks_value_label.setText(str(value)))
   
    open_folder_btn = QPushButton(centralwidget)
   
    if is_modded:
        open_folder_btn.setGeometry(QRect(90, 460, 141, 31))
    else:
        open_folder_btn.setGeometry(QRect(160, 460, 141, 31))
   
    font = QFont()
    font.setFamily("Play")
    font.setPointSize(12)
    font.setBold(True)
    font.setWeight(75)
    open_folder_btn.setFont(font)
    open_folder_btn.setStyleSheet("border-radius: 5px;")
    open_folder_btn.setText("Open folder")
    open_folder_btn.clicked.connect(lambda: open_server_folder(server_path))
    open_folder_btn.setCursor(QCursor(Qt.PointingHandCursor))
   
    delete_btn = QPushButton(centralwidget)
   
    if is_modded:
        delete_btn.setGeometry(QRect(90, 410, 141, 31))
    else:
        delete_btn.setGeometry(QRect(160, 410, 141, 31))
   
    delete_btn.setFont(font)
    delete_btn.setStyleSheet("background-color: #F62451; border-radius: 5px;")
    delete_btn.setText("Delete server")
    delete_btn.clicked.connect(lambda: delete_server(server_path, properties_path, server))
    delete_btn.setCursor(QCursor(Qt.PointingHandCursor))
   
    gamemode_text = QLabel(centralwidget)
    gamemode_text.setGeometry(QRect(470, 132, 100, 31))
    gamemode_text.setFont(font)
    gamemode_text.setStyleSheet("color: rgb(255, 255, 255); background-color: rgb(45, 57, 67);")
    gamemode_text.setText("Game mode:")
   
    combobox = QComboBox(centralwidget)
    combobox.setGeometry(QRect(610, 140, 69, 22))
    combobox.addItem("survival")
    combobox.addItem("adventure")
    combobox.addItem("spectator")
    combobox.addItem("creative")
    combobox.setCurrentText(gamemode_var)
   
    difficulty_choice = QComboBox(centralwidget)
    difficulty_choice.setGeometry(QRect(610, 170, 69, 22))
    difficulty_choice.addItem("peaceful")
    difficulty_choice.addItem("easy")
    difficulty_choice.addItem("normal")
    difficulty_choice.addItem("hard")
    difficulty_choice.setCurrentText(difficulty_var)
   
    difficulty_text = QLabel(centralwidget)
    difficulty_text.setGeometry(QRect(470, 162, 125, 31))
    difficulty_text.setFont(font)
    difficulty_text.setStyleSheet("color: rgb(255, 255, 255); background-color: rgb(45, 57, 67);")
    difficulty_text.setText("Difficulty:")
   
    if is_modded:
        mod_btn = QPushButton(centralwidget)
        mod_btn.setGeometry(QRect(570, 460, 141, 31))
        mod_btn.setFont(font)
        mod_btn.setStyleSheet("border-radius: 5px;")
        mod_btn.setText("Add mod")
        mod_btn.clicked.connect(lambda: add_mod(server_path))
        mod_btn.setCursor(QCursor(Qt.PointingHandCursor))
       
        remove_mod_btn = QPushButton(centralwidget)
        remove_mod_btn.setGeometry(QRect(570, 510, 141, 31))
        remove_mod_btn.setFont(font)
        remove_mod_btn.setStyleSheet("border-radius: 5px;")
        remove_mod_btn.setText("Remove mod")
        remove_mod_btn.clicked.connect(lambda: remove_mod(server_path))
        remove_mod_btn.setCursor(QCursor(Qt.PointingHandCursor))
   
    icon_btn = QPushButton(centralwidget)
    if is_modded:
        icon_btn.setGeometry(QRect(250, 460, 141, 31))
    else:
        icon_btn.setGeometry(QRect(320, 460, 141, 31))
    icon_btn.setFont(font)
    icon_btn.setStyleSheet("border-radius: 5px;")
    icon_btn.setText("Change icon")
    icon_btn.clicked.connect(lambda: change_icon(server_path))
    icon_btn.setCursor(QCursor(Qt.PointingHandCursor))
   
    upload_btn = QPushButton(centralwidget)
    if is_modded:
        upload_btn.setGeometry(QRect(250, 510, 141, 31))
    else:
        upload_btn.setGeometry(QRect(320, 510, 141, 31))
    upload_btn.setFont(font)
    upload_btn.setStyleSheet("border-radius: 5px;")
    upload_btn.setText("Upload world")
    upload_btn.clicked.connect(lambda: upload_world(server_path))
    upload_btn.setCursor(QCursor(Qt.PointingHandCursor))
   
    plugin_btn = QPushButton(centralwidget)
    if is_modded:
        plugin_btn.setGeometry(QRect(410, 460, 141, 31))
    else:
        plugin_btn.setGeometry(QRect(480, 460, 141, 31))
    plugin_btn.setFont(font)
    plugin_btn.setStyleSheet("border-radius: 5px;")
    plugin_btn.setText("Add plugin")
    plugin_btn.clicked.connect(lambda: add_plugin(server_path))
    plugin_btn.setCursor(QCursor(Qt.PointingHandCursor))
   
    remove_plugin_btn = QPushButton(centralwidget)
    if is_modded:
        remove_plugin_btn.setGeometry(QRect(410, 510, 141, 31))
    else:
        remove_plugin_btn.setGeometry(QRect(480, 510, 141, 31))
    remove_plugin_btn.setFont(font)
    remove_plugin_btn.setStyleSheet("border-radius: 5px;")
    remove_plugin_btn.setText("Remove plugin")
    remove_plugin_btn.clicked.connect(lambda: remove_plugin(server_path))
    remove_plugin_btn.setCursor(QCursor(Qt.PointingHandCursor))
   
    rename_btn = QPushButton(centralwidget)
    if is_modded:
        rename_btn.setGeometry(QRect(90, 510, 141, 31))
    else:
        rename_btn.setGeometry(QRect(160, 510, 141, 31))
    rename_btn.setFont(font)
    rename_btn.setStyleSheet("border-radius: 5px;")
    rename_btn.setText("Rename")
    rename_btn.clicked.connect(lambda: rename_server(server))
    rename_btn.setCursor(QCursor(Qt.PointingHandCursor))
    pass_btn = QPushButton(centralwidget)
    if is_modded:
        pass_btn.setGeometry(QRect(330, 410, 141, 31))
    else:
        pass_btn.setGeometry(QRect(320, 410, 141, 31))
    pass_btn.setFont(font)
    pass_btn.setStyleSheet("border-radius: 5px;")
    pass_btn.setText("Change password")
    pass_btn.clicked.connect(lambda: change_password(server))
    rename_btn.setCursor(QCursor(Qt.PointingHandCursor))
   
    save_btn = QPushButton(centralwidget)
    if is_modded:
        save_btn.setGeometry(QRect(570, 410, 141, 31))
    else:
        save_btn.setGeometry(QRect(480, 410, 141, 31))
    save_btn.setFont(font)
    save_btn.setStyleSheet("border-radius: 5px; background-color: #1FD78D;")
    save_btn.setText("Save")
    save_btn.clicked.connect(lambda: save_settings(server_path, properties_path, batch_path, yml_file, version, is_modded, combobox.currentText(), difficulty_choice.currentText(), netherallow.isChecked(), flyallow.isChecked(), commandallow.isChecked(), lineedit.text(), not piratka_check.isChecked(), pvp_check.isChecked(), lineedit_2.text(), hardcore_check.isChecked(), motd_entry.text(), ram.value(), chunks_distance.value(), anti_xray_check.isChecked() if not is_modded else None))
    save_btn.setCursor(QCursor(Qt.PointingHandCursor))
   
    start_stop_btn = QPushButton(centralwidget)
    start_stop_btn.setGeometry(QRect(330, 100, 141, 31))
    start_stop_btn.setFont(font)
    start_stop_btn.setStyleSheet("border-radius: 5px;")
   
    if running:
        start_stop_btn.setText("Stop server")
        start_stop_btn.clicked.connect(lambda: stop_with_ui(server_path, properties_path, server))
    else:
        start_stop_btn.setText("Start server")
        start_stop_btn.clicked.connect(lambda: start_server(batch_path, server_path, server, is_modded))
   
    start_stop_btn.setCursor(QCursor(Qt.PointingHandCursor))
   
    unsaved_label = QLabel(centralwidget)
    unsaved_label.setGeometry(QRect(200, 570, 440, 20))
    unsaved_label.setStyleSheet("font: 12pt Arial; color: yellow;")
    unsaved_label.setText("Settings not saved. Click 'Save'")
    unsaved_label.hide()
   
    max_players_text = QLabel(centralwidget)
    max_players_text.setGeometry(QRect(110, 320, 121, 31))
    font = QFont()
    font.setFamily("Play")
    font.setPointSize(10)
    max_players_text.setFont(font)
    max_players_text.setStyleSheet("color: rgb(255, 255, 255); background-color: rgb(45, 57, 67);")
    max_players_text.setText("Max players:")
   
    lineedit = QLineEdit(centralwidget)
    lineedit.setGeometry(QRect(230, 327, 113, 20))
    lineedit.setMaxLength(4)
    lineedit.setText(max_players_var)
   
    server_port_text = QLabel(centralwidget)
    server_port_text.setGeometry(QRect(110, 360, 121, 31))
    server_port_text.setFont(font)
    server_port_text.setStyleSheet("color: rgb(255, 255, 255); background-color: rgb(45, 57, 67);")
    server_port_text.setText("Server port:")
   
    lineedit_2 = QLineEdit(centralwidget)
    lineedit_2.setGeometry(QRect(230, 367, 113, 20))
    lineedit_2.setMaxLength(5)
    lineedit_2.setText(server_port_var)
   
    server_motd_text = QLabel(centralwidget)
    server_motd_text.setGeometry(QRect(110, 285, 121, 31))
    server_motd_text.setFont(font)
    server_motd_text.setStyleSheet("color: rgb(255, 255, 255); background-color: rgb(45, 57, 67);")
    server_motd_text.setText("Server MOTD:")
   
    motd_entry = QLineEdit(centralwidget)
    motd_entry.setGeometry(QRect(230, 290, 113, 20))
    motd_entry.setText(motd_var)
   
    commandallow = QCheckBox(centralwidget)
    commandallow.setGeometry(QRect(110, 180, 195, 16))
    font = QFont()
    font.setFamily("Play")
    font.setPointSize(10)
    font.setBold(True)
    commandallow.setFont(font)
    commandallow.setStyleSheet("color: rgb(255, 255, 255); background-color: rgb(45, 57, 67);")
    commandallow.setChecked(enable_command_block_var)
    commandallow.setTristate(False)
    commandallow.setText("Enable command blocks")
   
    piratka_check = QCheckBox(centralwidget)
    piratka_check.setGeometry(QRect(110, 140, 150, 16))
    piratka_check.setFont(font)
    piratka_check.setStyleSheet("color: rgb(255, 255, 255); background-color: rgb(45, 57, 67);")
    piratka_check.setIconSize(QSize(16, 16))
    piratka_check.setChecked(not online_mode_var)
    piratka_check.setTristate(False)
    piratka_check.setText("Cracked Minecraft")
   
    pvp_check = QCheckBox(centralwidget)
    pvp_check.setGeometry(QRect(110, 160, 131, 16))
    pvp_check.setFont(font)
    pvp_check.setStyleSheet("color: rgb(255, 255, 255); background-color: rgb(45, 57, 67);")
    pvp_check.setIconSize(QSize(16, 16))
    pvp_check.setChecked(pvp_var)
    pvp_check.setTristate(False)
    pvp_check.setText("Allow PVP")
   
    hardcore_check = QCheckBox(centralwidget)
    hardcore_check.setGeometry(QRect(110, 200, 131, 16))
    hardcore_check.setFont(font)
    hardcore_check.setStyleSheet("color: rgb(255, 255, 255);background-color: rgb(45, 57, 67);")
    hardcore_check.setIconSize(QSize(16, 16))
    hardcore_check.setChecked(hardcore_var)
    hardcore_check.setTristate(False)
    hardcore_check.setText("Hardcore")
   
    if not is_modded:
        anti_xray_check = QCheckBox(centralwidget)
        anti_xray_check.setGeometry(QRect(110, 260, 131, 16))
        anti_xray_check.setFont(font)
        anti_xray_check.setStyleSheet("color: rgb(255, 255, 255); background-color: rgb(45, 57, 67);")
        anti_xray_check.setIconSize(QSize(16, 16))
        anti_xray_check.setChecked(anti_xray_var)
        anti_xray_check.setTristate(False)
        anti_xray_check.setText("Anti Xray")
   
    def on_change():
        unsaved_label.show()
   
    combobox.currentIndexChanged.connect(on_change)
    difficulty_choice.currentIndexChanged.connect(on_change)
    netherallow.stateChanged.connect(on_change)
    flyallow.stateChanged.connect(on_change)
    commandallow.stateChanged.connect(on_change)
    lineedit.textChanged.connect(on_change)
    piratka_check.stateChanged.connect(on_change)
    pvp_check.stateChanged.connect(on_change)
    lineedit_2.textChanged.connect(on_change)
    hardcore_check.stateChanged.connect(on_change)
    motd_entry.textChanged.connect(on_change)
    ram.valueChanged.connect(on_change)
    chunks_distance.valueChanged.connect(on_change)
   
    if not is_modded:
        anti_xray_check.stateChanged.connect(on_change)
   
    if running:
        ram_value_label.hide()
        chunks_value_label.hide()
        combobox.hide()
        gamemode_text.hide()
        difficulty_text.hide()
        difficulty_choice.hide()
        netherallow.hide()
        flyallow.hide()
        commandallow.hide()
        lineedit.hide()
        piratka_check.hide()
        pvp_check.hide()
        lineedit_2.hide()
        hardcore_check.hide()
        motd_entry.hide()
        ram.hide()
        chunks_distance.hide()
        unsaved_label.hide()
        max_players_text.hide()
        server_port_text.hide()
        server_motd_text.hide()
        ram_text.hide()
        chunks_text.hide()
        rename_btn.hide()
        pass_btn.hide()
        save_btn.hide()
        open_folder_btn.hide()
        delete_btn.hide()
       
        if is_modded:
            mod_btn.hide()
            remove_mod_btn.hide()
       
        icon_btn.hide()
        upload_btn.hide()
        plugin_btn.hide()
        remove_plugin_btn.hide()
       
        if not is_modded:
            anti_xray_check.hide()
       
        save_btn.hide()
        rename_btn.hide()
       
        warning_label = QLabel(centralwidget)
        warning_label.setGeometry(QRect(40, 140, 721, 20))
        warning_label.setStyleSheet("font: 14pt Arial; color: white; background-color: rgb(45, 57, 67);")
        warning_label.setText("Cannot change server settings while running!")
        warning_label.setAlignment(Qt.AlignCenter)
       
        warning_label2 = QLabel(centralwidget)
        warning_label2.setGeometry(QRect(40, 170, 721, 20))
        warning_label2.setStyleSheet("font: 12pt Arial; color: white; background-color: rgb(45, 57, 67);")
        warning_label2.setText("Program can be closed, server runs separately")
        warning_label2.setAlignment(Qt.AlignCenter)
       
        status_label = QLabel(centralwidget)
        status_label.setGeometry(QRect(40, 200, 721, 20))
        status_label.setStyleSheet("font: 12pt Arial; color: yellow; background-color: rgb(45, 57, 67);")
        status_label.setText("Loading server. Please wait...")
        status_label.setAlignment(Qt.AlignCenter)
       
        check_rcon(server_path, properties_path, server)
        monitor_server_status(server)
   
    if is_blocked:
        combobox.setEnabled(False)
        commandallow.setChecked(False)
        commandallow.setEnabled(False)
       
        if not is_modded:
            anti_xray_check.setChecked(True)
            anti_xray_check.setEnabled(False)
   
    window.setCentralWidget(centralwidget)

def change_password(server):
    global current_server
    server_path = os.path.join(servers_dir, server)
    properties_path = os.path.join(server_path, 'server.properties')
    prop = {}
    if os.path.exists(properties_path):
        with open(properties_path, 'r', encoding='utf-8') as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    prop[key] = unescape_property(value)
    current_pass = prop.get('rcon.password', '')
    dialog = QDialog(window)
    dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
    dialog.setWindowTitle("Change server password")
    dialog.setStyleSheet("background-color: #121214; color: white;")
    dialog.setFixedSize(300, 250)
    layout = QVBoxLayout()
    font3 = QFont()
    font3.setFamily("Play")
    font3.setPointSize(12)
    font3.setBold(True)
    font3.setWeight(75)
    label_current = QLabel("Enter current password:")
    label_current.setFont(font3)
    label_current.setStyleSheet("color: white;")
    layout.addWidget(label_current)
    entry_current = QLineEdit()
    entry_current.setStyleSheet("background-color: #2a2a2e; color: white;")
    entry_current.setEchoMode(QLineEdit.Password)
    layout.addWidget(entry_current)
    label_new = QLabel("Enter new password:")
    label_new.setFont(font3)
    label_new.setStyleSheet("color: white;")
    layout.addWidget(label_new)
    entry_new = QLineEdit()
    entry_new.setStyleSheet("background-color: #2a2a2e; color: white;")
    entry_new.setEchoMode(QLineEdit.Password)
    layout.addWidget(entry_new)
    label_confirm = QLabel("Repeat new password:")
    label_confirm.setFont(font3)
    label_confirm.setStyleSheet("color: white;")
    layout.addWidget(label_confirm)
    entry_confirm = QLineEdit()
    entry_confirm.setStyleSheet("background-color: #2a2a2e; color: white;")
    entry_confirm.setEchoMode(QLineEdit.Password)
    layout.addWidget(entry_confirm)
    btn_layout = QHBoxLayout()
    ok_btn = QPushButton("OK")
    ok_btn.setStyleSheet("background-color: #2a2a2e; color: white; width: 100px;")
    ok_btn.setFont(font3)
    ok_btn.setCursor(QCursor(Qt.PointingHandCursor))
    ok_btn.clicked.connect(dialog.accept)
    cancel_btn = QPushButton("Cancel")
    cancel_btn.setFont(font3)
    cancel_btn.setStyleSheet("background-color: #2a2a2e; color: white; width: 100px;")
    cancel_btn.setCursor(QCursor(Qt.PointingHandCursor))
    cancel_btn.clicked.connect(dialog.reject)
    btn_layout.addWidget(ok_btn)
    btn_layout.addWidget(cancel_btn)
    layout.addLayout(btn_layout)
    dialog.setLayout(layout)
    if dialog.exec_() == QDialog.Accepted:
        set_dark_window_color(dialog)
        input_current = entry_current.text()
        input_new = entry_new.text()
        input_confirm = entry_confirm.text()
        if input_current != current_pass:
            msg("Incorrect current password", "Error", "error")
            return
        if not input_new:
            msg("New password cannot be empty", "Error", "error")
            return
        if len(input_new) > 16:
            msg("Password cannot exceed 16 characters", "Error", "error")
            return
        if input_new != input_confirm:
            msg("New passwords do not match", "Error", "error")
            return
        updates = {'rcon.password': input_new}
        update_properties(properties_path, updates)
        msg("Password changed successfully", "Info", "info")
        refresh_server_menu(server)

def clear_window():
    if window.centralWidget():
        central = window.centralWidget()
       
        if central.layout():
            dummy = QWidget()
            dummy.setLayout(central.layout())
            del dummy
       
        central.deleteLater()
   
    window.setCentralWidget(None)
   
    global status_label
    status_label = None

def back_to_selection():
    global monitoring_after_id
   
    if monitoring_after_id:
        monitoring_after_id.stop()
        monitoring_after_id = None
   
    for aid in list(rcon_after_ids.values()):
        if aid:
            aid.stop()
   
    rcon_after_ids.clear()
    monitored_servers.clear()
   
    show_server_selection()

def save_settings(server_path, properties_path, batch_path, yml_file, version, is_modded, gm, diff, allow_nether, allow_flight, enable_command_block, max_players, online_mode, pvp, server_port, hardcore, motd, xmx, view_distance, anti_xray=None):
    needs_numeric = is_numeric_version(version)
   
    updates = {
        'gamemode': gamemode_str_to_num[gm] if needs_numeric else gm,
        'difficulty': difficulty_str_to_num[diff] if needs_numeric else diff,
        'allow-nether': 'true' if allow_nether else 'false',
        'allow-flight': 'true' if allow_flight else 'false',
        'enable-command-block': 'true' if enable_command_block else 'false',
        'max-players': max_players,
        'online-mode': 'true' if online_mode else 'false',
        'pvp': 'true' if pvp else 'false',
        'server-port': server_port,
        'hardcore': 'true' if hardcore else 'false',
        'motd': motd,
        'view-distance': str(view_distance)
    }
   
    try:
        int(updates['max-players'])
        int(updates['server-port'])
        new_xmx = xmx
    except ValueError:
        msg("Invalid settings values", "Error", "error")
        return
   
    update_properties(properties_path, updates)
   
    with open(batch_path, 'r', encoding='utf-8') as f:
        content = f.read()
   
    content = re.sub(r'-Xmx\d+M', f'-Xmx{new_xmx}M', content)
   
    with open(batch_path, 'w', encoding='utf-8') as f:
        f.write(content)
   
    if not is_modded:
        if anti_xray:
            update_yml(yml_file, 'enabled', 'true')
            update_yml(yml_file, 'engine-mode', '2')
        else:
            update_yml(yml_file, 'enabled', 'false')
            update_yml(yml_file, 'engine-mode', '1')
   
    unsaved_label.hide()

def start_server(batch_path, server_path, server, is_modded=False):
    block_file = os.path.join(server_path, 'users.json')
    is_blocked = os.path.exists(block_file)
   
    if is_blocked:
        plugins_dir = os.path.join(server_path, 'plugins')
       
        if os.path.exists(plugins_dir):
            for file in os.listdir(plugins_dir):
                clean_name = file.lower().replace(" ", "").replace("_", "")
               
                if "essentials" in clean_name or "luckperms" in clean_name:
                    os.remove(os.path.join(plugins_dir, file))
   
    if is_modded:
        msg("Modded servers may take 2 to 10 minutes to start. Please wait", "Warning", "info")
   
    version_ini = os.path.join(server_path, 'version.ini')
   
    if os.path.exists(version_ini):
        with open(version_ini, 'r') as f:
            version = f.read().strip()
    else:
        version = "1.21"
   
    nums = version.split('.')
   
    if is_blocked:
        process = subprocess.Popen(["cmd.exe", "/c", batch_path], creationflags=subprocess.CREATE_NO_WINDOW, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
    else:
        if console_mode:
            process = subprocess.Popen([batch_path], creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:
            if is_modded:
                process = subprocess.Popen(["cmd.exe", "/c", batch_path], creationflags=subprocess.CREATE_NO_WINDOW, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
            else:
                if len(nums) >= 2 and int(nums[1]) < 16:
                    process = subprocess.Popen([batch_path], creationflags=subprocess.CREATE_NEW_CONSOLE)
                else:
                    process = subprocess.Popen(["cmd.exe", "/c", batch_path], creationflags=subprocess.CREATE_NO_WINDOW, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
   
    pid = process.pid
   
    active_file = os.path.join(server_path, 'Active.tmp')
   
    with open(active_file, 'w') as f:
        f.write(str(pid))
   
    refresh_server_menu(server)

def check_stopped(server):
    server_path = os.path.join(servers_dir, server)
   
    if is_server_running(server_path):
        QTimer.singleShot(1000, lambda: check_stopped(server))
    else:
        if current_screen == "server_menu" and current_server == server:
            refresh_server_menu(server)

def stop_server_thread(server_path, properties_path):
    prop = {}
   
    if os.path.exists(properties_path):
        with open(properties_path, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip() or line.strip().startswith('#'): continue
               
                if '=' in line:
                    k, v = line.strip().split('=', 1)
                    prop[k] = unescape_property(v)
   
    if prop.get('enable-rcon', 'false') != 'true':
        return False
   
    port = int(prop.get('rcon.port', '25575'))
    password = prop.get('rcon.password', '')
   
    if not password:
        return False
   
    connected = False
   
    for attempt in range(4):
        try:
            rcon = RCONClient("127.0.0.1", port=port)
           
            if rcon.login(password):
                rcon.command("stop")
                rcon.stop()
                connected = True
                break
        except Exception as e:
            print(f"RCON attempt {attempt+1}. Error: {e}")
       
        time.sleep(1)
   
    return connected

def stop_with_ui(server_path, properties_path, server):
    font = QFont()
    font.setFamily("Play")
    font.setPointSize(14)
    font.setBold(True)
    font.setWeight(75)
    shutdown_text = QLabel(centralwidget)
    shutdown_text.setGeometry(QRect(500, 100, 161, 31))
    shutdown_text.setFont(font)
    shutdown_text.setStyleSheet("color: rgb(255, 255, 255); background-color: rgb(45, 57, 67);")
    shutdown_text.setText("Shutting down...")
    shutdown_text.show()
   
    q = queue.Queue()
   
    thread = threading.Thread(target=lambda: q.put(stop_server_thread(server_path, properties_path)))
    thread.start()
   
    def check_queue():
        try:
            connected = q.get_nowait()
           
            try:
                shutdown_text.hide()
            except RuntimeError:
                pass
           
            if connected:
                check_stopped(server)
            else:
                msg("Error stopping server, it may not be fully started", "Error", "error")
           
            thread.join()
        except queue.Empty:
            QTimer.singleShot(500, check_queue)
   
    QTimer.singleShot(500, check_queue)

def create_server():
    global name_entry, password_entry, confirm_password_entry, block_check, version_menu
   
    name = name_entry.text().strip()
    password = password_entry.text().strip()
    confirm_password = confirm_password_entry.text().strip()
   
    invalid_chars = r'\/|:"*<>'
   
    if not name or any(c in invalid_chars for c in name):
        msg("Invalid server name", "Error", "error")
        return
   
    if len(name) > 16:
        msg("Server name cannot exceed 16 characters", "Error", "error")
        return
   
    if not password:
        msg("Password is required", "Error", "error")
        return
   
    if len(password) > 16:
        msg("Password cannot exceed 16 characters", "Error", "error")
        return
   
    if password != confirm_password:
        msg("Passwords do not match", "Error", "error")
        return
   
    server_path = os.path.join(servers_dir, name)
   
    if os.path.exists(server_path):
        msg("Server with this name already exists", "Error", "error")
        return
   
    if internet() != 0:
        msg("No internet connection", "Error", "error")
        return
    used_ports = set()
   
    for server in os.listdir(servers_dir):
        if os.path.isdir(os.path.join(servers_dir, server)):
            prop_path = os.path.join(servers_dir, server, 'server.properties')
           
            if os.path.exists(prop_path):
                with open(prop_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip().startswith('rcon.port='):
                            port = line.strip().split('=')[1]
                            used_ports.add(int(port))
                            break
   
    rcon_port = random.randint(20000, 21000)
   
    while rcon_port in used_ports:
        rcon_port = random.randint(20000, 21000)
   
    version = version_menu.currentText()
    os.makedirs(server_path)
    os.makedirs(f"{server_path}\\plugins")
   
    Download_paper(version, server_path)
   
    url = versions_data['versions'][version]
    paper_file = os.path.basename(url)
   
    eula_path = os.path.join(server_path, 'eula.txt')
   
    with open(eula_path, 'w') as f:
        f.write('eula=true')
   
    needs_numeric = is_numeric_version(version)
   
    update_defaults = defaults.copy()
   
    if needs_numeric:
        update_defaults['gamemode'] = gamemode_str_to_num[update_defaults['gamemode']]
        update_defaults['difficulty'] = difficulty_str_to_num[update_defaults['difficulty']]
   
    update_defaults['motd'] = name
    update_defaults['rcon.password'] = password
    update_defaults['rcon.port'] = str(rcon_port)
   
    if block_check.isChecked():
        update_defaults['enable-command-block'] = 'false'
   
    properties_path = os.path.join(server_path, 'server.properties')
    update_properties(properties_path, update_defaults)
   
    world_dir = os.path.join(server_path, 'world')
    os.makedirs(world_dir, exist_ok=True)
   
    default_icon = os.path.join('System', 'Textures', 'icon.png')
   
    if os.path.exists(default_icon):
        shutil.copy2(default_icon, os.path.join(world_dir, 'icon.png'))
   
    config_dir = os.path.join(server_path, 'config')
    os.makedirs(config_dir, exist_ok=True)
   
    yml_file = os.path.join(config_dir, 'paper-world-defaults.yml')
   
    with open(yml_file, 'w', encoding='utf-8') as f:
        f.write('''
anticheat:
  anti-xray:
    enabled: true
    engine-mode: 2
    hidden-blocks:
      - air
      - copper_ore
      - deepslate_copper_ore
      - raw_copper_block
      - diamond_ore
      - deepslate_diamond_ore
      - gold_ore
      - deepslate_gold_ore
      - iron_ore
      - deepslate_iron_ore
      - raw_iron_block
      - lapis_ore
      - deepslate_lapis_ore
      - redstone_ore
      - deepslate_redstone_ore
    lava-obscures: false
    max-block-height: 64
    replacement-blocks:
      - chest
      - amethyst_block
      - andesite
      - budding_amethyst
      - calcite
      - coal_ore
      - deepslate_coal_ore
      - deepslate
      - diorite
      - dirt
      - emerald_ore
      - deepslate_emerald_ore
      - granite
      - gravel
      - oak_planks
      - smooth_basalt
      - stone
      - tuff
    update-radius: 2
    use-permission: false
''')
   
    java_path = get_java_path(version)
   
    nogui_arg = ' nogui' if block_check.isChecked() else ''
   
    batch_content = f'@echo off\nchcp 65001 >nul\ncolor 0a\ntitle {name} - to stop the server, type stop or click "Stop server" in the program\npowershell.exe -NoProfile -ExecutionPolicy Unrestricted -File "System\\Hidden_close.ps1"\ncd /d "{server_path}"\n"{java_path}" -Xmx4096M -jar "{paper_file}"{nogui_arg}'
   
    batch_path = os.path.join(server_path, 'start.bat')
   
    with open(batch_path, 'w', encoding='utf-8') as f:
        f.write(batch_content)
   
    version_ini_path = os.path.join(server_path, 'version.ini')
   
    with open(version_ini_path, 'w') as f:
        f.write(version)
   
    if block_check.isChecked():
        block_file = os.path.join(server_path, 'users.json')
       
        with open(block_file, 'w') as f:
            pass
   
    show_server_menu(name)

def create_modded_server():
    global name_entry, password_entry, confirm_password_entry, block_check, version_menu
   
    name = name_entry.text().strip()
    password = password_entry.text().strip()
    confirm_password = confirm_password_entry.text().strip()
   
    invalid_chars = r'\/|:"*<>'
   
    if not name or any(c in invalid_chars for c in name):
        msg("Invalid server name", "Error", "error")
        return
   
    if len(name) > 16:
        msg("Server name cannot exceed 16 characters", "Error", "error")
        return
   
    if not password:
        msg("Password is required", "Error", "error")
        return
   
    if len(password) > 16:
        msg("Password cannot exceed 16 characters", "Error", "error")
        return
   
    if password != confirm_password:
        msg("Passwords do not match", "Error", "error")
        return
   
    server_path = os.path.join(servers_dir, name)
   
    if os.path.exists(server_path):
        msg("Server with this name already exists", "Error", "error")
        return
   
    used_ports = set()
   
    for server in os.listdir(servers_dir):
        if os.path.isdir(os.path.join(servers_dir, server)):
            prop_path = os.path.join(servers_dir, server, 'server.properties')
           
            if os.path.exists(prop_path):
                with open(prop_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip().startswith('rcon.port='):
                            port = line.strip().split('=')[1]
                            used_ports.add(int(port))
                            break
   
    rcon_port = random.randint(20000, 21000)
   
    while rcon_port in used_ports:
        rcon_port = random.randint(20000, 21000)
   
    version = version_menu.currentText().replace('-forge', '')
    os.makedirs(server_path)
    os.makedirs(f"{server_path}\\plugins")
    os.makedirs(f"{server_path}\\mods")
   
    arclight_file = f"arclight-forge-{version}.jar"
    shutil.copy(os.path.join("System\\Arclight", arclight_file), os.path.join(server_path, arclight_file))
   
    paper_file = arclight_file
   
    eula_path = os.path.join(server_path, 'eula.txt')
   
    with open(eula_path, 'w') as f:
        f.write('eula=true')
   
    needs_numeric = is_numeric_version(version)
   
    update_defaults = defaults.copy()
   
    if needs_numeric:
        update_defaults['gamemode'] = gamemode_str_to_num[update_defaults['gamemode']]
        update_defaults['difficulty'] = difficulty_str_to_num[update_defaults['difficulty']]
   
    update_defaults['motd'] = name
    update_defaults['rcon.password'] = password
    update_defaults['rcon.port'] = str(rcon_port)
   
    if block_check.isChecked():
        update_defaults['enable-command-block'] = 'false'
   
    properties_path = os.path.join(server_path, 'server.properties')
    update_properties(properties_path, update_defaults)
   
    world_dir = os.path.join(server_path, 'world')
    os.makedirs(world_dir, exist_ok=True)
   
    default_icon = os.path.join('System', 'Textures', 'icon.png')
   
    if os.path.exists(default_icon):
        shutil.copy2(default_icon, os.path.join(world_dir, 'icon.png'))
   
    java_path = get_java_path(version)
   
    nogui_arg = ' nogui' if block_check.isChecked() else ''
   
    batch_content = f'@echo off\npowershell.exe -NoProfile -ExecutionPolicy Unrestricted -File "System\\Hidden_close.ps1"\nchcp 65001 >nul\ntitle {name} - to stop the server, type stop or click "Stop server" in the program\ncd /d "{server_path}"\n"{java_path}" -Xmx4096M -jar "{paper_file}"{nogui_arg}'
   
    batch_path = os.path.join(server_path, 'start.bat')
   
    with open(batch_path, 'w', encoding='utf-8') as f:
        f.write(batch_content)
   
    version_ini_path = os.path.join(server_path, 'version.ini')
   
    with open(version_ini_path, 'w') as f:
        f.write(version)
   
    modded_marker = os.path.join(server_path, 'modded.txt')
   
    with open(modded_marker, 'w') as f:
        f.write('true')
   
    if block_check.isChecked():
        block_file = os.path.join(server_path, 'users.json')
       
        with open(block_file, 'w') as f:
            pass
   
    show_server_menu(name)

def back_from_create():
    show_server_selection()

def show_create_type_selection():
    global current_screen
   
    current_screen = "create_type"
   
    clear_window()
   
    centralwidget = QWidget()
    centralwidget.setStyleSheet("background-color: rgb(22, 28, 33); color: rgb(255, 255, 255);")
   
    topmenu = QLabel(centralwidget)
    topmenu.setGeometry(QRect(30, 30, 741, 541))
    topmenu.setStyleSheet("background-color: rgb(45, 57, 67);")
   
    server1name = QLabel(centralwidget)
    server1name.setGeometry(QRect(30, 120, 741, 21))
   
    font = QFont()
    font.setFamily("Play")
    font.setPointSize(14)
    font.setBold(True)
    font.setWeight(75)
   
    server1name.setFont(font)
    server1name.setStyleSheet("color: rgb(255, 255, 255); background-color: rgb(45, 57, 67);")
    server1name.setAlignment(Qt.AlignCenter)
    server1name.setText("Select server type to create")
   
    createbutton = QPushButton(centralwidget)
    createbutton.setGeometry(QRect(280, 250, 251, 71))
   
    font = QFont()
    font.setFamily("Play")
    font.setPointSize(14)
    font.setBold(True)
    font.setWeight(75)
   
    createbutton.setFont(font)
    createbutton.setStyleSheet("background-color: rgb(43, 135, 211); border-radius: 5px;")
    createbutton.setText("+ Create server")
    createbutton.clicked.connect(show_create_vanilla)
    createbutton.setCursor(QCursor(Qt.PointingHandCursor))
   
    createbutton_2 = QPushButton(centralwidget)
    createbutton_2.setGeometry(QRect(280, 340, 251, 71))
    createbutton_2.setFont(font)
    createbutton_2.setStyleSheet("background-color: rgb(43, 135, 211); border-radius: 5px;")
    createbutton_2.setText("+ Create modded")
    createbutton_2.clicked.connect(show_create_modded)
    createbutton_2.setCursor(QCursor(Qt.PointingHandCursor))
   
    back_btn = QPushButton(centralwidget)
    back_btn.setGeometry(QRect(360, 430, 100, 30))
    back_btn.setFont(font)
    back_btn.setStyleSheet("background-color: rgb(43, 135, 211); border-radius: 5px;")
    back_btn.setText("Back")
    back_btn.clicked.connect(show_server_selection)
    back_btn.setCursor(QCursor(Qt.PointingHandCursor))
   
    window.setCentralWidget(centralwidget)

def show_create_vanilla():
    global current_screen
   
    current_screen = "create"
   
    clear_window()
   
    centralwidget = QWidget()
    centralwidget.setStyleSheet("background-color: rgb(22, 28, 33); color: rgb(255, 255, 255);")
   
    topmenu = QLabel(centralwidget)
    topmenu.setGeometry(QRect(30, 30, 741, 541))
   
    font = QFont()
    font.setBold(True)
    font.setWeight(75)
   
    topmenu.setFont(font)
    topmenu.setStyleSheet("background-color: rgb(45, 57, 67);")
   
    textmain = QLabel(centralwidget)
    textmain.setGeometry(QRect(30, 120, 741, 41))
   
    font = QFont()
    font.setFamily("Play")
    font.setPointSize(14)
    font.setBold(True)
    font.setWeight(75)
   
    textmain.setFont(font)
    textmain.setStyleSheet("background-color: rgb(45, 57, 67);")
    textmain.setAlignment(Qt.AlignCenter)
    textmain.setText("Enter server name:")
   
    global name_entry
    name_entry = QLineEdit(centralwidget)
    name_entry.setGeometry(QRect(280, 160, 241, 31))
    name_entry.setStyleSheet("background-color: rgb(45, 57, 67); color: white;")
   
    textmain_2 = QLabel(centralwidget)
    textmain_2.setGeometry(QRect(30, 190, 741, 41))
    textmain_2.setFont(font)
    textmain_2.setStyleSheet("background-color: rgb(45, 57, 67);")
    textmain_2.setAlignment(Qt.AlignCenter)
    textmain_2.setText("Enter server password:")
   
    global password_entry
    password_entry = QLineEdit(centralwidget)
    password_entry.setGeometry(QRect(280, 230, 241, 31))
    password_entry.setStyleSheet("background-color: rgb(45, 57, 67); color: white;")
    password_entry.setEchoMode(QLineEdit.Password)
   
    textmain_3 = QLabel(centralwidget)
    textmain_3.setGeometry(QRect(30, 260, 741, 41))
    textmain_3.setFont(font)
    textmain_3.setStyleSheet("background-color: rgb(45, 57, 67);")
    textmain_3.setAlignment(Qt.AlignCenter)
    textmain_3.setText("Repeat password:")
   
    global confirm_password_entry
    confirm_password_entry = QLineEdit(centralwidget)
    confirm_password_entry.setGeometry(QRect(280, 300, 241, 31))
    confirm_password_entry.setStyleSheet("background-color: rgb(45, 57, 67); color: white;")
    confirm_password_entry.setEchoMode(QLineEdit.Password)
   
    global block_check
    block_check = QCheckBox(centralwidget)
    block_check.setGeometry(QRect(280, 350, 241, 16))
    font = QFont()
    font.setFamily("Play")
    font.setPointSize(10)
    font.setBold(True)
    font.setWeight(75)
    block_check.setFont(font)
    block_check.setStyleSheet("background-color: rgb(45, 57, 67);")
    block_check.setText("Lockdown mode")
    help_btn = QPushButton(centralwidget)
    help_btn.setGeometry(QRect(436, 350, 20, 16))
    font = QFont()
    font.setFamily("Play")
    font.setPointSize(10)
    font.setItalic(True)
    font.setWeight(75)
    help_btn.setFont(font)
    help_btn.setStyleSheet("background-color: rgb(45, 57, 67); border-radius: 5px;")
    help_btn.setText("(?)")
    help_btn.clicked.connect(lambda: msg("Lockdown mode removes admin privileges from the server owner. No access to console, cannot change game mode, etc. Only non-admin actions are allowed.", "Lockdown mode", "info"))
    help_btn.setCursor(QCursor(Qt.PointingHandCursor))
   
    global version_menu
    version_menu = QComboBox(centralwidget)
    version_menu.setGeometry(QRect(280, 380, 241, 22))
    version_menu.setStyleSheet("background-color: rgb(45, 57, 67); color: white;")
    version_menu.addItems(versions_list)
    version_menu.setCurrentText(latest_version)
   
    create_btn = QPushButton(centralwidget)
    create_btn.setGeometry(QRect(280, 410, 241, 71))
    font = QFont()
    font.setFamily("Play")
    font.setPointSize(14)
    font.setBold(True)
    font.setWeight(75)
    create_btn.setFont(font)
    create_btn.setStyleSheet("background-color: rgb(43, 135, 211); border-radius: 5px;")
    create_btn.setText("+ Create server")
    create_btn.clicked.connect(create_server)
    create_btn.setCursor(QCursor(Qt.PointingHandCursor))
   
    back_btn = QPushButton(centralwidget)
    back_btn.setGeometry(QRect(280, 490, 241, 71))
    back_btn.setFont(font)
    back_btn.setStyleSheet("background-color: rgb(43, 135, 211); border-radius: 5px;")
    back_btn.setText("Back")
    back_btn.clicked.connect(show_create_type_selection)
    back_btn.setCursor(QCursor(Qt.PointingHandCursor))
   
    window.setCentralWidget(centralwidget)

def show_create_modded():
    global current_screen
   
    current_screen = "create"
   
    clear_window()
   
    centralwidget = QWidget()
    centralwidget.setStyleSheet("background-color: rgb(22, 28, 33); color: rgb(255, 255, 255);")
   
    topmenu = QLabel(centralwidget)
    topmenu.setGeometry(QRect(30, 30, 741, 541))
    font = QFont()
    font.setBold(True)
    font.setWeight(75)
    topmenu.setFont(font)
    topmenu.setStyleSheet("background-color: rgb(45, 57, 67);")
   
    textmain = QLabel(centralwidget)
    textmain.setGeometry(QRect(30, 120, 741, 41))
    font = QFont()
    font.setFamily("Play")
    font.setPointSize(14)
    font.setBold(True)
    font.setWeight(75)
    textmain.setFont(font)
    textmain.setStyleSheet("background-color: rgb(45, 57, 67);")
    textmain.setAlignment(Qt.AlignCenter)
    textmain.setText("Enter server name:")
   
    global name_entry
    name_entry = QLineEdit(centralwidget)
    name_entry.setGeometry(QRect(280, 160, 241, 31))
    name_entry.setStyleSheet("background-color: rgb(45, 57, 67); color: white;")
   
    textmain_2 = QLabel(centralwidget)
    textmain_2.setGeometry(QRect(30, 190, 741, 41))
    textmain_2.setFont(font)
    textmain_2.setStyleSheet("background-color: rgb(45, 57, 67);")
    textmain_2.setAlignment(Qt.AlignCenter)
    textmain_2.setText("Enter server password:")
   
    global password_entry
    password_entry = QLineEdit(centralwidget)
    password_entry.setGeometry(QRect(280, 230, 241, 31))
    password_entry.setStyleSheet("background-color: rgb(45, 57, 67); color: white;")
    password_entry.setEchoMode(QLineEdit.Password)
   
    textmain_3 = QLabel(centralwidget)
    textmain_3.setGeometry(QRect(30, 260, 741, 41))
    textmain_3.setFont(font)
    textmain_3.setStyleSheet("background-color: rgb(45, 57, 67);")
    textmain_3.setAlignment(Qt.AlignCenter)
    textmain_3.setText("Repeat password:")
   
    global confirm_password_entry
    confirm_password_entry = QLineEdit(centralwidget)
    confirm_password_entry.setGeometry(QRect(280, 300, 241, 31))
    confirm_password_entry.setStyleSheet("background-color: rgb(45, 57, 67); color: white;")
    confirm_password_entry.setEchoMode(QLineEdit.Password)
   
    global block_check
    block_check = QCheckBox(centralwidget)
    block_check.setGeometry(QRect(280, 350, 241, 16))
    font = QFont()
    font.setFamily("Play")
    font.setPointSize(10)
    font.setBold(True)
    font.setWeight(75)
    block_check.setFont(font)
    block_check.setStyleSheet("background-color: rgb(45, 57, 67);")
    block_check.setText("Lockdown mode")
    help_btn = QPushButton(centralwidget)
    help_btn.setGeometry(QRect(436, 350, 20, 16))
    font = QFont()
    font.setFamily("Play")
    font.setPointSize(10)
    font.setItalic(True)
    font.setWeight(75)
    help_btn.setFont(font)
    help_btn.setStyleSheet("background-color: rgb(45, 57, 67); border-radius: 5px;")
    help_btn.setText("(?)")
    help_btn.clicked.connect(lambda: msg("In lockdown mode, game mode is always survival, admin cannot change it and has no admin privileges. Console access is blocked. This mode prevents admin cheating in survival servers.", "Lockdown mode", "info"))
    help_btn.setCursor(QCursor(Qt.PointingHandCursor))
   
    global version_menu
    version_menu = QComboBox(centralwidget)
    version_menu.setGeometry(QRect(280, 380, 241, 22))
    version_menu.setStyleSheet("background-color: rgb(45, 57, 67); color: white;")
    version_menu.addItems(versions_list_modded_display)
    version_menu.setCurrentText(latest_version_modded_display)
    create_btn = QPushButton(centralwidget)
    create_btn.setGeometry(QRect(280, 410, 241, 71))
    font = QFont()
    font.setFamily("Play")
    font.setPointSize(14)
    font.setBold(True)
    font.setWeight(75)
   
    create_btn.setFont(font)
    create_btn.setStyleSheet("background-color: rgb(43, 135, 211); border-radius: 5px;")
    create_btn.setText("+ Create server")
    create_btn.clicked.connect(create_modded_server)
    create_btn.setCursor(QCursor(Qt.PointingHandCursor))
   
    back_btn = QPushButton(centralwidget)
    back_btn.setGeometry(QRect(280,490, 241, 71))
    back_btn.setFont(font)
    back_btn.setStyleSheet("background-color: rgb(43, 135, 211); border-radius: 5px;")
    back_btn.setText("Back")
    back_btn.clicked.connect(show_create_type_selection)
    back_btn.setCursor(QCursor(Qt.PointingHandCursor))
   
    window.setCentralWidget(centralwidget)

required_dirs = [
    "System\\Arclight",
    "System\\jdk8u462",
    "System\\jdk-21",
    "System\\jdk-17.0.16",
    "System\\jdk-16.0.2",
    "System\\Textures"
]

required_files = [
    "System\\jdk8u462\\bin\\java.exe",
    "System\\jdk-21\\bin\\java.exe",
    "System\\jdk-17.0.16\\bin\\java.exe",
    "System\\jdk-16.0.2\\bin\\java.exe",
    "System\\Textures\\icon.png",
    "System\\Textures\\Icon_base.ico",
    "System\\Textures\\off.png",
    "System\\Textures\\on.png",
    "System\\Arclight\\arclight-forge-1.16.5.jar",
    "System\\Arclight\\arclight-forge-1.17.1.jar",
    "System\\Arclight\\arclight-forge-1.18.2.jar",
    "System\\Arclight\\arclight-forge-1.19.2.jar",
    "System\\Arclight\\arclight-forge-1.20.1.jar",
    "System\\Arclight\\arclight-forge-1.20.2.jar",
    "System\\Arclight\\arclight-forge-1.20.4.jar",
    "System\\Arclight\\arclight-forge-1.21.1.jar",
    "System\\Paper_versions.json",
    "System\\Hidden_close.ps1",
    "System\\Play-Bold.ttf",
    "System\\Play-Regular.ttf"
]

for d in required_dirs:
    if not os.path.exists(d):
        msg(f"Missing required directory: {d} Please check program integrity", "Critical error", "error")
        sys.exit(1)

for files_i in required_files:
    if not os.path.exists(files_i):
        msg(f"Missing required file: {files_i} Please check program integrity", "Critical error", "error")
        sys.exit(1)

current_screen = None
current_server = None

app = QApplication(sys.argv)
QFontDatabase.addApplicationFont("System\\Play-Bold.ttf")
QFontDatabase.addApplicationFont("System\\Play-Regular.ttf")
window = QMainWindow()
pywinstyles.apply_style(window.winId(), style="dark")
window.setWindowTitle("ConstructorMC 0.3 Beta")
window.setFixedSize(800, 600)
window.setWindowFlags(window.windowFlags() & ~Qt.WindowMaximizeButtonHint)
## To hide the window maximize button
window.setWindowIcon(QIcon(r'System/Textures/icon_base.ico'))
window.setStyleSheet("background-color: #121214;")

def msg(text, title, type_):
    msgbox = QMessageBox(window)
    font3 = QFont()
    font3.setFamily("Play")
    font3.setPointSize(12)
    font3.setBold(True)
    font3.setWeight(75)
    msgbox.setFont(font3)
    msgbox.setWindowTitle(title)
    msgbox.setText(text)
    msgbox.setStyleSheet("color: rgb(255, 255, 255);")
   
    if type_ == "error":
        msgbox.setIcon(QMessageBox.Critical)
    elif type_ == "info":
        msgbox.setIcon(QMessageBox.Information)
   
    msgbox.show()
    set_dark_window_color(msgbox)

def set_dark_window_color(window_2):
    pywinstyles.apply_style(window_2.winId(), style="dark")
    window_2.hide()
    window_2.show()

servers = [d for d in os.listdir(servers_dir) if os.path.isdir(os.path.join(servers_dir, d))]

for server in servers:
    server_path = os.path.join(servers_dir, server)
    version_ini = os.path.join(server_path, 'version.ini')
    if not os.path.exists(version_ini):
        continue
    with open(version_ini, 'r') as f:
        version = f.read().strip()
    batch_path = os.path.join(server_path, 'start.bat')
    if not os.path.exists(batch_path):
        continue
    with open(batch_path, 'r', encoding='utf-8') as f:
        content = f.read()
    match = re.search(r'"(.*?)"\s*-Xmx', content)
    if match:
        current_java = match.group(1)
        if not os.path.exists(current_java):
            new_java = get_java_path(version)
            content = content.replace(f'"{current_java}"', f'"{new_java}"')
            with open(batch_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Replaced Java from: {current_java} to: {new_java}")

console_mode = False
if sys.argv[1] != "0":
    console_mode = True

print("Console mode:", sys.argv[1])
print("Program started")

show_server_selection()
window.show()
set_dark_window_color(window)
window.raise_()
window.activateWindow()
sys.exit(app.exec_())