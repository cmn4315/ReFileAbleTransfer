import socket
import struct
import time
import argparse

def get_packet(pktnum: int, data: bytes, pktsize: int = 52, seqnum: int = -1):
    """ Get the portion of data that the {pktnum}th packet should contain, and add some RDT header info. 
    """
    if(seqnum == -1):
        seqnum = pktnum
    pktdata = data[pktnum*pktsize:int(((pktnum*pktsize) + pktsize if (pktnum*pktsize) + pktsize < len(data) else len(data)))]

    pktdata = struct.pack("!I", seqnum) + pktdata

    return pktdata

class RDTSender():
    def __init__(self, data: bytes, dstip: str = "127.0.0.1", dstport: int = 8081, srcport: int = 8080, window_size = 5,
                 timeout: int = 2, pktsize: int = 52) -> None:
        self.dstip = dstip
        self.dstport = dstport
        self.srcport = srcport
        self.window_size = window_size
        self.run = True
        self.data = data
        self.timeout = timeout
        self.pktsize = pktsize

    def start(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:# this will handle the checksum business for us.
            sock.setblocking(False)
            sock.bind(('127.0.0.1', self.srcport))
            start_time = time.time()
            last_ack = -1
            window_start = 0
            to_send = 0
            last_packet = -1
            while(self.run):
                # Check for ACK recvd
                try:
                    data, addr = sock.recvfrom(1024)  # Try receiving data
                    seq = int.from_bytes(data[:4])
                    data = data[4:]
                    # If correct ack is received, reset timer, slide window forward by difference 
                    # between expected seq num and actual seq num
                    if(data.decode('utf-8') == "RDTAck." and seq > last_ack):
                        start_time = time.time()
                        window_start += (seq - last_ack)
                        last_ack = seq
                        print(f"Sender: received ACK number {seq}")
                        if last_ack >= 0 and last_ack == last_packet:
                            to_send = -1
                    elif(data.decode('utf-8') == "RDTEndAck."):
                        self.run = False
                        print("Sender: received EndAck, Terminating.")
                except BlockingIOError:
                    pass

                if not self.run:
                    break

                # Check timeout 
                if (time.time() - start_time > self.timeout):
                    # reset to send from start of window if timeout happened
                    to_send = window_start
                    start_time = time.time()

                # send next packet iff there is still room in the window
                if to_send < (window_start + self.window_size) and to_send != last_packet:
                    if to_send == -1:
                        print("Sender: sending End. packet")
                        packet = get_packet(0, bytes("RDTEnd.", "utf-8"), seqnum=(last_packet + 1))
                    else:
                        packet = get_packet(to_send, self.data)
                        print(f"Sender: sending packet number {to_send}")
                    sock.sendto(packet, (self.dstip, self.dstport))
                    if len(packet) < (self.pktsize + 4): # if we've reached the end of the data
                        last_packet = to_send
                    else:
                        to_send += 1

class RDTRecvr():
    def __init__(self, srcport: int = 8082) -> None:
        self.srcport = srcport
        self.run = True
        self.recvd_data = bytes("", "utf-8")

    def start(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:# this will handle the checksum business for us.
            last_recvd = -1
            sock.bind(("127.0.0.1", self.srcport))
            while(self.run):
                # Check for ACK recvd
                data, addr = sock.recvfrom(1024)  # Try receiving data
                seq = int.from_bytes(data[:4])
                data = data[4:]
                msg = bytes("", "utf-8")
                if(data.decode('utf-8') == "RDTEnd."):
                    self.run = False
                    msg = bytes("RDTEndAck.", 'utf-8')
                    print("Receiver: received End. Sending EndAck.")
                elif(seq == last_recvd + 1):
                    self.recvd_data += data
                    last_recvd += 1
                    msg = bytes("RDTAck.", 'utf-8')
                    print(f"Receiver: received packet number {seq}")
                sock.sendto(get_packet(0, msg, seqnum=last_recvd), addr)
            print(self.recvd_data)


if __name__ == "__main__":
    # Create the parser
    parser = argparse.ArgumentParser(description='A simple ping utility')
    
    # Add arguments
    parser.add_argument('dst', type=str, default='127.0.0.1', help='The destination IP address for the RDTReceiver')
    parser.add_argument('src', type=str, default='127.0.0.1', help='The destination IP address for the RDTSender')
    parser.add_argument('dstport', type=int, default=8082, help='The destination port for the RDTReceiver')
    parser.add_argument('srcport', type=int, default=8080, help='The destination port for the RDTSender')
    parser.add_argument('middleport', type=int, default=8081, help="The port on which to open the middleman's socket.")
    parser.add_argument('-l', action="store_true", help='Sets the middleman to introduce packet losses. Chance to drop is 5% per packet.')
    parser.add_argument('-r', action="store_true", help='Sets the middleman to introduce packet reordering. Chance to reorder is 10% per packet.')
    parser.add_argument('-c', action="store_true", help='Sets the middleman to introduce packet corruption. Chance to corrupt is 15% per packet.')
    
    args = parser.parse_args()
    main(args.dst, args.src, args.dstport, args.srcport, args.l, args.r, args.c, args.middleport)
 
