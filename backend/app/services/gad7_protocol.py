from typing import Dict, List, Optional


class GAD7Protocol:
    """Research protocol for conversational GAD-7 administration.

    Flow per question:
        1. Ask symptom question (yes/no).
        2a. "No"  → record score 0, advance to next question.
        2b. "Yes" → set awaiting_frequency=True, ask frequency.
        3. Parse frequency (1-4 / text) → record score 0-3, advance.
    """

    QUESTIONS = [
        {
            "number": 1,
            "text": "To begin, over the last 2 weeks, have you been bothered by feeling nervous, anxious, or on edge?",
            "clarification": (
                "No problem. 'Nervous or on edge' means feeling restless, jumpy, or easily startled. "
                "Over the last 2 weeks, have you been bothered by that feeling?"
            ),
            "examples": (
                "Good question. Examples might include feeling like you might spill your drink if someone surprises "
                "you, finding it hard to sit still, or feeling a pit in your stomach. Over the last 2 weeks, have "
                "you been bothered by feelings like that?"
            ),
        },
        {
            "number": 2,
            "text": "Also, over the last 2 weeks, have you been bothered by not being able to stop or control worrying?",
            "clarification": "This means worried thoughts keep going even when you try to stop. Have you experienced that?",
            "examples": "Examples: lying awake thinking about problems, or your mind racing with worries.",
        },
        {
            "number": 3,
            "text": "Have you been bothered by worrying too much about different things?",
            "clarification": "This means worrying about multiple topics or situations. Have you experienced that?",
            "examples": "Examples: worrying about work, family, health, and money at the same time.",
        },
        {
            "number": 4,
            "text": "Have you had trouble relaxing?",
            "clarification": "This means finding it difficult to feel calm or at ease. Have you experienced that?",
            "examples": "Examples: feeling tense when trying to rest, or unable to unwind.",
        },
        {
            "number": 5,
            "text": "Have you been bothered by being so restless that it is hard to sit still?",
            "clarification": "This means feeling the need to move around or fidget. Have you experienced that?",
            "examples": "Examples: pacing, tapping your feet, or discomfort staying in one place.",
        },
        {
            "number": 6,
            "text": "Have you been bothered by becoming easily annoyed or irritable?",
            "clarification": "This means getting frustrated more easily than usual. Have you experienced that?",
            "examples": "Examples: snapping at people, impatience, or being bothered by small things.",
        },
        {
            "number": 7,
            "text": "And finally, have you been bothered by feeling afraid as if something awful might happen?",
            "clarification": "This means a sense of dread or fear about the future. Have you experienced that?",
            "examples": "Examples: feeling like something bad is coming or disaster may happen.",
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

    WITHDRAW_KEYWORDS = [
        "stop",
        "exit",
        "quit",
        "end session",
        "can we stop",
        "i want to stop",
    ]

    def __init__(self):
        self.reset()

    def reset(self):
        self.current_question: int = 0       # 0 = screening stage
        self.consent_given: bool = False
        self.screening_passed: bool = False
        self.screening_step: int = 0          # 0=age, 1=crisis, 2=consent
        self.responses: Dict[int, Optional[int]] = {}
        self.awaiting_frequency: bool = False  # True only after "yes" to symptom
        self.confusion_count: int = 0
        self.total_score: int = 0
        self.completed: bool = False

    # ------------------------------------------------------------------
    # State serialisation
    # ------------------------------------------------------------------

    def get_state(self) -> Dict:
        return {
            "current_question": self.current_question,
            "consent_given": self.consent_given,
            "screening_passed": self.screening_passed,
            "screening_step": self.screening_step,
            "responses": self.responses,
            "awaiting_frequency": self.awaiting_frequency,
            "confusion_count": self.confusion_count,
            "total_score": self.total_score,
            "completed": self.completed,
        }

    def load_state(self, state: Dict):
        self.current_question = state.get("current_question", 0)
        self.consent_given = state.get("consent_given", False)
        self.screening_passed = state.get("screening_passed", False)
        self.screening_step = state.get("screening_step", 0)
        self.responses = state.get("responses", {})
        self.awaiting_frequency = state.get("awaiting_frequency", False)
        self.confusion_count = state.get("confusion_count", 0)
        self.total_score = state.get("total_score", 0)
        self.completed = state.get("completed", False)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _normalize(self, text: str) -> str:
        return (text or "").strip().lower()

    def _contains_any(self, text: str, items: List[str]) -> bool:
        return any(item in text for item in items)

    # ------------------------------------------------------------------
    # Intent detection
    # ------------------------------------------------------------------

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
        )

    def is_example_request(self, text: str) -> bool:
        return "example" in self._normalize(text)

    def is_assessment_request(self, text: str) -> bool:
        value = self._normalize(text)
        checks = [
            "how do i know",
            "can you tell me if i",
            "am i nervous",
            "am i anxious",
            "can you tell if",
        ]
        return self._contains_any(value, checks)

    def is_justification(self, text: str) -> bool:
        value = self._normalize(text)
        return "because" in value or "the reason" in value

    def is_meta_question(self, text: str) -> bool:
        value = self._normalize(text)
        return (
            "how many questions" in value
            or "why are you asking" in value
            or "what is gad-7" in value
            or "what is gad7" in value
        )

    # ------------------------------------------------------------------
    # Meta replies
    # ------------------------------------------------------------------

    def get_meta_reply(self, text: str) -> str:
        value = self._normalize(text)
        if "how many questions" in value:
            if self.current_question <= 0:
                return "There are 7 questions in total. We will start after screening and consent."
            remaining = max(0, 7 - self.current_question + 1)
            if self.awaiting_frequency:
                return (
                    f"There are 7 questions total. We are currently scoring question "
                    f"{self.current_question}, with {remaining} question(s) including this one left."
                )
            return (
                f"There are 7 questions total. We are on question {self.current_question}, "
                f"with {remaining} left."
            )
        if "why are you asking" in value:
            return "This is a standard GAD-7 screening question used to understand anxiety symptoms."
        return "GAD-7 is a standard anxiety screening tool with 7 questions."

    # ------------------------------------------------------------------
    # Protocol scripts
    # ------------------------------------------------------------------

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
        if 1 <= self.current_question <= 7:
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
        if self.awaiting_frequency:
            q = self.get_frequency_question()
        else:
            q = self.get_current_question() or "Shall we continue?"
        return (
            "I'm sorry, I am only designed to discuss the GAD-7 symptoms. "
            f"Shall we return to our session?\n\n{q}"
        )

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
        if self.total_score <= 4:
            return "minimal"
        if self.total_score <= 9:
            return "mild"
        if self.total_score <= 14:
            return "moderate"
        return "severe"

    def get_completion_message(self) -> str:
        severity = self.calculate_severity()
        header = (
            "Thank you for completing the GAD-7 screening.\n\n"
            f"Your total score is: {self.total_score} out of 21\n"
            f"Severity level: {severity.upper()}\n\n"
        )
        if severity == "minimal":
            return header + "Your responses suggest minimal anxiety symptoms. This is only a screening result, not a diagnosis."
        if severity == "mild":
            return header + "Your responses suggest mild anxiety symptoms. Please consult a qualified professional for a full assessment."
        if severity == "moderate":
            return (
                header
                + "Your responses suggest moderate anxiety symptoms. Talking to a qualified professional "
                "(doctor or counselor) could be very important."
            )
        return (
            header
            + "Your responses suggest severe anxiety symptoms. It is very important to speak to a "
            "qualified professional soon.\n\n"
            "Support resources:\n"
            "- 1926 (National Mental Health Helpline, 24/7)\n"
            "- Ms Supeshala Rathnayaka (070 2211311)"
        )

    # ------------------------------------------------------------------
    # Parsers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_yes_no(text: str) -> Optional[bool]:
        value = (text or "").strip().lower()
        yes_words = {"yes", "y", "yeah", "yep", "sure", "ok", "okay", "yup", "definitely"}
        no_words = {"no", "n", "nope", "not really", "nah"}
        if value in yes_words:
            return True
        if value in no_words:
            return False
        # Partial match for natural phrasing: "yes i have" / "no i haven't"
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

    # ------------------------------------------------------------------
    # Internal transition helpers
    # ------------------------------------------------------------------

    def _record_no_and_advance(self) -> Dict:
        """User said No to a symptom question: score=0, move forward."""
        self.responses[self.current_question] = 0
        self.awaiting_frequency = False
        self.confusion_count = 0
        self.current_question += 1
        return self._check_completion()

    def _record_frequency_and_advance(self, score: int) -> Dict:
        """User provided frequency after saying Yes: record score, move forward."""
        self.responses[self.current_question] = score
        self.total_score += score
        self.awaiting_frequency = False
        self.confusion_count = 0
        self.current_question += 1
        return self._check_completion()

    def _advance_after_skip(self) -> Dict:
        """Skip current question: record null, move forward."""
        self.responses[self.current_question] = None
        self.awaiting_frequency = False
        self.confusion_count = 0
        self.current_question += 1
        result = self._check_completion()
        if not result.get("completed"):
            result["reply"] = f"No problem, we can skip that one.\n\n{self.get_current_question()}"
        return result

    def _check_completion(self) -> Dict:
        """Return completion dict if all 7 questions done, else next question."""
        if self.current_question > 7:
            self.completed = True
            return {
                "reply": self.get_completion_message(),
                "completed": True,
                "severity": self.calculate_severity(),
                "score": self.total_score,
            }
        return {"reply": self.get_current_question(), "completed": False}

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def process_user_input(self, text: str) -> Dict:
        value = self._normalize(text)

        # ── Already finished ──────────────────────────────────────────
        if self.completed:
            if value == "restart":
                self.reset()
                return {"reply": self.get_age_screening(), "completed": False}
            return {
                "reply": f"{self.get_completion_message()}\n\nType 'restart' to begin again.",
                "completed": True,
            }

        # ── Universal: withdraw ───────────────────────────────────────
        if self.is_withdraw_request(text):
            self.completed = True
            return {
                "reply": self.get_withdraw_message(),
                "completed": True,
                "withdrawn": True,
                "delete_partial": True,
            }

        # ── Universal: crisis ─────────────────────────────────────────
        if self.check_crisis(text):
            self.completed = True
            return {"reply": self.get_crisis_message(), "completed": True, "crisis": True}

        # ── Universal: meta questions ─────────────────────────────────
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

        # ── SCREENING STAGE ───────────────────────────────────────────
        if not self.screening_passed:
            if self.is_skip_request(text) or self.is_back_request(text):
                return {"reply": "During screening, please answer the current question with Yes or No."}

            # Step 0: age check
            if self.screening_step == 0:
                age_ok = self._parse_yes_no(text)
                if age_ok is None:
                    return {"reply": f"{self.get_age_screening()}\nPlease answer Yes or No."}
                if not age_ok:
                    self.completed = True
                    return {
                        "reply": "This study is only for adults (18+). We will stop here. Thank you.",
                        "completed": True,
                        "withdrawn": True,
                        "delete_partial": True,
                    }
                self.screening_step = 1
                return {"reply": self.get_crisis_screening()}

            # Step 1: crisis check
            if self.screening_step == 1:
                in_crisis = self._parse_yes_no(text)
                if in_crisis is None:
                    return {"reply": f"{self.get_crisis_screening()}\nPlease answer Yes or No."}
                if in_crisis:
                    self.completed = True
                    return {"reply": self.get_crisis_message(), "completed": True, "crisis": True}
                self.screening_step = 2
                return {"reply": self.get_consent_message()}

            # Step 2: consent
            consent = self._parse_yes_no(text)
            if consent is None:
                return {"reply": f"{self.get_consent_message()}\nPlease answer Yes or No."}
            if not consent:
                self.completed = True
                return {
                    "reply": "No problem. We can stop here. Thank you for your time.",
                    "completed": True,
                    "withdrawn": True,
                    "delete_partial": True,
                }
            self.consent_given = True
            self.screening_passed = True
            self.current_question = 1
            self.confusion_count = 0
            return {"reply": self.get_current_question()}

        # ── QUESTION STAGE ────────────────────────────────────────────

        # Navigation: back
        if self.is_back_request(text):
            if self.awaiting_frequency:
                # Back from frequency step → re-ask the symptom question
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

        # Navigation: skip
        if self.is_skip_request(text):
            return self._advance_after_skip()

        # ── FREQUENCY STAGE (awaiting_frequency == True) ──────────────
        if self.awaiting_frequency:
            score = self._parse_frequency(text)
            if score is None:
                return {
                    "reply": (
                        f"{self.get_frequency_question()}\n"
                        "Invalid input. Please choose 1, 2, 3, or 4."
                    )
                }
            return self._record_frequency_and_advance(score)

        # ── SYMPTOM QUESTION STAGE (awaiting_frequency == False) ──────
        q = self.QUESTIONS[self.current_question - 1]

        # Confusion handling
        if self.is_confused(text):
            self.confusion_count += 1
            if self.confusion_count >= 2:
                # Skip after 2 confused responses
                result = self._advance_after_skip()
                if result.get("completed"):
                    return result
                return {
                    "reply": (
                        "No problem at all, this can be confusing. Let's skip this one and move "
                        f"to the next question.\n\n{self.get_current_question()}"
                    ),
                    "completed": False,
                }
            return {"reply": q["clarification"]}

        # Example request
        if self.is_example_request(text):
            return {"reply": q["examples"]}

        # Assessment deflection
        if self.is_assessment_request(text):
            return {
                "reply": (
                    "That's an important question I cannot answer. I am an AI, not a doctor, and I can't diagnose.\n"
                    "In your own opinion, have you been bothered by this feeling over the last 2 weeks? (Yes/No)"
                )
            }

        # Justification: user explains why — accept as implicit "yes", ask frequency
        if self.is_justification(text):
            self.awaiting_frequency = True
            self.confusion_count = 0
            return {
                "reply": (
                    "Thank you for clarifying the reason. For this questionnaire, it doesn't matter why, "
                    "only if you felt that way.\n\n" + self.get_frequency_question()
                )
            }

        # Standard Yes/No response
        yn = self._parse_yes_no(text)
        if yn is True:
            # User experienced this symptom → ask frequency
            self.awaiting_frequency = True
            self.confusion_count = 0
            return {"reply": self.get_frequency_question()}
        if yn is False:
            # User did NOT experience this symptom → score 0, advance
            return self._record_no_and_advance()

        # Try direct frequency input even before yes/no (e.g. user types "2" at symptom stage)
        direct_score = self._parse_frequency(text)
        if direct_score is not None:
            # Treat as "yes + frequency in one go"
            return self._record_frequency_and_advance(direct_score)

        # Fallback guardrail
        return {"reply": self.get_guardrail_response()}