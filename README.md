# RinAI: Your Advanced Agentic Companion

RinAI is a sophisticated agentic companion, leveraging graph-based Retrieval Augmented Generation (RAG), real-time tool usage, intelligent context management, and a dynamic Large Language Model (LLM) gateway.  This combination empowers RinAI to engage in roleplaying, hold flirty conversations, and provide insightful responses based on a rich understanding of context and access to up-to-date information.

## Key Features

* **Rin Chat Agent:**
    * Engaging roleplay and flirty conversations powered by a fine-tuned uncensored LLM.
    * Parallel execution of tools, RAG, and LLM calls for efficient and comprehensive responses.
    * Dynamic Smart LLM Gateway intelligently selects the most appropriate model for each query.

* **Graph RAG:**
    * Utilizes a Neo4j database containing approximately 18,000 messages, analyzed and indexed for optimal retrieval.
    * Retrieval pipeline employs semantic embeddings, sentiment analysis, and subject classification.
    * Hybrid search combines vector lookups and rating-based filtering for precise information retrieval.

* **Tool Orchestrator:**
    * Integrates with the Perplexity API (powered by DeepSeek R1) for advanced web search, enabling access to current events, specialized knowledge, and critical reasoning.
    * Provides real-time and historical cryptocurrency price checks and analytics via the CoinGecko API.
    * Easily extensible architecture allows for seamless integration of new tools by adding API clients.

* **Smart Context Management & Summarization:**
    * Automated summarization of conversations once a token threshold is reached.
    * Maintains the latest 25% of messages intact while summarizing the older 75% in the background, ensuring context continuity.

## Architecture

RinAI's architecture comprises three main components:

* **Front-End Interface (Port 3003):** A user-friendly web application providing an interactive interface for chatting with Rin.  User input is captured and forwarded to the backend.  *(Consider adding a screenshot or mockup of the interface here)*

* **Backend Server (Port 3000):** A Node.js server that routes user messages between the front-end and the Python services.

* **Python Services (Port 8000):** Handles core agent logic, including:
    * Agent orchestration and message generation.
    * Active summarization of conversation context.
    * Retrieval and scoring from the message corpus.
    * Hybrid query analysis using Graph RAG and semantic embeddings.
    * Tool calls for cryptocurrency price checks and web searches.
    * Parallel execution of tools, RAG, and LLM calls.  *(Consider adding a diagram illustrating the data flow between these components)*

By default, you can run all three services locally on the following ports:
- Backend (Node.js): Port 3000
- Front-end: Port 3003
- Python Services: Port 8000 (auto-starts when backend is running)
Once running, navigate to http://localhost:3003 to access the Rin web app.

## Getting Started

### Prerequisites

* Node.js (v18+ recommended)
* Python (3.10+ recommended)
* `pip` and/or a virtual environment manager (e.g., `venv`, `conda`)
* Neo4j AuraDB instance (free tier is sufficient)
* MongoDB instance

### Installation

1. **Clone the Repository:**
   ```bash
   git clone [https://github.com/](https://github.com/)<your-username>/peak-ai-agent.git
   cd peak-ai-agent
   ```

2. **Node.js Setup:**
   ```bash
   cd backend/node
   npm install
   ```

3. **Python Environment Setup**
Navigate to the Python Services directory and create a virtual environment:
   ```bash
   cd backend/python_services
   python -m venv venv
   ```
Activate virtual environment:
   - Windows:
     ```bash
     .\venv\Scripts\activate
     ```
   - Unix/MacOS:
     ```bash
     source venv/bin/activate
     ```

Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration**
Create `.env` file in `/backend` directory:

5. **Start the Application**
Start the server (this will launch both Node.js and Python services):
   ```bash
   cd backend/node
   node server.js
   ```

## Common Issues
1. Port conflicts: Ensure ports 3000, 3003, and 8000 are available
2. Python venv: Make sure you're in the virtual environment when installing requirements
3. Node modules: If you get module not found errors, try `npm install` again
4. MongoDB connection: Ensure MongoDB is running and URI is correct

## Usage
**Access the application:**
   - Open your browser and navigate to: `http://localhost:3003`
   - The backend API will be running on: `http://localhost:3000`
   - The Python service will be running on: `http://localhost:8000` it will start automatically when the backend is running.

**Observe Real-Time Conversation:** The backend interacts with the Python services to determine if any tools should be called (e.g., crypto price checks, web searches). The Graph RAG pipeline retrieves relevant conversation snippets, considering sentiment and subject matter. Summarization occurs automatically when token limits are reached.

**Look for Tool Usage:** Queries involving cryptocurrency prices will trigger the Crypto Price Checker. Queries about current news or specialized information may invoke the Perplexity API for web search.

**Receive Final Answer:** RinAI compiles the final answer from tool outputs, RAG context, and the system prompt, reflecting Rin's personality.

## Configuration
Most configuration parameters are housed in environment variables or small config files within each subfolder. Some examples:

Backend:

PORT (default 3000)
FRONTEND_PORT (default 3003)
API keys for external services.
Python Services:

PYTHON_SERVICE_PORT (default 8000)
Paths or credentials for the DB (Neo4j, vector store).
API keys for Perplexity, CoinGecko, or other integrated tools.
Example .env for Backend

PORT=3000
FRONTEND_PORT=3003
PERPLEXITY_API_KEY=your-perplexity-key
COINGECKO_API_URL=https://api.coingecko.com/api/v3/
Example .env for Python Services

PYTHON_SERVICE_PORT=8000
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password
EMBEDDINGS_MODEL=all-mpnet-base-v2

Needing a DB Schema
For the Graph RAG functionality, you’ll want a Neo4j instance (or equivalent). We will soon provide:

DB Schema: Node labels (e.g., Message), relationships (e.g., HAS_SENTIMENT, HAS_SUBJECT), indices, constraints.
Processing Script: Bulk imports the 14,000+ Rin messages, setting attributes like sentiment, subject, effectiveness rating, etc.
Stay tuned for an update in which we release these schema details and a sample dataset or seeds for your own usage.

Extended Tooling
Additional APIs and specialized tools could be integrated (e.g., coding assistance, image generation, scheduling, and more).

Advanced Orchestration
Enhancements to the summarization logic, better concurrency handling, and plugin-based expansions for the agent’s toolkit.

Contributing
We heartily welcome and appreciate any and all contributions! To get started:

Fork this repository.
Create a new branch for your feature or fix.
Submit a Pull Request describing the changes you’ve made.
We will review PRs as quickly as we can. Please read our CONTRIBUTING.md (coming soon) for more detailed guidelines on style, commits, and testing.

License
This project is licensed under the MIT License. Feel free to use, modify, and distribute this software as stated within the license terms.