const express = require('express');
const router = express.Router();
const { authenticateRinToken } = require('../middleware/rinAuth');
const { getRateLimiter } = require('../middleware/rateLimiter');
const axios = require('axios');
const config = require('../config');
const jwt = require('jsonwebtoken');

const PYTHON_SERVICE_URL = config.pythonService.url;
const PYTHON_API_KEY = config.pythonService.apiKey;

// Session initialization endpoint
router.post('/session/init', 
    authenticateRinToken,
    getRateLimiter('session'),
    async (req, res) => {
        try {
            // Extract sessionId from the JWT token
            const sessionId = req.user.sessionId;
            console.log('Initializing session:', sessionId);
            
            try {
                // Initialize session with Python service
                const pythonResponse = await axios.post(
                    `${PYTHON_SERVICE_URL}/api/session/init`,
                    { session_id: sessionId },
                    {
                        headers: {
                            'Authorization': `Bearer ${req.token}`,
                            'X-API-Key': PYTHON_API_KEY,
                            'Content-Type': 'application/json'
                        }
                    }
                );
                
                console.log('Python service response:', pythonResponse.data);
                
                // Send success response regardless of Python service response
                res.json({
                    status: 'success',
                    sessionId: sessionId,
                    message: 'Session initialized'
                });
            } catch (pythonError) {
                console.warn('Python service warning:', pythonError.response?.data || pythonError);
                // Still return success to frontend since we have a valid sessionId
                res.json({
                    status: 'success',
                    sessionId: sessionId,
                    message: 'Session initialized'
                });
            }
        } catch (error) {
            console.error('Session initialization error:', error);
            res.status(500).json({
                status: 'error',
                message: 'Failed to initialize session'
            });
        }
    }
);

// Chat endpoint
router.post('/chat', 
    authenticateRinToken,
    getRateLimiter('chat'),
    async (req, res) => {
        try {
            const { sessionId, message } = req.body;
            
            if (!sessionId || !message) {
                return res.status(400).json({
                    status: 'error',
                    message: 'Missing sessionId or message'
                });
            }

            // Forward to Python service with session_id and bearer token
            const response = await axios.post(
                `${PYTHON_SERVICE_URL}/api/chat`,
                {
                    session_id: sessionId,
                    message: message,
                    auth_token: req.token  // Add the bearer token
                },
                {
                    headers: {
                        'X-API-Key': PYTHON_API_KEY,
                        'Content-Type': 'application/json'
                    }
                }
            );

            res.json({
                status: 'success',
                response: response.data.response
            });
        } catch (error) {
            console.error('Chat error:', error.response?.data || error.message);
            res.status(500).json({
                status: 'error',
                message: 'Failed to process message',
                details: error.response?.data?.detail || error.message
            });
        }
    }
);

// Get chat history endpoint
router.post('/history/:sessionId',
    authenticateRinToken,  // Validates the Bearer token
    getRateLimiter('history'),
    async (req, res) => {
        try {
            const response = await axios.get(
                `${PYTHON_SERVICE_URL}/api/history/${req.params.sessionId}`,
                {
                    headers: {
                        'X-API-Key': PYTHON_API_KEY
                    }
                }
            );

            res.json({
                status: 'success',
                history: response.data.history
            });
        } catch (error) {
            console.error('History error:', error);
            res.status(500).json({
                status: 'error',
                message: 'Failed to fetch history'
            });
        }
    }
);

// Auth endpoint (matches production)
router.post('/auth', async (req, res) => {
    try {
        const sessionId = require('crypto').randomUUID();
        
        // Generate token using server's secret
        const token = jwt.sign(
            {
                service: 'rin-chat',
                type: 'access',
                sessionId: sessionId
            },
            config.rin.secret,
            {
                expiresIn: config.rin.accessTokenExpiry,
                audience: config.rin.auth.audience,
                issuer: config.rin.auth.issuer
            }
        );
        
        res.json({
            status: 'success',
            accessToken: token,
            sessionId: sessionId
        });
    } catch (error) {
        console.error('Auth error:', error);
        res.status(500).json({
            status: 'error',
            message: 'Failed to authenticate'
        });
    }
});

module.exports = router; 