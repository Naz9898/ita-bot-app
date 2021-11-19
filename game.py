import os
import random
import asyncio

class Game:
    def __init__(self, listening=True):
        self.listening = listening
        files_arr = os.listdir("./audio") if self.listening else os.listdir("./img") 
        self.deck = files_arr
        self.n = len( self.deck )
        self.ranking = {}

        self.game_on = True
        self.current_file = None
        self.current_answer = None

        self.current_correct = []

        self.consecutive_misses = 0
        return

    def submit(self, answer, user):
        if self.current_answer is not None and self.current_answer == answer and user not in self.current_correct:
            if user not in self.ranking:
                self.ranking[user] = 1
            else:
                self.ranking[user] = self.ranking[user] + 1
            self.current_correct.append(user)
            self.consecutive_misses = 0
        return

    def printRanking(self):
        self.ranking = {k: v for k, v in sorted(self.ranking.items(), key=lambda x: x[1])}
        print( self.ranking )
        return

        
    def setupQuestion(self):
        idx = random.randint(0, self.n-1)
        file = self.deck[idx]
        answer = file.rsplit('.', 1)[0].lower()

        while(not answer.isalpha()):
            self.deck.remove(file)
            self.n = self.n - 1
            idx = random.randint(0, self.n-1)
            file = self.deck[idx]
            answer = file.rsplit('.', 1)[0].lower()
        self.deck.remove(file)
        self.n = self.n - 1
        self.current_file = "./audio/"+file if self.listening else "./img/"+file
        self.current_answer = answer
        self.consecutive_misses = self.consecutive_misses + 1

        print(self.current_answer)

    def endQuestion(self):
        self.current_answer = None
        self.current_correct = []
        #print("Time's up!\n")

        points = list(self.ranking.values())

        if len( self.ranking ) > 0 and points[0] >= 10 :
            print("Fine gioco")
            self.game_on = False
            #self.printRanking()

        if self.consecutive_misses == 5:
            print("Troppi errori")
            self.game_on = False

    def stop(self):
        print("Game stopped")
        self.game_on = False
        self.printRanking()

#game = Game(files_arr)
#asyncio.run(  game.start() ) 


