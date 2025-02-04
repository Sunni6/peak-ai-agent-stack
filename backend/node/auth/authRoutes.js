const express = require('express');
const router = express.Router();
const { generateRinToken } = require('./rinTokenManager');
const { authenticateRinToken } = require('../middleware/rinAuth');
const { getRateLimiter } = require('../middleware/rateLimiter');

// Auth endpoint for getting Rin token
router.post('/token', getRateLimiter('auth'), (req, res) => {
    try {
        const { apiKey } = req.body;
        if (!apiKey) {
            return res.status(400).json({ error: 'API key is required' });
        }

        const token = generateRinToken(apiKey);
        res.json(token);
    } catch (error) {
        res.status(401).json({ error: error.message });
    }
});

// Chat endpoint
router.post('/chat', 
    authenticateRinToken,
    getRateLimiter('chat'),
    (req, res) => {
        // Chat logic here
        res.json({ message: 'Chat endpoint working' });
    }
);

module.exports = router;