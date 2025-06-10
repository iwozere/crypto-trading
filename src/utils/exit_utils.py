"""
Exit Utilities Module
-------------------

This module provides utility functions for working with exit logic classes.
"""

from src.exit.exit_registry import EXIT_LOGIC_REGISTRY

def get_exit_class(exit_logic_name: str):
    """
    Get the exit logic class for a given name.
    
    Args:
        exit_logic_name: Name of the exit logic to get
        
    Returns:
        The exit logic class
        
    Raises:
        ValueError: If the exit logic name is not found
    """
    if exit_logic_name not in EXIT_LOGIC_REGISTRY:
        raise ValueError(f"Exit logic '{exit_logic_name}' not found in registry")
    return EXIT_LOGIC_REGISTRY[exit_logic_name] 