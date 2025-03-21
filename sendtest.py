from RDTUnit import RDTSender, RDTRecvr

sender = RDTSender(data = bytes(b"\x00"*1024))
sender.start()
