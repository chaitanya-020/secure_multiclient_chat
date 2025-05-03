# ------------------- server.py -------------------
import socket
import threading

PORT = 65432
BUFFER_SIZE = 4096

clients = []
lock = threading.Lock()

def handle_client(conn, addr):
    print(f"[+] New client connected: {addr}")
    with conn:
        while True:
            try:
                data = conn.recv(BUFFER_SIZE)
                if not data:
                    break
                with lock:
                    for c in clients:
                        if c != conn:
                            c.sendall(data)
            except:
                break
    with lock:
        clients.remove(conn)
    print(f"[-] Client disconnected: {addr}")

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('', PORT))
    server.listen(5)
    print(f"[*] Server listening on port {PORT}...")

    while True:
        conn, addr = server.accept()
        with lock:
            clients.append(conn)
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    start_server()


# ------------------- client.py -------------------
import tkinter as tk
from tkinter import scrolledtext, simpledialog
import threading
import socket
from crypto_utils import derive_key, encrypt_message, decrypt_message

PORT = 65432
BUFFER_SIZE = 4096
ROTATE_EVERY = 5

class ChatApp:
    def __init__(self, root, passphrase, server_ip):
        self.root = root
        self.root.title("Secure Chat")
        self.server_ip = server_ip

        self.chat_area = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=60, height=20)
        self.chat_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        self.chat_area.config(state=tk.DISABLED)

        input_frame = tk.Frame(root)
        input_frame.pack(padx=10, pady=(0, 10), fill=tk.X)

        self.entry = tk.Entry(input_frame, width=50)
        self.entry.pack(side=tk.LEFT, expand=True, fill=tk.X)
        self.entry.bind("<Return>", self.send_message_event)
        self.entry.focus_set()

        self.send_button = tk.Button(input_frame, text="Send", command=self.send_message)
        self.send_button.pack(side=tk.LEFT, padx=(10, 0))

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.server_ip, PORT))

        self.passphrase = passphrase.encode()
        self.message_count = 0
        self.current_salt_index = 0
        self.key = derive_key(self.passphrase, b'salt0', 32)

        threading.Thread(target=self.receive_messages, daemon=True).start()

    def rotate_key_if_needed(self):
        new_index = self.message_count // ROTATE_EVERY
        if new_index != self.current_salt_index:
            self.current_salt_index = new_index
            new_salt = f"salt{self.current_salt_index}".encode()
            self.key = derive_key(self.passphrase, new_salt, 32)
            rotation_msg = f"🔑 Key rotated (salt{self.current_salt_index})"
            self.display_message(rotation_msg)
            print(rotation_msg)

    def receive_messages(self):
        while True:
            try:
                data = self.sock.recv(BUFFER_SIZE)
                if not data:
                    break
                decrypted, _ = decrypt_message(self.key, data)
                self.message_count += 1
                self.rotate_key_if_needed()
                self.display_message(f"\nReceived Cipher:\n{data.hex()}")
                self.display_message(f"Decrypted: {decrypted.decode()}")
            except Exception as e:
                print(f"Error: {e}")
                self.display_message(f"Error: {e}")
                break

    def send_message_event(self, event):
        self.send_message()

    def send_message(self):
        msg = self.entry.get()
        if msg:
            self.message_count += 1
            self.rotate_key_if_needed()
            encrypted = encrypt_message(self.key, msg.encode())
            self.sock.sendall(encrypted)
            self.display_message(f"\nSent Cipher:\n{encrypted.hex()}")
            self.display_message(f"Plaintext: {msg}")
            self.entry.delete(0, tk.END)

    def display_message(self, msg):
        self.chat_area.config(state=tk.NORMAL)
        self.chat_area.insert(tk.END, msg + "\n")
        self.chat_area.config(state=tk.DISABLED)
        self.chat_area.see(tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()

    passphrase = simpledialog.askstring("Passphrase", "Enter shared passphrase:", show='*')
    server_ip = simpledialog.askstring("Server IP", "Enter server IP address:")

    if not passphrase or not server_ip:
        print("Passphrase and Server IP are required. Exiting.")
        exit()

    root.deiconify()
    app = ChatApp(root, passphrase, server_ip)
    root.mainloop()
