const axios = require('axios');
const path = require('path');

// Debug environment loading
console.log('🔍 Environment Check:');
console.log('Current directory:', __dirname);
console.log('ENV file path:', path.resolve(__dirname, '../../.env'));

// Load environment
require('dotenv').config({ path: path.resolve(__dirname, '../../.env') });

// Verify loaded variables
console.log('\n📋 Environment Variables:');
console.log('RIN_CHAT_API_KEY:', process.env.RIN_CHAT_API_KEY ? '✅ Found' : '❌ Missing');
console.log('NODE_URL:', process.env.NODE_URL || 'http://localhost:3000');

// Configuration
const NODE_URL = process.env.NODE_URL || 'http://localhost:3000';
const API_BASE = `${NODE_URL}/api`;
const RIN_CHAT_API_KEY = process.env.RIN_CHAT_API_KEY;
const PYTHON_SERVICE_URL = process.env.PYTHON_SERVICE_URL || 'http://localhost:8000';
const PYTHON_API_KEY = process.env.PYTHON_API_KEY;

// Colors for console output
const colors = {
    reset: '\x1b[0m',
    bright: '\x1b[1m',
    green: '\x1b[32m',
    red: '\x1b[31m',
    yellow: '\x1b[33m',
    blue: '\x1b[34m'
};

// Helper to log with colors
const log = {
    info: (msg) => console.log(`${colors.blue}${msg}${colors.reset}`),
    success: (msg) => console.log(`${colors.green}✓ ${msg}${colors.reset}`),
    error: (msg) => console.log(`${colors.red}✗ ${msg}${colors.reset}`),
    step: (msg) => console.log(`\n${colors.bright}${msg}${colors.reset}`)
};

// Main test function
async function main() {
    let token, sessionId;

    try {
        // Step 1: Get auth token
        log.step('Step 1: Getting auth token');
        log.info(`Using API Key: ${RIN_CHAT_API_KEY.substring(0, 8)}...`);
        
        const authResponse = await axios.post(`${API_BASE}/rin/auth/token`, {
            apiKey: RIN_CHAT_API_KEY
        });
        
        // Extract accessToken from response
        token = authResponse.data.accessToken;
        if (!token) {
            throw new Error('No access token received in auth response');
        }
        log.success('Received auth token');
        log.info(`Token: ${token.substring(0, 20)}...`);

        // Step 2: Initialize session - Changed to use Node API instead of Python service directly
        log.step('Step 2: Initializing chat session');
        const sessionResponse = await axios.post(
            `${API_BASE}/rin/session/init`,  // Changed URL to use Node API
            {},
            {
                headers: { 
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            }
        );

        // Debug session response
        log.info('Session Response:', JSON.stringify(sessionResponse.data, null, 2));
        
        sessionId = sessionResponse.data.sessionId;
        if (!sessionId) {
            throw new Error('No sessionId received in session response');
        }
        log.success(`Session initialized: ${sessionId}`);
        log.info(`Welcome message: ${sessionResponse.data.message || 'No welcome message'}`);

        // Step 3: Send test messages
        log.step('Step 3: Testing chat');
        const testMessages = [
            "Hello! How are you?",
            "What can you help me with?",
            "Tell me a joke!"
        ];

        for (const message of testMessages) {
            log.info(`\nSending: "${message}"`);
            try {
                const chatPayload = {
                    sessionId: sessionId,
                    message: message
                };
                log.info('Chat request payload:', JSON.stringify(chatPayload, null, 2));

                const chatResponse = await axios.post(
                    `${API_BASE}/rin/chat`,
                    chatPayload,
                    {
                        headers: { 
                            'Authorization': `Bearer ${token}`,
                            'Content-Type': 'application/json'
                        }
                    }
                );
                
                log.info('Chat Response:', JSON.stringify(chatResponse.data, null, 2));
                
                if (chatResponse.data.status === 'success') {
                    log.success(`Response: "${chatResponse.data.response}"`);
                } else {
                    throw new Error('Chat response indicates failure');
                }
            } catch (error) {
                log.error(`Failed to send message: "${message}"`);
                if (error.response) {
                    console.error('Error response:', {
                        status: error.response.status,
                        data: error.response.data,
                        details: error.response.data?.details
                    });
                }
                throw error;
            }
        }

        // Step 4: Get chat history
        log.step('Step 4: Getting chat history');
        const historyResponse = await axios.post(
            `${API_BASE}/rin/history/${sessionId}`,
            {},
            {
                headers: { 'Authorization': `Bearer ${token}` }
            }
        );
        log.success('Retrieved chat history:');
        console.log(JSON.stringify(historyResponse.data.history, null, 2));

        log.step('All tests completed successfully! 🎉');

    } catch (error) {
        log.error('Test failed:');
        if (error.response) {
            console.error({
                status: error.response.status,
                data: error.response.data,
                endpoint: error.config.url
            });
        } else {
            console.error(error.message);
            if (error.stack) console.error(error.stack);
        }
        process.exit(1);
    }
}

// Run the script
log.step('Starting Rin Chat Test');
main().catch(console.error); 