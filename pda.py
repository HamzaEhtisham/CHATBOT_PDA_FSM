class PDA:
    """
    Pushdown Automaton (PDA) for chatbot conversation memory.
    Keeps track of conversation states, previous queries, and user info.
    """

    def __init__(self):
        self.stack = []        # Stores conversation states
        self.history = []      # Stores past queries and intents
        self.user_name = None  # Stores the user's name
        self.user_dept = None  # Stores the user's department

    def push(self, item):
        """Push a new state or topic onto the stack."""
        self.stack.append(item)

    def pop(self):
        """Pop the top state/topic from the stack."""
        return self.stack.pop() if self.stack else None

    def top(self):
        """Peek the current state/topic."""
        return self.stack[-1] if self.stack else None

    def add_history(self, query, intent):
        """Save past query and its intent."""
        self.history.append({"query": query, "intent": intent})

    def get_history(self, limit=5):
        """Get last N queries for context retrieval."""
        return self.history[-limit:] if self.history else []

    def clear(self):
        """Clear stack, history, and user info."""
        self.stack = []
        self.history = []
        self.user_name = None
        self.user_dept = None
