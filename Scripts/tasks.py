import json as Json
import os
import os.path
import random
import threading
import time

import pygame

pygame.mixer.init()
_time = time.time()


def default_function(*arg):
    pass


def run_after_delay(func, delay):
    print("delay:", delay)
    threading.Event().wait(timeout=delay)
    func()
    print("func done:")


def start_task(task, on_done=None):
    def wrapped_task(task, on_done):
        task.run()
        if on_done is not None and task.isAlive is True:
            on_done()

    t = threading.Thread(target=wrapped_task, args=(task, on_done))
    t.setDaemon(True)
    t.start()
    return t


class NBackTask:
    class Trial:
        def __init__(self, words):
            self.couples = []
            self.target = None
            self.isTargetCorrect = False
            self.next_counter = 0
            for i in range(0, len(words), 2):
                self.couples.append(words[i:i + 2])

        def chooseTarget(self, nback, target=None):
            if target:
                self.target = target
                self.isTargetCorrect = False
            else:
                self.target = random.choice(self.couples[-nback])
                self.isTargetCorrect = True

        def getWrongTarget(self, nback):
            array = self.couples[:-nback] + [self.couples[-nback + 1]]
            return random.choice(random.choice(array))

        def next(self):
            values = None
            if self.next_counter < len(self.couples):
                values = self.couples[self.next_counter]
                self.next_counter += 1
            else:
                self.next_counter = 0
            return values

        def __repr__(self):
            return "* Couples:" + str(self.couples) + " Target: " + str(self.target) + " " + str(
                self.isTargetCorrect) + " *"

    def __init__(self, config: dict, functions: dict):
        # Config
        self.words = config['words'] if 'words' in config else []
        self.nback = config['nback'] if 'nback' in config else 2
        self.trials_amount = config['trials_amount'] if 'trials_amount' in config else 2
        self.timeout = config['timeout'] if 'timeout' in config else 2
        self.rest = config['rest'] if 'rest' in config else 30
        self.instructions = config['instructions'] if 'instructions' in config else None

        # Functions
        self.setContent = functions['setContent'] if 'setContent' in functions else default_function
        self.setInsVisibility = functions['setInsVisibility'] if 'setInsVisibility' in functions else default_function
        self.setContentVisibility = functions[
            'setContentVisibility'] if 'setContentVisibility' in functions else default_function
        self.setWaitVisibility = functions[
            'setWaitVisibility'] if 'setWaitVisibility' in functions else default_function
        self.setEndVisibility = functions['setEndVisibility'] if 'setEndVisibility' in functions else default_function
        self.evSpaceKeyPressed = functions[
            'evSpaceKeyPressed'] if 'evSpaceKeyPressed' in functions else default_function
        self.onStart = functions['onStart'] if 'onStart' in functions else default_function
        self.sendClick = functions['sendClick'] if 'sendClick' in functions else default_function
        self.setInstructionsData = functions[
            'setInstructionsData'] if 'setInstructionsData' in functions else default_function

        # Others
        self.status = "start"
        self.currentTrial = None
        self.trials = []
        self.trialCounter = 0
        self.coupleCounter = 0
        self.current_difficulty = -1
        self.click = {"clicked": False, "delay": -1.0, "target": None, "is_correct": False, "difficulty": -1}
        self.countClick = False
        self.evSpaceKeyPressed = threading.Event()
        self.evTaskWindowLoaded = threading.Event()

        self.isAlive = True
        self.evTimer = threading.Event()
        self.round = 0

        # Error checking
        words_needed = self.calcWordsNeeded(self.nback, self.trials_amount)
        if words_needed['error']:
            raise ValueError(words_needed['msg'])
        if words_needed['words_amount'] != len(self.words):
            raise ValueError(
                "Expected " + str(words_needed['words_amount']) + " words, got " + str(len(self.words)) + " instead.")

    def spaceKeyPressed(self):
        self.evSpaceKeyPressed.set()
        if self.countClick:
            self.click["delay"] = time.time()
        return None

    def generateTrials(self):
        arr = self.words
        random.shuffle(arr)
        for i in range(0, self.trials_amount // 3):
            self.trials.append(NBackTask.Trial(arr[0:2 * self.nback]))
            arr = arr[2 * self.nback:]
        for i in range(0, self.trials_amount // 3):
            self.trials.append(NBackTask.Trial(arr[0:2 * (self.nback + 1)]))
            arr = arr[2 * (self.nback + 1):]
        for i in range(0, self.trials_amount // 6):
            self.trials.append(NBackTask.Trial(arr[0:2 * (self.nback + 2)]))
            arr = arr[2 * (self.nback + 2):]
        for i in range(0, self.trials_amount // 6):
            self.trials.append(NBackTask.Trial(arr[0:2 * (self.nback + 3)]))
            arr = arr[2 * (self.nback + 3):]
        return

    def chooseTargets(self):
        for i in range(0, self.trials_amount, 2):
            self.trials[i].chooseTarget(self.nback)
        wrong_targets = []
        for i in range(1, self.trials_amount, 2):
            wrong_target = self.trials[i].getWrongTarget(self.nback)
            wrong_targets.append(wrong_target)
        random.shuffle(wrong_targets)
        for i in range(1, self.trials_amount, 2):
            self.trials[i].chooseTarget(self.nback, wrong_targets.pop())

    def startRound(self):
        global _time
        print("New Round")
        # print(time.time() - _time)
        # _time = time.time()
        random.shuffle(self.trials)
        self.trialCounter = 0
        return

    def next(self):
        if self.trialCounter == -1:
            return {}
        currentCouple = self.trials[self.trialCounter].next()
        if currentCouple:
            return {"word_1": currentCouple[0], "word_2": currentCouple[1], "target": ""}
        else:
            currentTrial = self.trials[self.trialCounter]
            if len(self.trials) - 1 > self.trialCounter:
                self.trialCounter += 1
            else:
                self.trialCounter = -1
            self.current_difficulty = len(currentTrial.couples)
            return {"word_1": "", "word_2": "", "target": currentTrial.target,
                    "isTargetCorrect": currentTrial.isTargetCorrect, "difficulty": self.current_difficulty}

    def jsonSetContent(self, json):
        self.setContent(json["word_1"], json["target"], json["word_2"])
        return

    def set_onStart(self, func):
        self.onStart = func

    def set_sendClick(self, func):
        self.sendClick = func

    def getStatus(self):
        return self.status

    def getRound(self):
        if self.round == -1:
            return "Waiting"
        elif self.round == 0:
            return "Trial Round"
        else:
            return "Round " + str(self.round)

    def getDifficulty(self):
        return self.current_difficulty

    def taskWindowLoaded(self):
        self.evTaskWindowLoaded.set()

    def run(self):
        global _time
        _time = time.time()

        self.generateTrials()
        self.chooseTargets()
        for trial in self.trials:
            print(trial)
        self.evTaskWindowLoaded.wait()
        self.setInsVisibility(True)
        self.setInstructionsData(self.instructions)

        print("self.instructions", self.instructions)

        print("**************Task.Run starting...****************\n")
        self.evSpaceKeyPressed.wait()
        self.evSpaceKeyPressed.clear()
        print("Task.Run space pressed...\n")
        self.setInsVisibility(False)
        self.setContentVisibility(True)
        print("**************On Start****************\n")
        try:
            self.onStart()
        except Exception as e:
            print("On start ERROR", e)
        print("**************End On Start****************\n")
        for i in range(0, 5):
            self.round = i
            countclicks = 0
            counttrue = 0
            countfalse = 0
            levels = {}
            self.startRound()
            if i == 1:
                self.round = -1
                self.setContentVisibility(False)
                self.setWaitVisibility(True)
                self.evSpaceKeyPressed.wait()
                self.round = 1
                self.evSpaceKeyPressed.clear()
                self.setWaitVisibility(False)
                self.setContentVisibility(True)
            print("Round", i, "starting...")
            self.setContent("", "", "")
            self.status = "rest"
            self.evTimer.wait(timeout=self.rest)  # Should be 30 sec, too long for debug
            self.setContent("", "+", "")
            self.status = "between"
            self.evTimer.wait(timeout=self.timeout)
            while True and self.isAlive:
                json = self.next()
                with open('log.txt', 'a') as the_file:
                    the_file.write(Json.dumps(json, ensure_ascii=False) + "\n")
                if json is None or not json:
                    break
                if json["target"] != "":
                    self.countClick = True
                    self.status = "target"
                else:
                    self.status = "no-target"
                self.jsonSetContent(json)
                delay_start_time = time.time()
                self.click = {"clicked": False, "delay": -1.0, "target": None, "is_correct": False,
                              "round": self.getRound()}
                self.evTimer.wait(timeout=self.timeout)
                self.countClick = False
                if json["target"] != "":
                    if self.click["delay"] != -1.0:
                        self.click["delay"] = self.click["delay"] - delay_start_time
                        self.click["clicked"] = True
                    self.click["is_correct"] = json["isTargetCorrect"] == self.click["clicked"]
                    self.click["target"] = json["target"]
                    self.click["difficulty"] = json["difficulty"]
                    if self.sendClick is not None:
                        try:
                            # print("Target=",self.click["target"],"Clicked = ", self.click["clicked"], "isTargetCorrect =", json["isTargetCorrect"], "is_correct =", self.click["is_correct"])
                            with open('real_log.txt', 'a') as the_file:
                                the_file.write("tasks.py - " + str(self.click) + '\n')
                            self.sendClick(self.click)
                            if self.click["difficulty"] in levels:
                                levels[self.click["difficulty"]] += 1
                            else:
                                levels[self.click["difficulty"]] = 1

                            countclicks += 1
                            if self.click['is_correct']:
                                counttrue += 1
                            else:
                                countfalse += 1
                        except Exception as e:
                            print("ERROR!!!", e)

                self.status = "between"
                self.setContent("", "+", "")
                self.evTimer.wait(timeout=self.timeout)

        if self.isAlive:
            self.setEndVisibility(True)
            self.setContentVisibility(False)
        return

    def stop(self):
        self.isAlive = False
        self.evTimer.set()
        self.evSpaceKeyPressed.set()

    @staticmethod
    def calcWordsNeeded(nback, trials_amount):
        if trials_amount % 6 != 0:
            return {"error": True, "msg": "The trials' amount must be divisible by 6"}
        words_amount = (trials_amount // 3) * (nback * 2) + (trials_amount // 3) * ((nback + 1) * 2) + \
                       (trials_amount // 6) * ((nback + 2) * 2) + (trials_amount // 6) * ((nback + 3) * 2)
        return {"error": False, "words_amount": words_amount}


class EyesTask:

    def __init__(self, config: dict, functions: dict):
        # Config
        self.open_time = config['open_time'] if 'open_time' in config else 15
        self.close_time = config['close_time'] if 'close_time' in config else 15
        self.rounds = config['rounds'] if 'rounds' in config else 10
        self.open_sound = config['open_sound'] if 'open_sound' in config else None
        self.close_sound = config['close_sound'] if 'close_sound' in config else None
        self.instructions = config['instructions'] if 'instructions' in config else None

        # Functions
        self.setContent = functions['setContent'] if 'setContent' in functions else default_function
        self.setInsVisibility = functions['setInsVisibility'] if 'setInsVisibility' in functions else default_function
        self.setContentVisibility = functions[
            'setContentVisibility'] if 'setContentVisibility' in functions else default_function
        self.setWaitVisibility = functions[
            'setWaitVisibility'] if 'setWaitVisibility' in functions else default_function
        self.setEndVisibility = functions['setEndVisibility'] if 'setEndVisibility' in functions else default_function
        self.onStart = functions['onStart'] if 'onStart' in functions else default_function
        self.setInstructionsData = functions[
            'setInstructionsData'] if 'setInstructionsData' in functions else default_function

        # Others
        self.eyesState = "Open"
        self.round = 1
        self.isAlive = True
        self.evSpaceKeyPressed = threading.Event()
        self.evTaskWindowLoaded = threading.Event()

    def spaceKeyPressed(self):
        self.evSpaceKeyPressed.set()

        return None

    def getEyesState(self):
        return self.eyesState

    def getRound(self):
        return "Round " + str(self.round)

    def set_onStart(self, func):
        self.onStart = func

    def taskWindowLoaded(self):
        self.evTaskWindowLoaded.set()

    def run(self):
        path = os.path.dirname(os.path.realpath(__file__))
        openSoundPlayer = None
        closeSoundPlayer = None
        if self.open_sound:
            playOpen = os.path.isfile(path + "/../DBS/sounds/" + self.open_sound)
        if self.close_sound:
            playClose = os.path.isfile(path + "/../DBS/sounds/" + self.close_sound)
        self.evTaskWindowLoaded.wait()
        self.setInsVisibility(True)
        self.setInstructionsData(self.instructions)
        self.evSpaceKeyPressed.wait()
        self.evSpaceKeyPressed.clear()
        self.setInsVisibility(False)
        self.setContentVisibility(True)
        try:
            self.onStart()
        except Exception as e:
            print("On start ERROR", e)
        for i in range(0, self.rounds):
            if not self.isAlive:
                return
            self.round = i + 1
            self.setContent("Open")
            self.eyesState = "Open"
            _t = time.time()
            if playOpen:
                pygame.mixer.music.load(path + "/../DBS/sounds/" + self.open_sound)
                pygame.mixer.music.play()
            # openSoundPlayer.play()
            print("openSoundPlayer - time:", time.time() - _t)
            threading.Event().wait(timeout=self.open_time)
            pygame.mixer.music.stop()
            self.setContent("Close")
            self.eyesState = "Closed"
            _t = time.time()
            if playOpen:
                pygame.mixer.music.load(path + "/../DBS/sounds/" + self.close_sound)
                pygame.mixer.music.play()
            print("closeSoundPlayer - time:", time.time() - _t)
            threading.Event().wait(timeout=self.open_time)
            pygame.mixer.music.stop()

        if self.isAlive:
            self.setEndVisibility(True)
            self.setContentVisibility(False)


class IAPSTask:

    def __init__(self, config: dict, functions: dict):
        # Config
        self.images = config['images'] if 'images' in config else []
        self.rounds = config['rounds'] if 'rounds' in config else []
        self.fixation = config['fixation'] if 'fixation' in config else 0.5
        self.rest = config['rest'] if 'rest' in config else 1.5
        self.mask = config['mask'] if 'mask' in config else ""
        self.mask_duration = config['mask_duration'] if 'mask_duration' in config else 0.1
        self.instructions = config['instructions'] if 'instructions' in config else None

        # Functions
        self.sendClick = functions['sendClick'] if 'sendClick' in functions else default_function
        self.setContent = functions['setContent'] if 'setContent' in functions else default_function
        self.setInsVisibility = functions['setInsVisibility'] if 'setInsVisibility' in functions else default_function
        self.setCrossVisibility = functions[
            'setCrossVisibility'] if 'setCrossVisibility' in functions else default_function
        self.setContentVisibility = functions[
            'setContentVisibility'] if 'setContentVisibility' in functions else default_function
        self.setWaitVisibility = functions[
            'setWaitVisibility'] if 'setWaitVisibility' in functions else default_function
        self.setEmotionVisibility = functions[
            'setEmotionVisibility'] if 'setEmotionVisibility' in functions else default_function
        self.setEndVisibility = functions['setEndVisibility'] if 'setEndVisibility' in functions else default_function
        self.setKeyChoosingVisibility = functions[
            'setKeyChoosingVisibility'] if 'setKeyChoosingVisibility' in functions else default_function
        self.onStart = functions['onStart'] if 'onStart' in functions else default_function
        self.setInstructionsData = functions[
            'setInstructionsData'] if 'setInstructionsData' in functions else default_function

        # Others
        self.isAlive = True
        self.emotion = ""
        self.evEmotionChosen = threading.Event()
        self.evSpaceKeyPressed = threading.Event()
        self.evTaskWindowLoaded = threading.Event()
        self.click = {"clicked": False, "delay": -1.0, "target": None, "is_correct": False, "difficulty": -1}

    def spaceKeyPressed(self):
        self.evSpaceKeyPressed.set()

    def emotionChosen(self, emotion):
        self.emotion = emotion
        self.evEmotionChosen.set()

    def set_onStart(self, func):
        self.onStart = func

    def set_sendClick(self, func):
        self.sendClick = func

    def taskWindowLoaded(self):
        self.evTaskWindowLoaded.set()

    def run(self):
        self.evTaskWindowLoaded.wait()
        self.setInsVisibility(True)
        self.setInstructionsData(self.instructions)
        self.setInsVisibility(True)
        self.evSpaceKeyPressed.wait()
        self.evSpaceKeyPressed.clear()
        self.setInsVisibility(False)
        self.setKeyChoosingVisibility(True)
        self.evSpaceKeyPressed.clear()
        self.evSpaceKeyPressed.wait()
        self.evSpaceKeyPressed.clear()
        self.setKeyChoosingVisibility(False)
        try:
            self.onStart()
        except Exception as e:
            print("On start ERROR", e)
        path = os.path.dirname(os.path.realpath(__file__))
        # for image in self.images:
        #     print("NEW IMAGE")
        #     print(image["path"])
        #     self.setContentVisibility(True)
        #     self.setContent(image["path"])
        #     if image["display_time"] > 0:
        #         threading.Event().wait(image["display_time"])
        #         self.setContentVisibility(False)
        #         self.setEmotionVisibility(True)
        #     start = time.time()
        #     self.evEmotionChosen.clear()
        #     self.evEmotionChosen.wait()
        #     print(self.emotion)
        #     self.evEmotionChosen.clear()
        #     end = time.time()
        #     rt = end - start
        #     print(rt)
        #     self.setEmotionVisibility(False)
        #     self.setContentVisibility(False)
        #     self.setWaitVisibility(True)
        #     self.evSpaceKeyPressed.clear()
        #     self.evSpaceKeyPressed.wait()
        #     self.evSpaceKeyPressed.clear()
        #     self.setWaitVisibility(False)
        random.shuffle(self.images)
        random.shuffle(self.rounds)
        round_size = len(self.images) // len(self.rounds)
        for i in range(0, len(self.rounds)):
            self.setWaitVisibility(True)
            self.evSpaceKeyPressed.clear()
            self.evSpaceKeyPressed.wait()
            self.evSpaceKeyPressed.clear()
            self.setWaitVisibility(False)
            start = i * round_size
            print(start)
            for j in range(start, start + round_size):
                print(self.images[j]["path"])
                self.setCrossVisibility(True)
                threading.Event().wait(timeout=self.fixation)
                self.setCrossVisibility(False)
                self.setContentVisibility(True)
                self.setContent(self.images[j]["path"])
                print("Round:", self.rounds[i])
                if self.rounds[i] > 0:
                    print("should call it")
                    content_off = lambda: [self.setContent(self.mask),
                                           threading.Event().wait(timeout=self.mask_duration),
                                           self.setContentVisibility(False)]
                    threading.Thread(target=run_after_delay, args=(content_off, self.rounds[i])).start()
                start = time.time()
                self.evEmotionChosen.clear()
                self.evEmotionChosen.wait()
                print(self.emotion)
                self.evEmotionChosen.clear()
                if self.rounds[i] == 0:
                    self.setContentVisibility(False)
                end = time.time()
                rt = end - start
                print(rt)
                self.sendClick(
                    {"image": self.images[j]["path"], "category": self.images[j]["category"], "reaction_time": rt,
                     "display_time": self.rounds[i], "response": self.emotion})
                threading.Event().wait(timeout=self.rest)
        if self.isAlive:
            self.setEndVisibility(True)
            self.setContentVisibility(False)


def pressForever(task):
    from random import randint, uniform
    e = ["Pleasant", "Unpleasant", "Neutral"]
    while True:
        emotion = e[randint(0, 2)]
        task.spaceKeyPressed()
        task.emotionChosen(emotion)
        threading.Event().wait(timeout=uniform(2, 3))


if __name__ == "__main__":
    # def sc(a, b, c):
    #     global _time
    #     print(time.time() - _time)
    #     _time = time.time()
    #     if not a:
    #         a = " "
    #     if not b:
    #         b = " "
    #     if not c:
    #         c = " "
    #     print(a, b, c)
    #
    #
    # config = {"words": list(range(1, 27)),
    #           "timeout": 0,
    #           "rest": 0,
    #           "nback": 1,
    #           "trials_amount": 6}
    # funcs = {
    #     "setContent": sc
    # }
    # task = NBackTask(config, funcs)
    # task.set_sendClick(lambda x: print(x))
    # t = start_task(task, lambda: print("Done"))

    funcs = {
        "setContent": lambda x: print(x)
    }
    config = {
        "images": [{"path": "image1", "display_time": 1}, {"path": "image2", "display_time": 0.8},
                   {"path": "image3", "display_time": 1}]
    }
    task = IAPSTask(config, funcs)
    t = start_task(task, lambda: print("Done"))
    press = threading.Thread(target=pressForever, args=(task,))
    press.setDaemon(True)
    press.start()
    t.join()
