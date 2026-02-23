# AI Screenplay Writer System
![AI Screenplay Writer Architecture](assets/Header_pic_01.png)

This project is an advanced, multi-agent AI system designed to generate entire seasons of original TV series screenplays. Using a sophisticated graph-based architecture powered by LangGraph, it orchestrates a team of specialized AI agents to collaboratively write, edit, and refine each episode while preserving continuity and evolving the narrative episodically.

The system is not just a generator; it's an interactive and persistent creative partner, allowing users to define their series' "World Bible," direct the story with rewrite commands, and build out multi-season arcs with proper pacing and structure.

## Core Features

- **Full Season Generation**: Creates a complete season of screenplays from a user-defined concept, not just a single script.

- **Episodic Structure**: The system is explicitly designed to think like a TV writer, generating one "chapter" of the story at a time and ending each episode on a cliffhanger or unresolved question to ensure proper pacing.

- **Interactive World-Building**: A guided setup process allows you to create a detailed "World Bible" for your series, including:
  - Logline
  - Genre & Rating
  - Character Biographies
  - Key Locations
  - Unique World Rules (magic systems, technologies, social rules, etc.)

- **Multi-Agent "Writers' Room"**: The writing process is decomposed into a robust sub-graph of specialized agents:
  - **Scene Plotter**: Outlines the episode with a focus on episodic structure.
  - **Outline Validator**: A crucial quality gate that forces the plotter to retry if its outline is weak or incomplete.
  - **Scene Writer**: Writes the script for each scene individually, ensuring focus and quality.
  - **Script Assembler**: Compiles the scenes into a final, coherent episode script.

- **Intelligent Continuity & Quality Control**:
  - A **First Episode Checker** ensures the pilot episode aligns with the World Bible.
  - A **Continuity Checker** acts as a "story editor," verifying that subsequent episodes are logical continuations of the established canon.
  - An **Optimized Editor Agent** efficiently generates titles and summaries using JSON for reliability.

- **Persistent, Multi-Season Projects**:
  - The entire state of a series is saved to `final_state.json`, allowing you to stop and resume work.
  - Supports multi-season narratives with a `next season` command that preserves world continuity.

- **Human-in-the-Loop Direction**:
  - The `rewrite [episode_number]` command lets you roll back the story to a specific point and regenerate it, giving you ultimate creative control.

## How It Works: The LangGraph Narrative Blueprint

The system is built as a state machine using LangGraph. The "state" is the entire TV series project. Specialized AI agents, defined as nodes in the graph, read and modify this state. Conditional edges act as routers, directing the workflow based on the output of the agents.

The main workflow is as follows:

1. **Project Setup**: The user either creates a new "World Bible" or loads an existing project.

2. **State Preparation**: A non-AI node processes user commands like `rewrite` or prepares for a new season.

3. **Writers' Room Sub-Graph**: The system enters a nested graph to write the episode:
   - a. The plotter outlines the scenes for the episode.
   - b. The validator checks the outline for quality. If it fails, the plotter retries.
   - c. The graph loops, calling the `scene_writer` for each approved scene.
   - d. The assembler compiles the final script.

4. **Quality Check**: The draft is passed to the appropriate checker. If errors are found, the graph loops back to the writer for a full rewrite.

5. **Metadata Generation**: The approved script is passed to the optimized editor, which generates a title and summary. If the editor fails to format its output, the graph loops back for a full rewrite.

6. **State Update & Loop**: The finished episode is saved to the state, and the graph either loops to create the next episode or ends if the season is complete.

7. **File Output**: All generated episodes are saved as `.txt` files in a structured format (e.g., `S01_E01_Title.txt`), and the final project state is saved to `final_state.json`.

## Prerequisites

- Python 3.9+
- An OpenAI API Key (or another compatible LLM provider, `gpt-4o-mini` was used for development).

## Setup and Installation

### 1. Clone the Repository

```bash
git clone https://github.com/E-Asrar-Haghighi/ai-screenplay-writer.git
cd ai-screenplay-writer


```

### 2. Create a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`

```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables

Copy the example environment file and add your OpenAI API key:

```bash
cp .env.example .env  # On Windows, use `copy .env.example .env`
```

Then edit `.env` and add your API key:

```
OPENAI_API_KEY=your-api-key-here
```

Get your API key from: https://platform.openai.com/api-keys
## How to Use the System

Simply run the main script from your terminal:

```bash
python main.py
```
### Starting a New Series

If no `output_season/final_state.json` file is found, the system will automatically launch the New Project Setup guide. Follow the on-screen prompts to build the World Bible for your series.

### Continuing or Reworking an Existing Series

If a `final_state.json` file is found, the system will load the existing project and prompt you for a command:

- **To start a new project**: Press Enter without typing anything.
- **To rewrite the story**: Type `rewrite [number]` (e.g., `rewrite 2`) and press Enter. The system will discard Episode 2 and all subsequent episodes and regenerate them.
- **To generate the next season**: Type `next season` and press Enter. The system will increment the season number, ask for the new episode count, and begin generating the next season while preserving the story's history.

## Example Output

The `output_season/` directory contains example episodes from an AI-generated series called **"Curating Chaos"** - a romantic comedy about a meticulous museum curator whose world is turned upside down by a spontaneous adventure vlogger.

### Sample Episodes:

- **S01_E01: "History Meets Adventure"** - The pilot episode where Oliver Grant, a careful museum curator, reluctantly agrees to collaborate with Zoe Rivera, an enthusiastic vlogger, to create an interactive scavenger hunt that blends history with modern engagement.

- **S01_E02: "Dinosaur Adventures and Dinner Dates"** - The team brainstorms a unique museum scavenger hunt that combines historical artifacts with romantic elements, leading to unexpected chaos and chemistry between Oliver and Zoe.

These episodes demonstrate:
- ✅ **Professional screenplay formatting** (INT/EXT scene headers, character names, dialogue)
- ✅ **Narrative continuity** between episodes with consistent characters and evolving storylines
- ✅ **Episodic structure** with proper pacing, character development, and scene transitions
- ✅ **AI-generated creative content** that maintains coherence across multiple episodes

Each episode is approximately 750 lines and includes detailed scene descriptions, character interactions, and a summary at the end.

> **Note**: All content in the `output_season/` directory is AI-generated and serves as a demonstration of the system's capabilities. Feel free to use these as reference examples for understanding the output format.

## Project Structure

```
.
├── output_season/      # Generated screenplays and state file appear here
├── venv/               # Python virtual environment
├── .env                # Stores API keys (not in repo)
├── .env.example        # Environment variable template
├── agents.py           # Contains all AI agent and sub-agent functions
├── main.py             # Main script to define the graph and run the system
├── state.py            # Defines the data structures for the graph states
├── requirements.txt    # Project dependencies
└── README.md           # This file
```
