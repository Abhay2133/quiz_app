import logging
import socket as socket_module
from sys import exit
from selectors import DefaultSelector, EVENT_READ, EVENT_WRITE
from types import SimpleNamespace
from threading import Thread
from socket import socket, SOCK_STREAM, AF_INET, error as SocketError
from .logger import get_logger
from ..config import config

logger = get_logger("network")
magicKey = config.get("network.magic_key", "India").encode() if isinstance(config.get("network.magic_key", "India"), str) else config.get("network.magic_key", b"India")

class EventEmitter:
    def __init__(self):
        self.__events = dict()
        self.__listen = None
        self.stop = False

    def attach(self, listener):
        "Attach a global listener which will be called at every event"
        self.__listen = listener
    
    def on(self, name, callback):
        # if self.stop : return
        if not bool(self.__events.get(name)):
            self.__events[name] = list()
        self.__events[name].append(callback)
        
        return len(self.__events[name])-1

    def emit(self, name, *args):
        if self.__listen:
            self.__listen(name, args)
        if name not in self.__events:
            return

        for callback in self.__events[name]:
            callback(args)
        pass

    def off(self,name, index:int=None):
        if not self.__events.get(name):
            return 
        if index is None:
            self.__events[name].clear()
        elif index < len(self.__events[name]):self.__events[name].pop(index)
    
    def off_all(self):
        for name in self.__events:
            self.off(name)

class Client():
    inb:list=None
    outb:list=None

class ServerSocket(EventEmitter):

    def __init__(self, addr:tuple) -> None:
        "pass the ip address and port number as argument in a tuple"
        super().__init__()
        self.sel = DefaultSelector()
        self.clients = dict() # { portNumber<id[int]> : key<keySelector>}
        self.killThread = True
        self.eventThread = None
        self.ssock = None
        self.addr = addr
        pass

    def start(self):
        self.killThread = False
        if self.eventThread:
            logger.warning("Server already started")
            return
        
        try:
            self.ssock = socket(AF_INET, SOCK_STREAM)
            # Allow address reuse to avoid "Address already in use" errors
            self.ssock.setsockopt(socket_module.SOL_SOCKET, socket_module.SO_REUSEADDR, 1)
            self.ssock.bind(self.addr)
            self.ssock.listen()
            logger.info(f"Server listening at {self.addr}")
            self.sel.register(self.ssock, EVENT_READ, data=None)

            self.eventThread = Thread(target=self._server_event_loop, daemon=True)
            self.eventThread.start()
        except OSError as e:
            logger.error(f"Failed to start server on {self.addr}: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.critical(f"Unexpected error starting server: {e}", exc_info=True)
            raise

    def sendTo(self, message:bytes|str,clientID=None):
        if type(message) is str:
            message = bytes(message, encoding="utf-8")

        if clientID not in self.clients:
            error_msg = f"Client ID '{clientID}' not found"
            logger.warning(error_msg)  # Warning instead of error - recoverable condition
            raise Exception(error_msg)

        client_key = self.clients[clientID]
        data = client_key.data
        data.outb += message
        logger.debug(f"Message queued for client {clientID}")

    def sendAllTo(self, message:bytes, clientID):
        if type(message) is str:
            message = bytes(message, encoding="utf-8")

        if clientID not in self.clients:
            raise Exception(f"Client ID '{clientID}' not found")

        client_key = self.clients[clientID]
        csoc = client_key.fileobj
        # data.outb += message
        csoc.sendall(message)

    def broadcast(self, message:bytes):
        for clientID in self.clients:
            self.sendAllTo(message, clientID)

    def stop(self):
        while self.eventThread:
            self.killThread = True

    def handshake(self, data):  # receive handshake -> send handshake
        """
        Perform handshake with client.
        Uses atomic stage checks to prevent race conditions.
        """
        stage = data.handshakeStage
        if stage == 1:
            # Stage 1: Verify received magic key
            if data.inb == magicKey:
                data.inb = b""
                logger.debug(f"Handshake stage 1 passed for client {data.addr[1]}")
            else:
                error_msg = f"Magic key mismatch for client {data.addr[1]}, received: {data.inb}"
                logger.warning(error_msg)
                self.emit("handshake-failed", (stage, data.addr[1]))
                return
        elif stage == 2:
            # Stage 2: Send magic key response
            data.outb = magicKey
            logger.debug(f"Sending handshake response to client {data.addr[1]}")
        # Note: Stage 3 (done) is set in __handle_RW_events after successful send

    def __add_connection(self, key):
        soc = key.fileobj
        conn, addr = soc.accept()
        clientID = addr[1]
        data = SimpleNamespace(addr=addr, outb=b"", inb=b"", clientID=clientID, handshakeStage=0)
        # HANDSHAKE STAGES # 1 -> Recieved | 2 -> Sent | 3 -> DONE
        self.sel.register(conn, EVENT_READ | EVENT_WRITE, data=data)
        self.clients[clientID] = SimpleNamespace(fileobj=conn, data=data)
        self.emit("new-connection", clientID)

    def __handle_RW_events(self, key, mask):
        soc = key.fileobj
        data = key.data
        if mask & EVENT_READ:
            try:
                recv = soc.recv(1024)
                if not recv:
                    # Connection closed
                    self._disconnect(key)
                    return
                    
                data.inb += recv
                
                # Handle handshake stage 0 -> 1 (receive magic key)
                if data.handshakeStage == 0:
                    data.handshakeStage = 1
                    self.handshake(data)
                    return
                
                # Only emit data-packet after handshake is complete
                if data.handshakeStage >= 3:
                    self.emit("data-packet", {"clientID": data.clientID, "data": recv})
            except SocketError as e:
                logger.error(f"Socket read error for client {data.clientID}: {e}")
                self._disconnect(key)
                return
                
        if mask & EVENT_WRITE:
            try:
                # Handle handshake stage 1 -> 2 (send magic key)
                if data.handshakeStage == 1:
                    data.handshakeStage = 2
                    self.handshake(data)
                
                # Send queued output data
                sent = 0
                if data.outb:
                    sent = soc.send(data.outb)
                    data.outb = data.outb[sent:]

                # Verify handshake completion after successful send
                if data.handshakeStage == 2 and not data.outb:
                    # All handshake data sent successfully
                    data.handshakeStage = 3  # handshake done
                    logger.info(f"Handshake completed with {data.addr}")
                    self.emit("handshake-done", data.clientID)
                
                # Emit data event and flush input buffer (only after handshake complete)
                if data.handshakeStage >= 3 and data.inb:
                    self.emit("data", {"clientID": data.clientID, "data": data.inb})
                    data.inb = b""
            except SocketError as e:
                logger.error(f"Socket write error for client {data.clientID}: {e}")
                self._disconnect(key)
                return
        
    def _server_event_loop(self):
        logger.info("Server event loop started")
        while not self.killThread:
            lastConnKey = None
            
            try:
                events = self.sel.select(timeout=None)
                for key, mask in events:
                    lastConnKey = key
                    if key.data is None:
                        # add new client
                        self.__add_connection(key)
                    else:
                        # read / write clients
                        self.__handle_RW_events(key=key, mask=mask)

            except KeyboardInterrupt:
                logger.info("Server interrupted by keyboard")
                exit(1)
            except SocketError as e:
                logger.error(f"Socket error in event loop: {e}", exc_info=True)
                if lastConnKey:
                    self._disconnect(lastConnKey)
            except Exception as e:
                logger.error(f"Error in server event loop: {e}", exc_info=True)
                if lastConnKey:
                    self._disconnect(lastConnKey)
            finally:
                pass

        self.eventThread = None
        logger.info("Server event loop ended")

    def _disconnect(self, key):
        sock = None
        clientID = None
        
        if key.data is None:
            logger.warning("No `data` attr found in `key` during disconnect")
            return
        
        try:
            sock = key.fileobj
            clientID = key.data.addr[1]

            self.sel.unregister(sock)
            sock.close()

            if clientID in self.clients:
                self.clients.pop(clientID)
                logger.info(f"Client {clientID} disconnected and removed")
        except KeyError:
            logger.debug(f"Client {clientID} already removed")
        except Exception as e:
            logger.error(f"Error during disconnect: {e}", exc_info=True)
        else:
            self.emit("disconnected", clientID)

class ClientSocket(EventEmitter):
    sel = None
    addr = None
    data = None
    eventThread = None
    csoc = None
    handshakeStage = 0 #  1 -> send | 2 -> recived | 3 -> DONE
    stopThread=False

    def __init__(self, addr) -> None:
        super().__init__()
        self.sel = DefaultSelector()
        self.addr = addr

    def handshake(self, recv=None):  # to verify the connection with server
        if self.handshakeStage == 3:
            logger.debug("Handshake already completed")
            return
        
        try:
            if self.handshakeStage == 1:
                logger.debug(f"Sending handshake to {self.addr}")
                self.csoc.send(magicKey)
                return
            
            if self.handshakeStage == 2:
                if recv == magicKey:
                    self.handshakeStage = 3
                    logger.info(f"Handshake completed with {self.addr}")
                    self.emit("handshake-done", None)
                else:
                    error = Exception(f"MAGIC KEY DOES NOT MATCH, {recv} != {magicKey}")
                    logger.error(f"Handshake failed: {error}")
                    self.emit("handshake-error", error)

        except SocketError as e:
            logger.error(f"Socket error during handshake: {e}", exc_info=True)
            self.emit("handshake-error", e)
        except Exception as e:
            logger.error(f"Handshake failed: {e}", exc_info=True)
            self.emit("handshake-error", e)

    def connect(self):
        """
        Connect to server asynchronously.
        Starts event loop thread to handle connection.
        """
        try:
            csoc = socket(AF_INET, SOCK_STREAM)
            csoc.setblocking(False)
            err = csoc.connect_ex(self.addr)
            # 0 = success, 115 = EINPROGRESS (Linux), 36 = EINPROGRESS (macOS)
            if err != 0 and err != 115 and err != 36:
                raise SocketError(f"Connection failed with error {err}")
            
            events = EVENT_WRITE | EVENT_READ

            self.data = SimpleNamespace(inb = b"", outb=b"")
            self.sel.register(csoc, events, data=self.data)
            self.csoc = csoc

            self.eventThread = Thread(target=self._client_event_loop, daemon=True)
            self.eventThread.start()
            logger.info(f"Connection attempt initiated to {self.addr}")
        except SocketError as e:
            logger.error(f"Socket error during connect: {e}", exc_info=True)
            self.emit("error", e)
            raise
        except Exception as e:
            logger.error(f"Unexpected error during connect: {e}", exc_info=True)
            self.emit("error", e)
            raise

    def disconnect(self):
        logger.info(f"Disconnecting from {self.addr}")
        try:
            if self.csoc:
                self.sel.unregister(self.csoc)
        except (KeyError, ValueError):
            logger.debug("Socket already unregistered")
        except Exception as e:
            logger.warning(f"Error unregistering socket: {e}")
        
        try:
            if self.csoc:
                self.csoc.close()
        except Exception as e:
            logger.warning(f"Error closing socket: {e}")
        
        self.csoc = None
        self.stopThread = True

    def send(self, message:bytes):
        self.data.outb += message

    def __handle_RW_events(self, key, mask):
        sock = key.fileobj
        data = key.data
        if mask & EVENT_READ: # ready to read
            try:
                recv_data = sock.recv(1024)
                if not recv_data:
                    # Connection closed
                    logger.info("Server closed connection")
                    self.emit("disconnected")
                    return
                
                # Handle handshake stage 1 -> 2 (receive magic key from server)
                if self.handshakeStage == 1:
                    self.handshakeStage = 2
                    self.handshake(recv_data)
                    return
                
                # Only process data after handshake is complete
                if self.handshakeStage >= 3:
                    data.inb += recv_data
                    self.emit("data-packet", recv_data)
            except SocketError as e:
                logger.error(f"Socket read error: {e}", exc_info=True)
                self.emit("error", e)
                self.emit("disconnected")
                return
                
        if mask & EVENT_WRITE: # ready to write
            try:
                # Handle handshake stage 0 -> 1 (send magic key to server)
                if self.handshakeStage == 0:
                    self.handshakeStage = 1
                    self.handshake()
                
                # Send queued output data
                if data.outb:
                    sent = sock.send(data.outb) 
                    data.outb = data.outb[sent:]
                
                # Emit data event and flush input buffer (only after handshake complete)
                if self.handshakeStage >= 3 and data.inb:
                    self.emit("data", data.inb)
                    data.inb = b"" # flush input buffer
            except SocketError as e:
                logger.error(f"Socket write error: {e}", exc_info=True)
                self.emit("error", e)
                self.emit("disconnected")
                return

    def _client_event_loop(self):
        logger.info(f"Client event loop started for {self.addr}")
        try:
            while True:
                if self.stopThread:
                    self.stopThread = False
                    logger.info("Client event loop stopped by flag")
                    return
                events = self.sel.select(timeout=None)
                for key, mask in events:
                    self.__handle_RW_events(key, mask)
        except KeyboardInterrupt:
            logger.info("Client interrupted by keyboard")
            exit(2)
        except SocketError as e:
            logger.error(f"Socket error in client event loop: {e}", exc_info=True)
            self.emit("error", e)
            try:
                self.sel.close()
            except Exception:
                pass
            self.emit("disconnected")
        except Exception as e:
            logger.error(f"Error in client event loop: {e}", exc_info=True)
            self.emit("error", e)
            try:
                self.sel.close()
            except Exception:
                pass
            self.emit("disconnected")
        finally:
            pass
        logger.info("Client event loop ended")

if __name__ == "__main__":
    ee = EventEmitter()
    ee.on("call", lambda arr : print(arr))
    ee.emit("call", 1,2,3,4)