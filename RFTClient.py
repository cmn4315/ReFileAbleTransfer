import argparse
import RDTUnit


def main(mode: str, server_ip: str, server_port: int, filename: str, my_port: int, timeout: int = 1):
    msg = ""
    if mode == "send":
        msg = bytes("RFTSend." + filename, "utf-8")
    elif mode == "recv":
        msg = bytes("RFTRecv." + filename, 'utf-8')
    else:
        return

    if msg != "":
        req_sender = RDTUnit.RDTSender(data = msg, dstip=server_ip, dstport=server_port, srcport=my_port, timeout=timeout)
        req_sender.start()

    if mode == "send":
        with open(filename, 'rb') as f:
            data = f.read()
        client = RDTUnit.RDTSender(data=data, dstip=server_ip, dstport=server_port, srcport=my_port, timeout=timeout)
        client.start()
    else:
        client = RDTUnit.RDTRecvr(srcport=my_port)
        filedata, _ = client.start()
        with open(filename, "wb") as f:
            f.write(filedata)


if __name__ == "__main__":
    # Create the parser
    parser = argparse.ArgumentParser(description='A simple ping utility')
    
    # Add arguments
    parser.add_argument("-f", type=str, required=True, help="The filename to either send to or request from the server.")
    parser.add_argument('-server_ip', required=False, type=str, default='127.0.0.1', help='The destination IP address for the RDTReceiver')
    parser.add_argument('-server_port', required=False, type=int, default=8082, help='The destination port for the RDTReceiver')
    parser.add_argument('-port',  required=False,type=int, default=8080, help='The destination port for the RDTSender')
    parser.add_argument("--mode", choices=["recv", "send"], type=str, required=True, help="The mode in which to run, either sending or receiving a file from the server.")
    
    args = parser.parse_args()
    main(args.mode, args.server_ip, args.server_port, args.f, args.port)
 

