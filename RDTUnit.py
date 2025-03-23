import socket
import struct
import time
import argparse


def calculate_checksum(data):
    """Calculate the checksum for a given piece of data and return the calculated checksum.
    :param data: the data for which to calculate the checksum
    """
    checksum = 0

    # Handle odd-length data
    if len(data) % 2 != 0:
        data += b"\x00"

    # Calculate checksum
    for i in range(0, len(data), 2):
        checksum += (data[i] << 8) + data[i+1] # sum the bits
        checksum = (checksum >> 16) + (checksum & 0xffff) # handle overflow


    return (~checksum) & 0xffff # 1s complement


def get_packet(pktnum: int, data: bytes, pktsize: int = 64, seqnum: int = -1):
    """ Get the portion of data that the {pktnum}th packet should contain, and add some RDT header info. 
    :param pktnum: the index of the packet to get from the data
    :param data: the data to extract packets from
    :param pktsize: the number of data bytes to include in each packet
    :param seqnum: the RDT sequence number to attach to the packet. if seqnum is not provided, pktnum is used instead.
    """
    if(seqnum == -1):
        seqnum = pktnum
    pktdata = data[pktnum*pktsize:int(((pktnum*pktsize) + pktsize if (pktnum*pktsize) + pktsize < len(data) else len(data)))]

    pktdata = struct.pack("!I", seqnum) + pktdata
    checksum = calculate_checksum(pktdata)

    pktdata = struct.pack("!H", checksum) + pktdata

    return pktdata

class RDTSender():
    def __init__(self, data: bytes, dstip: str = "127.0.0.1", dstport: int = 8081, srcport: int = 8080, window_size = 10,
                 timeout: int = 1, pktsize: int = 64) -> None:
        self.dstip = dstip
        self.dstport = dstport
        self.srcport = srcport
        self.window_size = window_size
        self.run = True
        self.data = data
        self.timeout = timeout
        self.pktsize = pktsize
        self.kill_timeout = 10

    def start(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:# this will handle the checksum business for us.
            sock.setblocking(False)
            sock.bind(('127.0.0.1', self.srcport))
            start_time = time.perf_counter()
            last_ack = -1
            window_start = 0
            to_send = 0
            last_packet = -1
            end_time = -1
            resend_last = False
            while(self.run):
                # Check for ACK recvd
                try:
                    data, addr = sock.recvfrom(1024)  # Try receiving data
                    checksum = data[:2]
                    calcdchecksum = calculate_checksum(data[2:])
                    seq = int.from_bytes(data[2:6])
                    data = data[6:]
                    # If correct ack is received, reset timer, slide window forward by difference 
                    # between expected seq num and actual seq num
                    if(int.from_bytes(checksum) == calcdchecksum and data.decode('utf-8') == "RDTAck." and seq > last_ack):
                        start_time = time.perf_counter()
                        window_start += (seq - last_ack)
                        last_ack = seq
                        print(f"Sender: received ACK number {seq}, LastAck = {last_ack}, LastPacket = {last_packet}")
                        if last_ack >= 0 and last_ack == last_packet:
                            to_send = -1
                    elif(int.from_bytes(checksum) == calcdchecksum and data.decode('utf-8') == "RDTEndAck."):
                        self.run = False
                        print("Sender: received EndAck, Terminating.")
                except BlockingIOError:
                    pass

                if not self.run:
                    break

                # Check timeout 
                if ((time.perf_counter() - start_time) > self.timeout):
                    # reset to send from start of window if timeout happened
                    to_send = window_start
                    start_time = time.perf_counter()
                if end_time != -1 and (time.perf_counter() - end_time) > self.kill_timeout: # this will only happen if the receiver dies or closes the connection without an EndAck.
                    self.run = False
                    break
                # send next packet iff there is still room in the window
                if to_send < (window_start + self.window_size) or end_time != -1 or resend_last:
                    if to_send == -1 or end_time != -1:
                        print("Sender: sending End. packet")
                        packet = get_packet(0, bytes("RDTEnd.", "utf-8"), seqnum=(last_packet + 1))
                        if end_time == -1:
                            end_time = time.perf_counter()
                    else:
                        packet = get_packet(to_send, self.data)
                        print(f"Sender: sending packet number {to_send}. Window Start = {window_start} Window Size = {self.window_size}")
                    sock.sendto(packet, (self.dstip, self.dstport))
                    if len(packet) < (self.pktsize + 6): # if we've reached the end of the data
                        last_packet = to_send
                        if window_start + self.window_size > last_packet:
                            self.window_size = last_packet - window_start
                            if self.window_size == 0:
                                resend_last = True
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
            addr = ""
            while(self.run):
                # Check for ACK recvd
                data, addr = sock.recvfrom(1024)  # Try receiving data
                checksum = data[:2]
                seq = int.from_bytes(data[2:6])
                calcdchecksum = calculate_checksum(data[2:])
                data = data[6:]
                msg = bytes("RDTAck.", "utf-8")
                try:
                    decoded = data.decode('utf-8')
                except UnicodeDecodeError:
                    decoded = ""
                if(int.from_bytes(checksum) == calcdchecksum and decoded == "RDTEnd."):
                    self.run = False
                    msg = bytes("RDTEndAck.", 'utf-8')
                    print("Receiver: received End. Sending EndAck.")
                elif(int.from_bytes(checksum) == calcdchecksum and seq == last_recvd + 1):
                    self.recvd_data += data
                    last_recvd += 1
                    msg = bytes("RDTAck.", 'utf-8')
                if last_recvd == -1: # This will only happen if the 0th packet is corrupted
                    continue # let the sender timeout, since we don't have a last packet to re-ack
                print(f"Receiver: received packet number {seq}, Sending ACK {last_recvd}")

                sock.sendto(get_packet(0, msg, seqnum=last_recvd), addr)
            print(addr)
            return self.recvd_data, addr


def main(mode, dst, dstport, srcport):
    if mode == "recv":
        recvr = RDTRecvr(dstport)
        recvr.start()
    elif mode == "send":
        data = ""
        for i in range(1):
            data = data + str(i) + ", "
        sender = RDTSender(bytes(data[:-2], 'utf-8'), srcport=srcport, dstip = dst)
        sender.start()


if __name__ == "__main__":
    # Create the parser
    parser = argparse.ArgumentParser(description='A simple ping utility')
    
    # Add arguments
    parser.add_argument('-dst', required=False, type=str, default='127.0.0.1', help='The destination IP address for the RDTReceiver')
    parser.add_argument('-dstport', required=False, type=int, default=8082, help='The destination port for the RDTReceiver')
    parser.add_argument('-srcport',  required=False,type=int, default=8080, help='The destination port for the RDTSender')
    parser.add_argument("--mode", choices=["recv", "send"], type=str, required=True, help="The mode in which to run the file, either as a Sender or a Receiver.")
    
    args = parser.parse_args()
    main(args.mode, args.dst, args.dstport, args.srcport)
 
