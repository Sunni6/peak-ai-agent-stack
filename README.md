# RinAI: Your Advanced Agentic Companion
![RinAI Banner](https://github.com/dleerdefi/peak-ai-agent-stack/blob/main/assets/images/RinAI%20Banner.png)

RinAI is a sophisticated agentic companion, leveraging graph-based Retrieval Augmented Generation (RAG), real-time tool usage, intelligent context management, and a dynamic Large Language Model (LLM) gateway.  This combination empowers RinAI to engage in roleplaying, hold flirty conversations, and provide insightful responses based on a rich understanding of context and access to up-to-date information.

## Key Features

![RinAI Agent Stack](https://github.com/dleerdefi/peak-ai-agent-stack/blob/main/assets/images/RinAI%20Agent%20Stack.png)

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

![RinAI Smart Context Management](https://github.com/dleerdefi/peak-ai-agent-stack/blob/main/assets/images/RinAI%20Smart%20Context.png)

## Architecture

RinAI's architecture comprises three main components:

* **Front-End Interface (Port 3003):** A user-friendly web application providing an interactive interface for chatting with Rin.  User input is captured and forwarded to the backend.

![RinAI Front-End Interface](https://github.com/dleerdefi/peak-ai-agent-stack/blob/main/assets/images/RinAI%20Frontend%20Interface.png)

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
   git clone [https://github.com/](https://github.com/)<your-username>/peak-ai-agent-stack.git
   cd peak-ai-agent
   ```

2. **Node.js Setup:**
   ```bash
   cd backend/node
   npm install
   ```

3. **Python Environment Setup**
   ```bash
   cd backend/python_services
   python -m venv venv
   ```
4. **Activate virtual environment:**
   - Windows:
     ```bash
     .\venv\Scripts\activate
     ```
   - Unix/MacOS:
     ```bash
     source venv/bin/activate
     ```

5. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

6. **Environment Configuration**
    Create `.env` file in `/backend` directory:

7. **Generate Keys (for Python Service and Rin Chat):**

Before starting the application, you need to generate API keys for the Python service and Rin Chat.

   ```bash
   cd backend/node/utils
   node generateKeys.js PYTHON_SERVICES
   node generateKeys.js RIN_CHAT
   ```
Example output:

    Generated keys for Client PYTHON_SERVICES:
    ----------------------------------------
    PYTHON_SERVICES_API_KEY=ea05d15b578a8e258d0a7864bbe7dd2d91312d5d75edc9677e326fbb2ac2d505
    PYTHON_SERVICES_SECRET=/j27kVwGGBb4fTaVNwnAzkac3xRy1qU+NZpST7MQaK0n6Lj+AaNCTid60ZNitT3htAFPSv5lAzpSKbflp3lW5A==

    Generated keys for Client RIN_CHAT:
    ----------------------------------------
    RIN_CHAT_API_KEY=c0aa64c5645821634cf2fb8380ebf25e856e90e9ec8c09f2170dd25932fc529e
    RIN_CHAT_SECRET=dpTkrTN04PuMXyIJw1MRd/V7MnTCXpmyzz6o3NER/HBaq/xhEzXCp67425B+CLqNW47tprDW/Yu/z64nryuVIQ==

    Copy these keys into your environment variables.

8. **Start the Application**
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
Reference env.example in the backend directory for a complete list of environment variables.
    
    LLM & RAG API Keys
    ANTHROPIC_API_KEY=your_anthropic_key
    TOGETHER_API_KEY=your_together_key
    NOVITA_API_KEY=your_novita_key
    PERPLEXITY_API_KEY=your_perplexity_key
    GROQ_API_KEY=your_groq_key
    OPENAI_API_KEY=your_openai_key
    VOYAGE_API_KEY=your_voyage_key

    Tools
    COINGECKO_API_KEY=your_coingecko_key

    MongoDB
    MONGO_DB=your_mongodb_database_name
    MONGO_URI=mongodb+srv://<your_mongodb_username>:<your_mongodb_password>@<your_mongodb_cluster>.mongodb.net/?retryWrites=true&w=majority  # Example URI

    Neo4j & AuraDB
    AURA_INSTANCE_ID=your_aura_instance_id
    AURA_INSTANCE_NAME=your_aura_instance_name
    NEO4J_PASSWORD=your_neo4j_password
    NEO4J_URI=bolt://<your_aura_instance_id>.databases.neo4j.io:7687  # Example URI
    NEO4J_USERNAME=neo4j  # Typically 'neo4j'

    Backend
    BACKEND_URL=http://localhost:3000  
    NODE_ENV=development # Or 'production'
    PORT=3000

    Python API Server
    PYTHON_SERVICE_API_KEY=your_python_api_key #from generateKeys.js
    PYTHON_SERVICE_SECRET=your_python_api_secret #from generateKeys.js
    PYTHON_SERVICE_URL=http://localhost:8000

    Rin Chat
    RIN_CHAT_API_KEY=your_rin_chat_api_key #from generateKeys.js
    RIN_CHAT_CLIENT_SECRET=your_rin_chat_client_secret #from generateKeys.js
    RIN_CHAT_RATE_LIMIT=100
    RIN_CHAT_WINDOW=25
    RIN_CHAT_ACCESS_TOKEN_EXPIRY=30m
    RIN_CHAT_REFRESH_TOKEN_EXPIRY=1d

## Neo4j Database Schema and Customization
The /backend/python_services/core/graphrag directory requires customization based on your data. Rin's schema is based on 18,000+ deeply processed messages focused on sentiment and intimacy. Your goals may differ, but the logic will be similar.  You can easily ingest any data or documentation into Neo4j for your own customized Graph RAG memory. LangChain provides a great template structure for any graphRAG implementation.

## Extended Tooling
Additional APIs and specialized tools could be integrated (e.g., coding assistance, image generation, scheduling, and more).

## Contributing
We heartily welcome and appreciate any and all contributions! To get started:

* Fork this repository.
* Create a new branch for your feature or fix.
* Submit a Pull Request describing the changes you’ve made.

We will review PRs as quickly as we can. Please read our CONTRIBUTING.md (coming soon) for more detailed guidelines on style, commits, and testing.

## License
This project is licensed under the MIT License. Feel free to use, modify, and distribute this software as stated within the license terms.
