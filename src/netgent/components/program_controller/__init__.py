"""
Program Controller

The Program Controller determines which states' trigger conditions are satisfied
and routes workflow execution accordingly.

This component:
- Evaluates state trigger conditions
- Determines which states should execute
- Enforces single vs. multiple state execution policies
- Routes workflow to appropriate next step

Classes:
    ProgramController: Main controller class for state checking

Usage:
    from netgent.components.program_controller import ProgramController
    
    controller = ProgramController(browser_controller, config)
    matching_states = controller.check(state_repository)
    
Configuration:
    config = {
        "allow_multiple_states": False,  # Allow multiple states to match
    }
"""

from .controller import ProgramController

__all__ = ["ProgramController"]

