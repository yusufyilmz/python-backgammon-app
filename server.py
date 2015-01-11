__author__ = 'yusufyilmz'

import socket
import datetime
import threading
import time
import Queue
import select
from MessageImplementer import *
import random

playerList = {}
playerListLock = threading.Lock()
dice = [1,2,3,4,5,6]


class BackgammonServer(object):

    def __init__(self):
        self.serverPort = 12351

    def initializeSocket(self):
        self.serverSocket = socket.socket()
        self.serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        #self.serverHost = socket.gethostname()
        self.serverHost = "0.0.0.0"
        self.serverSocket.bind((self.serverHost, self.serverPort))
        self.serverSocket.listen(200)

    def start(self):
        self.initializeSocket()
        print("Server is listening on ip: " + self.serverHost)
        print("Server is listening on port: " + str(self.serverPort))

        while True:
            clientSocket, clientAddress = self.serverSocket.accept()
            print "Client connected from: ", clientAddress
            playerThread = BackGammonPlayer(clientSocket, clientAddress)
            playerThread.start()

class BackGammonPlayerRoomList(object):

        def __init__(self):
                self.waitingList = Queue.Queue()


        def addPlayer(self, username):
                self.waitingList.put(username)

        def markAsDeleted(self, username):
                self.deletedWaiters[username] = 'deleted'

        def findPlayer(self, username):
                if self.waitingList.empty():
                        return False
                opponent = self.waitingList.get(True)
                if (opponent == username):
                    return False
                return opponent


class BackGammonPlayer(threading.Thread):

        def __init__(self, clientSocket, serverAddress):
                threading.Thread.__init__(self)
                self.playerSocket = clientSocket
                self.serverAddress = serverAddress
                self.state = 'CONNECTING'
                self.dice = -1
                self.userType = 'unknown'
                self.username = 'unknown'
                self.gameInitializer = False
                self.game = False

        def run(self):
                self.player = BackGammonPlayer(self.playerSocket, self.serverAddress)
                if self.requestConnection() is False:
                        self.playerSocket.close()
                        return
                else:
                        player = []
                        player.append(self)
                        playerList[self.username] = player
                        self.state = 'CONNECTED'

                while True:
                        if self.state == 'WAITING':
                                return

                        print("waiting client request")
                        res = self.playerSocket.recv(1024)
                        print("client request arrived")

                        header = messageHandler.getMessageHeader(res)
                        print("client message is" + header)
                        if header == 'CPNG':
                                self.GetPongResponse()
                        elif header == 'CPLY' and self.state == 'CONNECTED':
                                print("play requested")
                                self.RequestPlay()
                        elif header == 'CWTC' and self.state == 'CONNECTED':
                                self.RequestWatch()
                        elif header == 'CLVE' and self.state == 'WAITING':
                                print(self.username + ' wants to leave')
                                # Mark the client as leaving. It will be handled in the main loop
                                self.state = 'LEAVING'
                        else:
                                messageHandler.SendMessage(self.playerSocket, "SRVE", None)

        def setState(self, state):
                self.state = state

        def setUserType(self, userType):
                self.userType = userType


        def RequestPlay(self):
                self.userType = 'player'
                opponent = playerRoomList.findPlayer(self.username)
                if opponent is False:
                                        # No opponent to play
                        playerRoomList.addPlayer(self.username)
                        self.state = 'WAITING'
                                # send SREQRP play(fail) message to the user
                        paramDict = {}
                        paramDict["type"] = 'play'
                        paramDict["result"] = 'fail'
                        messageHandler.SendMessage(self.playerSocket, "SRVP", paramDict)
                        return

                playerListLock.acquire()
                opponent = playerList[opponent][0]
                playerListLock.release()

                self.setState('PLAYING')
                self.userType = 'player'
                opponent.player.setUserType('player')
                opponent.setState('PLAYING')

                game = BackGammonGame(self, opponent)
                self.game = game
                #gameList.addGameToGameList(g)
                game.start()

        def requestConnection(self):

                print('Connection requested from', self.serverAddress)
                data = self.playerSocket.recv(1024)
                msg = messageHandler.getMessageHeader(data)
                if msg != 'CCNT':
                        messageHandler.SendMessage(self.playerSocket, 'SRVE', None)
                        return False

                paramDict = messageHandler.getMessageBody(data)
                self.username = paramDict.get('playerId', None)
                if self.username is None or len(paramDict) > 1:
                        messageHandler.SendMessage(self.playerSocket, 'SRVE', None)
                        return False

                newParamDict = {}

                playerListLock.acquire()
                if playerList.get(self.username, None) is None:
                        newParamDict["result"] = 'success'
                        messageHandler.SendMessage(self.playerSocket, 'SRVK', newParamDict)
                        print('OK: ' + str(self.username) +
                              '. You are logged in to the server')
                        result = True
                else:
                        newParamDict["result"] = 'fail'
                        messageHandler.SendMessage(self.playerSocket, "SRVE", newParamDict)
                        print('FAIL: ' + str(self.username) + ' already exists.')
                        result = False

                playerListLock.release()

                if result is False:
                        return False
                return True


class BackGammonGame():

        def __init__(self, player, opponent):
                self.player = player
                self.opponent = opponent

                self.playerList = {}
                self.activePlayer = -1
                self.passivePlayer = -1
                self.board = 'board'

        def addWatcher(self):
                return


        def start(self):

                print('Game starts')
                paramDict = {}
                paramDict["type"] = 'play'
                paramDict["result"] = 'success'

                while True:
                        self.player.dice = random.choice(dice)
                        self.opponent.dice = random.choice(dice)
                        if self.player.dice != self.opponent.dice:
                                break

                if self.player.dice > self.opponent.dice:
                        self.activePlayer = self.player
                        self.passivePlayer = self.opponent
                else:
                        self.activePlayer = self.opponent
                        self.passivePlayer = self.player


                print('Active player:' + self.activePlayer.username)
                print('Passive player:' + self.passivePlayer.username)


                paramDict = {}
                paramDict["type"] = 'play'
                paramDict["result"] = 'success'
                paramDict["turn"] = 1
                paramDict["color"] = 'white'
                messageHandler.SendMessage(self.activePlayer.playerSocket, "SRVP", paramDict)
                paramDict = {}
                paramDict["type"] = 'play'
                paramDict["result"] = 'success'
                paramDict["turn"] = 0
                paramDict["color"] = 'black'
                messageHandler.SendMessage(self.passivePlayer.playerSocket, "SRVP", paramDict)


                while True:
                        self.playTurn()



        def playTurn(self):
                dicethrowed = False
                movesended = False
                turnEnded = False

                while turnEnded is False:
                        print("Waiting response from active player")
                        data = self.activePlayer.playerSocket.recv(1024);
                        cMsg = messageHandler.getMessageHeader(data)
                        print(cMsg + " message is got from active player")
                        if cMsg == 'CTDC' and movesended is False:
                                dicethrowed = True
                                self.throwDice()
                        elif cMsg == "CSMV" and dicethrowed is True:
                                self.sendMove()
                                dicethrowed = False
                                movesended = True
                                turnEnded = True
                        elif cMsg == "CWMA" and dicethrowed is False:
                                self.sendWrongMove()
                                turnEnded = True
                        else:
                                messageHandler.SendMessage(self.activePlayer.playerSocket, "SRVE", None)



        def throwDice(self):
                paramDict = {}
                paramDict["type"] = 'dice'
                paramDict["Dice1"] = random.choice(dice)
                paramDict["Dice2"] = random.choice(dice)
                paramDict['result'] = 'success'
                print("dice throwed, dice results are:" + str(paramDict['Dice1']) + ", " + str(paramDict['Dice2']))
                messageHandler.SendMessage(self.activePlayer.playerSocket, "SRVP", paramDict)


        def sendMove(self):
                print("active player turn ended")
                activePlayer = self.activePlayer
                self.activePlayer = self.passivePlayer
                self.passivePlayer = activePlayer

                paramDict = {}
                paramDict["type"] = 'move'
                paramDict['result'] = 'success'
                paramDict['turn'] = 1
                messageHandler.SendMessage(self.activePlayer.playerSocket, "SRVP", paramDict)
                paramDict['turn'] = 0
                messageHandler.SendMessage(self.passivePlayer.playerSocket, "SRVP", paramDict)


        def sendWrongMove(self):
                return

        def getBoard(self):
                """
                TODO: purpose of the method
                """
                return self.board

if __name__ == "__main__":
        messageHandler = MessageImplementer()
        playerRoomList = BackGammonPlayerRoomList()
        server = BackgammonServer()
        server.start()
