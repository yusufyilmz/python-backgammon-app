__author__ = 'yusufyilmz'


class MessageImplementer():

        def __init__(self):
                return

        def SendMessage(self, socket, messageType, parameter=None):
                msgToBeSent = str(messageType)
                if parameter is None:
                        msgToBeSent = msgToBeSent + "\n\r\n{\n}"
                else:
                        msgToBeSent = msgToBeSent + "\n\n\r\n\n{"
                        for key in parameter:
                                msgToBeSent = msgToBeSent + '\n\n\t\"' + str(key) + '\"= \"' + str(parameter[key]) + '\",'
                        msgToBeSent = msgToBeSent + '\n\n}'

                socket.send(msgToBeSent)

        def getMessageHeader(self, message):
                msg = message.split('\n')[0]
                return msg

        def getMessageBody(self, message):
                message = message.split('\n\n')
                paramDict = {}
                for i in range(3, len(message) -1):
                        e = message[i][1:len(message[i])-1].split('= ')
                        key = str(e[0][1:len(e[0])-1])
                        value = str(e[1][1:len(e[1])-1])
                        paramDict[key] = value
                return paramDict

        def getMessageBodyForMove(self, message):
                message = message.split('\n\n')
                list = []
                for i in range(3, len(message) -1):
                        e = message[i][1:len(message[i])-1].split('= ')
                        value = str(e[1][1:len(e[1])-1])
                        value = value.split(' ')
                        for i in range(0, len(value)):
                                list.append(int(value[i]))

                return list

