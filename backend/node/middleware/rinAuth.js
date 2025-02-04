const jwt = require('jsonwebtoken');
const config = require('../config');

const authenticateRinToken = (req, res, next) => {
    try {
        console.log('Config values:', {
            apiKey: config.rin.apiKey ? 'present' : 'missing',
            secret: config.rin.secret ? 'present' : 'missing'
        });

        // Get token from Authorization header
        const authHeader = req.headers.authorization;
        if (!authHeader || !authHeader.startsWith('Bearer ')) {
            return res.status(401).json({
                status: 'error',
                message: 'No token provided'
            });
        }

        const token = authHeader.split(' ')[1];
        
        // Verify token using the secret (not API key)
        const decoded = jwt.verify(token, config.rin.secret, {
            audience: config.rin.auth.audience,
            issuer: config.rin.auth.issuer
        });

        // Set user info from decoded token
        req.user = decoded;
        req.token = token;  // Store token for forwarding to Python service if needed
        
        next();
    } catch (error) {
        console.error('Token verification error:', error);
        return res.status(401).json({
            status: 'error',
            message: 'Invalid token'
        });
    }
};

module.exports = { authenticateRinToken };