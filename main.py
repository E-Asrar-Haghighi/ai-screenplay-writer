# main.py
import json
import os
from langgraph.graph import StateGraph, END
from state import GraphState, WriterState
from agents import (
    state_preparer_agent,
    first_episode_checker_agent,
    continuity_checker_agent,
    editor_agent,
    series_title_agent,
    scene_plotter_agent,
    scene_writer_agent,
)

# --- CONFIG & SETUP ---
config = {"recursion_limit": 50}

# --- NODE FUNCTIONS ---
def after_edit_logic_node(state: GraphState) -> dict:
    """Node function that processes after edit logic."""
    return state

def final_check_node(state: GraphState) -> dict:
    """Node function that performs final checks."""
    return state

# --- WRITER SUB-GRAPH DEFINITION ---
def call_writer_subgraph(state: GraphState) -> dict:
    """A wrapper that defines, compiles, and invokes the writer sub-graph."""
    print("\n---ENTERING WRITER'S ROOM SUB-GRAPH---")
    current_episode_num = len(state.get('episodes', [])) + 1
    print(f"---WRITING EPISODE {current_episode_num}---")
    
    # --- 1. DEFINE THE SUB-GRAPH ---
    writer_workflow = StateGraph(WriterState)
    
    # Define the nodes
    writer_workflow.add_node("plotter", scene_plotter_agent)
    writer_workflow.add_node("scene_writer", scene_writer_agent)

    # Define the routing functions for the sub-graph
    def validate_outline(state: WriterState) -> str:
        """Checks if the generated outline is usable."""
        print("---SUB-AGENT: VALIDATING OUTLINE---")
        outline = state.get('episode_outline', [])
        
        # Check if we have enough scenes and they're not just headers
        if not outline or len(outline) < 2:
            print("---VALIDATION FAILED: Outline is too short or empty. Retrying plotter.---")
            return "plotter"  # Route back to the plotter
        
        # Check if scenes have meaningful content (not just headers)
        meaningful_scenes = 0
        for scene in outline:
            # Count words and check for meaningful content
            words = scene.split()
            if len(words) > 4 and not any(header in scene.lower() for header in ['setup', 'development', 'climax', 'cliffhanger']):
                meaningful_scenes += 1
        
        if meaningful_scenes < 2:
            print(f"---VALIDATION FAILED: Only {meaningful_scenes} meaningful scenes found. Retrying plotter.---")
            return "plotter"  # Route back to the plotter
        else:
            print(f"---VALIDATION PASSED: {meaningful_scenes} meaningful scenes found.---")
            return "scene_writer" # Proceed to writing scenes

    def should_write_next_scene(state: WriterState) -> str:
        """Determines if there are more scenes to write."""
        return END if state.get('current_scene_index', 0) >= len(state.get('episode_outline', [])) else "scene_writer"
            
    # Build the sub-graph edges
    writer_workflow.set_entry_point("plotter")
    
    # After plotting, use the validator function to route
    writer_workflow.add_conditional_edges(
        "plotter",
        validate_outline,
        {
            "plotter": "plotter", # If validation fails, retry
            "scene_writer": "scene_writer" # If validation passes, proceed
        }
    )
    
    # After writing a scene, decide if we should write the next one or end
    writer_workflow.add_conditional_edges("scene_writer", should_write_next_scene)
    
    writer_graph = writer_workflow.compile()

    # --- 2. INITIALIZE AND INVOKE ---
    subgraph_state = WriterState(
        main_state=state, episode_outline=[], written_scenes=[], current_scene_index=0
    )
    final_subgraph_state = writer_graph.invoke(subgraph_state, config=config)

    # --- 3. ASSEMBLE AND RETURN ---
    print("---SUB-AGENT: SCRIPT ASSEMBLER---")
    full_script = "\n\n".join(final_subgraph_state.get('written_scenes', []))
    print(f"---COMPLETED DRAFT FOR EPISODE {current_episode_num}---")
    return {"current_draft": full_script, "continuity_errors": None}

# --- MAIN GRAPH DEFINITION ---
workflow = StateGraph(GraphState)

# 1. Define Nodes
workflow.add_node("state_preparer", state_preparer_agent)
workflow.add_node("writer", call_writer_subgraph)
workflow.add_node("first_episode_checker", first_episode_checker_agent)
workflow.add_node("continuity_checker", continuity_checker_agent)
workflow.add_node("editor", editor_agent)
workflow.add_node("series_title_creator", series_title_agent)
workflow.add_node("after_edit_logic", after_edit_logic_node)
workflow.add_node("final_check", final_check_node)

# 2. Define Routing Functions
def route_to_checker(state: GraphState) -> str:
    print("---ROUTER: DECIDING WHICH CHECKER TO USE---")
    return "first_episode_checker" if len(state.get('episodes', [])) == 0 else "continuity_checker"

def route_after_quality_check(state: GraphState) -> str:
    print("---ROUTER: CHECKING SCRIPT QUALITY---")
    return "writer" if state.get("continuity_errors") else "editor"

def route_after_editor(state: GraphState) -> str:
    print("---ROUTER: CHECKING EDITOR'S OUTPUT---")
    return "writer" if state.get("continuity_errors") else "after_edit_logic"

def route_to_final_check(state: GraphState) -> str:
    print("---ROUTER: POST-EDIT ROUTING---")
    if len(state.get('episodes', [])) == 1 and not state.get('final_series_title'):
        return "series_title_creator"
    else:
        return "final_check"

def route_after_edit_or_title(state: GraphState) -> str:
    print("---ROUTER: CHECKING IF SEASON IS COMPLETE---")
    return END if len(state.get('episodes', [])) >= state.get('num_episodes', 1) else "writer"

# 3. Build Graph Edges
workflow.set_entry_point("state_preparer")
workflow.add_edge("state_preparer", "writer")

workflow.add_conditional_edges("writer", route_to_checker)
workflow.add_conditional_edges("first_episode_checker", route_after_quality_check)
workflow.add_conditional_edges("continuity_checker", route_after_quality_check)
workflow.add_conditional_edges("editor", route_after_editor)

# Create logical nodes for routing
workflow.add_conditional_edges("after_edit_logic", route_to_final_check)
workflow.add_edge("series_title_creator", "final_check")
workflow.add_conditional_edges("final_check", route_after_edit_or_title)

# Compile the final graph
app = workflow.compile()

# --- HELPER FUNCTION FOR NEW PROJECT SETUP ---
def setup_new_project() -> GraphState:
    """Guides the user through setting up a new TV series project."""
    print("\n--- CREATING A NEW TV SERIES PROJECT ---")
    print("Please provide the details for your new series.\n")
    logline = input("1. Enter a one-sentence logline for your series:\n> ")
    genre = input("\n2. Enter the genre:\n> ")
    characters = input("\n3. Describe the main characters:\n> ")
    key_locations = input("\n4. Describe the key locations:\n> ")
    world_rules = input("\n5. Describe the unique rules or elements of your world:\n> ")
    rating = input("\n6. Enter the content rating:\n> ")
    while True:
        try:
            season_number = int(input("\n7. Enter the season number (e.g., 1, 2):\n> "))
            if season_number <= 0:
                print("Season number must be positive."); continue
            break
        except ValueError: print("Invalid input. Please enter a number.")
    while True:
        try:
            num_episodes = int(input("\n8. Enter the number of episodes for this season:\n> "))
            break
        except ValueError: print("Invalid input. Please enter a number.")
    initial_state = GraphState(
        logline=logline, characters=characters, key_locations=key_locations, world_rules=world_rules,
        genre=genre, rating=rating, season_number=season_number, num_episodes=num_episodes,
        episodes=[], summary_memory="", current_draft=None, continuity_errors=None,
        final_series_title=None, user_command=None,
    )
    print("\n--- World Bible created. Starting generation... ---")
    return initial_state

# --- MAIN EXECUTION BLOCK ---
output_dir = "output_season"
state_file = os.path.join(output_dir, "final_state.json")
user_command = ""
initial_state = None
if os.path.exists(state_file):
    with open(state_file, "r") as f:
        initial_state = json.load(f)
    print("\n--- FOUND EXISTING PROJECT ---")
    print(f"Series Title: {initial_state.get('final_series_title', 'Untitled')}")
    print(f"Season: {initial_state.get('season_number', 'N/A')}")
    print(f"Episodes Generated: {len(initial_state.get('episodes', []))}")
    print("----------------------------\n")
    command = input("Enter a command (e.g., 'rewrite 2', 'next season') or press Enter to start a new project: ")
    if command:
        if command.lower() == 'next season':
            initial_state['season_number'] += 1
            initial_state['episodes'] = []
            print(f"--- Preparing to generate Season {initial_state['season_number']}... ---")
            while True:
                try:
                    num_ep = int(input(f"How many episodes in Season {initial_state['season_number']}?\n> "))
                    initial_state['num_episodes'] = num_ep
                    break
                except ValueError: print("Invalid input.")
            initial_state['user_command'] = None
        else:
            initial_state['user_command'] = command
    else:
        initial_state = None
else:
    print("No existing project found.")
if not initial_state:
    initial_state = setup_new_project()
if 'user_command' not in initial_state:
    initial_state['user_command'] = None
final_state = app.invoke(initial_state, config=config)

# --- FINAL OUTPUT AND STORAGE ---
print("\n\n" + "=" * 50)
print("          AI SCREENPLAY WRITER - FINAL OUTPUT")
print("=" * 50 + "\n")
series_title = final_state.get("final_series_title", "Untitled Series")
print(f"SERIES TITLE: {series_title}\n")
print(f"GENRE: {final_state.get('genre')}")
print(f"RATING: {final_state.get('rating')}")
print(f"TOTAL EPISODES: {len(final_state.get('episodes', []))}")
print("\n" + "-" * 50 + "\n")
os.makedirs(output_dir, exist_ok=True)
for episode in final_state["episodes"]:
    raw_title = episode.get('title', 'Untitled Episode')
    clean_title = raw_title.replace('\n', ' ').replace('\r', '')
    safe_title = "".join(c for c in clean_title if c.isalnum() or c in (' ', '_')).strip()
    safe_title = (safe_title[:50]) if len(safe_title) > 50 else safe_title
    if not safe_title:
        safe_title = f"Episode_{episode['episode_number']}"
    season_num = final_state.get('season_number', 1)
    filename = f"S{season_num:02d}_E{episode['episode_number']:02d}_{safe_title}.txt"
    filepath = os.path.join(output_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"SERIES: {series_title}\n")
        f.write(f"EPISODE {episode['episode_number']}: {episode['title']}\n\n")
        f.write("--- SCRIPT ---\n\n")
        f.write(episode["script"])
        f.write("\n\n--- SUMMARY ---\n\n")
        f.write(episode["summary"])
    print(f"✅ Saved Episode {episode['episode_number']} to {filepath}")
with open(os.path.join(output_dir, "final_state.json"), "w", encoding="utf-8") as f:
    json.dump(final_state, f, indent=2)
print("\n✅ Full project state saved to final_state.json")