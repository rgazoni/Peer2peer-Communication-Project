import socket
import threading
import os
import time
import json
from datetime import datetime

bufferSize  = 1024

class ClientServerCon(socket.socket):

    def __init__(self, IP, port):

        self.IPserver = IP
        self.portServer = port
        self._flagACK = False
        self._bufferMsg = []
        self._bufferACK = []
        self._lock = threading.Lock()

        # socket.AF_INET -> IPV4
        # socket.SOCK_DGRAM -> UDP
        # Create a datagram socket
        super().__init__(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self._connect()

    def _connect(self):
        try:
            self.bind((self.IPserver, self.portServer))
            print("UDP server está funcionando e ouvindo pelo IP e porta ({}, {})".format(self.IPserver, self.portServer))
        except:
            print("Não conseguimos disponibilizar esse IP com essa porta para o servidor do UDP ({self.IPserver}, {self.portServer})")
            exit(1) 


    def serverSide(self):

        while True:

            bytesMessage = self.recv(bufferSize)
            messageStr = bytesMessage.decode("utf-8") 

            messageJSON = json.loads(messageStr)

            try:
                messageJSON['ACK']
                with self._lock:
                    self._flagACK = True
                    #We put the message into the buffer as a string
                    self._bufferACK.append(messageStr)
        
            except KeyError:
                
                with self._lock:
                    self._bufferMsg.append(messageStr)
                
                dt = datetime.now()
                messageTime = datetime.timestamp(dt)

                try:
                    time = messageJSON['Timestamp_da_mensagem']
                except KeyError:
                    time = messageJSON['Timestamp_da_mensagem_de_resposta']
                
                data = {
                "Ip_origem": self.IPserver,
                "Ip_destino": messageJSON['Ip_origem'],
                "Porta_origem": self.portServer,
                "Porta_destino": messageJSON['Porta_origem'],
                "Timestamp_da_mensagem_original": time,
                "Timestamp_da_mensagem_de_resposta": messageTime,
                "ACK" : True
                }   

                messageACKStr = json.dumps(data)
                bytesMessageAck = str.encode(messageACKStr)
                self.sendto(bytesMessageAck, (messageJSON['Ip_origem'], messageJSON['Porta_origem']))


    def clientSideInbox(self,):

        backMenu = True

        while True:
            with self._lock:
                if len(self._bufferMsg) == 0:
                    print("\n---------------------------------------\n")
                    print("Não existe mais mensagens disponíveis")
                    backMenu = False
                    break 
                else:
                    #We receive a message in string already
                    messageStr = self._bufferMsg.pop()

            messageJSON = json.loads(messageStr)

            try:
                msgOri = messageJSON['Mensagem_original']
                print("Mensagem original: \n\t{}".format(msgOri))
                print("Resposta da mensagem de Ip {} e porta {}".format(messageJSON['Ip_origem'], messageJSON['Porta_origem']))
                print("\t{}".format(messageJSON['Mensagem_de_resposta']))
                
                inp = ''
                while inp != 'q' and inp != 'Q':
                    inp = input("\n-> Aperte [Q/q] para voltar ao menu: ")
                    break


            except KeyError:

                print("Mensagem recebida do Ip {} e porta {}: ".format(messageJSON['Ip_origem'], messageJSON['Porta_origem']))
                print("\t {}".format(messageJSON['Mensagem']))
                answer = input("Deseja responder essa mensagem? [S/n] ")
                
                if answer == 'S' or answer == 's':

                    newMsg =  input("[Aperte ENTER para enviar] Escreva sua mensagem de resposta: ")
                
                    dt = datetime.now()
                    messageTime = datetime.timestamp(dt)
                    
                    data = {
                    "Ip_origem": self.IPserver,
                    "Ip_destino": messageJSON['Ip_origem'],
                    "Porta_origem": self.portServer,
                    "Porta_destino": messageJSON['Porta_origem'],
                    "Timestamp_da_mensagem_original": messageJSON['Timestamp_da_mensagem'],
                    "Timestamp_da_mensagem_de_resposta": messageTime,
                    "Mensagem_original": messageJSON['Mensagem'],
                    "Mensagem_de_resposta": newMsg
                    }

                    messageStr = json.dumps(data)

                    retryThread = threading.Thread(target=self._retry, args=(messageStr, messageJSON['Ip_origem'], messageJSON['Porta_origem']))
                    retryThread.start()
                

        if backMenu is False:
            inp = ''
            while inp != 'q' and inp != 'Q':
                inp = input("\n\n\n\n-> Aperte [Q/q] para voltar ao menu: ")
            backMenu = True

    def clientSideWrite(self,):

        ip = input("Para qual Ip voce deseja mandar mensagem: ")
        port = int(input("E para qual porta: "))
        message = input("(Aperte ENTER para enviar) Digite a mensagem que voce deseje mandar: ")
                    
        dt = datetime.now()
        messageTime = datetime.timestamp(dt)

        #Create JSON
        data = {
        "Ip_origem": self.IPserver,
        "Ip_destino": ip,
        "Porta_origem": self.portServer,
        "Porta_destino": port,
        "Timestamp_da_mensagem": messageTime,
        "Mensagem": message
        }

        #Converting dict to JSON
        messageJSON = json.dumps(data)

        retryThread = threading.Thread(target=self._retry, args=(messageJSON, ip, port))
        retryThread.start()


    def _retry(self, messageStr, ipDest, portDest):

        timeOut = 0
        while timeOut < 5:

            if self._flagACK:
                with self._lock:
                    self._flagACK = False
                break
            else:
                #Convert JSON - str -> bytes
                bytesToSend = str.encode(messageStr)
                #Sending message
                self.sendto(bytesToSend, (ipDest, portDest))
                timeOut += 1
                time.sleep(5)
                

        # In case timeout is exceeded put into ACKbuffer failed message to show on menu
        if timeOut >= 5:

            messageJSON = json.loads(messageStr)

            dt = datetime.now()
            messageTime = datetime.timestamp(dt)
            data = {
            "Ip_origem": self.IPserver,
            "Ip_destino": ipDest,
            "Porta_origem": self.portServer,
            "Porta_destino": portDest,
            "Timestamp_da_mensagem_original": messageJSON['Timestamp_da_mensagem'],
            "Timestamp_da_mensagem_de_resposta": messageTime,
            "Mensagem_original": messageJSON['Mensagem'],
            "ACK" : False
            }
                    
            messageACK = json.dumps(data)
            with self._lock:
                self._bufferACK.append(messageACK)


    def menu(self,):

        svThread = threading.Thread(target=self.serverSide, args=())
        svThread.start()

        while True:
            
            os.system('clear')

            while len(self._bufferACK) != 0:
        
                messageACKStr = self._bufferACK.pop()

                messageACKJSON = json.loads(messageACKStr)
            
                if messageACKJSON['ACK'] is True:
                    print("---------------------------------------")
                    print("Mensagem enviada com sucesso!")
                    print("\tIp Origem", messageACKJSON['Ip_origem'])
                    print("\tIp Destino", messageACKJSON['Ip_destino'])
                    print("\tPorta Origem", messageACKJSON['Porta_origem'])
                    print("\tPorta Destino", messageACKJSON['Porta_destino'])
                    print("\tTimestamp da Mensagem", messageACKJSON['Timestamp_da_mensagem_original'])
                    print("\tTimestamp da Resposta", messageACKJSON['Timestamp_da_mensagem_de_resposta'])
                    print("---------------------------------------\n")
                else :
                    print("---------------------------------------")
                    print("Não foi possivel enviar sua mensagem.")
                    print("\tIp Origem", messageACKJSON['Ip_origem'])
                    print("\tIp Destino", messageACKJSON['Ip_destino'])
                    print("\tPorta Origem", messageACKJSON['Porta_origem'])
                    print("\tPorta Destino", messageACKJSON['Porta_destino'])
                    print("\tTimestamp da Mensagem", messageACKJSON['Timestamp_da_mensagem_original'])
                    print("\tTimestamp da Resposta", messageACKJSON['Timestamp_da_mensagem_de_resposta'])
                    print("---------------------------------------\n")
            
            print("\nSeja bem-vindo ao minimail.")
            print("1 - Escrever uma mensagem")
            print("2 - Inbox")
            print("3 - Refresh para ver se suas mensagens foram enviadas com sucesso")
            option = int(input("Selecione o que voce deseja fazer? "))                  

            if option == 1:
                os.system('clear')
                self.clientSideWrite()
            elif option == 2:
                os.system('clear')
                self.clientSideInbox()
            elif option == 3:
                os.system('clear')
                


# Main on python
if __name__ == "__main__": 

    ip = input("Escolha um IP: ")
    port = int(input("Escolha uma porta: "))

    with ClientServerCon(ip, port) as scCon:
        scCon.menu()
