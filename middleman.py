import socket
import argparse
import random
import time

DROPCHANCE = 5
REORDERCHANCE = 10
CORRUPTCHANCE = 15

def main(dst, src, dstport, srcport, loss, reorder, corrupt, myport, timeout = 10):
    start = time.time()
    dest_addrs = {}
    dest_addrs[(src, srcport)] = (dst, dstport)
    dest_addrs[(dst, dstport)] = (src, srcport)
    while time.time() - start < timeout:
        start = time.time()
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.bind(("127.0.0.1", myport))
            sock.settimeout(timeout)
            try:
                data, addr = sock.recvfrom(1024)
                forward = dest_addrs[addr]
                if (loss and random.randint(1, 100) < DROPCHANCE):
                    continue
                if corrupt and random.randint(1,100) < CORRUPTCHANCE:
                    data = bytes(int.from_bytes(data) ^ 1<<random.randint(1, (len(data)*8) - 1))
                if reorder and random.randint(1,100) < REORDERCHANCE:
                    data2, addr2 = sock.recvfrom(1024)
                    while addr2 == forward: 
                        # if reordering, forward all packets going in the other direction correctly until we can reorder
                        sock.sendto(data2, dest_addrs[addr2])
                        data2, addr2 = sock.recvfrom(1024)
                    sock.sendto(data2, forward)
                sock.sendto(data, forward)
            except socket.timeout:
                pass



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
    
