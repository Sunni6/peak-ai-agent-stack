const rateLimit = require('express-rate-limit');

// Initialize endpoint-specific rate limiters at startup
const rateLimiters = {
    auth: rateLimit({
        windowMs: 5 * 60 * 1000,  // 5 minutes
        max: 20,
        message: {
            status: 'error',
            message: 'Too many auth requests, please try again later.'
        },
        standardHeaders: true,
        legacyHeaders: false,
        trustProxy: true,
        keyGenerator: (req) => {
            return req.ip || req.connection.remoteAddress || 'default';
        }
    }),
    session: rateLimit({
        windowMs: 5 * 60 * 1000,  // 5 minutes
        max: 20,
        message: {
            status: 'error',
            message: 'Too many session requests, please try again later.'
        },
        standardHeaders: true,
        legacyHeaders: false,
        trustProxy: true,
        keyGenerator: (req) => {
            return req.ip || req.connection.remoteAddress || 'default';
        }
    }),
    chat: rateLimit({
        windowMs: 60 * 1000,  // 1 minute
        max: 30,
        message: {
            status: 'error',
            message: 'Too many chat requests, please try again later.'
        },
        standardHeaders: true,
        legacyHeaders: false,
        trustProxy: true,
        keyGenerator: (req) => {
            return req.ip || req.connection.remoteAddress || 'default';
        }
    }),
    history: rateLimit({
        windowMs: 60 * 1000,  // 1 minute
        max: 30,
        message: {
            status: 'error',
            message: 'Too many history requests, please try again later.'
        },
        standardHeaders: true,
        legacyHeaders: false,
        trustProxy: true,
        keyGenerator: (req) => {
            return req.ip || req.connection.remoteAddress || 'default';
        }
    })
};

// Middleware factory function
const getRateLimiter = (endpoint) => {
    return rateLimiters[endpoint] || rateLimiters.chat; // Default to chat limiter
};

// Export both the middleware and the factory function
module.exports = { 
    getRateLimiter,
    rateLimiters 
};
