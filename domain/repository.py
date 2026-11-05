import threading
 
 

class GymRepository:
    
    
    def __init__(self):
        self.classes = {}
        self.members = {}
        self.lock = threading.RLock()