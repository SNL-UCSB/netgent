class NetGentError(Exception):
    def __init__(self, name: str, message: str):
        self.name = name
        self.message = message
        super().__init__(f"{name}: {message}")
    
    def __repr__(self):
        return f"NetGentError(name='{self.name}', message='{self.message}')"

class NetGentExecutionError(Exception):
    """Base exception for NetGent execution errors"""
    def __init__(self, name: str, message: str):
        self.name = name
        self.message = message
        super().__init__(message)
