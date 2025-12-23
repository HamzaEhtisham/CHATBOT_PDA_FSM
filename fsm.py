class FSM:
    """
    Finite State Machine (FSM) for chatbot.
    Tracks current conversation state and adapts based on user input.
    """

    def __init__(self):
        self.state = "START"

    def transition(self, text):
        """
        Decide next state based on user input.
        """
        text = text.lower()
        words = text.split()  # Split into words for exact matching

        # Check for greeting with word boundaries
        if any(word in words for word in ["hello", "hi", "hey", "hii", "helo"]):
            self.state = "GREETING"
        elif "course" in text or "semester" in text or "class" in text or "subject" in text or "unit" in text:
            self.state = "COURSE_QUERY"
        elif "events" in text or "happening" in text or "upcoming" in text or "event" in text or "activities" in text or "activity" in text:
            self.state = "EVENT_QUERY"
        elif "faculty" in text or "professor" in text or "teacher" in text:
            self.state = "FACULTY_QUERY"
        elif "gpa" in text or "calculate gpa" in text:
            self.state = "GPA_QUERY"
        elif any(word in words for word in ["bye", "goodbye"]) or "see you" in text:
            self.state = "GOODBYE"
        else:
            self.state = "GENERAL_QUERY"  # fallback

        return self.state