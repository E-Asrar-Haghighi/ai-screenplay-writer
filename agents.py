# agents.py
import os
import json
import re
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from state import GraphState, Episode, WriterState

# Load environment variables
load_dotenv()

# Initialize the LLM
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)

# --- MAIN GRAPH AGENTS ---

def state_preparer_agent(state: GraphState) -> dict:
    """Prepares the state based on a user command, like 'rewrite'."""
    print("---AGENT: STATE PREPARER---")
    user_command = state.get('user_command')

    if not user_command or not user_command.lower().startswith("rewrite"):
        print("---STATE PREPARER: No rewrite command. Proceeding normally.---")
        return {}

    try:
        match = re.search(r'\d+', user_command)
        if not match:
            raise ValueError("No episode number in rewrite command.")
        
        episode_num_to_rewrite = int(match.group(0))
        print(f"---STATE PREPARER: Rewriting from Episode {episode_num_to_rewrite}.---")

        if not (0 < episode_num_to_rewrite <= len(state['episodes'])):
            raise ValueError(f"Invalid episode number: {episode_num_to_rewrite}.")

        episodes_to_keep = state['episodes'][:episode_num_to_rewrite - 1]
        
        new_summary_memory = ""
        for ep in episodes_to_keep:
            new_summary_memory += f"\n\nEpisode {ep['episode_number']}: {ep['title']}\n{ep['summary']}"

        print(f"---STATE PREPARER: Rolled back. Kept {len(episodes_to_keep)} episodes.---")
        
        return {
            "episodes": episodes_to_keep,
            "summary_memory": new_summary_memory.strip(),
            "user_command": None # Clear command after processing
        }
    except (ValueError, IndexError) as e:
        print(f"---ERROR in State Preparer: {e}. Aborting rewrite.---")
        return {"user_command": None}

def first_episode_checker_agent(state: GraphState) -> dict:
    """A specialized, lenient checker for the first episode."""
    print("---AGENT: FIRST EPISODE CHECKER---")
    prompt = ChatPromptTemplate.from_template(
        """You are a story editor reviewing the pilot episode of a new TV series.
        Your job is to ensure this first script is a strong, logical starting point that aligns with the series's core concept, as defined in the Series Bible.

        **SERIES BIBLE:**
        - Logline: {logline}
        - Genre: {genre}
        - Characters: {characters}
        - Key Locations: {key_locations}
        - World Rules/Elements: {world_rules}
        
        **Draft Script for Episode 1:**
        {draft}

        **Instructions:**
        Review the script against the Series Bible. Do NOT flag elements simply for being "new," as this is the first episode.
        Only fail the script if it fundamentally contradicts the information provided in the Series Bible (e.g., wrong genre, wrong characters, ignoring key locations).

        If the script is a reasonable starting point, respond with the single word: "pass".
        If you find a show-breaking error, explain it clearly and concisely.
        
        Your response:"""
    )
    checker_chain = prompt | llm | StrOutputParser()
    errors = checker_chain.invoke({
        "logline": state['logline'], "genre": state['genre'], "rating": state['rating'],
        "characters": state['characters'], "key_locations": state['key_locations'],
        "world_rules": state['world_rules'], "draft": state['current_draft']
    })
    if errors.strip().lower() == "pass":
        print("---FIRST EPISODE CHECKER: Pass! A solid starting point.---")
        return {"continuity_errors": None}
    else:
        print(f"---FIRST EPISODE CHECKER: Fail! Found major issues: {errors}---")
        return {"continuity_errors": errors.strip().split('\n')}

def continuity_checker_agent(state: GraphState) -> dict:
    """Reviews the draft script, allowing for story progression."""
    print("---AGENT: CONTINUITY CHECKER---")
    prompt = ChatPromptTemplate.from_template(
        """You are a meticulous story editor for a TV series. Your job is to review a new episode script and ensure it logically follows the established canon while allowing for natural story progression.

        **CRITICAL INSTRUCTION:** A new episode should naturally introduce new developments, locations, or character nuances. Do NOT flag these as errors if they are logical extensions of the existing story. Your role is to catch major CONTRADICTIONS, not to prevent the story from evolving.

        **Established Story Canon (Summary of Previous Episodes):**
        {summary_memory}
        
        **Draft Script for the New Episode:**
        {draft}

        **Instructions:**
        Carefully read the new draft. Flag it for rewrite ONLY if you find a major, undeniable contradiction like a character returning from the dead, a sudden genre shift, or a direct contradiction of a major plot point.

        If the script is a logical continuation of the story, respond with the single word: "pass".
        If you find a major contradiction, list it clearly and concisely.
        
        Your response:"""
    )
    checker_chain = prompt | llm | StrOutputParser()
    errors = checker_chain.invoke({
        "summary_memory": state['summary_memory'],
        "draft": state['current_draft']
    })
    if errors.strip().lower() == "pass":
        print("---CONTINUITY CHECKER: Pass! A logical continuation.---")
        return {"continuity_errors": None}
    else:
        print(f"---CONTINUITY CHECKER: Fail! Found major contradictions: {errors}---")
        return {"continuity_errors": errors.strip().split('\n')}

def editor_agent(state: GraphState) -> dict:
    """OPTIMIZED v2: Reads the script and generates a JSON object with title and summary."""
    print("---AGENT: EDITOR (JSON)---")
    final_script = state['current_draft']
    prompt = ChatPromptTemplate.from_template(
        """You are a creative executive who needs to title and summarize a TV episode.
        Read the following script and generate a JSON object containing the title and summary.

        **CRITICAL: Your entire response must be a single, valid JSON object and nothing else.**
        
        Example Response:
        {{
          "title": "A Day at the Races",
          "summary": "In this episode, John enters a high-stakes horse race to win the money he needs to save his family's farm, but discovers the race is fixed by a rival."
        }}

        **Final Script to Analyze:**
        {draft}"""
    )
    editor_chain = prompt | llm | StrOutputParser()
    metadata_output = editor_chain.invoke({"draft": final_script})
    try:
        clean_json_str = metadata_output.strip().replace('```json', '').replace('```', '')
        data = json.loads(clean_json_str)
        title = data["title"]
        summary = data["summary"]
        if not title or not summary or '\n' in title:
             raise ValueError("Parsed JSON is missing fields or title is multi-line.")

        current_episode_num = len(state['episodes']) + 1
        new_episode = Episode(
            episode_number=current_episode_num, title=title, script=final_script, summary=summary
        )
        all_episodes = state['episodes'] + [new_episode]
        new_summary_memory = state['summary_memory'] + f"\n\nEpisode {current_episode_num}: {title}\n{summary}"
        
        return {
            "episodes": all_episodes, 
            "summary_memory": new_summary_memory.strip(),
            "continuity_errors": None 
        }
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        print(f"---ERROR: FAILED TO PARSE EDITOR JSON---")
        print(f"Error details: {e}")
        print(f"Raw LLM Output:\n---\n{metadata_output}\n---")
        return {"continuity_errors": ["Editor agent failed to produce valid JSON metadata."]}

def series_title_agent(state: GraphState) -> dict:
    """Generates a title for the entire series."""
    print("---AGENT: SERIES TITLE---")
    if state.get('final_series_title'):
        return {}
    first_episode_summary = state['episodes'][0]['summary']
    prompt = ChatPromptTemplate.from_template(
        """You are a creative executive at a TV studio.
        Based on the summary of the first episode, the characters, and the genre, propose a single, compelling title for the entire TV series.
        Respond with ONLY the title.

        **Genre:** {genre}
        **Characters:** {characters}
        **First Episode Summary:** {summary}"""
    )
    title_chain = prompt | llm | StrOutputParser()
    series_title = title_chain.invoke({
        "genre": state['genre'], "characters": state['characters'], "summary": first_episode_summary,
    })
    print(f"---SERIES TITLE PROPOSED: {series_title.strip()}---")
    return {"final_series_title": series_title.strip()}


# --- WRITER'S ROOM SUB-GRAPH AGENTS ---

def scene_plotter_agent(state: WriterState) -> dict:
    """
    Generates a flexible, episodic outline of 4-6 scenes.
    """
    print("---SUB-AGENT: SCENE PLOTTER (EPISODIC)---")
    main_state = state['main_state']
    current_episode_num = len(main_state['episodes']) + 1

    if main_state['episodes']:
        last_episode = main_state['episodes'][-1]
        recap_of_last_episode = f"Episode {last_episode['episode_number']}: {last_episode['title']}\n{last_episode['summary']}"
    else:
        recap_of_last_episode = "This is the very first episode. Start the story by introducing the main character and their core problem."

    prompt = ChatPromptTemplate.from_template(
        """You are a professional TV writer creating an episodic outline.

        **GOAL:** Create a concise outline for the next episode of a TV series. The outline should describe the next logical chapter of the story and end on a note of suspense or a new question (a cliffhanger). A good outline should be between 4 to 6 key scenes.

        **SERIES BIBLE (for context):**
        - Logline: {logline}
        - Genre: {genre}
        - Characters: {characters}
        
        **RECAP OF THE PREVIOUS EPISODE:**
        {recap}

        **Your Task:**
        Based on the recap, write a bullet-point outline for Episode {episode_num}. Each bullet point should be a single, descriptive scene.
        
        - The outline **MUST** be a direct continuation of the recap.
        - The outline **SHOULD** build towards a climactic moment for the episode.
        - The final scene **MUST** leave something unresolved.

        Create the episodic outline now:"""
    )

    plotter_chain = prompt | llm | StrOutputParser()
    
    outline_str = plotter_chain.invoke({
        "logline": main_state['logline'], "genre": main_state['genre'],
        "characters": main_state['characters'], "recap": recap_of_last_episode,
        "episode_num": current_episode_num,
    })
    
    # --- THE FIX: A more robust parser to eliminate junk lines ---
    scene_outlines_raw = outline_str.split('\n')
    cleaned_outlines = []
    
    for line in scene_outlines_raw:
        clean_line = line.strip()
        # A much stricter check:
        # Must start with a bullet/SCENE, have more than 4 words,
        # and NOT be just a simple header.
        is_header = ("setup" in clean_line.lower() or 
                    "development" in clean_line.lower() or 
                    "climax" in clean_line.lower() or 
                    "cliffhanger" in clean_line.lower()) and len(clean_line.split()) <= 6
        
        if (clean_line.startswith('-') or "SCENE" in clean_line.upper()) and len(clean_line.split()) > 4 and not is_header:
            # Remove leading bullet points or "SCENE X:" for cleaner processing
            processed_line = re.sub(r'^(?:\* |- |SCENE \d+: ?)', '', clean_line, flags=re.IGNORECASE).strip()
            if processed_line:  # Make sure we didn't strip everything
                cleaned_outlines.append(processed_line)

    print("\n--- CLEANED SCENE OUTLINE (EPISODIC) ---")
    for i, scene in enumerate(cleaned_outlines):
        print(f"{i+1}: {scene}")
    print("----------------------------------------\n")

    unique_outlines = list(dict.fromkeys(cleaned_outlines))
    if len(unique_outlines) < len(cleaned_outlines):
        print(f"---INFO: Removed {len(cleaned_outlines) - len(unique_outlines)} duplicate scene(s).---")
    
    print(f"---SUB-AGENT: Proceeding with {len(unique_outlines)} scenes.---")
    return {"episode_outline": unique_outlines[:4]} # Hard limit to 4 scenes

def scene_writer_agent(state: WriterState) -> dict:
    """Writes the script for a single scene."""
    current_index = state['current_scene_index']
    total_scenes = len(state['episode_outline'])
    print(f"---SUB-AGENT: SCENE WRITER (Scene {current_index + 1}/{total_scenes})---")
    scene_description = state['episode_outline'][current_index]
    print(f"   Writing scene: '{scene_description}'")
    main_state = state['main_state']
    context_from_this_episode = "\n\n".join(state['written_scenes'])
    prompt = ChatPromptTemplate.from_template(
        """You are a professional screenplay writer. Write a single, focused scene.

        **SERIES BIBLE:**
        - Genre: {genre}
        - Characters: {characters}
        
        **STORY SO FAR (Previous Episodes):**
        - Series Summary: {summary_memory}

        **CONTEXT FROM EARLIER IN THIS EPISODE:**
        {context_from_this_episode}

        **SCENE TO WRITE:**
        - Description: {scene_description}

        **Instructions:**
        Write a focused, well-paced scene (approx. 2-4 pages). Include scene headings (INT./EXT.), action lines, and dialogue. The scene must logically follow from the context provided. DO NOT write any scenes other than the one described."""
    )
    scene_writer_chain = prompt | llm | StrOutputParser()
    written_scene = scene_writer_chain.invoke({
        "genre": main_state['genre'], "characters": main_state['characters'],
        "summary_memory": main_state['summary_memory'], "context_from_this_episode": context_from_this_episode,
        "scene_description": scene_description,
    })
    all_written_scenes = state['written_scenes'] + [written_scene]
    next_index = current_index + 1
    print(f"---SUB-AGENT: Completed Scene {current_index + 1}/{total_scenes}---")
    return {"written_scenes": all_written_scenes, "current_scene_index": next_index}