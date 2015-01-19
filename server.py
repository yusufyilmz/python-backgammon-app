import socket
import datetime
import threading
import time
import Queue
import select
from MessageImplementer import *
import random
from temp import *
from board import Board, Point


playerList = {}
playerListLock = threading.Lock()
dice = [1,2,3,4,5,6]
heartBeatTimeout = 40
gameList = Queue.Queue()


WHITE = 'W'
BLACK = 'B'

class BackGammonBoard(object):

    def __init__(self, white=None, black=None):
        self.board = Board()
        self.history = []
        self.black = black
        self.white = white

    @property
    def color(self):
        return BLACK if len(self.history) % 2 == 0 else WHITE


    def draw(self):
        print()
        print(self.board)

    def getStateOfBoard(self):
        return self.board

    def move(self, src, dst):

        if isinstance(src, Point):
            src = src.num
        if isinstance(dst, Point):
            dst = dst.num
        new = self.board.move(src, dst)
        self.board = new
        return new


class BackGammonHeartBeat(threading.Thread):

        def __init__(self, player):
                threading.Thread.__init__(self)
                self.player = player

        def run(self):
            while True:
                time.sleep(30)
                if self.player.state == 'DELETED':
                        return

                messageHandler.SendMessage(self.player.playerSocket, "PING", None)


class BackGroundMessageHandler(threading.Thread):
        def __init__(self, player):
                threading.Thread.__init__(self)
                self.player = player

        def run(self):
                counter = 1
                while True:
                        if self.player.state == 'DELETED':
                                return
                        try:
                                self.player.playerSocket.settimeout(heartBeatTimeout)
                                msg = self.player.playerSocket.recv(1024)
                        except socket.timeout:
                                if self.player.state == 'DELETED':
                                        return

                                print("No Pong message is received from " + str(self.player.username) + "")
                                self.player.state = 'DELETED'
                                playerList.pop(self.player.username)
                                self.player.playerSocket.close()
                                return

                        if messageHandler.getMessageHeader(msg) == "PONG":
                                print("pong received from " + str(self.player.username))
                        else:
                                self.player.messageList.put((counter, msg))
                                counter += 1


class BackgammonServer(object):

    def __init__(self):
        self.serverPort = 12357

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
                self.messageList = Queue.PriorityQueue()

        def GetMessageList(self):
                return self.messageList

        def run(self):

                if self.requestConnection() is False:
                        self.playerSocket.close()
                        return
                else:
                        player = []
                        player.append(self)
                        playerList[self.username] = player
                        self.state = 'CONNECTED'

                heartbeat = BackGammonHeartBeat(self)
                heartbeat.start()

                backGroundMessageQueue = BackGroundMessageHandler(self)
                backGroundMessageQueue.start()

                while True:
                        if self.state == 'DELETED':
                                return

                        if self.state == 'PLAYING':
                                continue

                        if self.messageList.empty():
                                continue

                        res = self.messageList.get(True)[1]

                        print("client request arrived")

                        header = messageHandler.getMessageHeader(res)
                        print("client message is " + header)

                        if header == 'CPLY' and self.state == 'CONNECTED':
                                print("play requested")
                                self.RequestPlay()
                        elif header == 'CWTC' and self.state == 'CONNECTED':
                                self.RequestWatch()
                        elif header == 'CLVE' and self.state == 'CONNECTED':
                                self.state = 'DELETED'
                                print(self.username + 'leaved server')
                                messageHandler.SendMessage(self.playerSocket, "SRVL", None)
                                playerList.pop(self.username)
                                self.playerSocket.close()
                        elif header == 'CLVE' and self.state == 'WAITING':
                                self.state = 'CONNECTED'
                                paramDict = {}
                                paramDict["result"] = 'success'
                                messageHandler.SendMessage(self.playerSocket, "SRVK", paramDict)
                        else:
                                messageHandler.SendMessage(self.playerSocket, "SRVE", None)

        def setState(self, state):
                self.state = state

        def setUserType(self, userType):
                self.userType = userType

        def RequestWatch(self):
                self.userType = 'watcher'
                if gameList.empty():
                        self.state = 'WAITING'
                        paramDict = {}
                        paramDict["type"] = 'watch'
                        paramDict["result"] = 'fail'
                        messageHandler.SendMessage(self.playerSocket, "SRVW", paramDict)
                        return
                else:
                        game = gameList.get(True)
                        game.addWatcher(self)
                        paramDict = {}
                        paramDict["type"] = 'watch'
                        paramDict["result"] = 'success'
                        paramDict["board"] = game.getBoardState()
                        messageHandler.SendMessage(self.playerSocket, "SRVW", paramDict)

        def RequestPlay(self):
                self.userType = 'player'
                opponent = playerRoomList.findPlayer(self.username)
                if opponent is False:
                        # No opponent to play
                        playerRoomList.addPlayer(self.username)
                        self.state = 'WAITING'
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
                opponent.setUserType('player')
                opponent.setState('PLAYING')
                print("count " +str(playerRoomList.waitingList.qsize()))
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


class BackGammonGame(threading.Thread):

        def __init__(self, player, opponent):
                threading.Thread.__init__(self)
                self.player = player
                self.opponent = opponent
                self.board = BackGammonBoard()
                self.previousBoard = BackGammonBoard()
                self.playerList = {}
                self.activePlayer = -1
                self.passivePlayer = -1
                self.watcher = -1
                self.state = ''
                self.gameId = threading.currentThread().ident


        def addWatcher(self, watcher):
                self.watcher = watcher
                return


        def run(self):
                gameList.put(self)
                self.SetupStart()
                self.SetupPlayers()
                print('gameIdGame starts between ' + self.activePlayer.username + ' and ' + self.passivePlayer.username)

                while True:
                        self.playTurn()

                        if self.state == 'GAMEENDED':
                            print('Game ends between ' + self.activePlayer.username + ' and ' + self.passivePlayer.username)
                            return


        def SetupStart(self):
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

                self.activePlayer.setState('PLAYING')
                self.passivePlayer.setState('PLAYING')

                print('Active player:' + self.activePlayer.username)
                print('Passive player:' + self.passivePlayer.username)


        def SetupPlayers(self):
                paramDict = {}
                paramDict["type"] = 'play'
                paramDict["result"] = 'success'
                paramDict["turn"] = 1
                paramDict["color"] = 'white'
                paramDict["board"] = self.getBoardState()

                messageHandler.SendMessage(self.activePlayer.playerSocket, "SRVP", paramDict)
                paramDict = {}
                paramDict["type"] = 'play'
                paramDict["result"] = 'success'
                paramDict["turn"] = 0
                paramDict["color"] = 'black'
                paramDict["board"] = self.getBoardState()

                messageHandler.SendMessage(self.passivePlayer.playerSocket, "SRVP", paramDict)


        def playTurn(self):
                dicethrowed = False
                movesended = False
                turnEnded = False

                while turnEnded is False:
                        if self.watcher.state == 'DELETED':
                                self.watcher = -1
                            
                        if self.activePlayer.state == 'DELETED' or self.passivePlayer.state == 'DELETED':
                                self.EndGame()
                                turnEnded = True
                            
                        print("Waiting response from active player")
                        msgList = self.activePlayer.GetMessageList()
                    
                        if msgList.empty():
                                continue

                        data = msgList.get(True)[1]

                        cMsg = messageHandler.getMessageHeader(data)
                        print(cMsg + " message is got from active player")
                        if cMsg == "PONG":
                                print("PONG received from " + self.activePlayer.username)
                        elif cMsg == "CTDC" and movesended is False:
                                dicethrowed = True
                                self.throwDice()
                        elif cMsg == "CSMV" and dicethrowed is True:
                                self.setPreviousBoardState(self.getBoardState())
                                self.sendMove(data)
                                dicethrowed = False
                                movesended = True
                                turnEnded = True
                        elif cMsg == "CWMA" and dicethrowed is False:
                                self.sendWrongMove()
                                turnEnded = True
                        elif cMsg == "CGME":
                                self.EndGame()
                                turnEnded = True
                        else:
                                print(cMsg + " is received, server sending error")
                                messageHandler.SendMessage(self.activePlayer.playerSocket, "SRVE", None)

        def EndGame(self):
                self.state = 'GAMEENDED'
                paramDict = {}
                paramDict["type"] = 'gameended'
                paramDict["result"] = 'success'
                
                if self.activePlayer.state != 'DELETED':
                        self.activePlayer.setState('CONNECTED')
                        messageHandler.SendMessage(self.activePlayer.playerSocket, "SRVP", paramDict)
                if self.passivePlayer.state != 'DELETED':
                        self.passivePlayer.setState('CONNECTED')
                        messageHandler.SendMessage(self.passivePlayer.playerSocket, "SRVP", paramDict)
                if self.watcher != -1:
                        self.watcher.setState('CONNECTED')
                        messageHandler.SendMessage(self.watcher.playerSocket, "SRVW", paramDict)

        def throwDice(self):
                paramDict = {}
                paramDict["type"] = 'dice'
                paramDict["Dice1"] = random.choice(dice)
                paramDict["Dice2"] = random.choice(dice)
                paramDict["board"] = self.getBoardState()
                paramDict["result"] = 'success'
                print("dice throwed, dice results are:" + str(paramDict['Dice1']) + ", " + str(paramDict['Dice2']))
                paramDict["turn"] = 1
                messageHandler.SendMessage(self.activePlayer.playerSocket, "SRVP", paramDict)
                paramDict["turn"] = 0
                messageHandler.SendMessage(self.passivePlayer.playerSocket, "SRVP", paramDict)
                if self.watcher != -1:
                        messageHandler.SendMessage(self.watcher.playerSocket, "SRVW", paramDict)


        def sendMove(self, data):
                list = messageHandler.getMessageBodyForMove(data)
                try:
                        self.board.move(list[0], list[1])
                        self.board.move(list[2], list[3])
                        if len(list) > 4:
                                self.board.move(list[5], list[6])
                                self.board.move(list[7], list[8])
                except AssertionError, e:
                        messageHandler.SendMessage(self.activePlayer.playerSocket, "SRVE", None)

                print("active player turn ended")
                activePlayer = self.activePlayer
                self.activePlayer = self.passivePlayer
                self.passivePlayer = activePlayer

                paramDict = {}
                paramDict["type"] = 'move'
                paramDict["result"] = 'success'
                paramDict["turn"] = 1
                paramDict["board"] = self.getBoardState()

                messageHandler.SendMessage(self.activePlayer.playerSocket, "SRVP", paramDict)
                paramDict['turn'] = 0
                messageHandler.SendMessage(self.passivePlayer.playerSocket, "SRVP", paramDict)
                if self.watcher != -1:
                        messageHandler.SendMessage(self.watcher.playerSocket, "SRVW", paramDict)

        def sendWrongMove(self):
                print("active player turn ended")
                activePlayer = self.activePlayer
                self.activePlayer = self.passivePlayer
                self.passivePlayer = activePlayer

                paramDict = {}
                paramDict["type"] = 'wrongmove'
                paramDict["result"] = 'success'
                paramDict["turn"] = 1
                paramDict["board"] = self.getPreviousBoardState()

                messageHandler.SendMessage(self.activePlayer.playerSocket, "SRVP", paramDict)
                paramDict['turn'] = 0
                messageHandler.SendMessage(self.passivePlayer.playerSocket, "SRVP", paramDict)
                if self.watcher != -1:
                        messageHandler.SendMessage(self.watcher.playerSocket, "SRVW", paramDict)

        def getBoardState(self):
                return self.board.getStateOfBoard()

        def setPreviousBoardState(self, board):
                self.previousBoard = board

        def getPreviousBoardState(self):
                return self.previousBoard


if __name__ == "__main__":
        messageHandler = MessageImplementer()

        playerRoomList = BackGammonPlayerRoomList()
        server = BackgammonServer()
        server.start()
