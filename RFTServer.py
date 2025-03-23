"""
Author: Caleb Naeger - cmn4315@rit.edu
Server for ReFileable Transfer.
"""
import argparse
import RDTUnit


def main(my_port: int, timeout: int = 1):
    """Main function for the Server. Starts listening for a client req, processees it, and either sends or receives
    a file. 
    :param my_port: the port on which to listen for client messages
    :param timeout: timeout to pass to the RDTSender, if one is created.
    """
    req_rcvr = RDTUnit.RDTRecvr(srcport=my_port)
    data, clientaddr = req_rcvr.start()
    client_req = data.decode('utf-8')[:8]
    filename = data.decode('utf-8')[8:]
    print(f"Server: received a request: {data.decode("utf-8")}")

    if client_req == "RFTRecv.":
        with open(filename, 'rb') as f:
            data = f.read()
        print(f"Starting Server Sender to {clientaddr[0]}, port {int(clientaddr[1])}")
        client = RDTUnit.RDTSender(data=data, dstip=clientaddr[0], dstport=int(clientaddr[1]), srcport=my_port, timeout=timeout)
        client.start()
    elif client_req == "RFTSend.":
        client = RDTUnit.RDTRecvr(srcport=my_port)
        filedata, _ = client.start()
        with open(filename, "wb") as f:
            f.write(filedata)



if __name__ == "__main__":
    # Create the parser
    parser = argparse.ArgumentParser(description='Server for a simple reliable file-transfer application.')
    
    # Add arguments
    parser.add_argument('-port',  required=False,type=int, default=8082, help='The destination port for the RDTSender')
    
    args = parser.parse_args()
    main(args.port)
 

