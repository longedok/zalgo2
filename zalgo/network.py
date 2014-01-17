import asyncore
import json
import logging
from math import ceil
import socket
from time import sleep

from PyQt4.QtCore import QThread, pyqtSignal, QObject, QByteArray, QMutex, QMutexLocker
from PyQt4.QtGui import qApp

from zalgo.util import Util
from zalgo.database import Database
from zalgo.local_io import FileStreamer
from zalgo.audio import AudioBuffer


class ReceiveStates():
    RECEIVE_HEADER = 0
    RECEIVE_CONTENT = 1
    RECEIVE_COMPLETE = 2


class PacketTypes():
    HANDSHAKE = 0
    HANDSHAKE_ACCEPT = 1
    LOOKUP = 2
    FOUND = 3
    REQUEST_STREAM = 4
    READY_TO_STREAM = 5
    REQUEST_PART = 6
    CONTENT = 7


class Packet(QObject):
    def __init__(self, packetType=-1, additionalHeaders=None, content=None):
        QObject.__init__(self)
        self.header = {'type': packetType,
                       'packet_id': Util.generateId()}
        if isinstance(additionalHeaders, dict):
            for key, value in additionalHeaders.items():
                self.header[key] = value
        if isinstance(content, str):
            self.content = content
        else:
            self.content = ''

    def getBinary(self):
        if self.content and len(self.content) > 0:
            self.header['content_len'] = len(self.content)
        return "%s\0%s" % (json.dumps(self.header), str(self.content))

    def __str__(self):
        type2str = {0: "handshake", 1: "handshake_accept", 2: "lookup",
                    3: "found", 4: "request_stream", 5: "ready_to_stream",
                    6: "request_part", 7: "content"}
        result_string = "%s [id: %s" % (type2str[self.header['type']], self.header['packet_id'])
        if 'stream_id' in self.header:
            result_string += ", sid: %s" % (self.header['stream_id'])
        if 'from' in self.header:
            result_string += ", from: %s" % (self.header['from'])
        if self.content:
            result_string += ", len: %d" % (len(self.content))
        result_string += ']'
        return result_string

    def division_by_zero(self):
        return 1 / 0


class Server(asyncore.dispatcher, QObject):
    MAX_LOOKUP_STACK_LENGTH = 1000
    LOOKUP_HOPS_COUNT = 5
    STREAM_CHUNK_SIZE = 65536
    host_pid = Util.generateId()
    connected_peers = []
    handshaked_peers = []
    recent_lookups = []
    stream_handlers = {}
    sid2filestreamer = {}
    db = Database()
    logger = logging.getLogger('Server')

    def __init__(self, address):
        asyncore.dispatcher.__init__(self)
        QObject.__init__(self)

        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.bind(address)
        self.address = self.socket.getsockname()
        self.listen(1)

    # public interface
    def connectPeer(self, address):
        """

        @rtype : void
        """
        self.logger.debug("connectPeer(%s)" % str(address))
        peer_handler = self.createClientHandler(socket.socket(), address)
        peer_handler.connect(address)

    def search(self, request):
        request = unicode(request)
        request_id = Util.generateId()
        for peer in self.handshaked_peers:
            peer.sendPacket(Packet(PacketTypes.LOOKUP, {"requester_ip": "localhost",
                                                        "request_id": request_id,
                                                        "title": request,
                                                        "artist": "",
                                                        "album": "",
                                                        "hops": self.LOOKUP_HOPS_COUNT}))
        return request_id

    def initiateFileStream(self, peers, hash_):
        stream_handler = None
        stream_id = None
        if len(peers) > 0:
            stream_id = Util.generateId()
            stream_handler = StreamHandler(stream_id, self.STREAM_CHUNK_SIZE)
            print "stream handler created [stream_id: %s]" % stream_id
            for peer in set(peers):
                peer.readyToStream.connect(stream_handler.newPeerReady)
                peer.dataCome.connect(stream_handler.newDataCome)
                peer.sendPacket(Packet(PacketTypes.REQUEST_STREAM, {"hash": hash_,
                                                                    "chunk_size": self.STREAM_CHUNK_SIZE,
                                                                    "stream_id": stream_id}))
                self.stream_handlers[stream_id] = stream_handler
                stream_handler.start()
        if stream_handler:
            return stream_id

    def deleteFileStream(self, stream_id):
        if stream_id in self.stream_handlers:
            self.stream_handlers[stream_id].stop()
            del self.stream_handlers[stream_id]

    def getHandshakedPeers(self):
        return self.handshaked_peers

    def getHostPid(self):
        return self.host_pid

    def createFileStreamer(self, hash_, chunk_size, stream_id):
        path = self.db.getSongLocationByHash(hash_)
        if path:
            self.sid2filestreamer[stream_id] = FileStreamer(path, chunk_size, stream_id)
            return self.sid2filestreamer[stream_id]
        else:
            return None

    def getFileStreamerById(self, stream_id):
        return self.sid2filestreamer[stream_id]

    def getStreamHandlerById(self, stream_id):
        return self.stream_handlers[stream_id]
    # signals
    musicFound = pyqtSignal(unicode, list, QObject)

    # slots
    def peerHandshakedSlot(self, peer):
        self.handshaked_peers.append(peer)

    def peerConnectedSlot(self, peer):
        self.logger.debug("Add connected peer: %s", peer)
        if not peer in self.connected_peers:
            peer.sendPacket(Packet(PacketTypes.HANDSHAKE))
            self.connected_peers.append(peer)

    def peerDisconnectedSlot(self, peer):
        if peer in self.handshaked_peers:
            self.handshaked_peers.remove(peer)
        if peer in self.connected_peers:
            self.connected_peers.remove(peer)

    def musicFoundSlot(self, request_id, music_list, peer):
        self.musicFound.emit(request_id, music_list, peer)

    # asyncore callbacks
    def handle_accept(self):
        pair = self.accept()
        client_sock = pair[0]
        client_addr = pair[1]
        peer = self.createClientHandler(client_sock, client_addr)
        self.connected_peers.append(peer)
        self.logger.debug('handle_accept() -> %s', str(client_addr))

    # private methods
    def createClientHandler(self, sock, addr=None):
        peer_handler = PeerHandler(self, sock, addr)
        peer_handler.connectionComplete.connect(self.peerConnectedSlot)
        peer_handler.handshakeComplete.connect(self.peerHandshakedSlot)
        peer_handler.musicFound.connect(self.musicFoundSlot)
        peer_handler.disconnect.connect(self.peerDisconnectedSlot)
        return peer_handler


class NetworkThread(QThread):

    def __init__(self, host_address):
        self.server = Server(host_address)
        QThread.__init__(self)
        self.start()

    def run(self):
        asyncore.loop(timeout=0)


class PeerHandler(asyncore.dispatcher, QObject):
    chunk_size = 8192
    to_receive = 0
    audio_buffer = ""
    current_packet = Packet()
    peer_id = u""
    data_to_write = []
    state = ReceiveStates.RECEIVE_HEADER
    logger = None
    db = Database()

    def __init__(self, server, sock, remote_addr=None):
        QObject.__init__(self)

        self.server = server
        self.remote_addr = remote_addr
        if remote_addr:
            self.logger = logging.getLogger('\nPeerHandler(not yet connected)')
        else:
            self.logger = logging.getLogger('\nPeerHandler%s' % str(self.addr))

        asyncore.dispatcher.__init__(self, sock=sock)

    # public interface
    def sendPacket(self, packet):
        self.data_to_write.append(packet.getBinary())
        self.logger.debug("[SENT] %s" % packet)

    def getRemoteAddr(self):
        return self.addr

    # signals
    musicFound = pyqtSignal(unicode, list, QObject)
    handshakeComplete = pyqtSignal(QObject)
    connectionComplete = pyqtSignal(QObject)
    disconnect = pyqtSignal(QObject)
    readyToStream = pyqtSignal(unicode, int, QObject)
    dataCome = pyqtSignal(QByteArray, int, QObject)

    # asyncore callbacks
    def writable(self):
        if not self.connected:
            return True
        response = bool(self.data_to_write)
        return response

    def handle_connect(self):
        self.connected = True
        self.logger = logging.getLogger('\nPeerHandler%s' % str(self.socket.getsockname()))
        self.logger.debug("handle_connect")
        self.connectionComplete.emit(self)

    def handle_write(self):
        if len(self.data_to_write) == 0:
            return
        data = self.data_to_write.pop()
        sent = self.send(data[:self.chunk_size])
        if sent < len(data):
            remaining = data[sent:]
            self.data_to_write.append(remaining)

    def handle_read(self):
        data = self.recv(self.chunk_size)
        self.buffer += data
        if self.state == ReceiveStates.RECEIVE_HEADER:
            null_pos = self.buffer.find('\0')
            if null_pos > -1:
                header = self.buffer[:null_pos]
                self.buffer = self.buffer[null_pos+1:]
                try:
                    parsed_header = json.loads(header)
                except TypeError:
                    self.logger.error("ERROR: can't parse json header")
                except ValueError, err:
                    self.logger.error("ERROR: %s" % err)
                else:
                    self.packet = Packet()
                    self.packet.header = parsed_header
                    self.to_receive = parsed_header.get('content_len')
                    if self.to_receive:
                        self.state = ReceiveStates.RECEIVE_CONTENT
                    else:
                        self.state = ReceiveStates.RECEIVE_COMPLETE
        if self.state == ReceiveStates.RECEIVE_CONTENT:
            if len(self.buffer) >= self.to_receive:
                self.packet.content = self.buffer[:self.to_receive]
                self.buffer = self.buffer[self.to_receive:]
                self.state = ReceiveStates.RECEIVE_COMPLETE
        if self.state == ReceiveStates.RECEIVE_COMPLETE:
            self.state = ReceiveStates.RECEIVE_HEADER
            self.handlePacket(self.packet)
            self.logger.debug("[RECEIVED] %s" % self.packet)

    def handle_close(self):
        self.logger.debug('handle_close()')
        self.disconnect.emit(self)
        self.close()

    # private methods
    def handlePacket(self, packet):
        packet_type = packet.header.get('type')
        if packet_type == PacketTypes.HANDSHAKE:
            self.peer_id = packet.header.get('peer_id')
            other_peers = [peer.getRemoteAddr() for peer in self.server.getHandshakedPeers()]
            header = {'peer_id': self.server.getHostPid()}
            if len(other_peers) > 0:
                header['peers'] = other_peers
            self.sendPacket(Packet(PacketTypes.HANDSHAKE_ACCEPT, header))
            self.handshakeComplete.emit(self)
            self.logger.debug("Handshake")
        if packet_type == PacketTypes.HANDSHAKE_ACCEPT:
            self.peer_id = packet.header.get('peer_id')
            self.handshakeComplete.emit(self)
        if packet_type == PacketTypes.LOOKUP:
            request_id = packet.header.get('request_id')
            requester_ip = packet.header.get('requester_ip')
            if requester_ip == "localhost":
                requester_ip = "%s:%s" % self.socket.getsockname()
            artist = packet.header.get('artist') or ''
            title = packet.header.get('title') or ''
            album = packet.header.get('album') or ''
            results = self.db.lookupSong((title, artist, album))
            if results:
                result_list = list()
                for result in results:
                    result_dict = dict()
                    result_dict['hash'] = result[0]
                    result_dict['album'] = result[1]
                    result_dict['title'] = result[2]
                    result_dict['artist'] = result[3]
                    result_list.append(result_dict)
                found_packet = Packet(PacketTypes.FOUND, {'results': result_list, "request_id": request_id})
                self.sendPacket(found_packet)
            hops = packet.header.get('hops')
            packet_id = packet.header.get('packet_id')
            if hops > 0 and not (packet_id in self.server.recent_lookups):
                forward_packet = Packet(PacketTypes.LOOKUP, {'requester_ip': requester_ip,
                                                             'artist': artist, 'title': title, 'album': album,
                                                             'hops': hops - 1,
                                                             'packet_id': packet_id, "request_id": request_id})
                for other_peer in self.server.getHandshakedPeers():
                    if other_peer != self:
                        other_peer.sendPacket(forward_packet)
            elif hops > 0:
                if len(self.server.recent_lookups) < self.server.MAX_LOOKUP_STACK_LENGTH:
                    self.server.recent_lookups.pop()
                self.server.recent_lookups.insert(0, packet_id)
        if packet_type == PacketTypes.FOUND:
            self.musicFound.emit(packet.header.get('request_id'),
                    packet.header.get('results'), self)
        if packet_type == PacketTypes.REQUEST_STREAM:
            song_hash = packet.header.get('hash')
            chunk_size = packet.header.get('chunk_size')
            stream_id = packet.header.get('stream_id')
            file_streamer = self.server.createFileStreamer(song_hash, chunk_size, stream_id)
            if file_streamer:
                self.sendPacket(Packet(PacketTypes.READY_TO_STREAM, {'stream_id': stream_id, 'size': file_streamer.getSize()}))
        if packet_type == PacketTypes.READY_TO_STREAM:
            stream_id = packet.header.get('stream_id')
            file_size = packet.header.get('size')
            self.readyToStream.emit(stream_id, file_size, self)
        if packet_type == PacketTypes.REQUEST_PART:
            stream_id = packet.header.get('stream_id')
            from_ = packet.header.get('from')
            streamer = self.server.getFileStreamerById(stream_id)
            self.sendPacket(Packet(PacketTypes.CONTENT, {'stream_id': stream_id, 'from': from_},
                streamer.getChunk(from_)))
        if packet_type == PacketTypes.CONTENT:
            from_ = packet.header.get('from')
            self.dataCome.emit(QByteArray(packet.content), from_, self)


class StreamHandler(QThread):
    def __init__(self, stream_id, chunk_size):
        QThread.__init__(self)
        self.current_packet_number = 0
        self.last_packet_number = 0
        self.last_received_packet_number = 0
        self.skipped_packets = []
        self.not_appended_packets = {}
        self.chunks_count = 0
        self.mutex_new_peer_ready = QMutex()
        self.mutex_new_data_come = QMutex()
        self.peers = []
        self.receive_complete = False
        self.file_size = 0
        self.stream_id = stream_id
        self.chunk_size = chunk_size
        self.buffer = None

    # slots
    def newPeerReady(self, stream_id, file_size, peer):
        print "new peer ready [stream id: %s]" % stream_id
        with QMutexLocker(self.mutex_new_peer_ready):
            print "inside mutex"
            print peer
            print self.peers
            if not peer in self.peers and (self.stream_id == stream_id) and (file_size > 0):
                print "stream_id is right and file_size is ok"
                self.peers.append(peer)
                if len(self.peers) == 1:
                    print "self.peers len is exactly 1"
                    self.buffer = AudioBuffer(file_size)
                    self.file_size = file_size
                    self.chunks_count = ceil(file_size / self.chunk_size)
                    self.start()

    def newDataCome(self, data, from_, peer):
        with QMutexLocker(self.mutex_new_data_come):
            if peer in self.peers:
                data = str(data)
                self.buffer.receive_data(data)

    def get_audio_buffer(self):
        while self.buffer is None:
            qApp.processEvents()
            sleep(0.01)

        return self.buffer

    def stop(self):
        self.receive_complete = True

    # QThread methods
    def run(self):
        print "stream handler started [stream_id: %s, chunks_count: %d]" % (self.stream_id, self.chunks_count)
        while self.buffer is None:
            qApp.processEvents()
            sleep(0.01)
        while not self.receive_complete:
            for peer in self.peers:
                print "new request packet sent [stream_id: %s, n: %d]" % (self.stream_id, self.current_packet_number)
                print "current packet number: %d" % self.current_packet_number
                print "chunks count: %d" % self.chunks_count
                print "buffer size: %d" % self.buffer.size()
                print "bytes available: %d" % self.buffer.size()
                peer.sendPacket(Packet(PacketTypes.REQUEST_PART, {"stream_id": self.stream_id,
                                    "from": self.current_packet_number}))
            if self.current_packet_number >= self.chunks_count:
                break
            else:
                self.current_packet_number += 1
            sleep(0.01)