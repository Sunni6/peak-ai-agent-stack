const axios = require('axios');
require('dotenv').config();

class RinChatService {
    constructor() {
        this.baseUrl = process.env.PYTHON_SERVICE_URL || 'http://localhost:8000';
        this.apiKey = process.env.RIN_CHAT_API_KEY;
        this.token = null;
        this.tokenExpiry = null;
        this.sessions = new Map();
    }

    async authenticate() {
        try {
            // For local development, we'll create a simple token
            this.token = 'local_development_token';
            this.tokenExpiry = Date.now() + (60 * 60 * 1000); // 1 hour
            return true;
        } catch (error) {
            console.error('Auth error:', error);
            throw new Error(`Authentication failed: ${error.message}`);
        }
    }

    async initializeSession() {
        try {
            const sessionId = Math.random().toString(36).substring(2, 15);
            this.sessions.set(sessionId, {
                created: Date.now(),
                history: []
            });

            return {
                status: 'success',
                sessionId: sessionId,
                message: 'Konnichiwa! How can I help you today? ^_^'
            };
        } catch (error) {
            console.error('Session initialization error:', error);
            throw error;
        }
    }

    async sendMessage(sessionId, message) {
        try {
            if (!this.sessions.has(sessionId)) {
                throw new Error('Invalid session');
            }

            // Forward the message to the Python service
            const response = await axios.post(`${this.baseUrl}/api/chat`, {
                message: message
            });

            // Add to history
            await this.addToHistory(sessionId, message, 'user');
            await this.addToHistory(sessionId, response.data.response, 'assistant');

            return {
                status: 'success',
                response: response.data.response
            };
        } catch (error) {
            console.error('Message sending error:', error);
            throw error;
        }
    }

    async addToHistory(sessionId, message, role) {
        if (!this.sessions.has(sessionId)) {
            throw new Error('Invalid session');
        }
        const session = this.sessions.get(sessionId);
        session.history.push({
            role,
            content: message,
            timestamp: new Date().toISOString()
        });
    }

    async getHistory(sessionId) {
        if (!this.sessions.has(sessionId)) {
            throw new Error('Invalid session');
        }
        return this.sessions.get(sessionId).history;
    }
}

module.exports = RinChatService; 