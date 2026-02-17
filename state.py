# state.py
from typing import List, TypedDict, Optional

class Episode(TypedDict):
    """Represents a single episode's data."""
    episode_number: int
    title: str
    script: str
    summary: str

class GraphState(TypedDict):
    """
    Represents the entire state of our TV series generation graph.
    """
    # --- World Bible ---
    logline: str
    characters: str
    key_locations: str
    world_rules: str
    
    # --- Series Parameters ---
    season_number: int
    genre: str
    rating: str
    num_episodes: int
    
    # --- Dynamic State ---
    episodes: List[Episode]
    summary_memory: str
    current_draft: Optional[str]
    continuity_errors: Optional[list]
    final_series_title: Optional[str]
    user_command: Optional[str]

class WriterState(TypedDict):
    """
    Represents the state of the writer's room sub-graph.
    This is a temporary state used only during the writing of a single episode.
    """
    main_state: GraphState
    episode_outline: List[str]
    written_scenes: List[str]
    current_scene_index: int