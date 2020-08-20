import socket
import sys, os
import time
import traceback
import wx
from _thread import *


CWSTpassword = b'3kjhCJHKknjw4'
serverStatus = "STOPPED"
serverConnStatus = "DISCONNECTED"

BUFFER_SIZE = 1024
RECV_TIMEOUT = .00001

class actionFuncs:
    def __init__(self, options):
        self.open = True
        self.options = options

    def start(self):
        if (self.options['mode'] == 'listener'):
            print()
            listenhost, listenport = self.options['listener'].split(':')
            self.mode_listener(listenhost, int(listenport), self.options['tunnelport'], self.options['passwd'])
        elif (self.options['mode'] == 'client'):
            listenhost, listenport = self.options['listener'].split(':')
            clienthost, clientport = self.options['client'].split(':')
            self.mode_client(listenhost, int(listenport), clienthost, int(clientport), self.options['passwd'])

    def recvall(self, the_socket, timeout= ''):
        #setup to use non-blocking sockets
        #if no data arrives it assumes transaction is done
        #recv() returns a bytes string
        the_socket.setblocking(0)
        total_data=[];data=''
        begin=time.time()
        if not timeout:
            timeout=1
        while self.open:
            #if you got some data, then break after wait sec
            if total_data and time.time()-begin>timeout:
                break
            #if you got no data at all, wait a little longer
            elif time.time()-begin>timeout*2:
                break
            try:
                data=the_socket.recv(BUFFER_SIZE)
                if data:
                    total_data.append(data)
                    begin=time.time()
                else:
                    time.sleep(0.1)
            except:
                pass
            #When a recv returns 0 bytes, other side has closed
        result = b''
        for dataBit in total_data:
            result += dataBit
        return result

    def mode_listener(self, listenHost, listenPort, tunnelPort, passwd):
        global serverConnStatus
        global frm
        #1 - Wait for connection from the remote target host
        try:
            listenSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listenSock.bind((listenHost, listenPort))
            while self.open:
                try:
                    listenSock.settimeout(3)
                    listenSock.listen(1)
                    listenSock.settimeout(None)
                    break
                except socket.timeout:
                    continue
            print ('[*] Listening on TCP ' + str(listenPort))
        except socket.error as msg:
            traceback.print_exc()
            print ('[-] Socket Error: ' + str(msg))
            return
        
        #2 - Wait for target tunnel association
        try:
            listen_client_conn_tmp, listen_client_addr = listenSock.accept()
            listen_client_conn = listen_client_conn_tmp
            
            print ('[*] Connection from ' + str(listen_client_addr[0]))	
            print ('[*] Establishing association between client and listener')
            if (listen_client_conn.recv(BUFFER_SIZE) != passwd):
                print ('[-] Failed to associate tunnel')
                listen_client_conn.close()
                return
            else:
                print ('[*] Tunnel is now associated on listener side')
        except socket.error as msg:
            print ('[-] Tunnel Association Error: ' + str(msg))
            return
        #3 - #Bind localhost port for tunneling
        try:
            tunnelSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tunnelSock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            tunnelSock.bind(('', tunnelPort))#listen on all interfaces
            while self.open:
                try:
                    tunnelSock.settimeout(5)
                    tunnelSock.listen(1)
                    tunnelSock.settimeout(None)
                    break
                except socket.timeout:
                    continue
            print ('[*] Tunnel socket is accessible at localhost:' + str(tunnelPort))
            serverConnStatus = "CONNECTED"
            frm.updateStatusText()
        except socket.error as msg:
            traceback.print_exc()
            print ('[-] Socket Error: ' + str(msg))
            return
        
        #4 - Initate connection to target and tunnel traffic
        try:
            tunnel_client_conn = ''
            tunnel_client_addr = ''
            while self.open:
                try:
                    tunnelSock.settimeout(3)
                    tunnel_client_conn, tunnel_client_addr = tunnelSock.accept()
                    tunnelSock.settimeout(None)
                    break
                except socket.timeout:
                    continue
            
            print ('[*] Connecting to target host through tunnel')
            listen_client_conn.send(passwd)
            print ('[*] Connected')
            while self.open:
                data = self.recvall(tunnel_client_conn, RECV_TIMEOUT)
                listen_client_conn.sendall(data)
                data = self.recvall(listen_client_conn, RECV_TIMEOUT)
                tunnel_client_conn.sendall(data)
        except socket.error as msg:
            print ('[*] Socket Closed: ' + str(msg))

    def mode_client(self, listenHost, listenPort, clientHost, clientPort, passwd):
        global serverConnStatus
        global frm
        #1 - Establish connection with listener host
        try:
            print ('[*] Connecting to listening host at ' + listenHost + ':' + str(listenPort))
            listenSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            while self.open:
                try:
                    listenSock.settimeout(3)
                    listenSock.connect((listenHost, listenPort))
                    listenSock.settimeout(None)
                    break
                except (socket.timeout, ConnectionRefusedError):
                    continue
        except socket.error as msg:
            traceback.print_exc()
            print ('[-] Socket Error: ' + str(msg))
            return		
            
        #2 - Send/receive client-listener association to move forward with tunnel establi
        try:
            print ('[*] Establishing association between client and listener')
            listenSock.send(passwd)
            if (listenSock.recv(BUFFER_SIZE) != passwd):
                print ('[-] Failed to associate tunnel')
                serverConnStatus = "DISCONNECTED"
                frm.updateStatusText()
                listenSock.close()
                return
            else:
                print ('[*] Tunnel is now associated on client side')
                serverConnStatus = "CONNECTED"
                frm.updateStatusText()
        except socket.error as msg:
            print ('[-] Tunnel Association Error: ' + str(msg))
            return
        
        #3 - Setup tunneling to client host/service
        try:
            print ('[*] Connecting to tunneled client service at ' + clientHost + ':' + str(clientPort))
            tunnelSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            tunnelSock.connect((clientHost, clientPort))
        except socket.error as msg:
            traceback.print_exc()
            print ('[-] Socket Error: ' + str(msg))
            return	
        
        #4 - Tunnel traffic
        try:
            print ('[*] Connected')
            while self.open:
                data = self.recvall(listenSock, RECV_TIMEOUT)
                tunnelSock.sendall(data)
                data = self.recvall(tunnelSock, RECV_TIMEOUT)
                listenSock.sendall(data)
        except socket.error as msg:
            print ('[*] Socket Closed: ' + str(msg)) 
    

class GUIFrame(wx.Frame):
    
    def __init__(self, parent, title):
        super(GUIFrame, self).__init__(parent, title=title)

        self.InitUI()
        self.Centre()
        self.SetMaxSize(wx.Size(width=400, height=250))
        self.SetMinSize(wx.Size(width=400, height=250))
    def InitUI(self):

        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.sm = wx.GridSizer(2, 3, 5, 5)

        self.SetBackgroundColour("WHITE")
        self.clientModeBtn = wx.Button(self, label='Client')
        self.clientModeBtn.Bind(wx.EVT_BUTTON, self.startClientMode)
        self.serverModeBtn = wx.Button(self, label='Server')
        self.serverModeBtn.Bind(wx.EVT_BUTTON, self.startServerMode)
        self.sm.AddMany([
            wx.StaticText(self),
            (wx.StaticText(self, label="Choose a mode"), wx.ALIGN_CENTER , wx.ALIGN_CENTER),
            wx.StaticText(self),

            (self.clientModeBtn, wx.ALIGN_CENTER , wx.ALIGN_CENTER),
            wx.StaticText(self),
            (self.serverModeBtn, wx.ALIGN_CENTER , wx.ALIGN_CENTER)
        ])
        self.vbox.Add(self.sm, proportion=1, flag=wx.EXPAND)
        self.SetSizer(self.vbox)
    
    def startClientMode(self, event):
        self.vbox.Hide(self.sm)
        self.vbox.Remove(self.sm)
        frm.SetTitle("CWST Client - Nick Z.")
        gs = wx.GridSizer(5, 3, 5, 5)
        self.rshIn = wx.TextCtrl(self)
        self.rspIn = wx.TextCtrl(self, value="6830")
        self.sahIn = wx.TextCtrl(self, value="localhost")
        self.sapIn = wx.TextCtrl(self)
        self.serverStatus = wx.StaticText(self, label=serverStatus)
        self.serverStatus.SetForegroundColour((255,0,0))
        self.serverConnStatus = wx.StaticText(self, label=serverConnStatus)
        self.startButton = wx.Button(self, label='Start Server')
        self.startButton.Bind(wx.EVT_BUTTON, self.clientStartServer)
        self.stopButton = wx.Button(self, label='Stop Server')
        self.stopButton.Bind(wx.EVT_BUTTON, self.stopServer)
        gs.AddMany([
            (wx.StaticText(self, label="Remote CWST server"), wx.ALIGN_CENTER , wx.ALIGN_CENTER),
            wx.StaticText(self),
            (wx.StaticText(self, label="Serving app"), wx.ALIGN_CENTER , wx.ALIGN_CENTER),

            (self.rshIn, wx.ALIGN_CENTER , wx.ALIGN_CENTER),
            (wx.StaticText(self, label="←   Host   →"), wx.ALIGN_CENTER , wx.ALIGN_CENTER),
            (self.sahIn, wx.ALIGN_CENTER , wx.ALIGN_CENTER),

            (self.rspIn, wx.ALIGN_CENTER , wx.ALIGN_CENTER),
            (wx.StaticText(self, label="←   Port   →"), wx.ALIGN_CENTER , wx.ALIGN_CENTER),
            (self.sapIn, wx.ALIGN_CENTER , wx.ALIGN_CENTER),

            (wx.StaticText(self, label="Server status:"), wx.ALIGN_CENTER , wx.ALIGN_CENTER),
            (self.serverStatus, wx.ALIGN_CENTER , wx.ALIGN_CENTER),
            (self.serverConnStatus, wx.ALIGN_CENTER , wx.ALIGN_CENTER),
            
            wx.StaticText(self),
            self.startButton,
            self.stopButton,
            ])

        self.vbox.Add(gs, proportion=1, flag=wx.EXPAND)
        self.Layout()
        self.Fit()

    def startServerMode(self, event):
        self.vbox.Hide(self.sm)
        self.vbox.Remove(self.sm)
        frm.SetTitle("CWST Server - Nick Z.")

        gs = wx.GridSizer(5, 3, 5, 5)
        self.SetBackgroundColour("WHITE")
        self.cacIn = wx.TextCtrl(self, value="6820")
        self.icIn = wx.TextCtrl(self, value="6830")
        self.serverStatus = wx.StaticText(self, label=serverStatus)
        self.serverStatus.SetForegroundColour((255,0,0))
        self.serverConnStatus = wx.StaticText(self, label=serverConnStatus)
        self.startButton = wx.Button(self, label='Start Server')
        self.startButton.Bind(wx.EVT_BUTTON, self.serverStartServer)
        self.stopButton = wx.Button(self, label='Stop Server')
        self.stopButton.Bind(wx.EVT_BUTTON, self.stopServer)
        gs.AddMany([
            (wx.StaticText(self, label="Ports"), wx.ALIGN_CENTER , wx.ALIGN_CENTER),
            wx.StaticText(self),
            wx.StaticText(self),

            (wx.StaticText(self, label="Client app connection"), wx.ALIGN_CENTER , wx.ALIGN_CENTER),
            wx.StaticText(self),
            (wx.StaticText(self, label="Incoming connection"), wx.ALIGN_CENTER , wx.ALIGN_CENTER),

            (self.cacIn, wx.ALIGN_TOP , wx.ALIGN_CENTER),
            wx.StaticText(self),
            (self.icIn, wx.ALIGN_TOP , wx.ALIGN_CENTER),

            (wx.StaticText(self, label="Server status:"), wx.ALIGN_CENTER , wx.ALIGN_CENTER),
            (self.serverStatus, wx.ALIGN_CENTER , wx.ALIGN_CENTER),
            (self.serverConnStatus, wx.ALIGN_CENTER , wx.ALIGN_CENTER),
            
            wx.StaticText(self),
            self.startButton,
            self.stopButton,
            ])

        self.vbox.Add(gs, proportion=1, flag=wx.EXPAND)
        self.Layout()
        self.Fit()

    def clientStartServer(self, event):
        global serverStatus
        
        if (serverStatus == "STOPPED"):#gather inputs from GUI text fields
            rs_host = self.rshIn.GetLineText(0)
            sa_host = self.sahIn.GetLineText(0)
            rs_port = ''.join(filter(lambda i: i.isdigit(), self.rspIn.GetLineText(0)))
            sa_port = ''.join(filter(lambda i: i.isdigit(), self.sapIn.GetLineText(0)))
            if ((not rs_host) or (not rs_port) or (not sa_port) or (not sa_host)):
                wx.MessageDialog(self,
                    "Cannot start server: one or more of your inputs was left blank",
                    caption="Invalid", style=wx.OK|wx.CENTRE).ShowModal()
            else:
                rs_port = int(rs_port)
                sa_port = int(sa_port)
                options = {
                    "mode": 'client', #-m Modes- listener or client (string)
                    "passwd": CWSTpassword, #-p Passphrase for Authentication (bytes string)
                    "listener": rs_host + ':' + str(rs_port), #-l Listener Socket- host:port (i.e. 192.168.0.112:443) (string)
                    #"tunnelport": 0, #-t Tunnel port for listener (int)
                    "client": sa_host + ':' + str(sa_port), #-c Client Socket- host:port (i.e. 192.168.1.100:3389) (string)
                }
                serverStatus = 'RUNNING'
                start_new_thread(setup, (options,))
                self.updateStatusText()
        else:
            wx.MessageDialog(self,
                    "The server is already running.  Please stop it before starting again.",
                    caption="Already running", style=wx.OK|wx.CENTRE).ShowModal()
    
    def serverStartServer(self, event):
        global serverStatus
        if (serverStatus == "STOPPED"):
            server1_port = ''.join(filter(lambda i: i.isdigit(), self.cacIn.GetLineText(0)))
            server2_port = ''.join(filter(lambda i: i.isdigit(), self.icIn.GetLineText(0)))
            if ((not server1_port) or (not server2_port)):
                wx.MessageDialog(self,
                    "One or more of your ports were left blank",
                    caption="Invalid", style=wx.OK|wx.CENTRE).ShowModal()
            else:
                server1_port = int(server1_port)
                server2_port = int(server2_port)
                serverStatus = "RUNNING"
                self.updateStatusText()
                options = {
                    "mode": 'listener', #-m Modes- listener or client (string)
                    "passwd": CWSTpassword, #-p Passphrase for Authentication (bytes string)
                    "listener": ':' + str(server2_port), #-l Listener Socket- host:port (i.e. 192.168.0.112:443) (string)
                    "tunnelport": server1_port, #-t Tunnel port for listener (int)
                    #"client": sa_host + ':' + str(sa_port), #-c Client Socket- host:port (i.e. 192.168.1.100:3389) (string)
                }
                start_new_thread(setup, (options,))
        else:
            wx.MessageDialog(self,
                    "The server is already running.  Please stop it before starting again.",
                    caption="Already running", style=wx.OK|wx.CENTRE).ShowModal()

    def updateStatusText(self):
        global serverStatus
        global serverConnStatus
        self.serverConnStatus.SetLabel(serverConnStatus)
        self.serverStatus.SetLabel(serverStatus)
        if (serverStatus == "RUNNING"):
            self.serverStatus.SetForegroundColour((0,200,0))
        elif (serverStatus == "STOPPING"):
            self.serverStatus.SetForegroundColour((242, 153, 0))
        else:
            self.serverStatus.SetForegroundColour((255,0,0))
    
    def stopServer(self, event):
        global serverStatus
        global serverConnStatus
        global cla
        if (serverStatus == "RUNNING"):
            serverStatus = "STOPPING"
            self.updateStatusText()
            cla.open = False
        else:
            wx.MessageDialog(self,
                    "The server is already stopped.",
                    caption="Already stopped", style=wx.OK|wx.CENTRE).ShowModal()



def Main():
    app = wx.App()
    global frm
    frm = GUIFrame(None, title='CWST - Nick Z.')
    frm.Show()
    app.MainLoop()

def setup(options):
    global serverStatus
    global serverConnStatus
    global frm
    global cla
    cla = actionFuncs(options)
    while serverStatus == "RUNNING":
        cla.start()
        print("restarted")
    cla = ''
    serverStatus = "STOPPED"
    serverConnStatus = "DISCONNECTED"
    frm.updateStatusText()


    
if __name__ == "__main__":
    Main()
    # options = {
    #     "mode": 'listener', #-m Modes- listener or client (string)
    #     "passwd": 'test123', #-p Passphrase for Authentication (string)
    #     "listener": ':6820', #-l Listener Socket- host:port (i.e. 192.168.0.112:443) (string)
    #     "tunnelport": '4050', #-t Tunnel port for listener (int)
    #     "client": 'localhost:6820', #-c Client Socket- host:port (i.e. 192.168.1.100:3389) (string)
    # }
    #     On the socket server machine, setup pyrevtun in listener mode:
    # python pyrevtun.py -m listener -l [IP:port] -t [local tunnel port] -s [certificate file] -k [private key file] -p [auth password]
    # e.g. python pyrevtun.py -m listener -l 192.168.1.59:443 -t 33389 -s example_cert.pem -k example_key.pem -p pass
    # listener (server) mode required inputs: -m -p -l -t
    
    # On socket client machine, setup pyrevtun in client mode:
    # python pyrevtun.py -m client -l [listener IP:port] -c [target IP:port] -p [auth password]
    # e.g. python pyrevtun.py -m client -l 192.168.102.59:443 -c 10.5.5.5:3389 -p pass
    # This connection will open up the chosen local port on the pen test machine.
    # Using TCP app (i.e. RDP, SSH client), connect to specified local port as [localhost:local tunnel port]
    # e.g. localhost:33389
    # client mode required inputs: -m -p -l -c
    