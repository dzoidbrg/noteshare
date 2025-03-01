from pymongo import MongoClient, srv_resolver
from pymongo.errors import ConnectionFailure
import json
from bson.objectid import ObjectId
from cryptography.fernet import Fernet
import codecs
import os
from dotenv import load_dotenv
import random

load_dotenv()

uri = os.getenv("URI")

client = MongoClient(uri)
database = client[str(os.getenv("DATABASE"))] # Imports the database name from the config file
collection = database[str(os.getenv("COLLECTION"))] # Imports the collection name from the config file
users = database[str(os.getenv("USERCOLLECTION"))] # Imports the user collection name from the config file
groups = database[str(os.getenv("GROUPCOLLECTION"))] # Imports the group collection name from the config file
ecryptionKey = str(os.getenv("ENCRYPTIONKEY")) # Imports the encryption key from the config file
globalMessages = (database[str(os.getenv("GMESSAGECOLLECTION"))]) # Imports the global message collection name from the config file


if ecryptionKey != "": # Checks if the encryption key is empty (if so, it's disabled)
    encrypt = Fernet(codecs.encode((ecryptionKey).encode('utf-8'), 'base64'))     

print(f"Connected to {uri} and the application is running.") # Prints the connection string to the console, will be removed in the future due to security reasons
    

class Database:
    def __init__(self):
        self.collection = collection
        self.globalMessages = globalMessages
    
    def sampleConnection(self):
        try:
            username = random.randint(0, 100000)
            users.insert_one({"username": username, "password": "test"})
            print("Connected to the database.")
            users.delete_one({"username": username})
        except ConnectionFailure:
            print("Failed to connect to the database. {0}".format(ConnectionFailure))
        
    def insertNote(self, title, content, userID, private):
        self.collection.insert_one({"title": title, "content": content, "protected": "False", "userID": userID, "private": private})
        if private == "True":
            users.update_one({"_id": ObjectId(userID)}, {"$inc": {"privateNoteCount": 1}})
            return True
        elif private == "False":
            users.update_one({"_id": ObjectId(userID)}, {"$inc": {"publicNoteCount": 1}})
            return True
            
    def insertCustomIDNote(self, title, content, userID, private, id):
        if self.collection.count_documents({"customID": id}) > 0:
            return False
        else:
            self.collection.insert_one({"title": title, "content": content, "protected": "False", "userID": userID, "private": private, "CustomID": id})
            if private == "True":
                users.update_one({"_id": ObjectId(userID)}, {"$inc": {"privateNoteCount": 1}})
                return True
            elif private == "False":
                users.update_one({"_id": ObjectId(userID)}, {"$inc": {"publicNoteCount": 1}})
                return True
    
    def insertCustomIDNoteWithPassword(self, title, content, password, userID, private, id):
        if self.collection.count_documents({"customID": id}) > 0:
            return False
        else:
            self.collection.insert_one({"title": title, "content": content, "password": password, "protected": "True", "userID": userID, "private": private, "CustomID": id})
            if private == "True":
                users.update_one({"_id": ObjectId(userID)}, {"$inc": {"privateNoteCount": 1}})
                return True
            elif private == "False":
                users.update_one({"_id": ObjectId(userID)}, {"$inc": {"passwordNoteCount": 1}})
                return True
        
        
    def insertNoteWithPassword(self, title, content, password, userID, private):
        self.collection.insert_one({"title": title, "content": content, "password": password, "protected": "True", "userID": userID, "private": private})
        if private == "True":
            users.update_one({"_id": ObjectId(userID)}, {"$inc": {"privateNoteCount": 1}})
        elif private == "False":
            users.update_one({"_id": ObjectId(userID)}, {"$inc": {"passwordNoteCount": 1}})
    def getNotes(self):
        publicNotes = self.collection.find({"private": "False", "CustomID": {"$exists": False}})
        return publicNotes
    
    def deleteNotes(self):
        self.collection.delete_many({})
        
    def deleteNote(self, id):
        try:
            if self.collection.find_one({"CustomID": id}):
                if not self.collection.find_one({"CustomID": id})["private"] == "False":
                    if not self.collection.find_one({"CustomID": id})["protected"] == "False":
                        users.update_one({"_id": ObjectId(self.collection.find_one({"CustomID": id})["userID"])}, {"$inc": {"passwordNoteCount": -1}})
                    else:
                        users.update_one({"_id": ObjectId(self.collection.find_one({"CustomID": id})["userID"])}, {"$inc": {"privateNoteCount": -1}})
                else:
                    users.update_one({"_id": ObjectId(self.collection.find_one({"CustomID": id})["userID"])}, {"$inc": {"publicNoteCount": -1}})
                
                self.collection.delete_one({"CustomID": id})
                return True
            elif self.collection.find_one({"_id": ObjectId(id)}):
                self.collection.delete_one({"_id": ObjectId(id)})
                return True
            
        except Exception as e:
            print (e)
            return False
        
    def clearUserNotes(self, username):
        self.collection.delete_many({"userID": ObjectId(self.getUserID(username))})
    
    def updateNote(self, _id, newNote):
        self.collection.update_one(_id, {"$set": newNote})
        
    def getNoteById(self, id):
        try:
            if self.collection.find_one({"_id": ObjectId(id)}):
                return self.collection.find_one({"_id": ObjectId(id)})
            
        except:
            return self.collection.find_one({"CustomID": id})
    def getNoteByTitle(self, title):
        return self.collection.find_one({"title": title})
    
    def getNoteByContent(self, content):
        return self.collection.find_one({"content": content})
    def login(self, username, password):
        if ecryptionKey != "":
            password = password.encode('utf-8')
            if users.find_one({"username": username}):
                stored_password = users.find_one({"username": username})["password"]
                if password == encrypt.decrypt(stored_password):
                    return True
            else:
                return False
        return False
    
    def register(self, username, password):
        if ecryptionKey != "":
            password = password.encode('utf-8')
            password = encrypt.encrypt(password)
        if users.find_one({"username": username}):
            return False
        else:
            users.insert_one({"username": username, "password": password})
            return True

    def deleteAccount(self, username):
        if users.find_one({"username": username}):
            self.clearUserNotes(username)
            users.delete_one({"username": username})
            return True
        else:
            return False
        
    def changeUsername(self, username, newUsername):
        if users.find_one({"username": username}):
            users.update_one({"username": username}, {"$set": {"username": newUsername}})
            return True
        else:
            return False
        
    def changePassword(self, username, newPassword):
        if ecryptionKey != "":
            newPassword = newPassword.encode('utf-8')
            newPassword = encrypt.encrypt(newPassword)
        if users.find_one({"username": username}):
            users.update_one({"username": username}, {"$set": {"password": newPassword}})
            return True
        else:
            return False
        
    def changeTitle(self, id, newTitle):
        if self.collection.find_one({"_id": ObjectId(id)}):
            self.collection.update_one({"_id": ObjectId(id)}, {"$set": {"title": newTitle}})
            return True
        else:
            return False
    
    def changeContent(self, id, newContent):
        if self.collection.find_one({"_id": ObjectId(id)}):
            self.collection.update_one({"_id": ObjectId(id)}, {"$set": {"content": newContent}})
            return True
        else:
            return False
        
    def getUserID(self, username):
        if users.find_one({"username": username}):
            return users.find_one({"username": username})["_id"]
        else:
            return False
        
    def getPrivateNotes(self, userID):
        privateNotes = []
        for note in self.collection.find({"userID": userID}):
            if note["private"] == "True" and "CustomID" not in note:
                privateNotes.append(note)
        return privateNotes

    def getPrivateNotesWithCustomID(self, userID):
        notes = []
        for note in self.collection.find({"userID": userID}):
            if note["private"] == "True" and "CustomID" in note:
                notes.append(note)
        return notes
    
    def getNoteCreator(self, noteID):
        if self.collection.find_one({"CustomID": noteID}):
            if self.collection.find_one({"CustomID": noteID}):
                userID = self.collection.find_one({"CustomID": noteID})["userID"]
                return users.find_one({"_id": ObjectId(userID)})["_id"]
        else:
            if self.collection.find_one({"_id": ObjectId(noteID)}):
                userID = self.collection.find_one({"_id": ObjectId(noteID)})["userID"]
                return users.find_one({"_id": ObjectId(userID)})["_id"]
            else:
                return False
    
    def getPasswordProtectedNotes(self, userID):
        passwordProtectedNotes = []
        for note in self.collection.find({"userID": userID}):
            if note["protected"] == "True" and "CustomID" not in note:
                passwordProtectedNotes.append(note)
        return passwordProtectedNotes
    
    def getPasswordProtectedNotesWithCustomID(self, userID):
        passwordProtectedNotes = []
        for note in self.collection.find({"userID": userID}):
            if note["protected"] == "True" and "CustomID" in note:
                passwordProtectedNotes.append(note)
        return passwordProtectedNotes
    
    def getStatistics(self, userID, type):
        user = users.find_one({"_id": ObjectId(userID)})
        if type == "private":
            return user["privateNoteCount"]
        elif type == "public":
            return user["publicNoteCount"]
        elif type == "password":
            return user["passwordNoteCount"]
        elif type == "total":
            total_count = 0
            if "privateNoteCount" in user:
                total_count += user["privateNoteCount"]
            else:
                users.update_one({"_id": ObjectId(userID)}, {"$set": {"privateNoteCount": 0}})
            if "publicNoteCount" in user:
                total_count += user["publicNoteCount"]
            else:
                users.update_one({"_id": ObjectId(userID)}, {"$set": {"publicNoteCount": 0}})
            if "passwordNoteCount" in user:
                total_count += user["passwordNoteCount"]
            else:
                users.update_one({"_id": ObjectId(userID)}, {"$set": {"passwordNoteCount": 0}})
            return total_count
    
    def checkUsername(self, username):
        if users.find_one({"username": username}):
            return True
        else:
            return False
        
    def checkPassword(self, username, password):
        if users.find_one({"username": username}):
            if ecryptionKey != "":
                password = password.encode('utf-8')
                stored_password = users.find_one({"username": username})["password"]
                if password == encrypt.decrypt(stored_password):
                    return True
            else:
                if users.find_one({"username": username})["password"] == password:
                    return True
            return False
    
    def changeUsername(self, username, newUsername):
        if users.find_one({"username": username}):
            users.update_one({"username": username}, {"$set": {"username": newUsername}})
            return True
        else:
            return False
        
    def changePassword(self, username, newPassword):
        if users.find_one({"username": username}):
            if ecryptionKey != "":
                 newPassword = newPassword.encode('utf-8')
                 newPassword = encrypt.encrypt(newPassword)
                 users.update_one({"username": username}, {"$set": {"password": newPassword}})
                 return True
            else:
                users.update_one({"username": username}, {"$set": {"password": newPassword}})
                return True
        else:
            return False


    def setPro(self, username):
        userID = self.getUserID(username)
        if users.find_one({"_id": ObjectId(userID)}):
            if "pro" in users.find_one({"_id": ObjectId(userID)}):
                users.update_one({"_id": ObjectId(userID)}, {"$set": {"pro": True}})
            else:
                users.update_one({"_id": ObjectId(userID)}, {"$set": {"pro": True}})
    
    def removePro(self, username):
        userID = self.getUserID(username)
        if users.find_one({"_id": ObjectId(userID)}):
            if "pro" in users.find_one({"_id": ObjectId(userID)}):
                users.update_one({"_id": ObjectId(userID)}, {"$set": {"pro": False}})
            else:
                users.update_one({"_id": ObjectId(userID)}, {"$set": {"pro": False}})
    
    def removePro(self, username):
        userID = self.getUserID(username)
        if users.find_one({"_id": ObjectId(userID)}):
            if "pro" in users.find_one({"_id": ObjectId(userID)}):
                users.update_one({"_id": ObjectId(userID)}, {"$set": {"pro": False}})
            else:
                users.update_one({"_id": ObjectId(userID)}, {"$set": {"pro": False}})
                
    def checkPro(self, username):
        userID = self.getUserID(username)
        if users.find_one({"_id": ObjectId(userID)}):
            if "pro" in users.find_one({"_id": ObjectId(userID)}) and users.find_one({"_id": ObjectId(userID)})["pro"] == True:
                return True
            else:
                return False
            
    def getUsernameFromID(self, userID):
        if users.find_one({"_id": ObjectId(userID)}):
            return users.find_one({"_id": ObjectId(userID)})["username"]
        else:
            return False

    def checkNoteOwnerProStatus(self, noteID):
        userID = self.getNoteCreator(noteID)
        
        if users.find_one({"_id": ObjectId(userID)}):
            if "pro" in users.find_one({"_id": ObjectId(userID)}) and users.find_one({"_id": ObjectId(userID)})["pro"] == True:
                return True
            else:
                return False
            
    def checkNoteCustomID(self, customID):
        if self.collection.find_one({"CustomID": customID}):
            return True
        else:
            return False
    
    def getNoteByCustomID(self, customID):
        return self.collection.find_one({"CustomID": customID})
        
    def getCustomNotes(self):
        return self.collection.find({"CustomID": {"$exists": True}, "private": "False"})
    
    def getCustomIDByNoteID(self, noteID):
        if self.collection.find_one({"_id": ObjectId(noteID)}):
                print("Note found!: " + noteID)
                return self.collection.find_one({"_id": ObjectId(noteID)})["CustomID"]
        else:
            return False
    
    def getNoteContentByCustomID(self, noteID):
        if self.collection.find_one({"CustomID": noteID}):
            return self.collection.find_one({"CustomID": noteID})
        else:
            return False
        
    def addGlobalMessage(self, message):
        if self.globalMessages.count_documents({}) == 0:
            self.globalMessages.insert_one({"message": message})
            return True
        elif self.globalMessages.count_documents({"message": message}) > 0:
            return False
        else:
            self.globalMessages.insert_one({"message": message})
            return True

    def getGlobalMessages(self):
        messageDict = {}
        if self.globalMessages.count_documents({}) == 0:
            return False
        for messages in self.globalMessages.find():
            messageDict["message"] = messages["message"]
            messageDict["id"] = messages["_id"]
        return messageDict

    def removeGlobalMessage(self):
        if self.globalMessages.find_one_and_delete({}):
            return True
        else:
            return False
    
    def changeTitle(self, noteID, title):
        try:
            if ObjectId.is_valid(noteID):
                if self.collection.find_one({"_id": ObjectId(noteID)}):
                    self.collection.update_one({"_id": ObjectId(noteID)}, {"$set": {"title": title}})
                    return True
                else:
                    return False
            else:
                if self.collection.find_one({"CustomID": noteID}):
                    self.collection.update_one({"CustomID": noteID}, {"$set": {"title": title}})
                    return True
                else:
                    return False
            
        except Exception as e:
            return e
    
    def changeContent(self, noteID, content):
        try:
            if ObjectId.is_valid(noteID):
                if self.collection.find_one({"_id": ObjectId(noteID)}):
                    self.collection.update_one({"_id": ObjectId(noteID)}, {"$set": {"content": content}})
                    return True
                else:
                    return False
            else:
                if self.collection.find_one({"CustomID": noteID}):
                    self.collection.update_one({"CustomID": noteID}, {"$set": {"content": content}})
                    return True
                else:
                    return False
        except Exception as e:
            return e
    
    def changeCustomID(self, noteID, customID):
        try:
            if self.collection.find_one({"_id": ObjectId(noteID)}):
                self.collection.update_one({"_id": ObjectId(noteID)}, {"$set": {"CustomID": customID}})
                return True
            else:
                return False
        except Exception as e:
            return e
    
    def checkNoteExists(self, noteID):
        if ObjectId.is_valid(noteID):
            if self.collection.find_one({"_id": ObjectId(noteID)}):
                return True
            else:
                return False
        elif self.collection.find_one({"CustomID": noteID}):
            if self.collection.find_one({"CustomID": noteID}):
                return True
            else:
                return False
        else:
            return False

    def noteUpdate(self, noteID, title, content):
        if self.collection.find_one({"CustomID": noteID}):
            self.collection.update_one({"CustomID": noteID}, {"$set": {"title": title, "content": content}})
            return True
        else:
            if self.collection.find_one({"_id": ObjectId(noteID)}):
                self.collection.update_one({"_id": ObjectId(noteID)}, {"$set": {"title": title, "content": content}})
                return True
            
    def updateCustomIDNote(self, title, content, id):
        if self.collection.find_one({"CustomID": id}):
            self.collection.update_one({"CustomID": id}, {"$set": {"title": title, "content": content}})
            return True
        else:
            return False
        
    # Groups
    class group:
        def __init__(self) -> None:
            self.groups = groups
            self.users = users
        
        def addUserToGroup(self, groupName, userID):
            try:
                if self.users.find_one({"_id": ObjectId(userID)}):
                    if self.groups.find_one({"members": ObjectId(userID)}):
                        return False
                    else:
                        self.groups.update_one({"name": groupName}, {"$push": {"members": userID}})
                        return True
                else:
                    return False
            except:
                return False
                    
            
        def createGroup(self, name, groupOwner):
            try:
                if self.groups.find_one({"name": name}):
                    return False
                else:
                    if self.users.find_one({"_id": ObjectId(groupOwner)}):
                        if self.groups.find_one({"members": ObjectId(groupOwner)}):
                            return False
                        else: 
                            self.groups.insert_one({"name": name, "owner": groupOwner, "members": [groupOwner]})
                            return True
                    else:
                        return False
            except:
                return False
            
        def getGroupMembers(self, name):
            if self.groups.find_one({"name": name})["members"] != None:
                return self.groups.find_one({"name": name})["members"]
            else:
                return False
        
        def checkUserGroupName(self, userID):
            if self.groups.find({"members": userID})["name"] != None:
                return self.groups.find({"members": userID})["name"]
            else:
                return False
        
        def getUserGroups(self, userID):
            if self.groups.find({"members": userID})["name"] != None:
                return self.groups.find({"members": userID})["name"]
            else:
                return False     
            
            