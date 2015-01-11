__author__ = 'yusufyilmz'

class MessageImplementer():

        def __init__(self):
                return

        def SendMessage(self, socket, messageType, parameter=None):
                msgToBeSent = str(messageType)
                if parameter is None:
                        msgToBeSent = msgToBeSent + "\n\r\n{\n}"
                else:
                        msgToBeSent = msgToBeSent + "\n\r\n{"
                        for key in parameter:
                                msgToBeSent = msgToBeSent + '\n\t\"' + str(key) + '\": \"' + str(parameter[key]) + '\",'
                        msgToBeSent = msgToBeSent + '\n}'

                socket.send(msgToBeSent)

        def getMessageHeader(self, message):
                return message.split('\n')[0]

        def getMessageBody(self, message):
                message = message.split('\n')
                paramDict = {}
                for i in range(3, len(message) -1):
                        e = message[i][1:len(message[i])-1].split(': ')
                        key = str(e[0][1:len(e[0])-1])
                        value = str(e[1][1:len(e[1])-1])
                        paramDict[key] = value

        #print(paramDict)
                return paramDict
