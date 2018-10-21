# import dialogflow_v2 as df
from flask import Flask, request, jsonify, render_template, make_response
# import os
import requests
import json
import popo
from google.cloud.language import types
from google.cloud import language
from google.cloud.language import enums
import six
import stopwords


class Instance:

    def __init__(self, app):
        self.app = app
        self.value_critical = 0
        self.value_regular = 0
        self.cache_questions = []
        self.non_critical_only = []
        self.req_result = None
        self.stw_set = set(stopwords.stopword_list)

    def increment_critical(self):
        self.value_critical += 1

    def get_current_count_critical(self):
        return self.value_critical

    def set_current_count_critical(self, val):
        self.value_critical = val

    def increment_regular(self):
        self.value_regular += 1

    def get_current_count_regular(self):
        return self.value_regular

    def set_current_count_regular(self, val):
        self.value_regular = val


app = Flask(__name__)
sess_inst = Instance(app)

log = app.logger


@app.route("/")
def index():
    return "cyka blyat"


cacheQuestions = []


@app.route("/core", methods=["POST"])
def webhook():
    req = request.get_json()

    try:
        action = req.get("queryResult").get("action")
    except AttributeError:
        return "Something went wrong, Please try again. "

    res = ""
    if action == "learn":
        res = learnSubjectActivity(req)

    # This will be asked irrespective, so we will fetch all the questions irrespective

    elif action == "request.recital.critical":
        res = requestReciteActivity(req)




    # This will be called when user says yes to the above
    elif action == "confirm.start.recital":
        res = startCriticalActivity(req)

    # This is the feedback loop that is the result of the above two (for critical questions)
    elif action == "answer.on.prompt":
        res = processAnswerLoopForCritical(req)



    # This will be called when user says no to request.recital.critical
    elif action == "confirm.start.regular":
        res = startRegularActivity(req)

    # This is the feedback loop that is the result of the above two (for regular questions)
    elif action == "answer.on.prompt.regular":
        res = processAnswerLoopForRegular(req)



    elif action == "stop.training":
        res = sessionEnd(req)

    print("Action:" + action)
    print("Response:" + res)

    return make_response(jsonify({"fulfillmentText": res}))


"""
This method is used to start the recital, 
we send a request to the server, it fetches the questions
and we get a response saying the number of questions in this critical section
and a comfirmation prompting the user to start the recital
"""


def requestReciteActivity(req):
    if not cacheQuestions:
        req_url = "https://recall-bot.herokuapp.com/api/revise"
        # call rastogi's endpoint
        req_result = requests.get(req_url).content

        print(json.loads(req_result))

        result_mapped = popo.welcome_from_dict(json.loads(req_result))

        for indiv_result in result_mapped:
            qalist = indiv_result.qa
            for qas in qalist:
                print("Q:", qas.question)
                print("A:", qas.answer)
                sess_inst.cache_questions.append({"question": qas.question, "answer": qas.answer, "topic_id": indiv_result.id})
                if indiv_result.priority == 0:
                    sess_inst.non_critical_only.append({"question": qas.question, "answer": qas.answer, "topic_id": indiv_result.id})

        return " I have {0} questions in critical and {1} in regular, do you want to start critical?".format(len(sess_inst.cache_questions), len(sess_inst.non_critical_only))

    # TODO:same session restart

    return " I have {0} questions in critical and {1} in regular, do you want to start critical?".format(len(sess_inst.cache_questions), len(sess_inst.non_critical_only))


"""
This method inits the first question after the confirmation
Once we get the answer for the first we hook it to a loop 
so we deal with that in processAnswerLoopForCritical
"""


def startCriticalActivity(req):
    returnStr = "Ok, Here is Question {0}.  ".format(sess_inst.get_current_count_critical() + 1)
    if len(sess_inst.cache_questions)>0:
        append = sess_inst.cache_questions[sess_inst.get_current_count_critical()]["question"]
        returnStr += str(append)
        sess_inst.increment_critical()
        return returnStr
    else:
        return "No more questions available this session."

"""
Answer processor for ans 0--->n-1 and question hook for 
questions 1--->n-1

Process answer here and modify appropriately

When we enter this method, get_current_count_critical already points towards the next question/answer pair
so to get the previous ones, we must do -1
"""


def processAnswerLoopForCritical(req):
    parameters = req["queryResult"]["parameters"]["any"]

    if not sess_inst.cache_questions or sess_inst.cache_questions and len(sess_inst.cache_questions) > 0 and sess_inst.get_current_count_critical() > len(sess_inst.cache_questions):
        return "I am out of questions, your session has ended."
    elif len(sess_inst.cache_questions)>=sess_inst.get_current_count_critical():
        act_ans = sess_inst.cache_questions[sess_inst.get_current_count_critical() - 1]["answer"]
        act_ans_entities_set = entities_text(act_ans)
        act_ans_set = set([w.lower().replace(",", "").replace(".", "") for w in act_ans.split(" ")])
        act_ans_set = act_ans_set.difference(sess_inst.stw_set)

        user_ans = "" if not parameters else parameters
        user_ans_entities_set = entities_text(user_ans)
        user_ans_set = set([w.lower().replace(",", "").replace(".", "") for w in user_ans.split(" ")])
        user_ans_set = user_ans_set.difference(sess_inst.stw_set)

        print("act ans entity set", act_ans_entities_set)
        print("user ans entity set", user_ans_entities_set)
        print("act ans set", act_ans_set)
        print("user ans set", user_ans_set)
        print("entity intersection", act_ans_entities_set.intersection(user_ans_entities_set))
        print("ans intersection", act_ans_set.intersection(user_ans_set))

        drEntities = 1 if len(act_ans_entities_set) == 0 else len(act_ans_entities_set)
        drAns = 1 if len(act_ans_set) == 0 else len(act_ans_set)

        correct_entity_percent = float(len(act_ans_entities_set.intersection(user_ans_entities_set))) / drEntities
        correct_answer_percent = float(len(act_ans_set.intersection(user_ans_set))) / drAns



        if correct_entity_percent > 0.3 or correct_answer_percent > 0.2:
            # TODO:replace this with answer accuracy from GCP NLP
            returnStr = "Correct Answer"
            normalized_percent = 1
        else:
            # Prints out the correct Answer
            returnStr = "Your answer was {0}% accurate. {1}".format(correct_entity_percent, sess_inst.cache_questions[sess_inst.get_current_count_critical() - 1]["answer"])
            normalized_percent = 0
            # TODO:use the response.

        topic_id = sess_inst.cache_questions[sess_inst.get_current_count_critical() - 1]["topic_id"]
        dictToSend = {"score": normalized_percent}
        req_url = "https://recall-bot.herokuapp.com/api/revise/" + topic_id
        print(req_url)
        res = requests.put(req_url, json=dictToSend)

        if sess_inst.get_current_count_critical() < len(sess_inst.cache_questions):
            # Appends the next question to be asked
            next_ques = sess_inst.cache_questions[sess_inst.get_current_count_critical()]["question"]
            append = ". Your next question,  {0}".format(next_ques)
            sess_inst.increment_critical()
        else:
            sess_inst.set_current_count_critical(0)
            sess_inst.cache_questions.clear()
            sess_inst.set_current_count_regular(0)
            sess_inst.non_critical_only.clear()
            sess_inst.req_result = None
            append = ". I am out of questions, your session has ended."

        print("Response ye hai bhau:->", res)

        returnStr += append
        return returnStr
    return "No more questions available in this session."


def startRegularActivity(req):
    returnStr = "Here are your questions for the regular section, "
    returnStr += "Question {0}.  ".format(sess_inst.get_current_count_regular() + 1)
    if len(sess_inst.non_critical_only)>0:
        append = sess_inst.non_critical_only[sess_inst.get_current_count_regular()]["question"]
        returnStr += str(append)
        sess_inst.increment_regular()
        return returnStr
    else:
        return "No more questions available this session."


def processAnswerLoopForRegular(req):
    parameters = req["queryResult"]["parameters"]["any"]

    if not sess_inst.non_critical_only or sess_inst.non_critical_only and len(sess_inst.non_critical_only) > 0 and sess_inst.get_current_count_regular() > len(sess_inst.non_critical_only):
        return "I am out of questions, your session has ended."
    elif len(sess_inst.non_critical_only) >= sess_inst.get_current_count_regular():
        act_ans = sess_inst.non_critical_only[sess_inst.get_current_count_regular() - 1]["answer"]
        act_ans_entities_set = entities_text(act_ans)
        act_ans_set = set([w.lower().replace(",", "").replace(".", "") for w in act_ans.split(" ")])
        act_ans_set = act_ans_set.difference(sess_inst.stw_set)

        user_ans = "" if not parameters else parameters
        user_ans_entities_set = entities_text(user_ans)
        user_ans_set = set([w.lower().replace(",", "").replace(".", "") for w in user_ans.split(" ")])
        user_ans_set = user_ans_set.difference(sess_inst.stw_set)

        print("act ans entity set", act_ans_entities_set)
        print("user ans entity set", user_ans_entities_set)
        print("act ans set", act_ans_set)
        print("user ans set", user_ans_set)
        print("entity intersection", act_ans_entities_set.intersection(user_ans_entities_set))
        print("ans intersection", act_ans_set.intersection(user_ans_set))

        drEntities = 1 if len(act_ans_entities_set) == 0 else len(act_ans_entities_set)
        drAns = 1 if len(act_ans_set) == 0 else len(act_ans_set)

        correct_entity_percent = float(len(act_ans_entities_set.intersection(user_ans_entities_set))) / drEntities
        correct_answer_percent = float(len(act_ans_set.intersection(user_ans_set))) / drAns

        if correct_entity_percent > 0.3 or correct_answer_percent > 0.2:
            # TODO:replace this with answer accuracy from GCP NLP
            returnStr = "Correct Answer"
            normalized_percent = 1
        else:
            # Prints out the correct Answer
            returnStr = "Your answer was {0}% accurate. {1}".format(correct_entity_percent, sess_inst.non_critical_only[sess_inst.get_current_count_regular() - 1]["answer"])
            normalized_percent = 0
            # TODO:use the response.

        topic_id = sess_inst.non_critical_only[sess_inst.get_current_count_regular() - 1]["topic_id"]
        dictToSend = {"score": normalized_percent}
        req_url = "https://recall-bot.herokuapp.com/api/revise/" + topic_id
        print(req_url)
        res = requests.put(req_url, json=dictToSend)

        if sess_inst.get_current_count_regular() < len(sess_inst.non_critical_only):
            # Appends the next question to be asked
            next_ques = sess_inst.non_critical_only[sess_inst.get_current_count_regular()]["question"]
            append = ". Your next question,  {0}".format(next_ques)
            sess_inst.increment_regular()
        else:
            sess_inst.set_current_count_regular(0)
            sess_inst.non_critical_only.clear()
            sess_inst.set_current_count_critical(0)
            sess_inst.cache_questions.clear()
            sess_inst.req_result = None
            append = ". I am out of questions, your session has ended."

        print("Response ye hai bhau:->", res)
        returnStr += append
        return returnStr
    return "No more questions available in this session."


"""
Discontinued/Half Implemented/Unused features
"""


def learnSubjectActivity(req):
    parameters = req["queryResult"]["parameters"]["subject"]

    print(json.dumps(req, indent=5))

    print("Params are:")
    print(json.dumps(parameters, indent=4))

    # TODO:error handling for unknown or wrong
    # TODO:add personalization

    req_url = "https://recall-bot.herokuapp.com/api/"
    # call rastogi's endpoint
    subject_questions_json = requests.get(req_url).content
    subject_questions_json = json.loads(subject_questions_json)
    #
    # debug
    # print(subject_questions_json)

    return " Your requested subject is " + parameters


def sessionEnd(req):
    returnStr = "Buzzye"
    return returnStr


"""
Helper methods for NLP
"""


def entities_text(text):
    """Detects entities in the text."""
    client = language.LanguageServiceClient()

    if isinstance(text, six.binary_type):
        text = text.decode('utf-8')

    # Instantiates a plain text document.
    document = types.Document(
        content=text,
        type=enums.Document.Type.PLAIN_TEXT)

    # Detects entities in the document. You can also analyze HTML with:
    #   document.type == enums.Document.Type.HTML
    entities = client.analyze_entities(document).entities

    identified_entities = [str(entity.name).lower() for entity in entities]

    return set(identified_entities)


if __name__ == "__main__":
    app.run(debug=True)
