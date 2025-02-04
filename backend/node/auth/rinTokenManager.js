const jwt = require('jsonwebtoken');
const config = require('../config');
const logger = require('../utils/logger');

const validRinApiKeys = {
    [config.rin.apiKey]: 'rin-chat'
};

const generateRinToken = (apiKey) => {
    const service = validRinApiKeys[apiKey];
    if (!service) {
        logger.warn('Invalid Rin API key attempt');
        throw new Error('Invalid Rin API key');
    }
    
    const accessToken = jwt.sign(
        { 
            service,
            type: 'access',
            sessionId: require('crypto').randomUUID()
        },
        config.rin.secret,
        {
            expiresIn: config.rin.accessTokenExpiry,
            algorithm: config.rin.auth.algorithm,
            issuer: config.rin.auth.issuer,
            audience: config.rin.auth.audience
        }
    );

    logger.info('Generated Rin token', { service });
    return {
        accessToken,
        expiresIn: config.rin.accessTokenExpiry
    };
};

const verifyRinToken = (token) => {
    try {
        // First decode without verification to get service
        const decoded = jwt.decode(token);
        if (!decoded || !decoded.service) {
            logger.debug('Token decode failed:', decoded);
            return null;
        }

        // Verify token with secret
        const verified = jwt.verify(token, config.rin.secret, {
            algorithms: [config.rin.auth.algorithm],
            issuer: config.rin.auth.issuer,
            audience: config.rin.auth.audience
        });

        // Verify token type and service
        if (verified.type !== 'access' || verified.service !== 'rin-chat') {
            logger.debug('Token validation failed:', {
                type: verified.type,
                service: verified.service
            });
            return null;
        }

        return verified;
    } catch (error) {
        logger.error('Rin token verification error:', error.message);
        return null;
    }
};

module.exports = { generateRinToken, verifyRinToken };