const axios = require('axios');
const jwt = require('jsonwebtoken');
const config = require('../config');

class RinAgentService {
    constructor() {
        this.pythonServiceUrl = config.pythonService.url;  // This is http://localhost:8000
        this.apiKey = config.pythonService.apiKey;
        this.secret = config.pythonService.secret;
        this.token = null;
        this.tokenExpiry = null;
        this.sessions = new Map();
    }

    async ensureValidToken() {
        const now = Date.now();
        if (!this.token || !this.tokenExpiry || now >= (this.tokenExpiry - 300000)) {
            await this.authenticate();
        }
        return this.token;
    }

    async authenticate() {
        try {
            // This is the internal call from Node.js to Python service
            const authResponse = await axios.post(
                `${this.pythonServiceUrl}/api/token`,  // Correct endpoint on Python service
                {
                    api_key: this.apiKey
                },
                {
                    headers: {
                        'Content-Type': 'application/json',
                        'X-API-Key': this.apiKey
                    }
                }
            );

            if (!authResponse.data.access_token) {
                throw new Error('No access token received from Python service');
            }

            this.token = authResponse.data.access_token;
            this.tokenExpiry = Date.now() + (55 * 60 * 1000); // 55 minutes
            console.log('Authentication with Python service successful');
            return this.token;
        } catch (error) {
            console.error('Auth error:', error);
            throw new Error(`Authentication failed: ${error.message}`);
        }
    }

    async initializeSession() {
        try {
            const token = await this.ensureValidToken();
            
            const response = await axios.post(
                `${this.pythonServiceUrl}/api/session/init`,
                {
                    api_key: this.apiKey,
                    timestamp: new Date().toISOString()
                },
                {
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json',
                        'X-API-Key': this.apiKey
                    }
                }
            );
            
            const sessionId = response.data.session_id;
            this.sessions.set(sessionId, {
                created: Date.now(),
                history: []
            });
            
            return sessionId;
        } catch (error) {
            console.error('Session initialization error:', error);
            throw error;
        }
    }

    async sendMessage(sessionId, message) {
        try {
            const token = await this.ensureValidToken();
            
            const response = await axios.post(
                `${this.pythonServiceUrl}/api/chat`,
                {
                    session_id: sessionId,
                    message: message
                },
                {
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json',
                        'X-API-Key': this.apiKey
                    }
                }
            );

            await this.addToHistory(sessionId, message, 'user');
            await this.addToHistory(sessionId, response.data.response, 'assistant');

            return response.data.response;
        } catch (error) {
            console.error('Message sending error:', error);
            throw error;
        }
    }

    async getHistory(sessionId) {
        if (!this.sessions.has(sessionId)) {
            throw new Error('Invalid session');
        }
        return this.sessions.get(sessionId).history;
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
}

module.exports = RinAgentService; 