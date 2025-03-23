import socket
import argparse
import random
import time

DROPCHANCE = 5
REORDERCHANCE = 10
CORRUPTCHANCE = 15

def main(dst, src, dstport, srcport, loss, reorder, corrupt, myport, timeout = 10):
    start = time.perf_counter()
    dest_addrs = {}
    dest_addrs[(src, srcport)] = (dst, dstport)
    dest_addrs[(dst, dstport)] = (src, srcport)
    while time.perf_counter() - start < timeout:
        start = time.perf_counter()
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.bind(("127.0.0.1", myport))
            sock.settimeout(timeout)
            try:
                data, addr = sock.recvfrom(1024)
                forward = dest_addrs[addr]
                if (loss and random.randint(1, 100) < DROPCHANCE):
                    print("Middleman: Dropping Packet")
                    continue
                if corrupt and random.randint(1,100) < CORRUPTCHANCE:
                    print("Middleman: Corrupting Packet")
                    byte_array = bytearray(data)
                    byte_array[random.randint(0,len(data) - 1)] ^= 1<<(random.randint(0,7))
                    data = bytes(byte_array)
                if reorder and random.randint(1,100) < REORDERCHANCE:
                    data2, addr2 = sock.recvfrom(1024)
                    print("Middleman: Reordering Packets.")
                    while addr2 == forward: 
                        # if reordering, forward all packets going in the other direction correctly until we can reorder
                        sock.sendto(data2, dest_addrs[addr2])
                        data2, addr2 = sock.recvfrom(1024)
                    sock.sendto(data2, forward)
                print(f"Middleman: Forwarding to {forward}")
                sock.sendto(data, forward)
            except socket.timeout:
                pass



if __name__ == "__main__":
    # Create the parser
    parser = argparse.ArgumentParser(description='Middleman for testing RDTUnits, with the capability to corrupt, reorder, or drop packets.')
    
    # Add arguments
    parser.add_argument('-dst', required=False, type=str, default='127.0.0.1', help='The destination IP address for the RDTReceiver')
    parser.add_argument('-src', required=False, type=str, default='127.0.0.1', help='The destination IP address for the RDTSender')
    parser.add_argument('-dstport', required=False, type=int, default=8082, help='The destination port for the RDTReceiver')
    parser.add_argument('-srcport', required=False, type=int, default=8080, help='The destination port for the RDTSender')
    parser.add_argument('-middleport', required=False, type=int, default=8081, help="The port on which to open the middleman's socket.")
    parser.add_argument('-l', action="store_true", help='Sets the middleman to introduce packet losses. Chance to drop is 5% per packet.')
    parser.add_argument('-r', action="store_true", help='Sets the middleman to introduce packet reordering. Chance to reorder is 10% per packet.')
    parser.add_argument('-c', action="store_true", help='Sets the middleman to introduce packet corruption. Chance to corrupt is 15% per packet.')
    
    args = parser.parse_args()
    main(args.dst, args.src, args.dstport, args.srcport, args.l, args.r, args.c, args.middleport)
    
