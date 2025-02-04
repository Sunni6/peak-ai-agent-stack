const express = require('express');
const router = express.Router();
const axios = require('axios');
const { authenticateRinToken } = require('../middleware/rinAuth');

const PYTHON_SERVICE_URL = process.env.PYTHON_SERVICE_URL || 'http://localhost:8000';

// Initialize session with Python service
router.post('/session/init', authenticateRinToken, async (req, res) => {
    try {
        const response = await axios.post(`${PYTHON_SERVICE_URL}/api/session/init`, {}, {
            headers: {
                'Authorization': req.headers.authorization,
                'X-API-Key': process.env.PYTHON_SERVICE_API_KEY
            }
        });
        res.json(response.data);
    } catch (error) {
        console.error('Session init error:', error.response?.data || error.message);
        res.status(error.response?.status || 500).json({
            status: 'error',
            message: error.response?.data?.detail || 'Failed to initialize session'
        });
    }
});

// Forward chat messages to Python service
router.post('/chat', authenticateRinToken, async (req, res) => {
    try {
        const response = await axios.post(`${PYTHON_SERVICE_URL}/api/chat`, req.body, {
            headers: {
                'X-API-Key': process.env.PYTHON_SERVICE_API_KEY
            }
        });
        res.json(response.data);
    } catch (error) {
        console.error('Chat error:', error.response?.data || error.message);
        res.status(error.response?.status || 500).json({
            status: 'error',
            message: error.response?.data?.detail || 'Chat request failed'
        });
    }
});

// Get chat history from Python service
router.get('/history/:sessionId', authenticateRinToken, async (req, res) => {
    try {
        const response = await axios.get(
            `${PYTHON_SERVICE_URL}/api/history/${req.params.sessionId}`,
            {
                headers: {
                    'Authorization': req.headers.authorization,
                    'X-API-Key': process.env.PYTHON_SERVICE_API_KEY
                }
            }
        );
        res.json(response.data);
    } catch (error) {
        console.error('History error:', error.response?.data || error.message);
        res.status(error.response?.status || 500).json({
            status: 'error',
            message: error.response?.data?.detail || 'Failed to fetch history'
        });
    }
});

module.exports = router; 