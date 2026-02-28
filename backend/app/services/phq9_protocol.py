import re
from typing import Dict, List, Optional


class PHQ9Protocol:
    """Conversational PHQ-9 protocol with GAD-style flow:
    symptom yes/no first, then 4-point frequency when yes."""

    QUESTIONS = [
        {
            "number": 1,
            "text": "To begin, over the last 2 weeks, have you been bothered by having little interest or pleasure in doing things?",
            "clarification": "This means losing enjoyment in activities you usually like. Have you been bothered by that feeling?",
            "examples": "Examples: not wanting to do hobbies, avoiding social activities, or not enjoying things you usually enjoy.",
        },
        {
            "number": 2,
            "text": "Over the last 2 weeks, have you been bothered by feeling down, depressed, or hopeless?",
            "clarification": "This means a persistent sad, empty, or hopeless feeling beyond a normal bad day.",
            "examples": "Examples: feeling low for many days, feeling emotionally heavy, or feeling that things may not improve.",
        },
        {
            "number": 3,
            "text": "Have you been bothered by trouble sleeping, or by sleeping too much?",
            "clarification": "This includes trouble falling asleep, waking up and not returning to sleep, or sleeping much more than usual.",
            "examples": "Examples: broken sleep, insomnia, or oversleeping and still feeling tired.",
        },
        {
            "number": 4,
            "text": "Have you been bothered by feeling tired or having little energy?",
            "clarification": "This means low energy even after resting, or needing extra effort for simple tasks.",
            "examples": "Examples: feeling exhausted early, heavy body feeling, or low energy during routine work.",
        },
        {
            "number": 5,
            "text": "Have you been bothered by poor appetite or overeating?",
            "clarification": "This means noticeable appetite changes, such as eating much less or much more than usual.",
            "examples": "Examples: skipping meals often, loss of appetite, or frequent overeating.",
        },
        {
            "number": 6,
            "text": "Have you been bothered by feeling bad about yourself, or that you are a failure or have let yourself or your family down?",
            "clarification": "This refers to guilt, worthlessness, or feeling like a burden.",
            "examples": "Examples: frequent self-blame, feeling like a failure, or strong guilt about your role in the family.",
        },
        {
            "number": 7,
            "text": "Have you been bothered by trouble concentrating on things, such as reading or watching television?",
            "clarification": "This means difficulty maintaining focus on tasks, conversations, or decisions.",
            "examples": "Examples: rereading lines repeatedly, losing track in conversations, or difficulty finishing focused tasks.",
        },
        {
            "number": 8,
            "text": "Have you been bothered by moving or speaking so slowly that other people could notice, or the opposite, being so fidgety or restless that you move around more than usual?",
            "clarification": "This refers to visible slowing down or unusual restlessness that can be noticed.",
            "examples": "Examples: slowed speech/movement, pacing, frequent fidgeting, or inability to stay still.",
        },
        {
            "number": 9,
            "text": "And finally, have you been bothered by thoughts that you would be better off dead or of hurting yourself in some way?",
            "clarification": "This asks about thoughts of death, self-harm, or feeling better off not alive.",
            "examples": "Examples: repeated thoughts of self-harm, thoughts of being better off dead, or active self-harm thoughts.",
        },
    ]

    FREQUENCY_OPTIONS = {
        "not at all": 0,
        "several days": 1,
        "more than half the days": 2,
        "nearly every day": 3,
    }

    CRISIS_KEYWORDS = [
        "suicide",
        "kill myself",
        "end my life",
        "want to die",
        "self harm",
        "self-harm",
        "hurt myself",
        "cut myself",
        "overdose",
    ]

    WITHDRAW_KEYWORDS = ["stop", "exit", "quit", "end session", "can we stop", "i want to stop"]

    def __init__(self):
        self.reset()

    def reset(self):
        self.current_question: int = 0
        self.screening_step: int = 0
        self.screening_passed: bool = False
        self.consent_given: bool = False
        self.responses: Dict[int, Optional[int]] = {}
        self.awaiting_frequency: bool = False
        self.revisiting_skipped: bool = False
        self.skipped_queue: List[int] = []
        self.confusion_count: int = 0
        self.total_score: int = 0
        self.completed: bool = False
        self.terminal_reason: Optional[str] = None
        self.terminal_message: Optional[str] = None
        self.assessment_saved: bool = False

    def get_state(self) -> Dict:
        return {
            "current_question": self.current_question,
            "screening_step": self.screening_step,
            "screening_passed": self.screening_passed,
            "consent_given": self.consent_given,
            "responses": self.responses,
            "awaiting_frequency": self.awaiting_frequency,
            "revisiting_skipped": self.revisiting_skipped,
            "skipped_queue": self.skipped_queue,
            "confusion_count": self.confusion_count,
            "total_score": self.total_score,
            "completed": self.completed,
            "terminal_reason": self.terminal_reason,
            "terminal_message": self.terminal_message,
            "assessment_saved": self.assessment_saved,
        }

    def load_state(self, state: Dict):
        self.current_question = state.get("current_question", 0)
        self.screening_step = state.get("screening_step", 0)
        self.screening_passed = state.get("screening_passed", False)
        self.consent_given = state.get("consent_given", False)
        self.responses = state.get("responses", {})
        self.awaiting_frequency = state.get("awaiting_frequency", False)
        self.revisiting_skipped = state.get("revisiting_skipped", False)
        self.skipped_queue = state.get("skipped_queue", [])
        self.confusion_count = state.get("confusion_count", 0)
        self.total_score = state.get("total_score", 0)
        self.completed = state.get("completed", False)
        self.terminal_reason = state.get("terminal_reason")
        self.terminal_message = state.get("terminal_message")
        self.assessment_saved = state.get("assessment_saved", False)

    def _normalize(self, text: str) -> str:
        return (text or "").strip().lower()

    def _contains_any(self, text: str, items: List[str]) -> bool:
        return any(item in text for item in items)

    def check_crisis(self, text: str) -> bool:
        return self._contains_any(self._normalize(text), self.CRISIS_KEYWORDS)

    def is_withdraw_request(self, text: str) -> bool:
        return self._contains_any(self._normalize(text), self.WITHDRAW_KEYWORDS)

    def is_skip_request(self, text: str) -> bool:
        return "skip" in self._normalize(text)

    def is_back_request(self, text: str) -> bool:
        value = self._normalize(text)
        return "go back" in value or "back to last question" in value or value == "back"

    def is_confused(self, text: str) -> bool:
        value = self._normalize(text)
        return (
            "don't understand" in value
            or "dont understand" in value
            or "confused" in value
            or "not clear" in value
            or "i still don't get it" in value
            or "i still dont get it" in value
            or "is that about" in value
            or "what do you mean" in value
            or "day or night" in value
        )

    def is_example_request(self, text: str) -> bool:
        return "example" in self._normalize(text)

    def is_assessment_request(self, text: str) -> bool:
        value = self._normalize(text)
        checks = ["how do i know", "am i depressed", "can you tell me if", "can you diagnose"]
        return self._contains_any(value, checks)

    def is_justification(self, text: str) -> bool:
        value = self._normalize(text)
        return "because" in value or "the reason" in value

    def is_meta_question(self, text: str) -> bool:
        value = self._normalize(text)
        return (
            "how many questions" in value
            or "what is phq-9" in value
            or "what is phq9" in value
            or "why are you asking" in value
        )

    def get_meta_reply(self, text: str) -> str:
        value = self._normalize(text)
        if "how many questions" in value:
            if self.current_question <= 0:
                return "There are 9 questions in total. We will start after screening and consent."
            remaining = max(0, 9 - self.current_question + 1)
            if self.awaiting_frequency:
                return f"There are 9 questions total. We are currently scoring question {self.current_question}, with {remaining} question(s) including this one left."
            return f"There are 9 questions total. We are on question {self.current_question}, with {remaining} left."
        if "why are you asking" in value:
            return "This is a standard PHQ-9 screening question used to understand depression symptoms."
        return "PHQ-9 is a standard depression screening tool with 9 questions."

    def get_age_screening(self) -> str:
        return "Before we begin, please confirm: Are you 18 or older? (Yes/No)"

    def get_crisis_screening(self) -> str:
        return "Are you currently in a crisis or feeling actively suicidal? (Yes/No)"

    def get_consent_message(self) -> str:
        return (
            "My purpose is to have a conversation with you. I am not a doctor, and this is not a diagnosis. "
            "This is only a screening. Your data will be used anonymously for this research.\n"
            "Do you consent to participate? (Yes/No)"
        )

    def get_current_question(self) -> Optional[str]:
        if 1 <= self.current_question <= 9:
            return self.QUESTIONS[self.current_question - 1]["text"]
        return None

    def get_frequency_question(self) -> str:
        return (
            "Okay, how often have you been bothered by that over the last 2 weeks?\n"
            "1. Not at all\n"
            "2. Several days\n"
            "3. More than half the days\n"
            "4. Nearly every day\n\n"
            "Please choose 1, 2, 3, or 4."
        )

    def get_guardrail_response(self) -> str:
        q = self.get_frequency_question() if self.awaiting_frequency else (self.get_current_question() or "Shall we continue?")
        return "I'm sorry, I am only designed to discuss the PHQ-9 symptoms. Shall we return to our session?\n\n" + q

    def get_crisis_message(self) -> str:
        return (
            "I have detected that you may be in serious distress.\n"
            "I am an AI and not a crisis counselor.\n"
            "Please contact support immediately:\n"
            "- 1926 (National Mental Health Helpline, 24/7)\n"
            "- Ms Supeshala Rathnayaka (070 2211311)"
        )

    def get_withdraw_message(self) -> str:
        return "Of course. We can stop here. Thank you for your time."

    def calculate_severity(self) -> str:
        if self.total_score <= 9:
            return "minimal_to_mild"
        if self.total_score <= 19:
            return "moderate_to_moderately_severe"
        return "severe"

    def get_completion_message(self) -> str:
        severity = self.calculate_severity()
        header = (
            "Thank you for completing the PHQ-9 screening.\n\n"
            f"Your total score is: {self.total_score} out of 27\n"
            f"Severity level: {severity.upper()}\n\n"
        )
        if severity == "minimal_to_mild":
            return header + "Your responses suggest minimal to mild depressive symptoms. This is only a screening result, not a diagnosis."
        if severity == "moderate_to_moderately_severe":
            return header + "Your responses suggest moderate to moderately severe depressive symptoms. Please consult a qualified professional for a full assessment."
        return (
            header
            + "Your responses suggest severe depressive symptoms. It is very important to speak to a qualified professional soon.\n\n"
            "Support resources:\n"
            "- 1926 (National Mental Health Helpline, 24/7)\n"
            "- Ms Supeshala Rathnayaka (070 2211311)"
        )

    @staticmethod
    def _parse_yes_no(text: str) -> Optional[bool]:
        value = (text or "").strip().lower()
        yes_words = {"yes", "y", "yeah", "yep", "sure", "ok", "okay", "yup", "definitely"}
        no_words = {"no", "n", "nope", "not really", "nah"}
        if value in yes_words:
            return True
        if value in no_words:
            return False
        if value.startswith("yes") or value.startswith("yeah") or value.startswith("yep"):
            return True
        if value.startswith("no") and not value.startswith("not"):
            return False
        return None

    @classmethod
    def _parse_frequency(cls, text: str) -> Optional[int]:
        value = (text or "").strip().lower()
        if value in {"1", "2", "3", "4"}:
            return int(value) - 1
        return cls.FREQUENCY_OPTIONS.get(value)

    def _record_no_and_advance(self) -> Dict:
        self.responses[self.current_question] = 0
        self.awaiting_frequency = False
        self.confusion_count = 0
        return self._advance_to_next()

    def _record_frequency_and_advance(self, score: int) -> Dict:
        previous = self.responses.get(self.current_question)
        if isinstance(previous, int):
            self.total_score -= previous
        self.responses[self.current_question] = score
        self.total_score += score
        self.awaiting_frequency = False
        self.confusion_count = 0
        return self._advance_to_next()

    def _advance_after_skip(self) -> Dict:
        if self.revisiting_skipped:
            return {
                "reply": (
                    "This item still needs an answer before scoring can continue.\n"
                    "Please answer Yes or No.\n\n"
                    f"{self.get_current_question()}"
                ),
                "completed": False,
            }

        skipped_q = self.current_question
        self.responses[self.current_question] = None
        if not self.revisiting_skipped and skipped_q not in self.skipped_queue:
            self.skipped_queue.append(skipped_q)
        self.awaiting_frequency = False
        self.confusion_count = 0
        result = self._advance_to_next()
        if not result.get("completed"):
            result["reply"] = f"No problem, we can skip that one.\n\n{self.get_current_question()}"
        return result

    def _advance_to_next(self) -> Dict:
        if self.revisiting_skipped:
            if self.skipped_queue:
                self.current_question = self.skipped_queue.pop(0)
                return {
                    "reply": (
                        "Earlier you skipped this item. You can answer now or type 'skip' again.\n\n"
                        f"{self.get_current_question()}"
                    ),
                    "completed": False,
                }
            remaining_unanswered = [
                q["number"]
                for q in self.QUESTIONS
                if self.responses.get(q["number"], "__missing__") is None
            ]
            if remaining_unanswered:
                self.current_question = remaining_unanswered[0]
                return {
                    "reply": (
                        "Before scoring, all questions must be answered.\n"
                        "Please answer this item with Yes or No.\n\n"
                        f"{self.get_current_question()}"
                    ),
                    "completed": False,
                }

            self.completed = True
            self.terminal_reason = "completed"
            self.terminal_message = self.get_completion_message()
            return {
                "reply": self.terminal_message,
                "completed": True,
                "severity": self.calculate_severity(),
                "score": self.total_score,
            }

        self.current_question += 1
        if self.current_question <= 9:
            return {"reply": self.get_current_question(), "completed": False}

        unanswered = [
            q["number"]
            for q in self.QUESTIONS
            if self.responses.get(q["number"], "__missing__") is None
        ]
        if unanswered:
            self.revisiting_skipped = True
            self.skipped_queue = unanswered
            self.current_question = self.skipped_queue.pop(0)
            return {
                "reply": (
                    "Before we finish, let's revisit skipped items. "
                    "You can still type 'skip' if you prefer.\n\n"
                    f"{self.get_current_question()}"
                ),
                "completed": False,
            }

        self.completed = True
        self.terminal_reason = "completed"
        self.terminal_message = self.get_completion_message()
        return {
            "reply": self.terminal_message,
            "completed": True,
            "severity": self.calculate_severity(),
            "score": self.total_score,
        }

    def process_user_input(self, text: str) -> Dict:
        value = self._normalize(text)

        if self.completed:
            if value == "restart":
                self.reset()
                return {"reply": self.get_age_screening(), "completed": False}
            if self.terminal_reason in {"crisis", "withdrawn", "excluded"}:
                return {
                    "reply": self.terminal_message or self.get_crisis_message(),
                    "completed": True,
                    "crisis": self.terminal_reason == "crisis",
                    "withdrawn": self.terminal_reason in {"withdrawn", "excluded"},
                    "delete_partial": self.terminal_reason in {"withdrawn", "excluded"},
                    "no_result": True,
                    "terminal_reason": self.terminal_reason,
                }
            return {"reply": f"{self.get_completion_message()}\n\nType 'restart' to begin again.", "completed": True}

        if self.is_withdraw_request(text):
            self.completed = True
            self.terminal_reason = "withdrawn"
            self.terminal_message = self.get_withdraw_message()
            return {
                "reply": self.terminal_message,
                "completed": True,
                "withdrawn": True,
                "delete_partial": True,
                "no_result": True,
                "terminal_reason": "withdrawn",
            }

        if self.check_crisis(text):
            self.completed = True
            self.terminal_reason = "crisis"
            self.terminal_message = self.get_crisis_message()
            return {
                "reply": self.terminal_message,
                "completed": True,
                "crisis": True,
                "no_result": True,
                "terminal_reason": "crisis",
            }

        if self.is_meta_question(text):
            meta = self.get_meta_reply(text)
            if not self.screening_passed:
                stage_prompt = (
                    self.get_age_screening()
                    if self.screening_step == 0
                    else self.get_crisis_screening()
                    if self.screening_step == 1
                    else self.get_consent_message()
                )
                return {"reply": f"{meta}\n\n{stage_prompt}"}
            reprompt = self.get_frequency_question() if self.awaiting_frequency else (self.get_current_question() or "")
            return {"reply": f"{meta}\n\n{reprompt}"}

        if not self.screening_passed:
            if self.is_skip_request(text) or self.is_back_request(text):
                return {"reply": "During screening, please answer the current question with Yes or No."}

            if self.screening_step == 0:
                age_ok = self._parse_yes_no(text)
                if age_ok is None:
                    return {"reply": f"{self.get_age_screening()}\nPlease answer Yes or No."}
                if not age_ok:
                    self.completed = True
                    self.terminal_reason = "excluded"
                    self.terminal_message = "This study is only for adults (18+). We will stop here. Thank you."
                    return {
                        "reply": self.terminal_message,
                        "completed": True,
                        "withdrawn": True,
                        "delete_partial": True,
                        "no_result": True,
                        "terminal_reason": "excluded",
                    }
                self.screening_step = 1
                return {"reply": self.get_crisis_screening()}

            if self.screening_step == 1:
                in_crisis = self._parse_yes_no(text)
                if in_crisis is None:
                    return {"reply": f"{self.get_crisis_screening()}\nPlease answer Yes or No."}
                if in_crisis:
                    self.completed = True
                    self.terminal_reason = "crisis"
                    self.terminal_message = self.get_crisis_message()
                    return {
                        "reply": self.terminal_message,
                        "completed": True,
                        "crisis": True,
                        "no_result": True,
                        "terminal_reason": "crisis",
                    }
                self.screening_step = 2
                return {"reply": self.get_consent_message()}

            consent = self._parse_yes_no(text)
            if consent is None:
                return {"reply": f"{self.get_consent_message()}\nPlease answer Yes or No."}
            if not consent:
                self.completed = True
                self.terminal_reason = "withdrawn"
                self.terminal_message = "No problem. We can stop here. Thank you for your time."
                return {
                    "reply": self.terminal_message,
                    "completed": True,
                    "withdrawn": True,
                    "delete_partial": True,
                    "no_result": True,
                    "terminal_reason": "withdrawn",
                }
            self.consent_given = True
            self.screening_passed = True
            self.current_question = 1
            self.confusion_count = 0
            return {"reply": self.get_current_question()}

        if self.is_back_request(text):
            if self.awaiting_frequency:
                self.awaiting_frequency = False
                self.confusion_count = 0
                return {"reply": f"Sure, let's go back.\n\n{self.get_current_question()}"}
            if self.current_question > 1:
                prev = self.current_question - 1
                prev_score = self.responses.get(prev)
                if isinstance(prev_score, int):
                    self.total_score -= prev_score
                self.responses.pop(prev, None)
                self.current_question = prev
                self.awaiting_frequency = False
                self.confusion_count = 0
                return {"reply": f"Sure, let's go back.\n\n{self.get_current_question()}"}
            return {"reply": f"We are already at the first question.\n\n{self.get_current_question()}"}

        if self.is_skip_request(text):
            return self._advance_after_skip()

        if self.awaiting_frequency:
            score = self._parse_frequency(text)
            if score is None:
                return {"reply": f"{self.get_frequency_question()}\nInvalid input. Please choose 1, 2, 3, or 4."}
            return self._record_frequency_and_advance(score)

        q = self.QUESTIONS[self.current_question - 1]

        if self.is_confused(text):
            if self.current_question == 3 and ("day" in value or "night" in value):
                return {
                    "reply": (
                        "Good question. This sleep item covers both night-time sleep problems "
                        "(such as difficulty sleeping) and sleeping too much at any time.\n\n"
                        "Over the last 2 weeks, have you been bothered by this? (Yes/No)"
                    )
                }
            self.confusion_count += 1
            if self.confusion_count >= 2:
                result = self._advance_after_skip()
                if result.get("completed"):
                    return result
                return {
                    "reply": (
                        "No problem at all, this can be confusing. Let's skip this one and move to the next question.\n\n"
                        f"{self.get_current_question()}"
                    ),
                    "completed": False,
                }
            return {"reply": q["clarification"]}

        if self.is_example_request(text):
            return {"reply": q["examples"]}

        if self.is_assessment_request(text):
            return {
                "reply": (
                    "That's an important question I cannot answer. I am an AI, not a doctor, and I can't diagnose.\n"
                    "In your own opinion, have you been bothered by this feeling over the last 2 weeks? (Yes/No)"
                )
            }

        if self.is_justification(text):
            self.awaiting_frequency = True
            self.confusion_count = 0
            return {
                "reply": (
                    "Thank you for clarifying the reason. For this questionnaire, it doesn't matter why, only if you felt that way.\n\n"
                    + self.get_frequency_question()
                )
            }

        yn = self._parse_yes_no(text)
        if yn is True:
            self.awaiting_frequency = True
            self.confusion_count = 0
            return {"reply": self.get_frequency_question()}
        if yn is False:
            return self._record_no_and_advance()

        if re.search(r"\d", value):
            return {
                "reply": (
                    "Please answer this symptom question with Yes or No first.\n\n"
                    f"{self.get_current_question()}\n\n"
                    "If you answer Yes, I will then show the 4 fixed frequency options."
                )
            }

        return {"reply": self.get_guardrail_response()}
