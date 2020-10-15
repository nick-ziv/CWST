# CWST
Cross WAN Socket Tunnel

CWST is a reworked version of [bohops' pyrevtun (Python Reverse Tunnel)](https://github.com/bohops/pyrevtun) which includes a GUI and removes the SSL encryption (no need to generate certs). 

CWST enables its users to bypass blocked ports on a network.  Another great scenario is to use CWST to get around port forwarding on the server's network.

## Usage
Written using Python 3.7.8  To run using python, you must install wxPython.

```bash
pip install wxpython
```

Very detailed usage example:

Joe is hosting a LAN server listening to port 5000, he cannot port forward on his network.

Steve is on a separate LAN and can port forward.  He forwards port 6000 and starts CWST Server with "Client app connection" port 1234 and "incoming connection" port 6000.

Joe can now start CWST Client with "Remote CWST server" host as Steve's external IP and port 6000 and "Serving app" host as localhost and port 5000.

Once Steve and Joe both click "Start Server," Steve can use his client app to connect to localhost:1234 on his machine and the traffic will be forwarded to Steve's server.

## Author
This program was written by Nicholas Zivkovic

## Disclaimer
This is not a secure way of transmitting information because there is no encryption.  Please do not use this with any sensitive information.

This works ONLY when the program you are tunneling communicates with its server using a single socket connection (example: Minecraft, SSH).

## License
[MIT](https://choosealicense.com/licenses/mit/)
