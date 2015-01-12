import sys
import socket
from MessageImplementer import *
from temp import *
import threading
import time
import Queue

messageList = Queue.PriorityQueue()

class BackGroundMessageHandler(threading.Thread):
        def __init__(self, socket):
                threading.Thread.__init__(self)
                self.s = socket

        def run(self):
                counter = 1
                while True:
                        msg = self.s.recv(1024)
                        if messageHandler.getMessageHeader(msg) == "PING":
                                print("ping received")
                                messageHandler.SendMessage(self.s, "PONG")
                                print("pong sended")
                        else:
                                messageList.put((counter, msg))
                                counter += 1


class Client(object):
        def __init__(self, serverIP, port, username):
                self.serverIP = serverIP
                self.port = port
                self.username = username
                self.state = 'IDLE'
                self.turn = -1
                self.color = ''
                self.userType = 'unknown'
                self.playRequest = 'unknown'
                self.board = ''

        def CreateLoginRequest(self):
                paramDict = {}
                paramDict["playerId"] = self.username
                messageHandler.SendMessage(self.s, "CCNT", paramDict)

        def handleLoginResponse(self):
                msg = self.s.recv(1024)
                print(msg)
                msgHeader = messageHandler.getMessageHeader(msg)
                msgList = msg.split('\n')
                if msgHeader != 'SRVK':
                        print("server error")
                        return False
                msgBodyDict = messageHandler.getMessageBody(msg)
                print(msgBodyDict)
                if msgBodyDict['result'] != 'success':
                        print("server error no result")
                        return False

                return True

        def setupConnection(self):
                self.s = socket.socket()
                try:
                        self.s.connect((self.serverIP, self.port))
                except socket.error as err:
                        print(err)
                        self.s.close()
                        return False

                self.state = "CONNECTING"
                self.CreateLoginRequest()

                if self.handleLoginResponse() is False:
                        self.s.close()
                        self.state = "IDLE"
                        return False

                self.state = "CONNECTED"
                return True

        def run(self):

                print('serverIP is ' + self.serverIP)
                print('username is ' + self.username)

                if self.setupConnection() is False:
                        print("session setup is false")
                        return

                print("Welcome to backgammon server " + self.username)
                self.connectedInputScreen()

                clientInput = sys.stdin.readline()
                print(clientInput)
                self.CreateClientInput(clientInput)
                handler = BackGroundMessageHandler(self.s)
                handler.start()
                self.getMessageAndHandleIt()


        def getMessageAndHandleIt(self):
                while True:
                        print("waiting response from server")
                        if messageList.empty():
                                pass

                        data = messageList.get(True)[1]

                        if self.handleServerInput(data) is False:
                                break

                        print("waiting response from client")

                        clientInput = sys.stdin.readline()
                        print(clientInput)
                        self.CreateClientInput(clientInput)

        def CreateClientInput(self, userInput):

                if self.state is 'CONNECTED':
                        print('CONNECTED STATE')
                        self.CreateClientInputConnectedState(userInput)

                elif self.state is 'WAITING':
                        print('WAITING STATE')
                        self.CreateClientInputLeaveState(userInput)

                elif self.state is 'PLAYING':
                        print('PLAYING STATE')
                        self.CreateGameRequests(userInput)

                elif self.state is 'WATCHING':
                        print('WATCHING STATE')
                        self.CreateWatch(userInput)

        def handleServerInput(self, rMsg):
                header = messageHandler.getMessageHeader(rMsg)
                if rMsg == '':
                        return False
                elif header == 'SRVP':
                        self.HandleServerPlayMessage(rMsg)
                elif header == 'SRVW':
                        self.HandleServerWatchMessage(rMsg)
                elif header == 'SRVK':
                        self.HandleServerOkMessage(rMsg)
                elif header == 'SRVE':
                        print('you put wrong message, please try again later')
                        self.getMessageAndHandleIt()
                else:
                        print('unknown message from the server')
                        print(rMsg)
                return True

        def CreateClientInputConnectedState(self, userInput):
                sMsg = False
                try:
                        if 1 == int(userInput):
                                #todo
                                print("play is chosen")
                                sMsg = "CPLY"
                                self.state = 'PLAYREQUESTED'
                        elif 2 == int(userInput):
                                #todo
                                sMsg = "CWTC"
                                self.state = 'WATCHREQUESTED'
                        else:
                                self.connectedInputScreen()
                except ValueError:
                        print("error")
                        self.connectedInputScreen()

                if sMsg is not False:
                        print("sended message")
                        self.s.send(sMsg)


        def HandleServerOkMessage(self, rMsg):

                print('handleRequestResponse')
                print(rMsg)
                paramDict = messageHandler.getMessageBody(rMsg)
                request = paramDict['type']



        def HandleServerPlayMessage(self, rMsg):
                print('handleRequestResponse')
                print(rMsg)
                paramDict = messageHandler.getMessageBody(rMsg)
                self.playRequest = paramDict['type']
                result = paramDict['result']
                if result == 'success' and self.state == 'WAITING':
                        self.state = 'PLAYREQUESTED'

                print("request:" + self.playRequest)
                print("self.state:" + self.state)

                if self.playRequest == 'play' and self.state == 'PLAYREQUESTED':
                        print("result:" + result)

                        if result == 'fail':
                                print('result is fail')
                                self.state = 'WAITING'
                                self.failedPlayInputScreen()
                        elif result == 'success':
                                self.turn = paramDict['turn']
                                self.color = paramDict['color']
                                print('result is success')
                                self.state = 'PLAYING'
                                self.board = paramDict['board']
                                self.playingInputScreen()

                elif self.playRequest == 'dice':
                        dice1 = paramDict['Dice1']
                        dice2 = paramDict['Dice2']
                        self.board = paramDict['board']
                        print("dice results are:" + str(dice1) + ", " + str(dice2))
                        self.playingInputScreen()

                elif self.playRequest == 'move':
                        self.board = paramDict['board']
                        self.turn = paramDict['turn']
                        self.playingInputScreen()

                elif self.playRequest == 'wrongmove':
                        self.board = paramDict['board']
                        self.turn = paramDict['turn']
                        self.playingInputScreen()

        def CreateGameRequests(self, userInput):
                try:
                        if 4 == int(userInput):
                                self.CreateThrowDiceMessage()
                        elif 6 == int(userInput):
                                self.CreateSendMoveMessage()
                        elif 5 == int(userInput):
                                self.CreateWrongMoveMessage()
                        else:
                                self.playingInputScreen()
                except ValueError:
                        print("error")
                        self.connectedInputScreen()


        def CreateThrowDiceMessage(self):
                 print("dice request is sending")
                 messageHandler.SendMessage(self.s, "CTDC", None)


        def CreateSendMoveMessage(self):
                print("move is sending")
                print("Press moves sequentially from source to destination( ex: 6 2 4 2 5 3 10 2")
                sys.stdout.write("> ")
                sys.stdout.flush()
                clientInput = sys.stdin.readline()
                paramDict = {}
                paramDict['move'] = str(clientInput)
                messageHandler.SendMessage(self.s, "CSMV", paramDict)

        def CreateWrongMoveMessage(self):
                print("wrong move is sending")
                messageHandler.SendMessage(self.s, "CWMA", None)



        def CreateClientInputLeaveState(self, userInput):
                sMsg = False
                try:
                        if 3 == int(userInput):
                                sMsg = createLeaveRequest()
                        else:
                                self.waitingOpponentScreen()
                except ValueError:
                        self.failedPlayInputScreen()
                        if sMsg is not False:
                                self.s.send(sMsg)
                                self.state = 'LEAVING'


        def connectedInputScreen(self):
                print("Press 1 for Play")
                print("Press 2 for Watch")
                sys.stdout.write("> ")
                sys.stdout.flush()

        def failedPlayInputScreen(self):
                print("No opponent to play")
                print("For waiting an opponent press 4")
                print("For Leave press 3")
                sys.stdout.write("> ")
                sys.stdout.flush()

        def waitingOpponentScreen(self):
                print("Waiting an opponent to play")

        def playingInputScreen(self):
                print("turn : " + self.turn)
                print(self.board)
                while True:
                        if int(self.turn) == 1:
                                if self.playRequest == 'play':
                                        print("Press 4 for throwing Dice ")

                                elif self.playRequest == 'dice':
                                        print("Press 6 for send move ")

                                elif self.playRequest == 'move':
                                        print("Press 4 for throwing Dice ")
                                        print("Press 5 for wrong move alert ")

                                return
                        else:
                                print("waiting opponent to move")
                                self.getMessageAndHandleIt()


if __name__ == "__main__":
        messageHandler = MessageImplementer()
        print ("Please provide a username for login")
        sys.stdout.write("> ")
        sys.stdout.flush()
        clientInput = sys.stdin.readline()
        serverIP = '0.0.0.0'
        username = str(clientInput)
        port = 12352
        c = Client(serverIP, port, username)
        c.run()
