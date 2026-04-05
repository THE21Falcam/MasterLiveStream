import socket

server = "irc.chat.twitch.tv"
port = 6667
nickname = "justinfan30469"
token = "oauth:SCHMOOPIIE"  # Default Token
channel = "#marlon"
     
def getChat():
    # Initialize Socket
    sock = socket.socket()
    sock.connect((server, port))

    # Authenticate and Join
    sock.send(f"PASS {token}\n".encode("utf-8"))
    sock.send(f"NICK {nickname}\n".encode("utf-8"))
    sock.send(f"JOIN {channel}\n".encode("utf-8"))
    # Receive and Parse Data
    while True:
        resp = sock.recv(2048).decode("utf-8")
        if resp.startswith("PING"):
            sock.send("PONG\n".encode("utf-8"))
        elif len(resp) > 0 and "justinfan30469" not in resp:
            prefix, command, channel, message = resp.split(" ", 3)

            username = prefix.split("!", 1)[0][1:]
            message = message[1:]

            print(username)  # mrfalcam21
            print(message)
            # Parse logic here for user and message
