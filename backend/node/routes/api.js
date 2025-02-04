const express = require('express');
const router = express.Router();
const RinAgentService = require('../middleware/rinAgentService');

const rinAgent = new RinAgentService();

// Frontend auth endpoint
router.post('/auth', async (req, res) => {
    try {
        const sessionId = await rinAgent.initializeSession();
        res.json({
            status: 'success',
            sessionId: sessionId,
            message: 'Konnichiwa! How can I help you today? ^_^'
        });
    } catch (error) {
        console.error('Auth error:', error);
        res.status(500).json({ 
            status: 'error', 
            message: error.message 
        });
    }
});

// Frontend chat endpoint
router.post('/chat/:sessionId', async (req, res) => {
    try {
        const { message } = req.body;
        const { sessionId } = req.params;
        
        const response = await rinAgent.sendMessage(sessionId, message);
        res.json({
            status: 'success',
            data: {
                response: response
            }
        });
    } catch (error) {
        console.error('Chat error:', error);
        res.status(500).json({ 
            status: 'error', 
            message: error.message 
        });
    }
});

// Frontend history endpoint
router.get('/history/:sessionId', async (req, res) => {
    try {
        const history = await rinAgent.getHistory(req.params.sessionId);
        res.json({
            status: 'success',
            data: history
        });
    } catch (error) {
        console.error('History error:', error);
        res.status(500).json({
            status: 'error',
            message: error.message
        });
    }
});

module.exports = router; 