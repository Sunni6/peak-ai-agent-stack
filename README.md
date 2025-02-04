# Peak AI Agent Stack

A modern AI chat application featuring Rin, an engaging AI companion built with Node.js and Python.

## Project Structure 
peak-ai-agent-stack/
├── frontend/
│ └── index.html
├── backend/
│ ├── node/
│ │ ├── package.json
│ │ ├── package-lock.json
│ │ ├── server.js
│ │ ├── routes/
│ │ ├── middleware/
│ │ ├── utils/
│ │ └── config/
│ └── python_services/
│ └── core/
│ ├── agent/
│ └── db/
├── .gitignore
└── README.md

## Features

- 🤖 Engaging AI chat interface
- 🔒 Secure JWT-based authentication
- 🚀 Rate limiting and request throttling
- 📝 MongoDB chat history storage
- 🐍 Python-based AI processing
- 🔄 Real-time message updates

## Prerequisites

- Node.js >= 14
- Python >= 3.8
- MongoDB
- Redis (for rate limiting)

## Installation

1. Clone the repository:

```bash
git clone https://github.com/dleerdefi/peak-ai-agent-stack.git
cd peak-ai-agent-stack
```

2. Install Node.js dependencies:
```bash
cd backend/node
npm install
```

3. Install Python dependencies:
```bash
cd ../python_services
pip install -r requirements.txt
```

4. Set up environment variables:
```env
# In backend/node/.env
PORT=3000
MONGODB_URI=mongodb://localhost:27017/rin_dev_db
REDIS_URL=redis://localhost:6379
JWT_SECRET=your_jwt_secret

# In backend/python_services/.env
MONGO_URI=mongodb://localhost:27017/rin_dev_db
```

## Running the Application

1. Start the Node.js backend:
```bash
cd backend/node
npm start
```

2. Start the Python services:
```bash
cd backend/python_services
python main.py
```

3. Open `frontend/index.html` in your browser or serve it with a static file server.

## Development

- Frontend: Pure HTML/CSS/JS for simplicity and performance
- Backend: Express.js with JWT authentication and rate limiting
- AI Processing: Python with async support for AI operations
- Database: MongoDB for chat history and user data
- Caching: Redis for rate limiting and session management

## License

ISC License

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
